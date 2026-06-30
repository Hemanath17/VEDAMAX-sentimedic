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
    SMALL_TALK = "small_talk"  # casual chat; no KB retrieval needed
    DISTRESSED = "distressed"  # proceed, but use a gentler persona
    ROUTINE = "routine"  # proceed normally


@dataclass
class TriageResult:
    level: TriageLevel
    reason: str  # short internal note, not shown to the user verbatim


_TRIAGE_SYSTEM_PROMPT = """You are a medical triage classifier. Your ONLY job \
is to read a single user message and classify it into exactly one of four \
categories:

EMERGENCY -- current or imminent medical emergency (chest pain, difficulty \
breathing, suicidal intent, severe bleeding, stroke symptoms, loss of \
consciousness, severe allergic reaction). When in doubt between EMERGENCY and \
anything else, classify EMERGENCY.

SMALL_TALK -- greetings, thanks, casual chat, social check-ins, or any \
message with no health information need ("hi", "hello", "thanks", "how are \
you", "good morning", "bye", "can you help me?"). Judge by INTENT not length \
-- a single sentence asking a genuine health question is ROUTINE, not \
SMALL_TALK just because it's short. SMALL_TALK must never capture messages \
that contain a real health question or symptom, even if they start casually \
("hi, is my glucose high?" is ROUTINE, not SMALL_TALK).

DISTRESSED -- emotionally charged about a health topic but not an emergency \
("I'm really scared about my results", "I'm so worried").

ROUTINE -- normal informational health question with no urgency or distress \
signal.

Respond with EXACTLY one word from the four options above, nothing else:
EMERGENCY, SMALL_TALK, DISTRESSED, or ROUTINE.
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
    if "SMALL_TALK" in normalized:
        return TriageLevel.SMALL_TALK
    if "DISTRESSED" in normalized:
        return TriageLevel.DISTRESSED
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
    Classify a question into EMERGENCY / SMALL_TALK / DISTRESSED / ROUTINE.

    Args:
        question: The user's raw question text.
        risk_level: Phase 3 sentiment risk score (0.0-1.0). Used only for the
            DISTRESSED/ROUTINE distinction; emergency detection is independent
            of this score by design. Does not override SMALL_TALK.
        llm_client: Injected LLM client; defaults to AnthropicClient().
        distressed_threshold: risk_level at or above this is treated as
            DISTRESSED rather than ROUTINE (when not EMERGENCY or SMALL_TALK).

    Returns:
        TriageResult with the resolved level and an internal reason string.
    """
    if not question or not question.strip():
        return TriageResult(level=TriageLevel.ROUTINE, reason="empty question")

    client = llm_client or AnthropicClient()
    classification = _classify_with_llm(question, client)

    if classification is None:
        # Fail-safe rule: any classifier failure or unparseable output is
        # treated as DISTRESSED, never ROUTINE. We cannot confirm safety,
        # so we do not default to the least cautious path.
        logger.warning("Triage classification failed; defaulting to DISTRESSED")
        return TriageResult(level=TriageLevel.DISTRESSED, reason="triage_unavailable")

    if classification == TriageLevel.EMERGENCY:
        return TriageResult(level=TriageLevel.EMERGENCY, reason="emergency_content_detected")

    if classification == TriageLevel.SMALL_TALK:
        return TriageResult(level=TriageLevel.SMALL_TALK, reason="small_talk_detected")

    if classification == TriageLevel.DISTRESSED:
        return TriageResult(level=TriageLevel.DISTRESSED, reason="distressed_content_detected")

    if risk_level >= distressed_threshold:
        return TriageResult(level=TriageLevel.DISTRESSED, reason=f"risk_level={risk_level:.2f}")

    return TriageResult(level=TriageLevel.ROUTINE, reason="no_emergency_or_distress_signal")
