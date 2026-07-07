"""Query route: the single entry point for asking the assistant a question."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.agentic.router.orchestrator import TriageOrchestrator
from src.api.middleware.validation import validate_question

router = APIRouter(prefix="/query", tags=["query"])

_orchestrator = TriageOrchestrator()


class QueryRequest(BaseModel):
    question: str
    session_id: str
    user_id: Optional[str] = None
    risk_level: float = 0.0


class CitationResponse(BaseModel):
    marker: str
    source_ref: str
    corpus: str


class QueryResponse(BaseModel):
    answer: str
    triage_level: str
    citations: List[CitationResponse] = []
    disclaimer: str = ""
    flagged_numbers: List[str] = []


@router.post("", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest) -> QueryResponse:
    """Run a question through triage, retrieval, and generation."""
    verified_user_id = getattr(request.state, "user_id", None)
    user_id = verified_user_id or body.user_id

    question = validate_question(body.question)

    result = _orchestrator.handle(
        question=question,
        session_id=body.session_id,
        user_id=user_id,
        risk_level=body.risk_level,
    )

    citations: List[CitationResponse] = []
    disclaimer = ""
    flagged_numbers: List[str] = []

    if result.generated is not None:
        citations = [
            CitationResponse(
                marker=c.marker,
                source_ref=c.source_ref,
                corpus=c.corpus.value,
            )
            for c in result.generated.citations
        ]
        disclaimer = result.generated.disclaimer
        flagged_numbers = result.generated.flagged_numbers

    return QueryResponse(
        answer=result.answer_text,
        triage_level=result.triage_level.value,
        citations=citations,
        disclaimer=disclaimer,
        flagged_numbers=flagged_numbers,
    )
