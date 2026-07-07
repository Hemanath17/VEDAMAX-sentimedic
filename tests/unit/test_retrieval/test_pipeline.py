"""Unit tests for retrieval pipeline orchestration."""

from unittest.mock import MagicMock

from src.retrieval.hybrid_search import HybridHit
from src.retrieval.pipeline import Corpus, RetrievalPipeline, RetrievalStatus


def _hit(chunk_id: str, text: str, corpus: str, rrf: float = 1.0) -> HybridHit:
    return HybridHit(
        chunk_id=chunk_id,
        text=text,
        corpus=corpus,
        vector_score=0.8,
        bm25_score=0.5,
        rrf_score=rrf,
        metadata={"document_id": f"doc-{chunk_id}", "page_number": 1},
    )


def test_personal_question_with_authenticated_user_returns_no_user_docs():
    hybrid = MagicMock()
    hybrid.search.side_effect = [[], []]

    pipeline = RetrievalPipeline(
        hybrid_searcher=hybrid,
        reranker=MagicMock(),
    )

    result = pipeline.retrieve(
        query="Is my glucose high?",
        user_id="user-123",
        corpora=[Corpus.KB, Corpus.USER_DOC],
    )

    assert result.status == RetrievalStatus.NO_USER_DOCS
    assert result.chunks == []
    assert "No lab report" in (result.message or "")


def test_general_question_with_authenticated_user_uses_kb_only():
    hybrid = MagicMock()
    hybrid.search.return_value = [
        _hit("kb-1", "Normal fasting glucose is 70-99 mg/dL", "kb"),
    ]

    reranker = MagicMock()
    reranker.rerank.return_value = [(0, 2.5, 0.9)]

    pipeline = RetrievalPipeline(hybrid_searcher=hybrid, reranker=reranker)

    result = pipeline.retrieve(
        query="What is a normal fasting blood glucose level?",
        user_id="user-123",
        corpora=[Corpus.KB, Corpus.USER_DOC],
    )

    assert result.status != RetrievalStatus.NO_USER_DOCS
    assert hybrid.search.call_count == 1
    assert hybrid.search.call_args.kwargs["corpus"] == "kb"


def test_with_user_id_searches_both_corpora():
    hybrid = MagicMock()
    hybrid.search.side_effect = [
        [_hit("kb-1", "Hypertension overview", "kb")],
        [_hit("doc-1", "Glucose is 140 mg/dL", "user_doc", rrf=0.9)],
    ]

    reranker = MagicMock()
    reranker.rerank.return_value = [(1, 2.5, 0.9), (0, 1.1, 0.75)]

    pipeline = RetrievalPipeline(hybrid_searcher=hybrid, reranker=reranker)

    result = pipeline.retrieve(
        query="Should I worry about my glucose of 140?",
        user_id="user-123",
        corpora=[Corpus.KB, Corpus.USER_DOC],
    )

    assert result.status == RetrievalStatus.OK
    assert hybrid.search.call_count == 2
    assert {call.kwargs["corpus"] for call in hybrid.search.call_args_list} == {"kb", "user_doc"}
    assert result.kb_found is True
    assert result.user_doc_found is True


def test_below_threshold_blocks_weak_matches():
    hybrid = MagicMock()
    hybrid.search.return_value = [_hit("kb-1", "Unrelated text", "kb")]

    reranker = MagicMock()
    reranker.rerank.return_value = [(0, -4.0, 0.1)]

    pipeline = RetrievalPipeline(hybrid_searcher=hybrid, reranker=reranker)

    result = pipeline.retrieve(
        query="What is hypertension?",
        corpora=[Corpus.KB],
        score_floor=0.3,
    )

    assert result.status == RetrievalStatus.BELOW_THRESHOLD
    assert result.chunks == []
