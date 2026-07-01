"""Screen Analyzer — orchestrates the full CV + AI pipeline for autonomous control.

This is the central module that:
1. Captures/streams the screen (Method 1 or Method 2)
2. Runs computer vision analysis (edge detection, contours, template matching)
3. Feeds analysis to the AI for instruction generation
4. Executes cursor actions
5. Manages method switching (auto/manual)
6. Provides interactive chat

Pipeline:
    Screen → Method Switch → CV Analysis → AI Controller → Cursor Controller
                  ↑                                                ↓
                  └────────────── Feedback Loop ───────────────────┘
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np

from modules.ai_controller import AIConfig, AIController, AIProvider, AIResponse
from modules.cursor_controller import CursorAction, CursorController
from modules.direct_analyzer import AnalysisFrame, DirectAnalyzer, ScreenRegion
from modules.method_switch import AnalysisMethod, MethodSwitch, PerformanceMetrics
from modules.stream_client import StreamClient, StreamFrame
from modules.stream_server import ScreenStreamServer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class PipelineState(Enum):
    """States of the analysis pipeline."""

    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()


@dataclass
class AnalyzerConfig:
    """Configuration for the screen analyzer pipeline.

    Attributes:
        method: Initial analysis method (DIRECT or STREAM).
        fps: Target frames per second.
        stream_port: Port for Method 1 stream server.
        enable_ai: Whether to use AI for instruction generation.
        enable_autonomy: Whether to enable autonomous mode.
        monitor_index: Monitor to capture (None = primary).
        headless: If True, suppress verbose logging.
    """

    method: AnalysisMethod = AnalysisMethod.DIRECT
    fps: int = 30
    stream_port: int = 8765
    enable_ai: bool = True
    enable_autonomy: bool = False
    monitor_index: int | None = None
    headless: bool = False


# ---------------------------------------------------------------------------
# Screen analyzer
# ---------------------------------------------------------------------------


class ScreenAnalyzer:
    """Central orchestrator for the Mouse CV + AI pipeline.

    Manages the complete pipeline from screen capture to cursor control.
    Supports both Method 1 (stream) and Method 2 (direct), with automatic
    fallback when performance degrades.

    Usage:
        >>> cfg = AnalyzerConfig(method=AnalysisMethod.DIRECT, fps=30)
        >>> sa = ScreenAnalyzer(cfg)
        >>> sa.start()
        >>> # Autonomous mode
        >>> sa.set_goal("Open the browser and search for 'weather today'")
        >>> sa.run_once()  # Process one frame
        >>> sa.run_loop()  # Continuous loop (blocking)
        >>> sa.chat("What's on my screen?")
        >>> sa.stop()
    """

    def __init__(
        self,
        config: AnalyzerConfig | None = None,
        ai_config: AIConfig | None = None,
    ) -> None:
        """Initialize the screen analyzer pipeline.

        Args:
            config: Pipeline configuration.
            ai_config: AI provider configuration (if None, reads from env).
        """
        self._config = config or AnalyzerConfig()
        self._state = PipelineState.IDLE

        # Components (initialized in start())
        self._direct_analyzer: DirectAnalyzer | None = None
        self._stream_server: ScreenStreamServer | None = None
        self._stream_client: StreamClient | None = None
        self._method_switch = MethodSwitch(initial_method=self._config.method)
        self._cursor = CursorController()
        self._ai: AIController | None = None

        if self._config.enable_ai:
            self._ai = AIController(ai_config)

        # State
        self._goal: str = ""
        self._last_frame: AnalysisFrame | None = None
        self._last_regions: list[ScreenRegion] = []
        self._action_history: list[CursorAction] = []
        self._loop_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def current_method(self) -> AnalysisMethod:
        return self._method_switch.current

    @property
    def is_running(self) -> bool:
        return self._state == PipelineState.RUNNING

    @property
    def current_fps(self) -> float:
        if self._direct_analyzer is not None:
            return self._direct_analyzer.current_fps
        return 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the screen analysis pipeline.

        Initializes the selected method and all sub-components.

        Raises:
            RuntimeError: If already running.
        """
        if self._state == PipelineState.RUNNING:
            raise RuntimeError("ScreenAnalyzer is already running.")

        logger.info("Starting ScreenAnalyzer with method=%s", self._config.method.value)

        # Initialize Method 2 (direct)
        if self._config.method in (AnalysisMethod.DIRECT, AnalysisMethod.HYBRID):
            self._direct_analyzer = DirectAnalyzer(
                fps=self._config.fps,
                monitor_index=self._config.monitor_index,
            )
            self._direct_analyzer.start()

        # Initialize Method 1 (stream) if needed
        if self._config.method == AnalysisMethod.STREAM:
            self._start_stream_method()

        # Initialize cursor controller (already done in __init__)

        self._state = PipelineState.RUNNING
        logger.info("ScreenAnalyzer started.")

    def stop(self) -> None:
        """Stop the pipeline and release all resources."""
        logger.info("Stopping ScreenAnalyzer...")
        self._stop_event.set()

        if self._direct_analyzer is not None:
            self._direct_analyzer.stop()
            self._direct_analyzer = None

        if self._stream_client is not None:
            self._stream_client.disconnect()
            self._stream_client = None

        if self._stream_server is not None:
            self._stream_server.stop()
            self._stream_server = None

        if self._loop_thread is not None and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=2.0)

        self._state = PipelineState.IDLE
        logger.info("ScreenAnalyzer stopped.")

    # ------------------------------------------------------------------
    # Method management
    # ------------------------------------------------------------------

    def switch_method(self, method: AnalysisMethod) -> None:
        """Switch the analysis method (manual override).

        Args:
            method: New method to use.
        """
        logger.info("Switching method: %s → %s", self._method_switch.current.value, method.value)

        # Stop current method components
        if method != AnalysisMethod.STREAM and self._stream_client is not None:
            self._stream_client.disconnect()
            self._stream_client = None
        if method != AnalysisMethod.STREAM and self._stream_server is not None:
            self._stream_server.stop()
            self._stream_server = None
        if method == AnalysisMethod.STREAM and self._stream_server is None:
            self._start_stream_method()

        if method in (AnalysisMethod.DIRECT, AnalysisMethod.HYBRID) and self._direct_analyzer is None:
            self._direct_analyzer = DirectAnalyzer(
                fps=self._config.fps,
                monitor_index=self._config.monitor_index,
            )
            self._direct_analyzer.start()

        self._method_switch.set_method(method)

    def set_auto_switch(self) -> None:
        """Enable automatic method switching based on performance."""
        self._method_switch.set_auto()

    def _start_stream_method(self) -> None:
        """Initialize the stream server and client for Method 1."""
        self._stream_server = ScreenStreamServer(
            port=self._config.stream_port,
            fps=self._config.fps,
        )
        self._stream_server.start()

        self._stream_client = StreamClient(port=self._config.stream_port)
        self._stream_client.connect()

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    def capture_frame(self) -> AnalysisFrame | StreamFrame:
        """Capture a single frame using the active method.

        Returns:
            AnalysisFrame (Method 2) or StreamFrame (Method 1).

        Raises:
            RuntimeError: If pipeline is not running.
        """
        if self._state != PipelineState.RUNNING:
            raise RuntimeError("ScreenAnalyzer is not running. Call start() first.")

        method = self._method_switch.current

        if method == AnalysisMethod.STREAM:
            if self._stream_client is None:
                self._start_stream_method()
            return self._stream_client.read_frame()  # type: ignore[return-value]
        else:
            if self._direct_analyzer is None:
                self._direct_analyzer = DirectAnalyzer(
                    fps=self._config.fps,
                    monitor_index=self._config.monitor_index,
                )
                self._direct_analyzer.start()
            return self._direct_analyzer.get_frame()

    def run_once(self) -> AIResponse | None:
        """Process one frame through the full pipeline.

        1. Capture frame
        2. Detect regions
        3. Feed to AI (if enabled)
        4. Execute actions
        5. Report metrics for auto-switch

        Returns:
            AIResponse with actions, or None if AI is disabled.
        """
        # Capture
        method = self._method_switch.current
        if method == AnalysisMethod.STREAM:
            sf = self.capture_frame()
            assert isinstance(sf, StreamFrame)
            frame_np = sf.frame

            # Run basic CV on the streamed frame
            import cv2

            gray = cv2.cvtColor(frame_np, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            # Detect regions from edges
            cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            regions: list[ScreenRegion] = []
            for cnt in cnts:
                area = cv2.contourArea(cnt)
                if area > 100:
                    x, y, w, h = cv2.boundingRect(cnt)
                    regions.append(ScreenRegion(label="region", x=x, y=y, w=w, h=h))

            # Report metrics
            self._method_switch.report_metrics(
                self._method_switch.get_metrics_from_stream(fps=self._config.fps)
            )
        else:
            af = self.capture_frame()
            assert isinstance(af, AnalysisFrame)
            frame_np = af.frame
            regions = self._direct_analyzer.detect_regions(af)  # type: ignore[union-attr]

            # Report metrics
            self._method_switch.report_metrics(
                PerformanceMetrics(fps=af.fps, avg_processing_ms=(1000.0 / af.fps) if af.fps > 0 else 0.0)
            )

        self._last_regions = regions

        # Auto-evaluate method switch
        switched = self._method_switch.evaluate()
        if switched is not None:
            logger.info("Method auto-switched to %s", switched.value)
            # Re-capture with new method next iteration

        # AI analysis
        ai_response: AIResponse | None = None
        if self._ai is not None and self._config.enable_ai:
            cursor_pos = self._cursor.get_position()
            ai_response = self._ai.analyze_frame(
                regions=regions,
                cursor_pos=(cursor_pos.x, cursor_pos.y),
                user_goal=self._goal,
            )

            # Execute actions
            if ai_response.actions:
                self._cursor.execute_actions(ai_response.actions)
                self._action_history.extend(ai_response.actions)

        return ai_response

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def run_loop(
        self,
        duration: float | None = None,
        on_frame: Callable[[AIResponse | None], None] | None = None,
    ) -> None:
        """Run the analysis pipeline continuously (blocking).

        Args:
            duration: Run for this many seconds; None = run until stop().
            on_frame: Optional callback invoked after each frame, receives
                the AI response (or None if AI disabled).
        """
        self._stop_event.clear()
        deadline = time.monotonic() + duration if duration else float("inf")

        logger.info("Starting analysis loop (duration=%s)", duration or "indefinite")
        frame_count = 0

        try:
            while not self._stop_event.is_set() and time.monotonic() < deadline:
                response = self.run_once()
                frame_count += 1

                if on_frame is not None:
                    on_frame(response)

                # Maintain target FPS
                period = 1.0 / self._config.fps
                time.sleep(max(0, period * 0.5))  # Rough pacing
        except KeyboardInterrupt:
            logger.info("Analysis loop interrupted by user.")
        finally:
            logger.info("Analysis loop ended. Processed %d frames.", frame_count)

    def start_loop_async(self) -> None:
        """Start the analysis loop in a background thread."""
        if self._loop_thread is not None and self._loop_thread.is_alive():
            logger.warning("Analysis loop already running.")
            return

        self._loop_thread = threading.Thread(
            target=self.run_loop,
            name="screen-analyzer-loop",
            daemon=True,
        )
        self._loop_thread.start()

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def chat(self, message: str) -> str:
        """Chat with the AI assistant, optionally with screen context.

        Args:
            message: User message.

        Returns:
            AI's response.

        Raises:
            RuntimeError: If AI is not enabled.
        """
        if self._ai is None:
            raise RuntimeError("AI is not enabled. Set enable_ai=True in AnalyzerConfig.")

        # Build screen context from last frame
        screen_context = ""
        if self._last_regions:
            descs = [f"{r.label} at ({r.x},{r.y}) {r.w}x{r.h}" for r in self._last_regions[:10]]
            screen_context = "Detected: " + "; ".join(descs)
            cursor = self._cursor.get_position()
            screen_context += f" | Cursor at ({cursor.x}, {cursor.y})"

        return self._ai.chat(message, include_screen_context=screen_context)

    # ------------------------------------------------------------------
    # Goal setting (autonomy)
    # ------------------------------------------------------------------

    def set_goal(self, goal: str) -> None:
        """Set the current autonomous goal.

        Args:
            goal: Natural language description of what to accomplish.
        """
        self._goal = goal
        logger.info("Goal set: %s", goal)

    def clear_goal(self) -> None:
        """Clear the current goal (exit autonomous mode)."""
        self._goal = ""
        logger.info("Goal cleared.")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Return a status summary of the pipeline."""
        return {
            "state": self._state.name,
            "method": self._method_switch.current.value,
            "switch_mode": self._method_switch.switch_mode.value,
            "fps": self.current_fps,
            "goal": self._goal,
            "ai_enabled": self._ai is not None,
            "stream_port": self._config.stream_port,
            "actions_executed": len(self._action_history),
            "regions_detected": len(self._last_regions),
        }

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> ScreenAnalyzer:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()
