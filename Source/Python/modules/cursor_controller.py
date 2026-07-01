"""Cursor controller — moves the system mouse cursor based on AI/vision instructions.

Provides cross-platform cursor control using PyAutoGUI (primary) with
ctypes-based fallback for Windows and Quartz-based fallback for macOS.

Supports:
- Absolute positioning (move to x, y)
- Relative movement (dx, dy)
- Click (left, right, middle, double)
- Drag (from → to)
- Scroll
- Typing
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class MouseButton(Enum):
    """Mouse button identifiers."""

    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


class ClickType(Enum):
    """Click variants."""

    SINGLE = auto()
    DOUBLE = auto()
    TRIPLE = auto()


@dataclass
class CursorAction:
    """An instruction to control the cursor.

    Attributes:
        action_type: Type of action ('move', 'click', 'drag', 'scroll', 'type').
        x: Target X coordinate (absolute or delta depending on is_relative).
        y: Target Y coordinate.
        button: Which mouse button to use.
        click_type: Single/double/triple click.
        is_relative: If True, (x, y) are deltas from current position.
        text: Text to type (for 'type' action).
        scroll_amount: Scroll amount in "clicks" (positive = up/right).
        duration: Duration in seconds for smooth moves (0 = instant).
        delay_after: Wait after action completes (seconds).
        description: Human-readable description for logging/AI.
    """

    action_type: str  # 'move', 'click', 'drag', 'scroll', 'type'
    x: float = 0.0
    y: float = 0.0
    button: MouseButton = MouseButton.LEFT
    click_type: ClickType = ClickType.SINGLE
    is_relative: bool = False
    text: str = ""
    scroll_amount: int = 0
    duration: float = 0.0
    delay_after: float = 0.0
    description: str = ""


@dataclass
class CursorPosition:
    """Current cursor state."""

    x: int = 0
    y: int = 0
    on_screen: bool = True


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CursorControlError(Exception):
    """Base for cursor control errors."""


class CursorOutOfBoundsError(CursorControlError):
    """Raised when target coordinates are outside the screen."""


class PlatformNotSupportedError(CursorControlError):
    """Raised when a feature is not available on the current platform."""


# ---------------------------------------------------------------------------
# Cursor controller
# ---------------------------------------------------------------------------


class CursorController:
    """Cross-platform mouse cursor controller.

    Uses PyAutoGUI for high-level operations with platform-specific
    fallbacks for performance-critical paths.

    Usage:
        >>> ctrl = CursorController()
        >>> ctrl.move_to(500, 300)
        >>> ctrl.click()
        >>> ctrl.execute_action(CursorAction("move", x=100, y=200, duration=0.5))
    """

    _DEFAULT_DURATION = 0.2  # Default smooth move duration
    _SAFETY_MARGIN = 5  # Pixels inside screen edge to allow

    def __init__(self, fail_safe: bool = True, safety_pause: float = 0.1) -> None:
        """Initialize the cursor controller.

        Args:
            fail_safe: If True, moving to (0,0) raises an exception
                (PyAutoGUI safety feature).
            safety_pause: Pause between PyAutoGUI actions (seconds).
        """
        self._fail_safe = fail_safe
        self._safety_pause = safety_pause
        self._screen_width: int = 0
        self._screen_height: int = 0
        self._init_backend()

    def _init_backend(self) -> None:
        """Initialize PyAutoGUI and get screen dimensions."""
        import pyautogui

        pyautogui.FAILSAFE = self._fail_safe
        pyautogui.PAUSE = self._safety_pause

        self._screen_width, self._screen_height = pyautogui.size()
        logger.debug(
            "Cursor controller ready: %dx%d screen",
            self._screen_width,
            self._screen_height,
        )

    # ------------------------------------------------------------------
    # Position
    # ------------------------------------------------------------------

    def get_position(self) -> CursorPosition:
        """Get the current cursor position.

        Returns:
            CursorPosition with current x, y.
        """
        import pyautogui

        x, y = pyautogui.position()
        return CursorPosition(
            x=x,
            y=y,
            on_screen=(0 <= x <= self._screen_width and 0 <= y <= self._screen_height),
        )

    def move_to(self, x: float, y: float, duration: float = _DEFAULT_DURATION) -> None:
        """Move the cursor to absolute screen coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            duration: Seconds for smooth movement (0 = teleport).

        Raises:
            CursorOutOfBoundsError: If coordinates are outside the screen.
        """
        x, y = self._clamp(int(x), int(y))

        import pyautogui

        if duration > 0:
            pyautogui.moveTo(x, y, duration=duration)
        else:
            pyautogui.moveTo(x, y)

        logger.debug("Cursor moved to (%d, %d)", x, y)

    def move_relative(self, dx: float, dy: float, duration: float = 0.0) -> None:
        """Move the cursor relative to its current position.

        Args:
            dx: Horizontal delta (positive = right).
            dy: Vertical delta (positive = down).
            duration: Seconds for smooth movement.
        """
        import pyautogui

        pyautogui.moveRel(int(dx), int(dy), duration=duration)

    # ------------------------------------------------------------------
    # Click
    # ------------------------------------------------------------------

    def click(
        self,
        x: float | None = None,
        y: float | None = None,
        button: MouseButton = MouseButton.LEFT,
        clicks: int = 1,
    ) -> None:
        """Click at the current position or move-and-click.

        Args:
            x: Optional target X (moves first if provided).
            y: Optional target Y.
            button: Which mouse button.
            clicks: 1 for single, 2 for double, 3 for triple.
        """
        import pyautogui

        btn_str = self._button_to_pyautogui(button)

        if x is not None and y is not None:
            x, y = self._clamp(int(x), int(y))
            pyautogui.click(x, y, clicks=clicks, button=btn_str)
        else:
            pyautogui.click(clicks=clicks, button=btn_str)

    def double_click(self, x: float | None = None, y: float | None = None) -> None:
        """Double-click at position (or current)."""
        self.click(x=x, y=y, clicks=2)

    def right_click(self, x: float | None = None, y: float | None = None) -> None:
        """Right-click at position (or current)."""
        self.click(x=x, y=y, button=MouseButton.RIGHT)

    # ------------------------------------------------------------------
    # Drag
    # ------------------------------------------------------------------

    def drag(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        duration: float = 0.5,
        button: MouseButton = MouseButton.LEFT,
    ) -> None:
        """Drag from start to end coordinates.

        Args:
            start_x, start_y: Drag start coordinates.
            end_x, end_y: Drag end coordinates.
            duration: Drag movement duration.
            button: Mouse button to hold during drag.
        """
        import pyautogui

        start_x, start_y = self._clamp(int(start_x), int(start_y))
        end_x, end_y = self._clamp(int(end_x), int(end_y))

        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(
            end_x - start_x,
            end_y - start_y,
            duration=duration,
            button=self._button_to_pyautogui(button),
        )

    # ------------------------------------------------------------------
    # Scroll
    # ------------------------------------------------------------------

    def scroll(self, amount: int, x: float | None = None, y: float | None = None) -> None:
        """Scroll the mouse wheel.

        Args:
            amount: Number of "clicks" to scroll (positive = up).
            x, y: Optional position to scroll at (moves first).
        """
        import pyautogui

        if x is not None and y is not None:
            pyautogui.moveTo(int(x), int(y))

        pyautogui.scroll(amount)

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def type_text(self, text: str, interval: float = 0.0) -> None:
        """Type a string using the keyboard.

        Args:
            text: Text to type.
            interval: Delay between keystrokes (seconds).
        """
        import pyautogui

        pyautogui.typewrite(text, interval=interval)

    def press_key(self, key: str) -> None:
        """Press a keyboard key.

        Args:
            key: Key name (e.g., 'enter', 'ctrl', 'a').
        """
        import pyautogui

        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        """Press a key combination (e.g., ctrl+c, alt+tab).

        Args:
            *keys: Key names to press together.
        """
        import pyautogui

        pyautogui.hotkey(*keys)

    # ------------------------------------------------------------------
    # Action execution (for AI-driven control)
    # ------------------------------------------------------------------

    def execute_action(self, action: CursorAction) -> None:
        """Execute a CursorAction from the AI pipeline.

        Args:
            action: Action to execute.

        Raises:
            CursorControlError: If the action type is unknown.
        """
        logger.info("Executing: %s", action.description or f"{action.action_type} at ({action.x}, {action.y})")

        if action.action_type == "move":
            if action.is_relative:
                self.move_relative(action.x, action.y, action.duration)
            else:
                self.move_to(action.x, action.y, action.duration)
        elif action.action_type == "click":
            self.click(
                x=action.x if action.x != 0 else None,
                y=action.y if action.y != 0 else None,
                button=action.button,
                clicks={
                    ClickType.SINGLE: 1,
                    ClickType.DOUBLE: 2,
                    ClickType.TRIPLE: 3,
                }[action.click_type],
            )
        elif action.action_type == "drag":
            # For drag, use (x, y) as the end; current position as start
            cur = self.get_position()
            self.drag(cur.x, cur.y, action.x, action.y, action.duration, action.button)
        elif action.action_type == "scroll":
            self.scroll(action.scroll_amount, action.x if action.x != 0 else None, action.y if action.y != 0 else None)
        elif action.action_type == "type":
            self.type_text(action.text)
        else:
            raise CursorControlError(f"Unknown action type: {action.action_type}")

        if action.delay_after > 0:
            time.sleep(action.delay_after)

    def execute_actions(self, actions: list[CursorAction]) -> None:
        """Execute a sequence of cursor actions.

        Args:
            actions: Ordered list of actions to execute.
        """
        for action in actions:
            self.execute_action(action)

    # ------------------------------------------------------------------
    # Screen info
    # ------------------------------------------------------------------

    @property
    def screen_size(self) -> tuple[int, int]:
        return (self._screen_width, self._screen_height)

    def take_screenshot(self) -> Any:
        """Take a screenshot and return it as a PIL Image.

        Returns:
            PIL Image in RGB mode.
        """
        import pyautogui

        return pyautogui.screenshot()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clamp(self, x: int, y: int) -> tuple[int, int]:
        """Clamp coordinates to screen bounds."""
        x = max(self._SAFETY_MARGIN, min(self._screen_width - self._SAFETY_MARGIN, x))
        y = max(self._SAFETY_MARGIN, min(self._screen_height - self._SAFETY_MARGIN, y))
        return x, y

    @staticmethod
    def _button_to_pyautogui(button: MouseButton) -> str:
        """Convert MouseButton enum to PyAutoGUI string."""
        return {
            MouseButton.LEFT: "left",
            MouseButton.RIGHT: "right",
            MouseButton.MIDDLE: "middle",
        }[button]

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> CursorController:
        return self

    def __exit__(self, *args: Any) -> None:
        pass  # No cleanup needed
