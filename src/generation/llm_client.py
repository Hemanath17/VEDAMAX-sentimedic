"""Abstract and concrete LLM clients for grounded answer generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from src.config.logging_config import get_logger

if TYPE_CHECKING:
    from anthropic import Anthropic
    from openai import OpenAI
from src.config.settings import settings

logger = get_logger(__name__)


class LLMError(Exception):
    """Raised when an LLM provider call fails."""


def effective_temperature() -> float:
    """Return generation temperature capped for medical grounding."""
    if settings.LLM_TEMPERATURE > 0.3:
        return 0.2
    return settings.LLM_TEMPERATURE


class LLMClient(ABC):
    """Provider-agnostic interface for text generation."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generate a completion from system and user prompts.

        Args:
            system_prompt: Instructions and safety rules for the model.
            user_prompt: Evidence blocks, conversation context, and question.

        Returns:
            Raw model text response.

        Raises:
            LLMError: When the provider call fails.
        """


class OpenAIClient(LLMClient):
    """OpenAI chat-completions client backed by project settings."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        client: Optional["OpenAI"] = None,
    ) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature if temperature is not None else effective_temperature()
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self._client = client

    def _get_client(self) -> "OpenAI":
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("openai package is not installed.") from exc
        return OpenAI(api_key=self.api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI chat completions and return assistant message text."""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            choice = response.choices[0]
            content = choice.message.content
            if not content:
                raise LLMError("OpenAI returned an empty response.")
            return content.strip()
        except LLMError:
            raise
        except Exception as exc:
            logger.error("OpenAI generation failed: %s", exc, exc_info=True)
            raise LLMError(f"OpenAI generation failed: {exc}") from exc


class AnthropicClient(LLMClient):
    """Anthropic Messages API client backed by project settings."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        client: Optional["Anthropic"] = None,
    ) -> None:
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.temperature = temperature if temperature is not None else effective_temperature()
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self._client = client

    def _get_client(self) -> "Anthropic":
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured.")
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise LLMError("anthropic package is not installed.") from exc
        return Anthropic(api_key=self.api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call Anthropic messages API and return assistant message text."""
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text_parts = [
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text" and getattr(block, "text", "")
            ]
            content = "\n".join(text_parts).strip()
            if not content:
                raise LLMError("Anthropic returned an empty response.")
            return content
        except LLMError:
            raise
        except Exception as exc:
            logger.error("Anthropic generation failed: %s", exc, exc_info=True)
            raise LLMError(f"Anthropic generation failed: {exc}") from exc
