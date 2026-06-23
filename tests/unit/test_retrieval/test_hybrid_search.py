"""Unit tests for hybrid retrieval fusion."""

from unittest.mock import MagicMock

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


def test_tokenize_preserves_clinical_terms():
    from src.retrieval.hybrid_search import tokenize

    assert tokenize("Glucose 5.8 mmol/L and 140 mg/dL on X-ray follow-up.") == [
        "glucose",
        "5.8",
        "mmol/l",
        "and",
        "140",
        "mg/dl",
        "on",
        "x-ray",
        "follow-up",
    ]


def test_bm25_cache_is_bounded_and_evicts_oldest():
    searcher = HybridSearcher(vector_store=MagicMock(), max_cached_indexes=2)
    searcher._bm25_indexes[("user_doc", "u1")] = MagicMock()
    searcher._bm25_indexes[("user_doc", "u2")] = MagicMock()
    searcher._bm25_indexes[("user_doc", "u3")] = MagicMock()

    searcher._evict_if_needed()

    assert list(searcher._bm25_indexes.keys()) == [
        ("user_doc", "u2"),
        ("user_doc", "u3"),
    ]
