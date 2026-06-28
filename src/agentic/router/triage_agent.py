"""
Triage agent: detects emergency medical content in a user's question,
independent of emotional tone. This is the one judgment Phase 3's
risk_level score cannot make on its own — a calmly-worded message
describing a true emergency can score low on emotional intensity while
still needing to bypass retrieval and generation entirely.

Design rules (do not relax these without deliberate review):
- On ANY uncertainty (LLM failure, unparseable response), default to the
  MORE cautious classification, never silently fall through to ROUTINE.
- This agent only classifies. It never writes the user-facing emergency
  message itself — that text is fixed and reviewed separately, so a model
  is never improvising the wording of a safety-critical response.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.generation.llm_client import LLMClient, LLMError, AnthropicClient
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class TriageLevel(str, Enum):
    EMERGENCY = "emergency"  # bypass retrieval/generation entirely
    DISTRESSED = "distressed"  # proceed, but use a gentler persona
    ROUTINE = "routine"  # proceed normally


@dataclass
class TriageResult:
    level: TriageLevel
    reason: str  # short internal note, not shown to the user verbatim


_TRIAGE_SYSTEM_PROMPT = """You are a medical triage classifier. Your ONLY job \
is to read a single user message and decide if it describes a possible \
medical emergency RIGHT NOW (e.g. chest pain, difficulty breathing, signs of \
stroke, severe bleeding, suicidal intent, loss of consciousness, severe \
allergic reaction).

Judge the CONTENT, not the tone. A calmly-worded message describing an \
emergency is still an emergency. A frightened-sounding message about a routine \
topic (like asking about a normal lab value) is NOT an emergency.

Respond with EXACTLY one word, nothing else:
EMERGENCY - if the message describes a current or imminent medical emergency.
ROUTINE - if it does not.
"""


def _classify_with_llm(question: str, llm_client: LLMClient) -> Optional[TriageLevel]:
    """Call the LLM classifier. Returns None on any failure or unparseable output."""
    try:
        raw = llm_client.generate(_TRIAGE_SYSTEM_PROMPT, question.strip())
    except LLMError as exc:
        logger.error(f"Triage LLM call failed: {exc}")
        return None

    normalized = raw.strip().upper()
    if "EMERGENCY" in normalized:
        return TriageLevel.EMERGENCY
    if "ROUTINE" in normalized:
        return TriageLevel.ROUTINE

    logger.warning(f"Triage classifier returned unparseable output: {raw!r}")
    return None


def run_triage(
    question: str,
    risk_level: float = 0.0,
    llm_client: Optional[LLMClient] = None,
    distressed_threshold: float = 0.6,
) -> TriageResult:
    """
    Classify a question into EMERGENCY / DISTRESSED / ROUTINE.

    Args:
        question: The user's raw question text.
        risk_level: Phase 3 sentiment risk score (0.0-1.0). Used only for the
            DISTRESSED/ROUTINE distinction; emergency detection is independent
            of this score by design.
        llm_client: Injected LLM client; defaults to AnthropicClient().
        distressed_threshold: risk_level at or above this is treated as
            DISTRESSED rather than ROUTINE (when not EMERGENCY).

    Returns:
        TriageResult with the resolved level and an internal reason string.
    """
    if not question or not question.strip():
        return TriageResult(level=TriageLevel.ROUTINE, reason="empty question")

    client = llm_client or AnthropicClient()
    emergency_check = _classify_with_llm(question, client)

    if emergency_check is None:
        # Fail-safe rule: any classifier failure or unparseable output is
        # treated as DISTRESSED, never ROUTINE. We cannot confirm safety,
        # so we do not default to the least cautious path.
        logger.warning("Triage classification failed; defaulting to DISTRESSED")
        return TriageResult(level=TriageLevel.DISTRESSED, reason="triage_unavailable")

    if emergency_check == TriageLevel.EMERGENCY:
        return TriageResult(level=TriageLevel.EMERGENCY, reason="emergency_content_detected")

    if risk_level >= distressed_threshold:
        return TriageResult(level=TriageLevel.DISTRESSED, reason=f"risk_level={risk_level:.2f}")

    return TriageResult(level=TriageLevel.ROUTINE, reason="no_emergency_or_distress_signal")