"""Method switching system — chooses between Method 1 (stream) and Method 2 (direct).

Allows automatic fallback based on performance metrics (FPS, latency) and
manual override by the user. Method 2 (direct) is the default.

Switch logic:
    1. Default: Method 2 (direct in-process capture)
    2. Auto-switch to Method 1 if:
       - FPS drops below threshold for N consecutive frames
       - Memory pressure detected
       - GPU/CPU usage exceeds threshold
    3. Manual override always takes precedence
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class AnalysisMethod(enum.Enum):
    """Available screen analysis methods."""

    DIRECT = "direct"  # Method 2: In-process capture + analysis
    STREAM = "stream"  # Method 1: Stream to port, read via OpenCV
    HYBRID = "hybrid"  # Use C++/CUDA backend for heavy lifting


class SwitchMode(enum.Enum):
    """How method switching is controlled."""

    AUTO = "auto"  # Automatic based on performance metrics
    MANUAL = "manual"  # User explicitly sets the method


@dataclass
class PerformanceMetrics:
    """Real-time performance data used for switching decisions.

    Attributes:
        fps: Current effective frames per second.
        avg_processing_ms: Average time to process one frame in ms.
        dropped_frames: Number of frames dropped recently.
        memory_mb: Current memory usage in MB (estimate).
        timestamp: When these metrics were recorded.
    """

    fps: float = 0.0
    avg_processing_ms: float = 0.0
    dropped_frames: int = 0
    memory_mb: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class MethodSwitchError(Exception):
    """Base for method switching errors."""


class MethodUnavailableError(MethodSwitchError):
    """Raised when the requested method cannot be activated."""


# ---------------------------------------------------------------------------
# Method switch
# ---------------------------------------------------------------------------


class MethodSwitch:
    """Manages switching between screen analysis methods.

    Default: Method 2 (DIRECT). Automatically falls back to Method 1
    (STREAM) or Method 3 (HYBRID) when performance degrades.

    Usage:
        >>> switch = MethodSwitch()
        >>> print(switch.current)  # AnalysisMethod.DIRECT
        >>> # Process frames...
        >>> switch.report_metrics(MethodSwitch.get_metrics(direct_analyzer))
        >>> # Auto-switch if needed
        >>> switch.evaluate()

        >>> # Manual override
        >>> switch.set_method(AnalysisMethod.STREAM)
    """

    # Performance thresholds for auto-switching
    _FPS_FALLBACK_THRESHOLD = 10.0  # FPS below this → consider switching
    _FPS_CRITICAL_THRESHOLD = 5.0  # FPS below this → switch immediately
    _PROCESSING_MS_THRESHOLD = 100.0  # ms per frame → too slow
    _CONSECUTIVE_BAD_FRAMES = 8  # Number of bad frames before switching
    _METRICS_HISTORY_SIZE = 64  # Rolling window for metrics

    def __init__(self, initial_method: AnalysisMethod = AnalysisMethod.DIRECT) -> None:
        """Initialize the method switch.

        Args:
            initial_method: Starting analysis method (default: DIRECT).
        """
        self._current = initial_method
        self._switch_mode = SwitchMode.AUTO
        self._manual_target: AnalysisMethod | None = None

        # Rolling metric history
        self._metrics: deque[PerformanceMetrics] = deque(maxlen=self._METRICS_HISTORY_SIZE)
        self._consecutive_bad = 0

        # Used to detect if a method is unavailable
        self._available_methods: set[AnalysisMethod] = {
            AnalysisMethod.DIRECT,
            AnalysisMethod.STREAM,
        }

        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current(self) -> AnalysisMethod:
        return self._current

    @property
    def switch_mode(self) -> SwitchMode:
        return self._switch_mode

    @property
    def is_auto(self) -> bool:
        return self._switch_mode == SwitchMode.AUTO

    @property
    def latest_metrics(self) -> PerformanceMetrics | None:
        if not self._metrics:
            return None
        return self._metrics[-1]

    # ------------------------------------------------------------------
    # Manual control
    # ------------------------------------------------------------------

    def set_method(self, method: AnalysisMethod) -> None:
        """Manually set the analysis method. Switches to MANUAL mode.

        Args:
            method: The method to use.

        Raises:
            MethodUnavailableError: If the method is not available
                (e.g., STREAM when no stream server is running).
        """
        if method not in self._available_methods:
            raise MethodUnavailableError(
                f"Method {method.value} is not currently available."
            )

        with self._lock:
            self._switch_mode = SwitchMode.MANUAL
            self._manual_target = method
            self._current = method
            self._consecutive_bad = 0
            logger.info("Method manually set to %s", method.value)

    def set_auto(self) -> None:
        """Switch back to automatic mode."""
        with self._lock:
            self._switch_mode = SwitchMode.AUTO
            self._manual_target = None
            logger.info("Method switch set to AUTO mode")

    def mark_method_unavailable(self, method: AnalysisMethod) -> None:
        """Report that a method is unavailable (e.g., stream server stopped)."""
        self._available_methods.discard(method)
        logger.warning("Method %s marked as unavailable", method.value)

    def mark_method_available(self, method: AnalysisMethod) -> None:
        """Report that a method is now available."""
        self._available_methods.add(method)
        logger.info("Method %s marked as available", method.value)

    # ------------------------------------------------------------------
    # Performance reporting
    # ------------------------------------------------------------------

    def report_metrics(self, metrics: PerformanceMetrics) -> None:
        """Submit performance metrics from the active method.

        Call this once per frame (or every N frames) from the analysis
        loop. The switcher uses these to decide when to fall back.

        Args:
            metrics: Current performance snapshot.
        """
        self._metrics.append(metrics)

    @staticmethod
    def get_metrics_from_direct(analyzer: Any) -> PerformanceMetrics:
        """Extract metrics from a ``DirectAnalyzer`` instance.

        Args:
            analyzer: A ``DirectAnalyzer`` that is currently running.

        Returns:
            PerformanceMetrics populated from the analyzer's state.
        """
        return PerformanceMetrics(
            fps=analyzer.current_fps,
            avg_processing_ms=(1000.0 / analyzer.current_fps) if analyzer.current_fps > 0 else 0.0,
        )

    @staticmethod
    def get_metrics_from_stream(
        fps: float = 0.0, processing_ms: float = 0.0
    ) -> PerformanceMetrics:
        """Create metrics for the stream method.

        Args:
            fps: Effective FPS from the stream.
            processing_ms: Average processing time per frame.

        Returns:
            A populated PerformanceMetrics.
        """
        return PerformanceMetrics(
            fps=fps,
            avg_processing_ms=processing_ms,
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self) -> AnalysisMethod | None:
        """Evaluate metrics and potentially switch methods.

        Returns:
            The new method if a switch occurred, or None if no change.

        Only acts in AUTO mode. In MANUAL mode, the user's choice
        is always respected.
        """
        if self._switch_mode == SwitchMode.MANUAL:
            return None

        if not self._metrics:
            return None

        latest = self._metrics[-1]
        old_method = self._current

        # Check for critical condition → switch immediately
        if latest.fps < self._FPS_CRITICAL_THRESHOLD and latest.fps > 0:
            self._consecutive_bad += 1
            if self._consecutive_bad >= 3:
                return self._attempt_switch()
        elif latest.fps < self._FPS_FALLBACK_THRESHOLD and latest.fps > 0:
            self._consecutive_bad += 1
            if self._consecutive_bad >= self._CONSECUTIVE_BAD_FRAMES:
                return self._attempt_switch()
        elif latest.avg_processing_ms > self._PROCESSING_MS_THRESHOLD:
            self._consecutive_bad += 1
            if self._consecutive_bad >= self._CONSECUTIVE_BAD_FRAMES:
                return self._attempt_switch()
        else:
            # Performance recovered → reset counter
            if self._consecutive_bad > 0:
                self._consecutive_bad = max(0, self._consecutive_bad - 1)

            # If we fell back to STREAM and performance is fine, consider
            # returning to DIRECT (the preferred default)
            if self._current != AnalysisMethod.DIRECT:
                stable_frames = sum(
                    1 for m in list(self._metrics)[-self._CONSECUTIVE_BAD_FRAMES:]
                    if m.fps >= self._FPS_FALLBACK_THRESHOLD
                )
                if stable_frames >= self._CONSECUTIVE_BAD_FRAMES:
                    with self._lock:
                        self._current = AnalysisMethod.DIRECT
                        self._consecutive_bad = 0
                    logger.info("Auto-switched back to DIRECT (recovered)")
                    return AnalysisMethod.DIRECT

        return None

    def _attempt_switch(self) -> AnalysisMethod | None:
        """Try to switch to an alternative method.

        Priority: DIRECT → STREAM → HYBRID (fallback chain).
        """
        with self._lock:
            if self._current == AnalysisMethod.DIRECT:
                # Fall back to stream
                if AnalysisMethod.STREAM in self._available_methods:
                    self._current = AnalysisMethod.STREAM
                    self._consecutive_bad = 0
                    logger.info("Auto-switched to STREAM (FPS/performance degraded)")
                    return AnalysisMethod.STREAM
            elif self._current == AnalysisMethod.STREAM:
                # Fall back to hybrid (C++/CUDA)
                if AnalysisMethod.HYBRID in self._available_methods:
                    self._current = AnalysisMethod.HYBRID
                    self._consecutive_bad = 0
                    logger.info("Auto-switched to HYBRID (C++/CUDA backend)")
                    return AnalysisMethod.HYBRID

        logger.warning("No better method available; staying on %s", self._current.value)
        return None

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a summary of the current switching state."""
        return {
            "current_method": self._current.value,
            "mode": self._switch_mode.value,
            "available_methods": [m.value for m in self._available_methods],
            "consecutive_bad_frames": self._consecutive_bad,
            "latest_fps": self._metrics[-1].fps if self._metrics else None,
        }
