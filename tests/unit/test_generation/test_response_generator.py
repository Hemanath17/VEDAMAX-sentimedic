"""Unit tests for response generation orchestration."""

from unittest.mock import MagicMock

import pytest

from src.generation.llm_client import LLMError
from src.generation.response_generator import ResponseGenerator
from src.retrieval.pipeline import Corpus, RetrievalResult, RetrievalStatus, RetrievedChunk


def _chunk(chunk_id: str, text: str, corpus: Corpus) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        corpus=corpus,
        score=0.9,
        vector_score=0.8,
        rerank_score=1.0,
        metadata={"document_id": f"doc-{chunk_id}"},
    )


def _ok_result() -> RetrievalResult:
    return RetrievalResult(
        status=RetrievalStatus.OK,
        chunks=[
            _chunk("kb-1", "Fasting glucose reference range is 70-99 mg/dL.", Corpus.KB),
            _chunk("u-1", "Patient glucose: 140 mg/dL.", Corpus.USER_DOC),
        ],
        kb_found=True,
        user_doc_found=True,
    )


@pytest.mark.parametrize(
    "status,message",
    [
        (RetrievalStatus.NO_USER_DOCS, "No lab report or uploaded document was found for this user."),
        (RetrievalStatus.BELOW_THRESHOLD, "Retrieved evidence was not relevant enough to answer safely."),
        (RetrievalStatus.EMPTY, "No matching evidence was found."),
    ],
)
def test_status_gate_returns_safe_message_without_calling_llm(status, message):
    llm = MagicMock()
    generator = ResponseGenerator(llm_client=llm)

    result = generator.generate(
        question="Is my glucose high?",
        retrieval_result=RetrievalResult(status=status, message=message),
    )

    llm.generate.assert_not_called()
    assert result.answer == message
    assert result.status == status
    assert result.used_patient_data is False
    assert result.citations == []


def test_llm_error_returns_safe_fallback():
    llm = MagicMock()
    llm.generate.side_effect = LLMError("API down")
    generator = ResponseGenerator(llm_client=llm)

    result = generator.generate(
        question="Is my glucose high?",
        retrieval_result=_ok_result(),
    )

    assert result.status == "llm_error"
    assert "trouble generating" in result.answer.lower()
    assert result.citations == []
    llm.generate.assert_called_once()


def test_successful_generation_validates_citations_and_sets_metadata():
    llm = MagicMock()
    llm.generate.return_value = (
        "A typical fasting range is 70-99 mg/dL [S1]. "
        "Your report shows 140 mg/dL [S2], which is above that range [S99]."
    )
    generator = ResponseGenerator(llm_client=llm)

    result = generator.generate(
        question="Is my glucose high?",
        retrieval_result=_ok_result(),
        persona="The user seems anxious; be reassuring and gentle.",
    )

    assert result.status == RetrievalStatus.OK
    assert result.used_patient_data is True
    assert "[S99]" not in result.answer
    assert len(result.citations) == 2
    assert result.disclaimer
    llm.generate.assert_called_once()
