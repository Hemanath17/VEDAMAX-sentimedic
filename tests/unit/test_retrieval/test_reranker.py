"""Unit tests for reranker behavior and fallback mode."""

from src.retrieval.reranker import CrossEncoderReranker


def test_reranker_fallback_returns_passing_scores():
    reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
    reranker._model = None

    ranked = reranker.rerank(
        query="What does glucose 140 mean?",
        candidates=[("a", "glucose 140 mg/dL"), ("b", "blood pressure guidance")],
        top_k=2,
    )

    assert ranked[0][2] >= 0.5
    assert ranked[1][2] >= 0.5
    assert ranked[0][2] >= ranked[1][2]
