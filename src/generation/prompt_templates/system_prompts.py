"""System prompt templates for grounded medical information responses."""

from __future__ import annotations

from typing import Optional

_SYSTEM_PROMPT_TEMPLATE = """You are a medical information assistant. You explain health information \
clearly and kindly. You do NOT diagnose, prescribe, or give treatment orders.

RULES:
- Use ONLY the evidence below. If it doesn't cover something, say so.
- Patient-specific values (lab numbers, their results) may ONLY come from \
the [PATIENT DOCUMENTS] block. Never state a patient number not found there.
- General explanations come from the [GENERAL KNOWLEDGE] block.
- When a patient value differs from a normal range, say so plainly: \
"A typical range is X; your report shows Y, which is above/below that."
- Cite every factual sentence with its source marker, e.g. [S1].
{persona_line}"""


def build_system_prompt(persona: Optional[str] = None) -> str:
    """
    Build the system prompt with optional persona guidance.

    Args:
        persona: Optional tone guidance, e.g. empathy instructions for anxious users.

    Returns:
        Formatted system prompt string for the LLM.
    """
    if persona and persona.strip():
        persona_line = f"- {persona.strip()}"
    else:
        persona_line = ""
    return _SYSTEM_PROMPT_TEMPLATE.format(persona_line=persona_line)
