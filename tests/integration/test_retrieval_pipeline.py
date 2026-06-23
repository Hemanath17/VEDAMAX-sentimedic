"""Integration-style tests for retrieval freshness behavior."""

from src.retrieval.hybrid_search import HybridSearcher


class FakeVectorStore:
    """Tiny in-memory vector store stub for BM25 freshness tests."""

    def __init__(self):
        self.chunks = {}

    def scroll_chunks(self, corpus, user_id=None, document_id=None, limit=100):
        rows = []
        for chunk in self.chunks.get((corpus, user_id or ""), []):
            if document_id and chunk["metadata"].get("document_id") != document_id:
                continue
            rows.append(chunk)
        return rows

    def search(self, query, corpus, user_id=None, top_k=10, score_threshold=None, document_id=None):
        results = []
        for chunk in self.scroll_chunks(corpus, user_id=user_id, document_id=document_id):
            if query.lower() in chunk["text"].lower():
                results.append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "score": 0.9,
                        "corpus": corpus,
                        "user_id": user_id or "",
                        "metadata": chunk["metadata"],
                    }
                )
        return results[:top_k]


def _chunk(chunk_id, text, document_id):
    return {
        "chunk_id": chunk_id,
        "text": text,
        "corpus": "user_doc",
        "user_id": "user-1",
        "metadata": {"document_id": document_id, "page_number": 1},
    }


def test_deleted_doc_not_retrievable_after_index_rebuild():
    store = FakeVectorStore()
    store.chunks[("user_doc", "user-1")] = [
        _chunk("a", "glucose 140 mg/dL", "doc-1"),
        _chunk("b", "cholesterol 200 mg/dL", "doc-2"),
    ]

    searcher = HybridSearcher(vector_store=store, max_cached_indexes=4)
    first = searcher.search("glucose", corpus="user_doc", user_id="user-1", top_k=5)
    assert [hit.chunk_id for hit in first] == ["a"]

    store.chunks[("user_doc", "user-1")] = [_chunk("b", "cholesterol 200 mg/dL", "doc-2")]
    second = searcher.search("glucose", corpus="user_doc", user_id="user-1", top_k=5)
    assert second == []


def test_new_doc_becomes_searchable_without_manual_restart():
    store = FakeVectorStore()
    store.chunks[("user_doc", "user-1")] = []

    searcher = HybridSearcher(vector_store=store, max_cached_indexes=4)
    assert searcher.search("glucose", corpus="user_doc", user_id="user-1", top_k=5) == []

    store.chunks[("user_doc", "user-1")] = [_chunk("a", "glucose 140 mg/dL", "doc-1")]
    refreshed = searcher.search("glucose", corpus="user_doc", user_id="user-1", top_k=5)
    assert [hit.chunk_id for hit in refreshed] == ["a"]
