"""Method 2: Direct real-time screen analyzer — captures and processes in-process.

This module captures the screen directly using ``files.KEEPER.ScreenCapture``
and runs OpenCV analysis on each frame without streaming overhead. Lower
latency than Method 1 but uses more CPU in the same process.

This is the **default method** for screen analysis.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class AnalysisFrame:
    """A single frame with pre-computed analysis data.

    Attributes:
        frame: Raw RGB screen capture (H×W×3, uint8).
        gray: Grayscale conversion (H×W, uint8).
        edges: Canny edge detection result (H×W, uint8).
        timestamp: Unix timestamp of capture.
        fps: Current effective frames per second.
        contours: Detected contours, if contour detection is enabled.
        keypoints: Detected ORB/SIFT keypoints, if feature detection is enabled.
    """

    frame: np.ndarray
    gray: np.ndarray
    edges: np.ndarray
    timestamp: float = field(default_factory=time.time)
    fps: float = 0.0
    contours: list[np.ndarray] = field(default_factory=list)
    keypoints: list[Any] = field(default_factory=list)


@dataclass
class ScreenRegion:
    """A labeled region of interest on the screen.

    Attributes:
        label: Human-readable label (e.g., "button", "text_field").
        x: Left coordinate.
        y: Top coordinate.
        w: Width in pixels.
        h: Height in pixels.
        confidence: Detection confidence 0.0–1.0.
        text: OCR text if applicable.
    """

    label: str
    x: int
    y: int
    w: int
    h: int
    confidence: float = 0.0
    text: str = ""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DirectAnalyzerError(Exception):
    """Base for direct analyzer errors."""


class CaptureFailedError(DirectAnalyzerError):
    """Raised when screen capture fails repeatedly."""


# ---------------------------------------------------------------------------
# Direct Analyzer
# ---------------------------------------------------------------------------


class DirectAnalyzer:
    """Capture and analyze screen frames directly in-process (Method 2).

    Performs real-time computer vision operations:
    - Grayscale conversion
    - Edge detection (Canny)
    - Contour detection
    - Feature/keypoint detection (ORB)
    - Template matching (using ``modules.KEEPER.CursorDetector``)

    Usage:
        >>> analyzer = DirectAnalyzer(fps=30)
        >>> analyzer.start()
        >>> frame = analyzer.get_frame()
        >>> regions = analyzer.detect_regions(frame)
        >>> analyzer.stop()
    """

    _DEFAULT_FPS = 30

    def __init__(
        self,
        fps: int = _DEFAULT_FPS,
        monitor_index: int | None = None,
        enable_contours: bool = True,
        enable_features: bool = False,
        edge_low: int = 50,
        edge_high: int = 150,
    ) -> None:
        """Initialize the direct analyzer.

        Args:
            fps: Target frames per second.
            monitor_index: Monitor to capture; None = primary.
            enable_contours: Whether to run contour detection (useful for
                UI element detection).
            enable_features: Whether to run ORB feature detection (useful
                for scene matching; heavier).
            edge_low: Canny edge detection lower threshold.
            edge_high: Canny edge detection upper threshold.
        """
        self._fps = fps
        self._monitor_index = monitor_index
        self._enable_contours = enable_contours
        self._enable_features = enable_features
        self._edge_low = edge_low
        self._edge_high = edge_high

        self._capturing = False
        self._cap: Any = None  # ScreenCapture instance
        self._orb: Any = None  # ORB detector (lazy init)
        self._fps_history: list[float] = []
        self._frame_count = 0
        self._last_time = 0.0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._capturing

    @property
    def current_fps(self) -> float:
        """Effective FPS averaged over recent frames."""
        if not self._fps_history:
            return 0.0
        return sum(self._fps_history[-10:]) / min(len(self._fps_history), 10)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin screen capture and analysis.

        Raises:
            ImportError: If OpenCV is not installed.
            CaptureFailedError: If the screen capture backend fails.
        """
        import cv2  # noqa: F401 — validate OpenCV

        from files.KEEPER import ScreenCapture

        self._cap = ScreenCapture()
        self._capturing = True
        self._last_time = time.perf_counter()
        logger.info("DirectAnalyzer started (fps=%d)", self._fps)

    def stop(self) -> None:
        """Stop capture and release resources."""
        self._capturing = False
        self._cap = None
        self._orb = None
        logger.info("DirectAnalyzer stopped.")

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    def get_frame(self) -> AnalysisFrame:
        """Capture and analyze a single frame.

        Returns:
            AnalysisFrame with raw image + pre-computed analysis data.

        Raises:
            CaptureFailedError: If the capture fails.
            RuntimeError: If the analyzer has not been started.
        """
        if not self._capturing or self._cap is None:
            raise RuntimeError("DirectAnalyzer has not been started. Call start() first.")

        import cv2

        from files.KEEPER import ScreenCaptureError

        try:
            frame_rgb = self._cap.capture(monitor_index=self._monitor_index)
        except ScreenCaptureError as exc:
            raise CaptureFailedError(f"Screen capture failed: {exc}") from exc

        # Timings
        now = time.perf_counter()
        elapsed = now - self._last_time
        self._fps_history.append(1.0 / elapsed if elapsed > 0 else 0.0)
        self._last_time = now
        self._frame_count += 1

        # Grayscale
        gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

        # Edge detection
        edges = cv2.Canny(gray, self._edge_low, self._edge_high)

        # Contours
        contours: list[np.ndarray] = []
        if self._enable_contours:
            cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = list(cnts)

        # Feature keypoints
        keypoints: list[Any] = []
        if self._enable_features:
            if self._orb is None:
                self._orb = cv2.ORB_create(nfeatures=500)
            kps = self._orb.detect(gray, None)
            keypoints = list(kps)

        return AnalysisFrame(
            frame=frame_rgb,
            gray=gray,
            edges=edges,
            timestamp=time.time(),
            fps=self.current_fps,
            contours=contours,
            keypoints=keypoints,
        )

    def get_frame_raw(self) -> np.ndarray:
        """Capture only the raw RGB frame (no analysis). Fast path."""
        if not self._capturing or self._cap is None:
            raise RuntimeError("DirectAnalyzer has not been started. Call start() first.")

        from files.KEEPER import ScreenCaptureError

        try:
            return self._cap.capture(monitor_index=self._monitor_index)
        except ScreenCaptureError as exc:
            raise CaptureFailedError(f"Screen capture failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Region detection
    # ------------------------------------------------------------------

    def detect_regions(
        self,
        frame: AnalysisFrame | None = None,
        min_area: int = 100,
    ) -> list[ScreenRegion]:
        """Detect UI regions (buttons, text fields, etc.) from contours.

        Args:
            frame: Pre-analyzed frame; if None, captures a new one.
            min_area: Minimum contour area (in pixels²) to consider.

        Returns:
            List of ScreenRegion objects describing detected UI elements.
        """
        if frame is None:
            frame = self.get_frame()

        regions: list[ScreenRegion] = []
        for cnt in frame.contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            regions.append(
                ScreenRegion(
                    label="region",
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    confidence=min(area / 10000.0, 1.0),
                )
            )

        return regions

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> DirectAnalyzer:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


# Lazy import for cv2 to avoid import error at module level
import cv2  # noqa: E402
