"""System prompt templates for grounded medical information responses."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

_PROMPT_FILE = Path(__file__).with_name("vedamax_system_prompt.txt")


@lru_cache(maxsize=1)
def _load_base_system_prompt() -> str:
    """Load the VEDAMAX system prompt from the companion text file."""
    return _PROMPT_FILE.read_text(encoding="utf-8").strip()


def build_system_prompt(persona: Optional[str] = None) -> str:
    """
    Build the system prompt with optional persona guidance.

    Args:
        persona: Optional tone guidance, e.g. empathy instructions for anxious users.

    Returns:
        Formatted system prompt string for the LLM.
    """
    prompt = _load_base_system_prompt()
    if persona and persona.strip():
        prompt = (
            f"{prompt}\n\n[ADDITIONAL TONE GUIDANCE FOR THIS RESPONSE]\n"
            f"- {persona.strip()}"
        )
    return prompt
