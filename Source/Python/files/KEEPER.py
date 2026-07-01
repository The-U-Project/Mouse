"""Screen capture backend for the Mouse project.

Provides cross-platform screen capture via `mss`, returning frames as
numpy arrays suitable for computer vision processing.

Supports:
- Windows: DXGI Desktop Duplication (via mss)
- macOS: CoreGraphics (via mss)
- Linux: X11/XCB (via mss)

All captures return H×W×RGB uint8 numpy arrays.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MonitorInfo:
    """Metadata about a detected display monitor."""

    index: int
    left: int
    top: int
    width: int
    height: int
    is_primary: bool


class ScreenCaptureError(Exception):
    """Raised when screen capture fails."""


class NoMonitorsError(ScreenCaptureError):
    """Raised when no monitors are detected."""


class ScreenCapture:
    """Cross-platform screen capture using the `mss` library.

    Captures screenshots as numpy arrays (H×W×RGB, uint8). Handles
    multi-monitor setups and provides both in-memory and file-based
    capture methods.

    Usage:
        >>> cap = ScreenCapture()
        >>> frame = cap.capture()  # captures primary monitor
        >>> assert frame.ndim == 3 and frame.shape[2] == 3

        >>> cap.capture_to_file("screenshot.png")
        >>> for mon in cap.list_monitors():
        ...     print(f"Monitor {mon.index}: {mon.width}x{mon.height}")
    """

    def __init__(self) -> None:
        """Initialize the screen capture backend.

        Raises:
            ImportError: If `mss` is not installed. Install with:
                mamba install python-mss
        """
        self._sct: object | None = None
        self._monitors: list[MonitorInfo] = []
        self._init_backend()

    def _init_backend(self) -> None:
        """Lazy-import mss and enumerate monitors."""
        try:
            import mss
        except ImportError as exc:
            raise ImportError(
                "mss is required for screen capture. Install it with: mamba install python-mss"
            ) from exc

        self._sct = mss.MSS()
        self._refresh_monitors()

    def _refresh_monitors(self) -> None:
        """Re-scan available monitors."""

        monitors: list[MonitorInfo] = []
        raw = self._sct.monitors  # type: ignore[union-attr]
        # mss monitor 0 is the "all monitors" virtual display
        for i, region in enumerate(raw):
            if i == 0 and len(raw) > 1:
                # Skip virtual "all monitors" region when real monitors exist
                continue
            monitors.append(
                MonitorInfo(
                    index=i,
                    left=region["left"],
                    top=region["top"],
                    width=region["width"],
                    height=region["height"],
                    is_primary=(i == 1),  # mss: monitor 1 is primary
                )
            )

        if not monitors:
            raise NoMonitorsError("No monitors detected.")

        self._monitors = monitors

    def list_monitors(self) -> list[MonitorInfo]:
        """Return metadata for all detected monitors.

        Returns:
            List of MonitorInfo, one per display. Monitor 1 is
            typically the primary display on mss.

        Raises:
            NoMonitorsError: If no monitors are detected.
        """
        self._refresh_monitors()
        return list(self._monitors)

    def get_primary_monitor(self) -> MonitorInfo:
        """Return the primary monitor.

        Returns:
            MonitorInfo for the primary display.

        Raises:
            NoMonitorsError: If no primary monitor is found.
        """
        for mon in self.list_monitors():
            if mon.is_primary:
                return mon
        raise NoMonitorsError("No primary monitor found.")

    def capture(
        self, monitor_index: int | None = None, region: dict[str, int] | None = None
    ) -> np.ndarray:
        """Capture a screenshot as a numpy RGB array.

        Args:
            monitor_index: Index of the monitor to capture (from
                ``list_monitors()``). If None, captures the primary
                monitor.
            region: Optional dict with ``left``, ``top``, ``width``,
                ``height`` for capturing a sub-region. Overrides
                monitor_index.

        Returns:
            numpy array of shape (height, width, 3), dtype uint8,
            in RGB order.

        Raises:
            NoMonitorsError: If no monitor is available.
            ScreenCaptureError: If capture fails.
        """
        import mss

        if region is None:
            mon = (
                self.get_primary_monitor()
                if monitor_index is None
                else self._monitors[monitor_index]
            )
            region = {"left": mon.left, "top": mon.top, "width": mon.width, "height": mon.height}

        try:
            raw = self._sct.grab(region)  # type: ignore[union-attr]
        except mss.exception.ScreenShotError as exc:
            raise ScreenCaptureError(f"Failed to capture screen region {region}: {exc}") from exc

        # mss returns BGRA; convert to RGB
        frame_bgra = np.array(raw, dtype=np.uint8)
        frame_rgb: np.ndarray = frame_bgra[:, :, :3][:, :, ::-1]  # BGR → RGB
        return frame_rgb

    def capture_to_file(
        self,
        path: str | Path,
        monitor_index: int | None = None,
        region: dict[str, int] | None = None,
        fmt: str = "png",
    ) -> Path:
        """Capture a screenshot and save it to disk.

        Idempotent: safe to call repeatedly with the same path;
        overwrites existing files.

        Args:
            path: Destination file path.
            monitor_index: Monitor to capture (None = primary).
            region: Sub-region dict (``left``, ``top``, ``width``,
                ``height``).
            fmt: File format (``png``, ``jpg``, ``bmp``, ``tiff``).

        Returns:
            Path to the saved file.

        Raises:
            ScreenCaptureError: If capture or save fails.
        """
        from PIL import Image

        frame = self.capture(monitor_index=monitor_index, region=region)
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            img = Image.fromarray(frame)
            img.save(str(dest), format=fmt)
            logger.info("Saved screenshot to %s (%dx%d)", dest, frame.shape[1], frame.shape[0])
        except OSError as exc:
            raise ScreenCaptureError(f"Failed to save screenshot to {dest}: {exc}") from exc
        return dest


def capture_primary() -> np.ndarray:
    """Convenience: capture the primary monitor as RGB numpy array.

    Returns:
        numpy array (height, width, 3), uint8, RGB.

    Raises:
        ImportError: If mss is not installed.
        NoMonitorsError: If no monitors detected.
        ScreenCaptureError: If capture fails.
    """
    return ScreenCapture().capture()
