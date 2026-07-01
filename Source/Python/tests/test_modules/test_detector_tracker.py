"""Tests for modules.KEEPER — cursor detection and tracking."""

from __future__ import annotations

import time
from unittest.mock import patch

import numpy as np
import pytest

from modules.KEEPER import (
    CursorDetector,
    CursorPosition,
    CursorShape,
    CursorState,
    CursorTracker,
    NoCursorFoundError,
)

# ---------------------------------------------------------------------------
# CursorPosition / CursorState
# ---------------------------------------------------------------------------


class TestCursorPosition:
    """Tests for the CursorPosition dataclass."""

    def test_defaults(self) -> None:
        pos = CursorPosition(x=100.0, y=200.0, confidence=0.85, shape=CursorShape.ARROW)
        assert pos.x == 100.0
        assert pos.y == 200.0
        assert pos.confidence == 0.85
        assert pos.shape == CursorShape.ARROW
        assert pos.timestamp > 0

    def test_timestamp_custom(self) -> None:
        pos = CursorPosition(x=0.0, y=0.0, confidence=0.5, timestamp=1234567890.0)
        assert pos.timestamp == 1234567890.0


class TestCursorState:
    """Tests for the CursorState dataclass."""

    def test_defaults(self) -> None:
        state = CursorState()
        assert state.position == (0.0, 0.0)
        assert state.velocity == (0.0, 0.0)
        assert state.shape == CursorShape.UNKNOWN
        assert state.confidence == 0.0
        assert state.is_tracking is False

    def test_custom(self) -> None:
        state = CursorState(position=(100.0, 200.0), velocity=(5.0, -3.0), is_tracking=True)
        assert state.position == (100.0, 200.0)
        assert state.velocity == (5.0, -3.0)
        assert state.is_tracking is True


# ---------------------------------------------------------------------------
# CursorDetector
# ---------------------------------------------------------------------------


class TestCursorDetector:
    """Tests for the CursorDetector class."""

    def test_init_loads_templates(self) -> None:
        """Detector initializes with synthetic templates for all shapes."""
        detector = CursorDetector()
        assert len(detector.templates) >= 6  # arrow, hand, text, 3 resize, move
        assert CursorShape.ARROW in detector.templates
        for shape in detector.templates:
            for tmpl in detector.templates[shape]:
                assert tmpl.ndim == 2
                assert tmpl.dtype == np.uint8

    def test_detect_arrow_on_blank_frame(self) -> None:
        """Detect a synthetic arrow drawn on a blank frame."""
        detector = CursorDetector(match_threshold=0.15)
        # Create blank frame with a bold arrow-like pattern
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        # Draw a thick white diagonal line (arrow stem)
        for i in range(16):
            for j in range(-2, 3):
                y, x = 50 + i, 50 + i + j
                if 0 <= y < 200 and 0 <= x < 200:
                    frame[y, x] = [255, 255, 255]
        # Fill a larger block at the tip (arrow head)
        frame[48:58, 48:54] = [255, 255, 255]

        # Specify ARROW shape to disambiguate from diagonal resize cursor
        pos = detector.detect(frame, search_shape=CursorShape.ARROW)
        assert pos.confidence > 0.15
        assert 40 < pos.x < 80
        assert 40 < pos.y < 80
        assert pos.shape == CursorShape.ARROW

    def test_detect_no_cursor_raises(self) -> None:
        """Detection on pure noise raises NoCursorFoundError."""
        detector = CursorDetector(match_threshold=0.8)
        noise = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
        with pytest.raises(NoCursorFoundError):
            detector.detect(noise)

    def test_detect_with_search_region(self) -> None:
        """Search region speeds up detection and constrains results."""
        detector = CursorDetector(match_threshold=0.3)
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        # Arrow at (150, 150)
        for i in range(10):
            frame[150 + i, 150 + i] = [255, 255, 255]
        frame[150:156, 150:153] = [255, 255, 255]

        # Search only a region around (140, 140) to (180, 180)
        pos = detector.detect(frame, search_region=(130, 130, 60, 60))
        assert 140 < pos.x < 180
        assert 140 < pos.y < 180

    def test_detect_specific_shape(self) -> None:
        """Searching for a specific shape only matches that shape."""
        detector = CursorDetector(match_threshold=0.4)
        # Create a hand-like pattern
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        # Draw a rectangle (palm) + finger
        frame[80:96, 74:84] = [255, 255, 255]  # palm
        frame[74:82, 84:89] = [255, 255, 255]  # index finger

        pos = detector.detect(frame, search_shape=CursorShape.HAND)
        assert pos.shape == CursorShape.HAND
        assert pos.confidence > 0.4

    def test_match_threshold_setter(self) -> None:
        """Can adjust match threshold after init."""
        detector = CursorDetector()
        detector.match_threshold = 0.9
        assert detector.match_threshold == 0.9
        with pytest.raises(ValueError):
            detector.match_threshold = 1.5
        with pytest.raises(ValueError):
            detector.match_threshold = -0.1


# ---------------------------------------------------------------------------
# CursorTracker
# ---------------------------------------------------------------------------


class TestCursorTracker:
    """Tests for the CursorTracker class."""

    def test_initial_state_not_tracking(self) -> None:
        tracker = CursorTracker()
        assert tracker.state.is_tracking is False
        assert tracker.state.position == (0.0, 0.0)

    def test_update_with_detection(self) -> None:
        """First update with alpha=1.0 sets position immediately (no smoothing)."""
        tracker = CursorTracker(smoothing_alpha=1.0)
        det = CursorPosition(x=100.0, y=200.0, confidence=0.9, shape=CursorShape.ARROW)
        state = tracker.update(det)
        assert state.is_tracking is True
        assert state.position == (100.0, 200.0)
        assert state.velocity == (0.0, 0.0)  # No velocity on first frame

    def test_ema_smoothing(self) -> None:
        """Position is smoothed via exponential moving average."""
        tracker = CursorTracker(smoothing_alpha=0.5)
        # First frame
        tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))
        # Second frame jumps to (100, 0)
        state = tracker.update(
            CursorPosition(x=100.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW)
        )
        # alpha=0.5 → smoothed = 0.5*100 + 0.5*0 = 50
        assert state.position[0] == pytest.approx(50.0, abs=0.1)
        assert state.position[1] == 0.0

    def test_velocity_computation(self) -> None:
        """Velocity is computed from frame-to-frame deltas."""
        tracker = CursorTracker(smoothing_alpha=1.0)  # no smoothing
        t0 = time.time()
        # 4 calls: update now + _prune_shape_history each
        with patch("time.time", side_effect=[t0, t0, t0 + 0.1, t0 + 0.1]):
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))
            state = tracker.update(
                CursorPosition(x=10.0, y=5.0, confidence=1.0, shape=CursorShape.ARROW)
            )
            assert state.velocity[0] == pytest.approx(100.0, abs=5.0)  # 10px / 0.1s
            assert state.velocity[1] == pytest.approx(50.0, abs=5.0)

    def test_tracking_loss(self) -> None:
        """Tracker reports is_tracking=False after loss_timeout + LOSS_FRAMES."""
        tracker = CursorTracker(loss_timeout=0.05)
        tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))

        t0 = time.time()
        # First _LOSS_FRAMES=5 None updates go to prediction;
        # the 6th None (beyond loss_timeout) triggers loss
        with patch("time.time", return_value=t0 + 0.1):
            for _ in range(6):
                state = tracker.update(None)
            # After _LOSS_FRAMES exhausted + timeout, should be lost
            assert state.is_tracking is False

    def test_position_prediction_during_loss(self) -> None:
        """During brief loss, position is predicted from velocity."""
        tracker = CursorTracker(smoothing_alpha=1.0)
        t0 = time.time()
        with patch("time.time", side_effect=[t0, t0, t0 + 0.1, t0 + 0.1]):
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))
            tracker.update(CursorPosition(x=10.0, y=5.0, confidence=1.0, shape=CursorShape.ARROW))

        # Next frame: no detection, predict from (10, 5) with v=(100, 50)
        with patch("time.time", return_value=t0 + 0.2):
            state = tracker.update(None)
            # Predicted: 10 + 100*0.1 = 20, 5 + 50*0.1 = 10
            assert state.is_tracking is True  # still predicting
            assert state.position[0] == pytest.approx(20.0, abs=1.0)

    def test_click_detection(self) -> None:
        """ARROW → HAND → ARROW within window = click."""
        tracker = CursorTracker()
        t0 = time.time()
        # 3 updates × 2 time calls each = 6, + detect_click's _prune = 7
        ticks = [t0] * 2 + [t0 + 0.05] * 2 + [t0 + 0.10] * 3
        with patch("time.time", side_effect=ticks):
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.HAND))
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))
        assert tracker.detect_click() is True

    def test_no_click_without_hand(self) -> None:
        """ARROW → ARROW → ARROW is not a click."""
        tracker = CursorTracker()
        for _ in range(3):
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))
        assert tracker.detect_click() is False

    def test_click_consumed_once(self) -> None:
        """detect_click consumes the event; second call returns False."""
        tracker = CursorTracker()
        t0 = time.time()
        # 3 updates × 2 each = 6, + 2 detect_click = 8
        ticks = [t0] * 2 + [t0 + 0.05] * 2 + [t0 + 0.10] * 4
        with patch("time.time", side_effect=ticks):
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.HAND))
            tracker.update(CursorPosition(x=0.0, y=0.0, confidence=1.0, shape=CursorShape.ARROW))
        assert tracker.detect_click() is True
        assert tracker.detect_click() is False  # consumed

    def test_reset(self) -> None:
        """reset clears all state."""
        tracker = CursorTracker()
        tracker.update(CursorPosition(x=100.0, y=200.0, confidence=1.0, shape=CursorShape.ARROW))
        tracker.reset()
        assert tracker.state.is_tracking is False
        assert tracker.state.position == (0.0, 0.0)

    def test_alpha_bounds(self) -> None:
        """smoothing_alpha must be in [0, 1]."""
        with pytest.raises(ValueError):
            CursorTracker(smoothing_alpha=1.5)
        with pytest.raises(ValueError):
            CursorTracker(smoothing_alpha=-0.1)


# ---------------------------------------------------------------------------
# CursorShape
# ---------------------------------------------------------------------------


class TestCursorShape:
    """Enum sanity checks."""

    def test_all_shapes_distinct(self) -> None:
        values = [s.value for s in CursorShape]
        assert len(values) == len(set(values))

    def test_unknown_is_last(self) -> None:
        assert CursorShape.UNKNOWN.value == max(s.value for s in CursorShape)
