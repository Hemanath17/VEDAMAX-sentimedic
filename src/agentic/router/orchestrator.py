"""
Triage-aware orchestrator: wraps the existing retrieval + generation pipeline
with an emergency bypass. Does not modify RetrievalPipeline or
ResponseGenerator — both remain exactly as validated in Phase 6/7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.agentic.router.triage_agent import TriageLevel, TriageResult, run_triage
from src.config.logging_config import get_logger
from src.context.context_manager import ContextManager
from src.generation.llm_client import LLMError
from src.generation.response_generator import GeneratedAnswer, ResponseGenerator
from src.retrieval.pipeline import RetrievalPipeline

logger = get_logger(__name__)

# Fixed, reviewed message. The LLM never generates this text — see module
# docstring in triage_agent.py for why that matters.
_EMERGENCY_MESSAGE = (
    "This sounds like it may be a medical emergency. I'm not able to help with "
    "emergencies — please contact emergency services right away (in the US, call "
    "911) or go to your nearest emergency room. If you are thinking about harming "
    "yourself, you can call or text 988 (Suicide & Crisis Lifeline) in the US, "
    "available 24/7."
)

_SMALL_TALK_FALLBACK = (
    "Hi! I'm here whenever you're ready to talk. How can I help you today?"
)

_SMALL_TALK_SYSTEM_PROMPT = (
    "You are VEDAMAX, a warm, calm health information assistant with the "
    "personality of Baymax from Big Hero 6 -- caring, gentle, and reassuring. "
    "The user is having a casual conversation. Respond warmly and briefly "
    "(2-3 sentences maximum). If the conversation summary mentions prior "
    "health topics the user discussed, you may gently acknowledge them but "
    "do not bring up medical details unprompted. Never diagnose, prescribe, "
    "or give medical advice in this reply. Just be a warm, present friend."
)


@dataclass
class TriagedAnswer:
    answer_text: str
    triage_level: TriageLevel
    generated: Optional[GeneratedAnswer] = None  # None when triage_level == EMERGENCY


class TriageOrchestrator:
    """Routes a question through triage before retrieval/generation."""

    def __init__(
        self,
        retrieval_pipeline: Optional[RetrievalPipeline] = None,
        response_generator: Optional[ResponseGenerator] = None,
        context_manager: Optional[ContextManager] = None,
    ) -> None:
        self.retrieval_pipeline = retrieval_pipeline or RetrievalPipeline()
        self.response_generator = response_generator or ResponseGenerator()
        self.context_manager = context_manager or ContextManager()

    def _memory_user_id(self, user_id: Optional[str]) -> str:
        return user_id or "anonymous"

    def _safe_process_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Record a message; degrade gracefully if Postgres/memory is unavailable."""
        try:
            self.context_manager.process_message(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
            )
        except Exception as exc:
            logger.warning(
                "Context memory unavailable for %s message in session %s: %s",
                role,
                session_id,
                exc,
                exc_info=True,
            )

    def _safe_get_personalization_context(self, user_id: str, session_id: str) -> Optional[str]:
        try:
            summary = self.context_manager.get_personalization_prompt_context(
                user_id=user_id,
                session_id=session_id,
            )
            return summary or None
        except Exception as exc:
            logger.warning(
                "Could not load personalization context for session %s: %s",
                session_id,
                exc,
                exc_info=True,
            )
            return None

    def _safe_get_escalation_alert(self, user_id: str, session_id: str) -> bool:
        """
        Read escalation_alert from ContextManager.

        This is an ADDITIONAL caution signal only — it never overrides triage.
        Phase 8's run_triage() EMERGENCY decision is the structural safety gate.
        """
        try:
            context = self.context_manager.get_context(user_id=user_id, session_id=session_id)
            return bool(context.get("escalation_alert"))
        except Exception as exc:
            logger.warning(
                "Could not read escalation alert for session %s: %s",
                session_id,
                exc,
                exc_info=True,
            )
            return False

    @staticmethod
    def _resolve_persona(
        triage_level: TriageLevel,
        escalation_alert: bool,
    ) -> Optional[str]:
        """
        Choose response persona.

        Triage always wins for EMERGENCY (handled before this is called).
        escalation_alert adds gentleness on ROUTINE turns but never bypasses
        retrieval/generation and never grants emergency status on its own.
        """
        if triage_level == TriageLevel.DISTRESSED:
            return "gentle_and_reassuring"
        if triage_level == TriageLevel.ROUTINE and escalation_alert:
            return "gentle_and_reassuring"
        return None

    def _generate_small_talk_reply(
        self,
        question: str,
        context_summary: Optional[str],
    ) -> str:
        """Generate a brief, warm reply for casual conversation turns."""
        user_parts = [f"User message: {question.strip()}"]
        if context_summary:
            user_parts.insert(0, f"Conversation summary:\n{context_summary}")
        user_prompt = "\n\n".join(user_parts)

        try:
            return self.response_generator.llm_client.generate(
                _SMALL_TALK_SYSTEM_PROMPT,
                user_prompt,
            ).strip()
        except LLMError as exc:
            logger.warning("Small-talk LLM call failed; using fallback reply: %s", exc)
            return _SMALL_TALK_FALLBACK

    def handle(
        self,
        question: str,
        session_id: str,
        user_id: Optional[str] = None,
        risk_level: float = 0.0,
    ) -> TriagedAnswer:
        """
        Run triage, then either return the fixed emergency message or proceed
        through the normal retrieve -> generate pipeline.
        """
        memory_user_id = self._memory_user_id(user_id)

        # Record every user turn before triage so memory accumulates regardless
        # of classification (small-talk, emergency, etc.).
        self._safe_process_message(
            user_id=memory_user_id,
            session_id=session_id,
            role="user",
            content=question,
        )

        triage_result: TriageResult = run_triage(question, risk_level=risk_level)

        # Phase 8 triage is the structural safety guarantee — it always wins
        # over ContextManager escalation signals and cannot be weakened by them.
        if triage_result.level == TriageLevel.EMERGENCY:
            self._safe_process_message(
                user_id=memory_user_id,
                session_id=session_id,
                role="assistant",
                content=_EMERGENCY_MESSAGE,
            )
            return TriagedAnswer(
                answer_text=_EMERGENCY_MESSAGE,
                triage_level=TriageLevel.EMERGENCY,
                generated=None,
            )

        if triage_result.level == TriageLevel.SMALL_TALK:
            context_summary = self._safe_get_personalization_context(
                memory_user_id, session_id
            )
            reply = self._generate_small_talk_reply(question, context_summary)
            self._safe_process_message(
                user_id=memory_user_id,
                session_id=session_id,
                role="assistant",
                content=reply,
            )
            return TriagedAnswer(
                answer_text=reply,
                triage_level=TriageLevel.SMALL_TALK,
                generated=None,
            )

        escalation_alert = self._safe_get_escalation_alert(memory_user_id, session_id)
        persona = self._resolve_persona(triage_result.level, escalation_alert)

        context_summary = self._safe_get_personalization_context(memory_user_id, session_id)

        retrieval_result = self.retrieval_pipeline.retrieve(question, user_id=user_id)
        generated = self.response_generator.generate(
            question=question,
            retrieval_result=retrieval_result,
            persona=persona,
            session_summary=context_summary,
        )

        self._safe_process_message(
            user_id=memory_user_id,
            session_id=session_id,
            role="assistant",
            content=generated.answer,
        )

        return TriagedAnswer(
            answer_text=generated.answer,
            triage_level=triage_result.level,
            generated=generated,
        )
