"""Request validation: enforce sane limits on incoming query input
before it reaches triage, retrieval, or generation."""

from __future__ import annotations

from fastapi import HTTPException

MAX_QUESTION_LENGTH = 2000
MIN_QUESTION_LENGTH = 1


def validate_question(question: str) -> str:
    """Reject empty, whitespace-only, or absurdly long questions."""
    stripped = question.strip()

    if len(stripped) < MIN_QUESTION_LENGTH:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    if len(stripped) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Question too long (max {MAX_QUESTION_LENGTH} characters).",
        )

    return stripped
