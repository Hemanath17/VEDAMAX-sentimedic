"""Orchestrates grounded answer generation from retrieval evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from src.generation.llm_client import LLMClient, LLMError, OpenAIClient
from src.generation.post_processor import (
    Citation,
    build_disclaimer,
    validate_citations,
    verify_numbers,
)
from src.generation.prompt_templates.system_prompts import build_system_prompt
from src.generation.prompt_templates.user_prompts import build_user_prompt
from src.retrieval.pipeline import RetrievalResult, RetrievalStatus

_LLM_ERROR_MESSAGE = (
    "I'm having trouble generating a response right now. Please try again."
)


@dataclass
class GeneratedAnswer:
    """Final grounded answer with validation metadata."""

    answer: str
    citations: List[Citation] = field(default_factory=list)
    disclaimer: str = ""
    status: Union[RetrievalStatus, str] = RetrievalStatus.OK
    used_patient_data: bool = False
    flagged_numbers: List[str] = field(default_factory=list)


class ResponseGenerator:
    """
    Turn retrieval evidence into a safe, cited medical information response.

    Applies a status gate before calling the LLM, then validates citations and
    patient-specific numbers in the model output.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm_client = llm_client or OpenAIClient()

    def generate(
        self,
        question: str,
        retrieval_result: RetrievalResult,
        persona: Optional[str] = None,
        session_summary: Optional[str] = None,
    ) -> GeneratedAnswer:
        """
        Generate a grounded answer from retrieval evidence.

        Args:
            question: User health question.
            retrieval_result: Evidence and status from the retrieval pipeline.
            persona: Optional tone guidance for empathetic responses.
            session_summary: Optional condensed conversation history.

        Returns:
            GeneratedAnswer with validated text, citations, and disclaimer.
        """
        if retrieval_result.status != RetrievalStatus.OK:
            return GeneratedAnswer(
                answer=retrieval_result.message or "Unable to answer this question safely.",
                citations=[],
                disclaimer=build_disclaimer(retrieval_result.status),
                status=retrieval_result.status,
                used_patient_data=False,
                flagged_numbers=[],
            )

        system_prompt = build_system_prompt(persona)
        user_prompt, marker_to_chunk = build_user_prompt(
            question=question,
            retrieval_result=retrieval_result,
            session_summary=session_summary,
        )

        try:
            raw_answer = self.llm_client.generate(system_prompt, user_prompt)
        except LLMError:
            return GeneratedAnswer(
                answer=_LLM_ERROR_MESSAGE,
                citations=[],
                disclaimer=build_disclaimer("llm_error"),
                status="llm_error",
                used_patient_data=retrieval_result.user_doc_found,
                flagged_numbers=[],
            )

        cleaned_answer, citations = validate_citations(raw_answer, marker_to_chunk)
        flagged_numbers = verify_numbers(cleaned_answer, retrieval_result)

        return GeneratedAnswer(
            answer=cleaned_answer,
            citations=citations,
            disclaimer=build_disclaimer(RetrievalStatus.OK),
            status=RetrievalStatus.OK,
            used_patient_data=retrieval_result.user_doc_found,
            flagged_numbers=flagged_numbers,
        )
