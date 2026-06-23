"""End-to-end retrieval orchestration for dual-corpus medical RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from src.config.constants import RERANK_POOL_MAX, RETRIEVAL_SCORE_FLOOR
from src.config.logging_config import get_logger
from src.config.settings import settings
from src.retrieval.hybrid_search import HybridHit, HybridSearcher
from src.retrieval.reranker import CrossEncoderReranker

logger = get_logger(__name__)

class Corpus(str, Enum):
    KB = "kb"
    USER_DOC = "user_doc"


class RetrievalStatus(str, Enum):
    OK = "ok"
    NO_USER_DOCS = "no_user_docs"
    BELOW_THRESHOLD = "below_threshold"
    EMPTY = "empty"


@dataclass
class RetrievedChunk:
    """One piece of evidence. Phase 7 reads these to ground its answer."""

    chunk_id: str
    text: str
    corpus: Corpus
    score: float
    vector_score: float
    rerank_score: float
    metadata: dict

    @property
    def source_ref(self) -> str:
        doc = self.metadata.get("document_id", "unknown")
        page = self.metadata.get("page_number")
        return f"{doc}" + (f", p.{page}" if page else "")


@dataclass
class RetrievalResult:
    """Stable contract for Phase 7 generation."""

    status: RetrievalStatus
    chunks: list[RetrievedChunk] = field(default_factory=list)
    kb_found: bool = False
    user_doc_found: bool = False
    message: Optional[str] = None
    query: str = ""


class RetrievalPipeline:
    """Hybrid retrieval + reranking across KB and user document corpora."""

    def __init__(
        self,
        hybrid_searcher: Optional[HybridSearcher] = None,
        reranker: Optional[CrossEncoderReranker] = None,
    ) -> None:
        self.hybrid_searcher = hybrid_searcher or HybridSearcher()
        self.reranker = reranker or CrossEncoderReranker()

    def retrieve(
        self,
        query: str,
        user_id: Optional[str] = None,
        corpora: Optional[Sequence[Corpus]] = None,
        document_id: Optional[str] = None,
        score_floor: float = RETRIEVAL_SCORE_FLOOR,
    ) -> RetrievalResult:
        """Retrieve grounded evidence for a query."""
        if not query or not query.strip():
            return RetrievalResult(
                status=RetrievalStatus.EMPTY,
                message="Query is empty.",
                query=query or "",
            )

        requested_corpora = list(corpora or [Corpus.KB, Corpus.USER_DOC])
        resolved_corpora = self._resolve_corpora(query, requested_corpora, user_id)

        user_doc_requested = Corpus.USER_DOC in requested_corpora
        user_doc_searched = Corpus.USER_DOC in resolved_corpora

        per_corpus_hits: dict[Corpus, List[HybridHit]] = {}
        for corpus in resolved_corpora:
            hits = self.hybrid_searcher.search(
                query=query,
                corpus=corpus.value,
                user_id=user_id if corpus == Corpus.USER_DOC else None,
                document_id=document_id if corpus == Corpus.USER_DOC else None,
                top_k=settings.VECTOR_SEARCH_TOP_K,
            )
            per_corpus_hits[corpus] = hits

        if (
            user_doc_requested
            and user_id
            and user_doc_searched
            and not per_corpus_hits.get(Corpus.USER_DOC)
        ):
            return RetrievalResult(
                status=RetrievalStatus.NO_USER_DOCS,
                message="No lab report or uploaded document was found for this user.",
                query=query,
            )

        candidate_pool = self._merge_candidates(per_corpus_hits)
        if not candidate_pool:
            return RetrievalResult(
                status=RetrievalStatus.EMPTY,
                message="No matching evidence was found.",
                query=query,
            )

        candidate_pool = candidate_pool[:RERANK_POOL_MAX]
        rerank_input = [(hit.chunk_id, hit.text) for hit in candidate_pool]
        reranked = self.reranker.rerank(
            query=query,
            candidates=rerank_input,
            top_k=settings.RERANKER_TOP_K,
        )

        if not reranked:
            return RetrievalResult(
                status=RetrievalStatus.BELOW_THRESHOLD,
                message="Retrieved evidence was not relevant enough to answer safely.",
                query=query,
            )

        best_normalized = reranked[0][2]
        if best_normalized < score_floor:
            return RetrievalResult(
                status=RetrievalStatus.BELOW_THRESHOLD,
                message="Retrieved evidence was not relevant enough to answer safely.",
                query=query,
            )

        chunks: List[RetrievedChunk] = []
        kb_found = False
        user_doc_found = False

        for candidate_idx, raw_score, normalized_score in reranked:
            hit = candidate_pool[candidate_idx]
            corpus = Corpus(hit.corpus)
            if corpus == Corpus.KB:
                kb_found = True
            if corpus == Corpus.USER_DOC:
                user_doc_found = True

            chunks.append(
                RetrievedChunk(
                    chunk_id=hit.chunk_id,
                    text=hit.text,
                    corpus=corpus,
                    score=normalized_score,
                    vector_score=hit.vector_score,
                    rerank_score=raw_score,
                    metadata=hit.metadata,
                )
            )

        return RetrievalResult(
            status=RetrievalStatus.OK,
            chunks=chunks,
            kb_found=kb_found,
            user_doc_found=user_doc_found,
            query=query,
        )

    def _resolve_corpora(
        self,
        query: str,
        corpora: List[Corpus],
        user_id: Optional[str],
    ) -> List[Corpus]:
        """Apply guardrails; search both corpora whenever a user document is allowed."""
        resolved = list(corpora)

        if Corpus.USER_DOC in resolved and not user_id:
            resolved = [corpus for corpus in resolved if corpus != Corpus.USER_DOC]
            logger.debug("Dropped USER_DOC corpus because user_id is missing")

        return resolved or [Corpus.KB]

    @staticmethod
    def _merge_candidates(per_corpus_hits: dict[Corpus, List[HybridHit]]) -> List[HybridHit]:
        """Merge per-corpus hybrid hits and deduplicate by chunk_id."""
        merged: dict[str, HybridHit] = {}
        for hits in per_corpus_hits.values():
            for hit in hits:
                existing = merged.get(hit.chunk_id)
                if existing is None or hit.rrf_score > existing.rrf_score:
                    merged[hit.chunk_id] = hit
        return sorted(merged.values(), key=lambda item: item.rrf_score, reverse=True)
