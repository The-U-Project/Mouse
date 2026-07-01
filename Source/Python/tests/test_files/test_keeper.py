"""Tests for files.KEEPER — screen capture backend."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from files.KEEPER import (
    MonitorInfo,
    NoMonitorsError,
    ScreenCapture,
    capture_primary,
)

# ---------------------------------------------------------------------------
# Helper: build a mock mss module
# ---------------------------------------------------------------------------


def _mock_mss(monitors: list[dict], *, grab_return: np.ndarray | None = None) -> MagicMock:
    """Create a mock mss module with the given monitors and grab return value."""
    mock_module = MagicMock()
    mock_sct = MagicMock()
    mock_sct.monitors = monitors
    if grab_return is not None:
        mock_sct.grab.return_value = grab_return
    mock_module.MSS.return_value = mock_sct
    return mock_module


# ---------------------------------------------------------------------------
# MonitorInfo
# ---------------------------------------------------------------------------


class TestMonitorInfo:
    """Tests for the MonitorInfo dataclass."""

    def test_defaults(self) -> None:
        mon = MonitorInfo(index=1, left=0, top=0, width=1920, height=1080, is_primary=True)
        assert mon.index == 1
        assert mon.width == 1920
        assert mon.height == 1080
        assert mon.is_primary is True

    def test_equality(self) -> None:
        a = MonitorInfo(index=0, left=0, top=0, width=800, height=600, is_primary=False)
        b = MonitorInfo(index=0, left=0, top=0, width=800, height=600, is_primary=False)
        assert a == b


# ---------------------------------------------------------------------------
# ScreenCapture (mocked — no actual screen needed)
# ---------------------------------------------------------------------------


class TestScreenCaptureMocked:
    """Tests that don't require a real display."""

    def test_import_error_when_mss_missing(self) -> None:
        """ScreenCapture raises ImportError if mss is not installed."""
        import builtins

        _orig = builtins.__import__

        def _block_mss(name, *a, **kw):
            if name == "mss" or name.startswith("mss."):
                raise ImportError(f"No module named '{name}'")
            return _orig(name, *a, **kw)

        with patch("builtins.__import__", side_effect=_block_mss), pytest.raises(
            ImportError
        ):
            ScreenCapture()

    def test_no_monitors_raises(self) -> None:
        """ScreenCapture raises NoMonitorsError when no monitors."""
        with patch.dict(sys.modules, {"mss": _mock_mss([])}), pytest.raises(NoMonitorsError):
            ScreenCapture()

    def test_primary_monitor_selection(self) -> None:
        """get_primary_monitor returns the monitor with is_primary=True."""
        with patch.dict(
            sys.modules,
            {
                "mss": _mock_mss(
                    [
                        {"left": 0, "top": 0, "width": 3840, "height": 1080},  # virtual
                        {"left": 0, "top": 0, "width": 1920, "height": 1080},  # primary
                        {"left": 1920, "top": 0, "width": 1920, "height": 1080},  # secondary
                    ]
                )
            },
        ):
            cap = ScreenCapture()
            primary = cap.get_primary_monitor()
            assert primary.is_primary is True
            assert primary.width == 1920

    def test_capture_returns_rgb_array(self) -> None:
        """capture() returns a 3D uint8 RGB array."""
        fake_bgra = np.zeros((600, 800, 4), dtype=np.uint8)
        fake_bgra[:, :, 0] = 255  # Blue channel

        with patch.dict(
            sys.modules,
            {
                "mss": _mock_mss(
                    [
                        {"left": 0, "top": 0, "width": 1920, "height": 1080},
                        {"left": 0, "top": 0, "width": 800, "height": 600},
                    ],
                    grab_return=fake_bgra,
                )
            },
        ):
            cap = ScreenCapture()
            frame = cap.capture()
            assert isinstance(frame, np.ndarray)
            assert frame.ndim == 3
            assert frame.shape[2] == 3  # RGB
            assert frame.dtype == np.uint8
            # BGRA → RGB: B channel (255) → R channel
            assert frame[0, 0, 2] == 255  # channel 2 = Red after BGR→RGB flip

    def test_capture_to_file(self, tmp_path: Path) -> None:
        """capture_to_file saves a screenshot to disk."""
        fake_bgra = np.zeros((100, 100, 4), dtype=np.uint8)

        with patch.dict(
            sys.modules,
            {
                "mss": _mock_mss(
                    [
                        {"left": 0, "top": 0, "width": 100, "height": 100},
                        {"left": 0, "top": 0, "width": 100, "height": 100},
                    ],
                    grab_return=fake_bgra,
                )
            },
        ):
            cap = ScreenCapture()
            dest = tmp_path / "test_screenshot.png"
            result = cap.capture_to_file(dest)
            assert result == dest
            assert dest.exists()

    def test_capture_region(self) -> None:
        """capture() with a region dict captures only that area."""
        fake_bgra = np.zeros((50, 100, 4), dtype=np.uint8)
        region = {"left": 100, "top": 200, "width": 100, "height": 50}

        with patch.dict(
            sys.modules,
            {
                "mss": _mock_mss(
                    [
                        {"left": 0, "top": 0, "width": 1920, "height": 1080},
                        {"left": 0, "top": 0, "width": 1920, "height": 1080},
                    ],
                    grab_return=fake_bgra,
                )
            },
        ):
            cap = ScreenCapture()
            frame = cap.capture(region=region)
            assert frame.shape == (50, 100, 3)
            # Verify region was passed to grab
            cap._sct.grab.assert_called_once_with(region)

    def test_capture_primary_convenience(self) -> None:
        """capture_primary() returns an RGB array."""
        fake_bgra = np.zeros((100, 100, 4), dtype=np.uint8)

        with patch.dict(
            sys.modules,
            {
                "mss": _mock_mss(
                    [
                        {"left": 0, "top": 0, "width": 100, "height": 100},
                        {"left": 0, "top": 0, "width": 100, "height": 100},
                    ],
                    grab_return=fake_bgra,
                )
            },
        ):
            frame = capture_primary()
            assert frame.ndim == 3
            assert frame.shape[2] == 3

    def test_list_monitors(self) -> None:
        """list_monitors returns MonitorInfo for each real display."""
        with patch.dict(
            sys.modules,
            {
                "mss": _mock_mss(
                    [
                        {"left": 0, "top": 0, "width": 3840, "height": 1080},  # virtual (skipped)
                        {"left": 0, "top": 0, "width": 1920, "height": 1080},  # primary
                        {"left": 1920, "top": 0, "width": 1920, "height": 1080},  # secondary
                    ]
                )
            },
        ):
            cap = ScreenCapture()
            monitors = cap.list_monitors()
            assert len(monitors) == 2
            assert monitors[0].is_primary is True
            assert monitors[1].is_primary is False


# ---------------------------------------------------------------------------
# ScreenCapture — real display (integration, skipped in CI)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScreenCaptureIntegration:
    """Integration tests requiring a real display."""

    def test_capture_primary_real(self) -> None:
        """Capture the primary monitor and verify shape."""
        try:
            cap = ScreenCapture()
        except ImportError, NoMonitorsError:
            pytest.skip("No display or mss available")
        frame = cap.capture()
        assert frame.ndim == 3
        assert frame.shape[2] == 3
        assert frame.dtype == np.uint8
        assert frame.shape[0] > 0
        assert frame.shape[1] > 0

    def test_list_monitors_real(self) -> None:
        """List real monitors."""
        try:
            cap = ScreenCapture()
        except ImportError, NoMonitorsError:
            pytest.skip("No display or mss available")
        monitors = cap.list_monitors()
        assert len(monitors) >= 1
        assert any(m.is_primary for m in monitors)
