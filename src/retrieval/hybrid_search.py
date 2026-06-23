"""Hybrid BM25 + dense vector retrieval with per-corpus RRF fusion."""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

from src.config.constants import CORPUS_KB, CORPUS_USER_DOC, RRF_K
from src.config.logging_config import get_logger
from src.config.settings import settings
from src.retrieval.vector_store.vector_store import VectorStore

logger = get_logger(__name__)

# Preserve clinical tokens like "5.8", "mg/dl", "x-ray", and "covid-19".
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[./%-][a-z0-9]+)*")
DEFAULT_BM25_CACHE_SIZE = 128


def tokenize(text: str) -> List[str]:
    """Simple lowercase tokenizer for BM25."""
    return _TOKEN_PATTERN.findall(text.lower())


@dataclass
class HybridHit:
    """Single hybrid retrieval candidate before reranking."""

    chunk_id: str
    text: str
    corpus: str
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BM25Index:
    """In-memory BM25 index for one corpus partition."""

    def __init__(self) -> None:
        self._chunks: List[Dict[str, Any]] = []
        self._bm25: Optional[BM25Okapi] = None

    def build(self, chunks: List[Dict[str, Any]]) -> None:
        """Build BM25 index from chunk records."""
        self._chunks = [c for c in chunks if c.get("text", "").strip()]
        tokenized = [tokenize(chunk["text"]) for chunk in self._chunks]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None
        logger.debug(f"Built BM25 index with {len(self._chunks)} chunks")

    def search(self, query: str, top_k: int) -> List[Tuple[Dict[str, Any], float]]:
        """Return top-k chunks with BM25 scores."""
        if not self._bm25 or not self._chunks:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        ranked = sorted(
            zip(self._chunks, scores),
            key=lambda item: item[1],
            reverse=True,
        )
        return [(chunk, float(score)) for chunk, score in ranked[:top_k] if score > 0]


class HybridSearcher:
    """
    Hybrid search per corpus partition.

    Dense and sparse retrieval are fused with RRF within each corpus independently.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        max_cached_indexes: int = DEFAULT_BM25_CACHE_SIZE,
    ) -> None:
        self.vector_store = vector_store or VectorStore()
        self.max_cached_indexes = max_cached_indexes
        self._bm25_indexes: "OrderedDict[Tuple[str, str], BM25Index]" = OrderedDict()

    def index_key(self, corpus: str, user_id: str = "") -> Tuple[str, str]:
        """Cache key for BM25 index partitions."""
        if corpus == CORPUS_USER_DOC:
            return (corpus, user_id)
        return (corpus, "")

    def rebuild_index(
        self,
        corpus: str,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> int:
        """
        Rebuild BM25 index for a corpus partition from Qdrant.

        Returns:
            Number of chunks indexed
        """
        normalized_user_id = user_id or ""
        if corpus == CORPUS_USER_DOC and not normalized_user_id:
            raise ValueError("user_id is required to rebuild user_doc BM25 index")

        chunks = self.vector_store.scroll_chunks(
            corpus=corpus,
            user_id=normalized_user_id or None,
            document_id=document_id,
        )
        key = self.index_key(corpus, normalized_user_id)
        index = BM25Index()
        index.build(chunks)
        self._bm25_indexes.pop(key, None)
        self._bm25_indexes[key] = index
        self._evict_if_needed()
        logger.info(
            f"Rebuilt BM25 index for corpus='{corpus}' user_id='{normalized_user_id or 'n/a'}' "
            f"({len(chunks)} chunks)"
        )
        return len(chunks)

    def ensure_index(
        self,
        corpus: str,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> None:
        """Build BM25 index lazily if missing."""
        normalized_user_id = user_id or ""
        self.rebuild_index(
            corpus,
            user_id=normalized_user_id or None,
            document_id=document_id,
        )

    def invalidate_index(
        self,
        corpus: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Drop one cached BM25 index so the next query rebuilds it."""
        key = self.index_key(corpus, user_id or "")
        removed = self._bm25_indexes.pop(key, None)
        if removed is not None:
            logger.info(
                f"Invalidated BM25 index for corpus='{corpus}' user_id='{user_id or 'n/a'}'"
            )

    def invalidate_all(self) -> None:
        """Clear all cached BM25 indexes."""
        self._bm25_indexes.clear()

    def _evict_if_needed(self) -> None:
        """Bound BM25 cache growth with oldest-entry eviction."""
        while len(self._bm25_indexes) > self.max_cached_indexes:
            evicted_key, _ = self._bm25_indexes.popitem(last=False)
            logger.info(
                "Evicted BM25 index from cache: "
                f"corpus='{evicted_key[0]}' user_id='{evicted_key[1] or 'n/a'}'"
            )

    def search(
        self,
        query: str,
        corpus: str,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[HybridHit]:
        """
        Hybrid search within a single corpus using RRF fusion.

        Args:
            query: Search query
            corpus: ``kb`` or ``user_doc``
            user_id: Required for ``user_doc``
            document_id: Optional document filter
            top_k: Number of fused hits to return

        Returns:
            List of HybridHit ordered by fused RRF score
        """
        top_k = top_k or settings.VECTOR_SEARCH_TOP_K
        normalized_user_id = user_id or ""

        if settings.HYBRID_SEARCH_ENABLED:
            self.ensure_index(corpus, user_id=normalized_user_id or None, document_id=document_id)

        vector_hits = self.vector_store.search(
            query=query,
            corpus=corpus,
            user_id=normalized_user_id or None,
            top_k=top_k,
            document_id=document_id,
        )

        if not settings.HYBRID_SEARCH_ENABLED:
            return [
                HybridHit(
                    chunk_id=hit["chunk_id"],
                    text=hit["text"],
                    corpus=hit.get("corpus", corpus),
                    vector_score=float(hit["score"]),
                    bm25_score=0.0,
                    rrf_score=float(hit["score"]),
                    metadata=hit.get("metadata", {}),
                )
                for hit in vector_hits
            ]

        key = self.index_key(corpus, normalized_user_id)
        bm25_index = self._bm25_indexes.get(key)
        if bm25_index is not None:
            self._bm25_indexes.move_to_end(key)
        bm25_hits = (
            bm25_index.search(query, top_k=top_k) if bm25_index else []
        )

        return self._fuse_rrf(vector_hits, bm25_hits, corpus=corpus, top_k=top_k)

    @staticmethod
    def _fuse_rrf(
        vector_hits: List[Dict[str, Any]],
        bm25_hits: List[Tuple[Dict[str, Any], float]],
        corpus: str,
        top_k: int,
        rrf_k: int = RRF_K,
    ) -> List[HybridHit]:
        """Fuse dense and sparse rankings with reciprocal rank fusion."""
        fused: Dict[str, HybridHit] = {}

        for rank, hit in enumerate(vector_hits, start=1):
            chunk_id = hit["chunk_id"]
            fused[chunk_id] = HybridHit(
                chunk_id=chunk_id,
                text=hit["text"],
                corpus=hit.get("corpus", corpus),
                vector_score=float(hit["score"]),
                bm25_score=0.0,
                rrf_score=1.0 / (rrf_k + rank),
                metadata=hit.get("metadata", {}),
            )

        for rank, (chunk, score) in enumerate(bm25_hits, start=1):
            chunk_id = chunk["chunk_id"]
            rrf_component = 1.0 / (rrf_k + rank)
            if chunk_id in fused:
                fused[chunk_id].bm25_score = float(score)
                fused[chunk_id].rrf_score += rrf_component
            else:
                fused[chunk_id] = HybridHit(
                    chunk_id=chunk_id,
                    text=chunk["text"],
                    corpus=chunk.get("corpus", corpus),
                    vector_score=0.0,
                    bm25_score=float(score),
                    rrf_score=rrf_component,
                    metadata=chunk.get("metadata", {}),
                )

        ranked = sorted(fused.values(), key=lambda hit: hit.rrf_score, reverse=True)
        return ranked[:top_k]
