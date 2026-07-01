"""Cursor detection and tracking for the Mouse project.

Uses OpenCV template matching to detect the mouse cursor in screen
captures, then applies EMA smoothing for stable tracking.

Detection pipeline:
    1. Screen capture (numpy RGB array from ``files.KEEPER``)
    2. Template matching against known cursor shapes
    3. Non-maximum suppression for multi-match disambiguation
    4. EMA smoothing across frames
    5. Shape-change detection (click events)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CursorDetectionError(Exception):
    """Base for all cursor detection / tracking errors."""


class NoCursorFoundError(CursorDetectionError):
    """Raised when cursor cannot be detected in a frame."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class CursorShape(Enum):
    """Known cursor shape types."""

    ARROW = auto()
    HAND = auto()
    TEXT = auto()  # I-beam
    RESIZE_HORIZONTAL = auto()
    RESIZE_VERTICAL = auto()
    RESIZE_DIAGONAL = auto()
    MOVE = auto()
    NOT_ALLOWED = auto()
    UNKNOWN = auto()


@dataclass
class CursorPosition:
    """Raw detection result for a single frame.

    Attributes:
        x: Center X coordinate in screen pixels.
        y: Center Y coordinate in screen pixels.
        confidence: Match confidence, 0.0–1.0.
        shape: Detected cursor shape.
        timestamp: Unix timestamp when the frame was captured.
    """

    x: float
    y: float
    confidence: float
    shape: CursorShape = CursorShape.UNKNOWN
    timestamp: float = field(default_factory=time.time)


@dataclass
class CursorState:
    """Smoothed cursor state across frames.

    Attributes:
        position: Current (x, y) in screen pixels.
        velocity: Per-second velocity (dx, dy) in pixels/s.
        shape: Current cursor shape.
        confidence: Detection confidence, 0.0–1.0.
        is_tracking: ``True`` when actively tracking; ``False`` when
            the cursor is lost.
        timestamp: Unix timestamp of the last update.
    """

    position: tuple[float, float] = (0.0, 0.0)
    velocity: tuple[float, float] = (0.0, 0.0)
    shape: CursorShape = CursorShape.UNKNOWN
    confidence: float = 0.0
    is_tracking: bool = False
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Cursor detector
# ---------------------------------------------------------------------------


class CursorDetector:
    """Detect the mouse cursor in a screen frame via template matching.

    Uses OpenCV's ``matchTemplate`` with normalized cross-correlation
    to find the most likely cursor location. Supports multiple cursor
    shape templates (arrow, hand, text, resize, etc.).

    Usage:
        >>> detector = CursorDetector()
        >>> pos = detector.detect(screenshot_array)
        >>> print(f"Cursor at ({pos.x:.0f}, {pos.y:.0f}), "
        ...       f"shape={pos.shape.name}, confidence={pos.confidence:.2f}")
    """

    # Typical Windows 10 cursor sizes at 100% DPI
    _CURSOR_SIZE = 32
    _MATCH_THRESHOLD = 0.5  # minimum confidence to accept a match

    def __init__(self, match_threshold: float = 0.5) -> None:
        """Initialize the detector.

        Args:
            match_threshold: Minimum normalized correlation score
                (0.0–1.0) to accept a template match. Higher values
                reduce false positives but may miss the cursor.

        Raises:
            ImportError: If ``cv2`` (OpenCV) is not installed. Install
                with: ``mamba install opencv-python``
        """
        self._match_threshold = match_threshold
        self._templates: dict[CursorShape, list[np.ndarray]] = {}
        self._last_detection: CursorPosition | None = None
        self._init_opencv()
        self._load_templates()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _init_opencv(self) -> None:
        """Verify OpenCV is importable."""
        try:
            import cv2  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "opencv-python is required for cursor detection. "
                "Install it with: mamba install opencv-python"
            ) from exc

    def _load_templates(self) -> None:
        """Generate synthetic cursor templates.

        Real cursor bitmaps vary by OS, DPI, and theme. Synthetic
        templates provide a baseline that works cross-platform.
        Users can replace these with captured cursor images for
        higher accuracy.
        """
        import cv2

        size = self._CURSOR_SIZE
        templates: dict[CursorShape, list[np.ndarray]] = {}

        # --- Arrow (default pointer) ---
        arrow = np.zeros((size, size), dtype=np.uint8)
        # Diagonal stem
        for i in range(3, size - 6):
            cv2.line(arrow, (i, 3), (i + 6, i + 6), 255, 2)
        # Vertical fill at hotspot
        arrow[3:12, 3:6] = 255
        templates[CursorShape.ARROW] = [arrow]

        # --- Hand (link hover) ---
        hand = np.zeros((size, size), dtype=np.uint8)
        # Palm rectangle
        cv2.rectangle(hand, (4, 10), (14, 26), 255, -1)
        # Index finger pointing up
        cv2.rectangle(hand, (14, 4), (19, 12), 255, -1)
        templates[CursorShape.HAND] = [hand]

        # --- Text / I-beam ---
        text = np.zeros((size, size), dtype=np.uint8)
        # Vertical I-bar
        cv2.rectangle(text, (13, 4), (18, 28), 255, -1)
        # Top and bottom crossbars
        cv2.rectangle(text, (8, 4), (23, 8), 255, -1)
        cv2.rectangle(text, (8, 24), (23, 28), 255, -1)
        templates[CursorShape.TEXT] = [text]

        # --- Resize cursors ---
        # Horizontal ↔
        horiz = np.zeros((size, size), dtype=np.uint8)
        cv2.line(horiz, (4, size // 2), (28, size // 2), 255, 2)
        cv2.line(horiz, (4, size // 2), (10, size // 2 - 4), 255, 2)
        cv2.line(horiz, (4, size // 2), (10, size // 2 + 4), 255, 2)
        cv2.line(horiz, (28, size // 2), (22, size // 2 - 4), 255, 2)
        cv2.line(horiz, (28, size // 2), (22, size // 2 + 4), 255, 2)
        templates[CursorShape.RESIZE_HORIZONTAL] = [horiz]

        # Vertical ↕
        vert = np.rot90(horiz)
        templates[CursorShape.RESIZE_VERTICAL] = [vert]

        # Diagonal ↖↘
        diag = np.zeros((size, size), dtype=np.uint8)
        cv2.line(diag, (4, 4), (28, 28), 255, 2)
        cv2.line(diag, (4, 4), (10, 4), 255, 2)
        cv2.line(diag, (4, 4), (4, 10), 255, 2)
        cv2.line(diag, (28, 28), (22, 28), 255, 2)
        cv2.line(diag, (28, 28), (28, 22), 255, 2)
        templates[CursorShape.RESIZE_DIAGONAL] = [diag]

        # --- Move (four-way arrow) ---
        move = np.zeros((size, size), dtype=np.uint8)
        mid = size // 2
        cv2.line(move, (4, mid), (28, mid), 255, 2)
        cv2.line(move, (mid, 4), (mid, 28), 255, 2)
        templates[CursorShape.MOVE] = [move]

        self._templates = templates
        logger.debug(
            "Loaded %d cursor templates (%d shapes)",
            sum(len(v) for v in templates.values()),
            len(templates),
        )

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(
        self,
        frame: np.ndarray,
        search_shape: CursorShape | None = None,
        search_region: tuple[int, int, int, int] | None = None,
    ) -> CursorPosition:
        """Detect the cursor in a screen frame.

        Args:
            frame: RGB screen capture (H×W×3, uint8).
            search_shape: If given, only match against this cursor
                shape. Otherwise, try all known shapes.
            search_region: Optional ``(x, y, w, h)`` sub-region to
                search. Speeds up detection when the cursor's rough
                location is known (e.g., from the previous frame).

        Returns:
            CursorPosition with the best match.

        Raises:
            NoCursorFoundError: If no template matches above the
                confidence threshold.
        """
        import cv2

        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        if search_region is not None:
            x, y, w, h = search_region
            # Clamp to frame bounds
            x = max(0, x)
            y = max(0, y)
            w = min(w, gray.shape[1] - x)
            h = min(h, gray.shape[0] - y)
            if w <= 0 or h <= 0:
                raise NoCursorFoundError(f"Invalid search region: {search_region}")
            gray = gray[y : y + h, x : x + w]
            offset_x, offset_y = x, y
        else:
            offset_x, offset_y = 0, 0

        best_shape = CursorShape.UNKNOWN
        best_score = -1.0
        best_loc: tuple[int, int] | None = None

        shapes_to_try = [search_shape] if search_shape is not None else list(self._templates.keys())

        for shape in shapes_to_try:
            for tmpl in self._templates.get(shape, []):
                if tmpl.shape[0] > gray.shape[0] or tmpl.shape[1] > gray.shape[1]:
                    continue  # template larger than search region

                result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val > best_score:
                    best_score = max_val
                    best_shape = shape
                    best_loc = max_loc

        if best_loc is None or best_score < self._match_threshold:
            raise NoCursorFoundError(
                f"No cursor match above threshold ({best_score:.3f} < {self._match_threshold})"
            )

        # Cursor center = template top-left + half template size
        tmpl_h, tmpl_w = self._templates[best_shape][0].shape
        cursor_x = float(offset_x + best_loc[0] + tmpl_w / 2)
        cursor_y = float(offset_y + best_loc[1] + tmpl_h / 2)

        pos = CursorPosition(
            x=cursor_x,
            y=cursor_y,
            confidence=float(best_score),
            shape=best_shape,
        )
        self._last_detection = pos
        return pos

    @property
    def match_threshold(self) -> float:
        """Current minimum confidence threshold."""
        return self._match_threshold

    @match_threshold.setter
    def match_threshold(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("match_threshold must be between 0.0 and 1.0")
        self._match_threshold = value

    @property
    def templates(self) -> dict[CursorShape, list[np.ndarray]]:
        """Registered cursor templates (read-only view)."""
        return dict(self._templates)


# ---------------------------------------------------------------------------
# Cursor tracker
# ---------------------------------------------------------------------------


class CursorTracker:
    """Track the cursor across frames with EMA smoothing.

    Applies exponential moving average to position, computes velocity,
    and detects click events from shape transitions.

    Handles tracking loss: if no detection is available for more than
    ``loss_timeout`` seconds, the tracker reports ``is_tracking=False``.

    Usage:
        >>> tracker = CursorTracker()
        >>> state = tracker.update(detected_position)
        >>> if state.is_tracking:
        ...     print(f"Cursor: {state.position}, v={state.velocity}")
    """

    # Frames to extrapolate position before reporting lost
    _LOSS_FRAMES = 5
    # Click detection: arrow → hand → arrow within this many seconds
    _CLICK_WINDOW = 0.5

    def __init__(self, smoothing_alpha: float = 0.7, loss_timeout: float = 1.0) -> None:
        """Initialize the tracker.

        Args:
            smoothing_alpha: EMA α factor (0.0–1.0). Higher = more
                responsive to new detections; lower = smoother.
            loss_timeout: Seconds before the tracker reports
                ``is_tracking=False`` after the last detection.
        """
        if not 0.0 <= smoothing_alpha <= 1.0:
            raise ValueError("smoothing_alpha must be between 0.0 and 1.0")
        self._alpha = smoothing_alpha
        self._loss_timeout = loss_timeout

        self._state = CursorState(is_tracking=False)
        self._last_detection: CursorPosition | None = None
        self._last_detection_time: float = 0.0
        self._loss_counter: int = 0
        # Click detection state machine
        self._shape_history: list[tuple[float, CursorShape]] = []  # (timestamp, shape)

    def update(self, detection: CursorPosition | None) -> CursorState:
        """Incorporate a new detection and return the smoothed state.

        Args:
            detection: A CursorPosition from ``CursorDetector.detect()``,
                or ``None`` if no cursor was found in this frame.

        Returns:
            Updated ``CursorState`` with smoothed position, velocity,
            and tracking status.
        """
        now = time.time()

        if detection is not None:
            self._loss_counter = 0
            prev_x, prev_y = self._state.position
            prev_time = self._state.timestamp if self._state.is_tracking else now

            # EMA smoothing
            alpha = self._alpha
            smooth_x = alpha * detection.x + (1 - alpha) * prev_x
            smooth_y = alpha * detection.y + (1 - alpha) * prev_y

            # Velocity (pixels per second)
            dt = now - prev_time
            if dt > 1e-6 and self._state.is_tracking:
                vx = (smooth_x - prev_x) / dt
                vy = (smooth_y - prev_y) / dt
            else:
                vx, vy = 0.0, 0.0

            self._state = CursorState(
                position=(smooth_x, smooth_y),
                velocity=(vx, vy),
                shape=detection.shape,
                confidence=detection.confidence,
                is_tracking=True,
                timestamp=now,
            )
            self._last_detection = detection
            self._last_detection_time = now

            # Track shape history for click detection
            self._shape_history.append((now, detection.shape))
            self._prune_shape_history()

        else:
            # No detection — predict position or report lost
            self._loss_counter += 1
            if self._loss_counter <= self._LOSS_FRAMES and self._state.is_tracking:
                # Extrapolate using current velocity
                dt_predict = now - self._state.timestamp
                px = self._state.position[0] + self._state.velocity[0] * dt_predict
                py = self._state.position[1] + self._state.velocity[1] * dt_predict
                self._state = CursorState(
                    position=(px, py),
                    velocity=self._state.velocity,
                    shape=self._state.shape,
                    confidence=max(0.0, self._state.confidence - 0.2),
                    is_tracking=True,
                    timestamp=now,
                )
            elif now - self._last_detection_time > self._loss_timeout:
                self._state.is_tracking = False

        return self._state

    def detect_click(self) -> bool:
        """Check if a click event was detected from cursor shape changes.

        A click is detected when the cursor transitions:
        ``ARROW → HAND → ARROW`` within ``_CLICK_WINDOW`` seconds.
        This captures the typical "hover then click" pattern.

        Returns:
            ``True`` if a click was detected in the recent history.
            Calling this method consumes the detection (idempotent for
            the same shape pattern).
        """
        self._prune_shape_history()
        if len(self._shape_history) < 3:
            return False

        # Look for ARROW → HAND → ARROW pattern
        for i in range(len(self._shape_history) - 2):
            t0, s0 = self._shape_history[i]
            t1, s1 = self._shape_history[i + 1]
            t2, s2 = self._shape_history[i + 2]
            if (
                s0 == CursorShape.ARROW
                and s1 == CursorShape.HAND
                and s2 == CursorShape.ARROW
                and (t2 - t0) <= self._CLICK_WINDOW
            ):
                # Consume this pattern
                self._shape_history = self._shape_history[i + 3 :]
                return True
        return False

    def _prune_shape_history(self) -> None:
        """Remove entries older than ``_CLICK_WINDOW``."""
        cutoff = time.time() - self._CLICK_WINDOW * 2
        self._shape_history = [(t, s) for t, s in self._shape_history if t >= cutoff]

    def reset(self) -> None:
        """Reset tracker state. Call when switching capture targets."""
        self._state = CursorState(is_tracking=False)
        self._last_detection = None
        self._last_detection_time = 0.0
        self._loss_counter = 0
        self._shape_history.clear()

    @property
    def state(self) -> CursorState:
        """Current smoothed cursor state (read-only)."""
        return self._state

    @property
    def smoothing_alpha(self) -> float:
        """EMA smoothing factor."""
        return self._alpha
