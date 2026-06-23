"""Unit tests for hybrid retrieval fusion."""

from src.retrieval.hybrid_search import HybridSearcher


def test_rrf_fuses_vector_and_bm25_rankings():
    vector_hits = [
        {"chunk_id": "a", "text": "alpha", "score": 0.9, "metadata": {}},
        {"chunk_id": "b", "text": "beta", "score": 0.8, "metadata": {}},
    ]
    bm25_hits = [
        ({"chunk_id": "b", "text": "beta", "metadata": {}}, 3.5),
        ({"chunk_id": "c", "text": "gamma", "metadata": {}}, 2.1),
    ]

    fused = HybridSearcher._fuse_rrf(vector_hits, bm25_hits, corpus="kb", top_k=3)

    assert [hit.chunk_id for hit in fused] == ["b", "a", "c"]
    assert fused[0].bm25_score == 3.5
    assert fused[0].vector_score == 0.8
