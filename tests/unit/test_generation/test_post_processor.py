"""Unit tests for post-generation validation helpers."""

from src.generation.post_processor import validate_citations, verify_numbers
from src.retrieval.pipeline import Corpus, RetrievalResult, RetrievalStatus, RetrievedChunk


def _chunk(
    chunk_id: str,
    text: str,
    corpus: Corpus = Corpus.USER_DOC,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        corpus=corpus,
        score=0.9,
        vector_score=0.8,
        rerank_score=1.0,
        metadata={"document_id": f"doc-{chunk_id}", "page_number": 1},
    )


def test_validate_citations_drops_unknown_marker():
    chunk = _chunk("c1", "Glucose is 140 mg/dL")
    marker_map = {"[S1]": chunk}

    cleaned, citations = validate_citations(
        "Your glucose is 140 mg/dL [S1]. This is high [S99].",
        marker_map,
    )

    assert "[S99]" not in cleaned
    assert "[S1]" in cleaned
    assert len(citations) == 1
    assert citations[0].marker == "[S1]"
    assert citations[0].corpus == Corpus.USER_DOC


def test_verify_numbers_flags_hallucinated_value_not_in_any_chunk():
    retrieval = RetrievalResult(
        status=RetrievalStatus.OK,
        chunks=[
            _chunk("u1", "Glucose is 140 mg/dL", Corpus.USER_DOC),
            _chunk("k1", "Normal fasting glucose is 70-99 mg/dL", Corpus.KB),
        ],
        kb_found=True,
        user_doc_found=True,
    )

    flagged = verify_numbers(
        "Your glucose is 140 mg/dL and your cholesterol is 250 mg/dL.",
        retrieval,
    )

    assert "140" not in flagged
    assert "250" in flagged


def test_verify_numbers_flags_substring_of_real_patient_number():
    retrieval = RetrievalResult(
        status=RetrievalStatus.OK,
        chunks=[_chunk("u1", "Glucose is 250 mg/dL", Corpus.USER_DOC)],
        user_doc_found=True,
    )

    flagged = verify_numbers("Your glucose is 25 mg/dL.", retrieval)

    assert "25" in flagged
    assert "250" not in flagged


def test_verify_numbers_does_not_flag_kb_normal_range_number():
    retrieval = RetrievalResult(
        status=RetrievalStatus.OK,
        chunks=[
            _chunk("u1", "Patient glucose: 140 mg/dL", Corpus.USER_DOC),
            _chunk("k1", "Normal fasting glucose range is 70-99 mg/dL", Corpus.KB),
        ],
        kb_found=True,
        user_doc_found=True,
    )

    flagged = verify_numbers(
        "A typical fasting range is 70-99 mg/dL; your report shows 140 mg/dL.",
        retrieval,
    )

    assert flagged == []


def test_verify_numbers_returns_empty_when_no_numbers():
    retrieval = RetrievalResult(
        status=RetrievalStatus.OK,
        chunks=[_chunk("u1", "Mild elevation noted", Corpus.USER_DOC)],
        user_doc_found=True,
    )

    assert verify_numbers("No numeric values here.", retrieval) == []
