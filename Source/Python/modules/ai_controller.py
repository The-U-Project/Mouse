"""AI Controller — interfaces with AI APIs to give instructions and chat with user.

Supports OpenAI-compatible APIs (OpenAI, Azure OpenAI, local models via
Ollama/LM Studio) for:
1. Screen analysis → instruction generation
2. Natural language cursor control
3. Interactive chat with the user
4. Autonomous task execution
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from modules.cursor_controller import ClickType, CursorAction, MouseButton

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class AIProvider(Enum):
    """Supported AI API providers."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"  # Local models
    LM_STUDIO = "lm_studio"  # Local models
    CUSTOM = "custom"  # Any OpenAI-compatible endpoint


@dataclass
class AIConfig:
    """Configuration for an AI provider.

    Attributes:
        provider: Which AI backend to use.
        api_key: API key (or "local" for local models).
        base_url: API base URL (auto-detected if empty).
        model: Model name (e.g., "gpt-4o", "llama3.2-vision").
        max_tokens: Max tokens per response.
        temperature: Response randomness 0.0–2.0.
        system_prompt: System-level instructions for the model.
    """

    provider: AIProvider = AIProvider.OPENAI
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 1024
    temperature: float = 0.7
    system_prompt: str = (
        "You are Mouse, an AI-powered cursor control assistant. "
        "You help users control their computer by understanding their screen "
        "and generating precise cursor actions. Be concise and accurate."
    )


@dataclass
class AIResponse:
    """Parsed AI response.

    Attributes:
        text: Raw text response.
        actions: Extracted cursor actions (if any).
        reasoning: Model's reasoning about the screen (if any).
        raw_json: Full raw JSON response from the API.
    """

    text: str = ""
    actions: list[CursorAction] = field(default_factory=list)
    reasoning: str = ""
    raw_json: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AIControllerError(Exception):
    """Base for AI controller errors."""


class AIConnectionError(AIControllerError):
    """Raised when the AI API is unreachable."""


class AIResponseError(AIControllerError):
    """Raised when the AI response cannot be parsed."""


class AIQuotaError(AIControllerError):
    """Raised when API quota is exceeded."""


# ---------------------------------------------------------------------------
# AI Controller
# ---------------------------------------------------------------------------


class AIController:
    """Interfaces with AI APIs for screen analysis and cursor control.

    Usage:
        >>> ai = AIController(AIConfig(provider=AIProvider.OPENAI, api_key="..."))
        >>> response = ai.analyze_screen(screen_description)
        >>> for action in response.actions:
        ...     cursor_controller.execute_action(action)
        >>> reply = ai.chat("What do you see on my screen?")
    """

    _DEFAULT_TIMEOUT = 30.0
    _MAX_RETRIES = 3
    _RETRY_DELAY = 1.0

    def __init__(self, config: AIConfig | None = None) -> None:
        """Initialize the AI controller.

        Args:
            config: AI provider configuration. If None, uses defaults
                and reads API key from ``OPENAI_API_KEY`` env var.
        """
        self._config = config or self._default_config()
        self._conversation_history: list[dict[str, Any]] = []

    @staticmethod
    def _default_config() -> AIConfig:
        """Build config from environment variables."""
        import os

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "")
        model = os.environ.get("MOUSE_AI_MODEL", "gpt-4o")

        provider = AIProvider.OPENAI
        if os.environ.get("MOUSE_AI_PROVIDER") == "ollama":
            provider = AIProvider.OLLAMA
            base_url = base_url or "http://localhost:11434/v1"
            model = model or "llama3.2-vision"
        elif os.environ.get("MOUSE_AI_PROVIDER") == "lm_studio":
            provider = AIProvider.LM_STUDIO
            base_url = base_url or "http://localhost:1234/v1"
        elif os.environ.get("MOUSE_AI_PROVIDER") == "azure":
            provider = AIProvider.AZURE_OPENAI

        return AIConfig(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> AIConfig:
        return self._config

    def update_config(self, **kwargs: Any) -> None:
        """Update AI configuration fields."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Get an OpenAI-compatible client."""
        from openai import OpenAI

        base_url = self._config.base_url or None
        api_key = self._config.api_key or "local"  # "local" for Ollama/LM Studio

        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=self._DEFAULT_TIMEOUT,
        )

    def _call_api(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the AI API with retry logic.

        Args:
            messages: Chat messages list.
            response_format: Optional JSON schema for structured output.

        Returns:
            Parsed API response.

        Raises:
            AIConnectionError: If the API is unreachable.
            AIQuotaError: If the API quota is exceeded.
        """
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                response = client.chat.completions.create(**kwargs)
                raw = response.model_dump()
                return raw
            except Exception as exc:
                error_msg = str(exc).lower()
                if "quota" in error_msg or "rate limit" in error_msg:
                    raise AIQuotaError(f"API quota exceeded: {exc}") from exc
                if attempt < self._MAX_RETRIES:
                    delay = self._RETRY_DELAY * attempt
                    logger.warning("API call failed (attempt %d/%d): %s — retrying in %.1fs",
                                   attempt, self._MAX_RETRIES, exc, delay)
                    time.sleep(delay)
                else:
                    raise AIConnectionError(
                        f"AI API call failed after {self._MAX_RETRIES} attempts: {exc}"
                    ) from exc

        raise AIConnectionError("Unreachable")

    # ------------------------------------------------------------------
    # Screen analysis
    # ------------------------------------------------------------------

    def analyze_screen(
        self,
        screen_description: str,
        user_goal: str = "",
        extra_context: str = "",
    ) -> AIResponse:
        """Send a screen description to the AI and get cursor actions back.

        The AI receives a text description of what's on screen (generated
        by the CV pipeline) and the user's goal, then returns precise
        cursor actions to accomplish the goal.

        Args:
            screen_description: Text describing visible UI elements.
            user_goal: What the user wants to accomplish.
            extra_context: Additional context (app name, etc.).

        Returns:
            AIResponse with parsed actions and reasoning.
        """
        system = f"""{self._config.system_prompt}

You are analyzing a screen description and generating cursor actions.
Respond ONLY with a JSON object in this exact format:
{{
    "reasoning": "Brief explanation of what you see and your plan",
    "actions": [
        {{
            "action_type": "move|click|drag|scroll|type",
            "x": <pixel_x or 0>,
            "y": <pixel_y or 0>,
            "button": "left|right|middle",
            "click_type": "single|double",
            "text": "<text to type, if action_type=type>",
            "scroll_amount": <int, positive=up>,
            "is_relative": false,
            "duration": <seconds for smooth move>,
            "description": "<human-readable description>"
        }}
    ],
    "done": false,
    "message": "What to tell the user"
}}
"""

        user_prompt = f"""Screen description:
{screen_description}

User goal: {user_goal or "Analyze the screen and describe what you see"}

{extra_context}

Generate the cursor actions needed to accomplish the goal."""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]

        raw = self._call_api(messages)
        return self._parse_response(raw)

    def analyze_frame(
        self,
        regions: list[Any],  # list[ScreenRegion]
        cursor_pos: tuple[float, float] = (0, 0),
        user_goal: str = "",
    ) -> AIResponse:
        """Analyze screen regions detected by CV and generate actions.

        Args:
            regions: Detected ScreenRegion objects from DirectAnalyzer.
            cursor_pos: Current cursor position (x, y).
            user_goal: What the user wants to accomplish.

        Returns:
            AIResponse with actions.
        """
        # Build a text description from regions
        descriptions: list[str] = []
        for i, r in enumerate(regions):
            desc = f"  [{i}] {r.label} at ({r.x}, {r.y}) size {r.w}x{r.h}"
            if r.text:
                desc += f" text='{r.text}'"
            desc += f" confidence={r.confidence:.2f}"
            descriptions.append(desc)

        screen_desc = (
            f"Cursor is at ({cursor_pos[0]:.0f}, {cursor_pos[1]:.0f}).\n"
            f"Detected regions ({len(regions)}):\n"
            + "\n".join(descriptions)
        )

        return self.analyze_screen(screen_desc, user_goal=user_goal)

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def chat(self, message: str, include_screen_context: str = "") -> str:
        """Chat with the AI assistant.

        Maintains a conversation history so the AI remembers context
        across multiple calls.

        Args:
            message: User message.
            include_screen_context: Optional screen description to include.

        Returns:
            AI's text response.
        """
        if not self._conversation_history:
            self._conversation_history.append({
                "role": "system",
                "content": self._config.system_prompt,
            })

        content = message
        if include_screen_context:
            content = f"[Current screen: {include_screen_context}]\n\nUser: {message}"

        self._conversation_history.append({"role": "user", "content": content})

        raw = self._call_api(self._conversation_history)

        reply = ""
        choices = raw.get("choices", [])
        if choices:
            reply = choices[0].get("message", {}).get("content", "")

        self._conversation_history.append({"role": "assistant", "content": reply})

        # Trim history if too long (keep system + last 20 messages)
        if len(self._conversation_history) > 21:
            self._conversation_history = (
                self._conversation_history[:1] + self._conversation_history[-20:]
            )

        return reply

    def clear_history(self) -> None:
        """Reset the conversation history."""
        self._conversation_history = []

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_response(self, raw: dict[str, Any]) -> AIResponse:
        """Parse the AI API response into an AIResponse.

        Args:
            raw: Full API response dict.

        Returns:
            Parsed AIResponse.

        Raises:
            AIResponseError: If the response cannot be parsed.
        """
        choices = raw.get("choices", [])
        if not choices:
            raise AIResponseError("AI returned no choices in response.")

        content = choices[0].get("message", {}).get("content", "{}")
        text = content

        actions: list[CursorAction] = []
        reasoning = ""
        message = ""

        try:
            # Try to parse JSON from the response
            data = json.loads(content) if isinstance(content, str) else content

            reasoning = data.get("reasoning", "")
            message = data.get("message", "")

            for act in data.get("actions", []):
                button_map = {
                    "left": MouseButton.LEFT,
                    "right": MouseButton.RIGHT,
                    "middle": MouseButton.MIDDLE,
                }
                click_map = {
                    "single": ClickType.SINGLE,
                    "double": ClickType.DOUBLE,
                    "triple": ClickType.TRIPLE,
                }

                actions.append(
                    CursorAction(
                        action_type=act.get("action_type", "move"),
                        x=float(act.get("x", 0)),
                        y=float(act.get("y", 0)),
                        button=button_map.get(act.get("button", "left"), MouseButton.LEFT),
                        click_type=click_map.get(act.get("click_type", "single"), ClickType.SINGLE),
                        is_relative=bool(act.get("is_relative", False)),
                        text=str(act.get("text", "")),
                        scroll_amount=int(act.get("scroll_amount", 0)),
                        duration=float(act.get("duration", 0.2)),
                        description=str(act.get("description", "")),
                    )
                )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("Could not parse AI response as JSON: %s", exc)
            # Non-JSON response → treat as plain text
            text = content

        return AIResponse(
            text=text if not message else message,
            actions=actions,
            reasoning=reasoning,
            raw_json=raw,
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> AIController:
        return self

    def __exit__(self, *args: Any) -> None:
        self.clear_history()
