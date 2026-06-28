"""
Triage-aware orchestrator: wraps the existing retrieval + generation pipeline
with an emergency bypass. Does not modify RetrievalPipeline or
ResponseGenerator — both remain exactly as validated in Phase 6/7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.agentic.router.triage_agent import TriageLevel, TriageResult, run_triage
from src.generation.response_generator import GeneratedAnswer, ResponseGenerator
from src.retrieval.pipeline import RetrievalPipeline

# Fixed, reviewed message. The LLM never generates this text — see module
# docstring in triage_agent.py for why that matters.
_EMERGENCY_MESSAGE = (
    "This sounds like it may be a medical emergency. I'm not able to help with "
    "emergencies — please contact emergency services right away (in the US, call "
    "911) or go to your nearest emergency room. If you are thinking about harming "
    "yourself, you can call or text 988 (Suicide & Crisis Lifeline) in the US, "
    "available 24/7."
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
    ) -> None:
        self.retrieval_pipeline = retrieval_pipeline or RetrievalPipeline()
        self.response_generator = response_generator or ResponseGenerator()

    def handle(
        self,
        question: str,
        user_id: Optional[str] = None,
        risk_level: float = 0.0,
        session_summary: Optional[str] = None,
    ) -> TriagedAnswer:
        """
        Run triage, then either return the fixed emergency message or proceed
        through the normal retrieve -> generate pipeline.
        """
        triage_result: TriageResult = run_triage(question, risk_level=risk_level)

        if triage_result.level == TriageLevel.EMERGENCY:
            return TriagedAnswer(
                answer_text=_EMERGENCY_MESSAGE,
                triage_level=TriageLevel.EMERGENCY,
                generated=None,
            )

        persona = "gentle_and_reassuring" if triage_result.level == TriageLevel.DISTRESSED else None

        retrieval_result = self.retrieval_pipeline.retrieve(question, user_id=user_id)
        generated = self.response_generator.generate(
            question=question,
            retrieval_result=retrieval_result,
            persona=persona,
            session_summary=session_summary,
        )

        return TriagedAnswer(
            answer_text=generated.answer,
            triage_level=triage_result.level,
            generated=generated,
        )