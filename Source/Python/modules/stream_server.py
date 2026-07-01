"""Method 1: Screen streaming server — captures display and serves as MJPEG over HTTP.

This module streams the screen capture to a configurable localhost port as an
MJPEG (Motion JPEG) stream. OpenCV on the client side reads the stream via
``cv2.VideoCapture("http://localhost:<port>")`` for analysis.

Architecture:
    Screen → ``files.KEEPER.ScreenCapture`` → JPEG encode → HTTP MJPEG server
                                                                    ↓
                                            OpenCV ``VideoCapture`` reads stream

Uses a simple threaded HTTP server (stdlib ``http.server``) to avoid heavy
dependencies. In production, the C++ backend can replace this with a
zero-copy shared-memory transport for lower latency.
"""

from __future__ import annotations

import io
import logging
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from queue import Queue
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class StreamServerError(Exception):
    """Base for all stream server errors."""


class PortInUseError(StreamServerError):
    """Raised when the target port is already in use."""


class StreamNotRunningError(StreamServerError):
    """Raised when attempting to interact with a stopped stream."""


# ---------------------------------------------------------------------------
# MJPEG stream handler
# ---------------------------------------------------------------------------


class _MJPEGHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves an MJPEG stream at ``/stream`` and a snapshot at ``/``.

    The handler reads frames from a shared ``Queue`` that is populated by the
    ``ScreenStreamServer`` capture thread.
    """

    # Class-level shared state — set by the server on creation
    frame_queue: Queue[bytes | None] = Queue(maxsize=2)
    server_started: float = 0.0

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP request logging; use our own logger."""
        logger.debug("HTTP %s", format % args)

    def _send_mjpeg_stream(self) -> None:
        """Send a continuous MJPEG stream response."""
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=--frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            while True:
                frame = self.frame_queue.get(timeout=2.0)
                if frame is None:  # Sentinel: stop streaming
                    break
                try:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n".encode())
                    self.wfile.write(b"\r\n")
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    break
        except Exception:
            pass  # Client disconnected or queue empty timeout

    def _send_snapshot(self) -> None:
        """Send the latest single JPEG frame."""
        try:
            frame = self.frame_queue.get(timeout=1.0)
            if frame is None:
                self.send_error(503, "Stream not available")
                return
            # Put it back so stream consumers don't miss it
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
        except Exception:
            self.send_error(503, "No frame available")
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(frame)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(frame)

    def _send_status(self) -> None:
        """Return JSON status of the stream server."""
        import json

        uptime = time.time() - self.server_started
        status = {
            "running": True,
            "uptime_seconds": round(uptime, 1),
            "queue_size": self.frame_queue.qsize(),
        }
        payload = json.dumps(status).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/stream":
            self._send_mjpeg_stream()
        elif self.path == "/":
            self._send_snapshot()
        elif self.path == "/status":
            self._send_status()
        else:
            self.send_error(404, "Not found")


# ---------------------------------------------------------------------------
# Screen stream server
# ---------------------------------------------------------------------------


class ScreenStreamServer:
    """Capture the screen and serve it as an MJPEG stream over HTTP.

    This implements **Method 1**: stream the screen to a port, then use
    OpenCV to read and analyze the port.

    Usage:
        >>> server = ScreenStreamServer(port=8765, fps=30)
        >>> server.start()
        >>> # From another process or via OpenCV:
        >>> # cap = cv2.VideoCapture("http://localhost:8765/stream")
        >>> # ...
        >>> server.stop()
    """

    _DEFAULT_PORT = 8765
    _DEFAULT_FPS = 30
    _DEFAULT_JPEG_QUALITY = 80

    def __init__(
        self,
        port: int = _DEFAULT_PORT,
        fps: int = _DEFAULT_FPS,
        jpeg_quality: int = _DEFAULT_JPEG_QUALITY,
        monitor_index: int | None = None,
    ) -> None:
        """Initialize the stream server.

        Args:
            port: HTTP port to serve on (localhost only).
            fps: Target capture frames per second.
            jpeg_quality: JPEG compression quality (1–100).
            monitor_index: Monitor to capture; None = primary.
        """
        self._port = port
        self._fps = fps
        self._jpeg_quality = jpeg_quality
        self._monitor_index = monitor_index

        self._http_server: HTTPServer | None = None
        self._capture_thread: threading.Thread | None = None
        self._capturing = threading.Event()

        # Frame queue shared with the HTTP handler
        self._frame_queue: Queue[bytes | None] = Queue(maxsize=2)

        self._started = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def port(self) -> int:
        return self._port

    @property
    def is_running(self) -> bool:
        return self._started and (self._capture_thread is not None and self._capture_thread.is_alive())

    @property
    def stream_url(self) -> str:
        """URL for OpenCV ``VideoCapture`` to read the MJPEG stream."""
        return f"http://localhost:{self._port}/stream"

    @property
    def snapshot_url(self) -> str:
        """URL for fetching a single JPEG frame."""
        return f"http://localhost:{self._port}/"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the stream server (non-blocking).

        Spawns a capture thread and an HTTP server thread. The stream
        is immediately available at ``http://localhost:<port>/stream``.

        Raises:
            PortInUseError: If the port is already bound.
        """
        if self._started:
            logger.warning("Stream server already running on port %d", self._port)
            return

        # Check port availability
        if not self._port_is_available():
            raise PortInUseError(
                f"Port {self._port} is already in use. Choose a different port or free this one."
            )

        # Configure the HTTP handler class with our queue
        _MJPEGHandler.frame_queue = self._frame_queue
        _MJPEGHandler.server_started = time.time()

        # Create and start HTTP server
        self._http_server = HTTPServer(("localhost", self._port), _MJPEGHandler)
        server_thread = threading.Thread(
            target=self._http_server.serve_forever,
            name="mjpeg-http-server",
            daemon=True,
        )
        server_thread.start()

        # Start capture thread
        self._capturing.set()
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name="screen-capture",
            daemon=True,
        )
        self._capture_thread.start()

        self._started = True
        logger.info(
            "Screen stream server started on http://localhost:%d (fps=%d, quality=%d)",
            self._port,
            self._fps,
            self._jpeg_quality,
        )

    def stop(self) -> None:
        """Stop the stream server gracefully."""
        if not self._started:
            return

        logger.info("Stopping screen stream server...")
        self._capturing.clear()

        # Send sentinel to unblock queue consumers
        try:
            self._frame_queue.put_nowait(None)
        except Exception:
            pass

        # Wait for capture thread
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=3.0)

        # Shutdown HTTP server
        if self._http_server is not None:
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None

        self._started = False
        logger.info("Screen stream server stopped.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _port_is_available(self) -> bool:
        """Check whether ``_port`` is free on localhost."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("localhost", self._port))
            return True
        except OSError:
            return False
        finally:
            sock.close()

    def _capture_loop(self) -> None:
        """Background thread: capture screen → JPEG encode → push to queue."""
        from files.KEEPER import ScreenCapture, ScreenCaptureError

        cap = ScreenCapture()
        period = 1.0 / self._fps
        last_frame = time.monotonic()

        try:
            from PIL import Image
        except ImportError:
            raise ImportError(
                "pillow is required for JPEG encoding. Install: uv pip install pillow"
            )

        while self._capturing.is_set():
            loop_start = time.monotonic()

            try:
                frame_rgb: np.ndarray = cap.capture(monitor_index=self._monitor_index)
            except ScreenCaptureError as exc:
                logger.error("Capture failed: %s", exc)
                time.sleep(0.1)
                continue

            # Encode as JPEG
            img = Image.fromarray(frame_rgb, mode="RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=self._jpeg_quality)
            jpeg_bytes = buf.getvalue()

            # Push to queue (non-blocking, drop oldest if consumer is slow)
            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()  # Drop oldest
                except Exception:
                    pass
            try:
                self._frame_queue.put_nowait(jpeg_bytes)
            except Exception:
                pass

            # Maintain target FPS
            elapsed = time.monotonic() - loop_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> ScreenStreamServer:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()
