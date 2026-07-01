"""Stream client — reads screen frames from the MJPEG stream server (Method 1).

Uses OpenCV's ``VideoCapture`` to consume frames from the HTTP MJPEG
stream produced by ``modules.stream_server.ScreenStreamServer``.

This is the client-side of Method 1: the stream server runs in a separate
thread/process and this client reads and analyzes the streamed frames.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class StreamClientError(Exception):
    """Base for stream client errors."""


class StreamConnectionError(StreamClientError):
    """Raised when cannot connect to the stream server."""


class StreamDisconnectedError(StreamClientError):
    """Raised when the stream disconnects unexpectedly."""


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class StreamFrame:
    """A frame read from the MJPEG stream.

    Attributes:
        frame: RGB frame (H×W×3, uint8).
        raw_jpeg: Raw JPEG bytes (for forwarding/re-broadcasting).
        timestamp: Unix timestamp when received.
        frame_id: Monotonically increasing frame counter.
    """

    frame: np.ndarray
    raw_jpeg: bytes = field(default=b"", repr=False)
    timestamp: float = field(default_factory=time.time)
    frame_id: int = 0


# ---------------------------------------------------------------------------
# Stream client
# ---------------------------------------------------------------------------


class StreamClient:
    """Read screen frames from an MJPEG stream (Method 1 client).

    Connects to a ``ScreenStreamServer`` running on localhost and
    reads the MJPEG stream as individual frames for analysis.

    Usage:
        >>> client = StreamClient(port=8765)
        >>> client.connect()
        >>> sf = client.read_frame()
        >>> # Analyze sf.frame with OpenCV...
        >>> client.disconnect()
    """

    _DEFAULT_PORT = 8765
    _CONNECT_TIMEOUT = 5.0
    _MAX_RECONNECT_RETRIES = 3

    def __init__(self, port: int = _DEFAULT_PORT) -> None:
        """Initialize the stream client.

        Args:
            port: HTTP port of the stream server.
        """
        self._port = port
        self._cap: Any = None  # cv2.VideoCapture
        self._connected = False
        self._frame_count = 0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        if self._cap is None:
            return False
        return self._cap.isOpened()

    @property
    def stream_url(self) -> str:
        return f"http://localhost:{self._port}/stream"

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, timeout: float = _CONNECT_TIMEOUT) -> None:
        """Connect to the MJPEG stream server.

        Args:
            timeout: Seconds to wait for the stream to become available.

        Raises:
            StreamConnectionError: If the server is unreachable or the
                stream cannot be opened.
        """
        import cv2

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            self._cap = cv2.VideoCapture(self.stream_url)
            if self._cap.isOpened():
                self._connected = True
                self._frame_count = 0
                logger.info("Connected to stream at %s", self.stream_url)
                return

            if self._cap is not None:
                self._cap.release()

            time.sleep(0.5)

        raise StreamConnectionError(
            f"Could not connect to stream at {self.stream_url} within {timeout}s. "
            "Ensure ScreenStreamServer is running."
        )

    def disconnect(self) -> None:
        """Close the stream connection."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._connected = False
        logger.info("Disconnected from stream.")

    # ------------------------------------------------------------------
    # Frame reading
    # ------------------------------------------------------------------

    def read_frame(self) -> StreamFrame:
        """Read the next frame from the stream.

        Returns:
            StreamFrame containing the RGB frame and metadata.

        Raises:
            StreamDisconnectedError: If the stream connection is lost.
            StreamConnectionError: If not connected.
        """
        import cv2

        if not self.is_connected:
            raise StreamConnectionError("Not connected. Call connect() first.")

        ret, frame_bgr = self._cap.read()
        if not ret or frame_bgr is None:
            raise StreamDisconnectedError(
                f"Stream at {self.stream_url} disconnected or returned empty frame."
            )

        self._frame_count += 1
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        return StreamFrame(
            frame=frame_rgb,
            timestamp=time.time(),
            frame_id=self._frame_count,
        )

    def read_gray(self) -> np.ndarray:
        """Read the next frame as grayscale (convenience method)."""
        import cv2

        sf = self.read_frame()
        return cv2.cvtColor(sf.frame, cv2.COLOR_RGB2GRAY)

    # ------------------------------------------------------------------
    # Reconnect
    # ------------------------------------------------------------------

    def reconnect(self) -> None:
        """Attempt to reconnect after a disconnection.

        Raises:
            StreamConnectionError: If reconnection fails after retries.
        """
        self.disconnect()
        for attempt in range(1, self._MAX_RECONNECT_RETRIES + 1):
            try:
                logger.info("Reconnect attempt %d/%d...", attempt, self._MAX_RECONNECT_RETRIES)
                self.connect()
                return
            except StreamConnectionError:
                if attempt == self._MAX_RECONNECT_RETRIES:
                    raise
                time.sleep(1.0)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> StreamClient:
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()
