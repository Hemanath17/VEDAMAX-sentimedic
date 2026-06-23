"""Cross-encoder reranking for retrieved chunks."""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from src.config.logging_config import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None  # type: ignore


def sigmoid(score: float) -> float:
    """Map cross-encoder logit to a 0-1 confidence scale."""
    if score >= 0:
        z = math.exp(-score)
        return 1.0 / (1.0 + z)
    z = math.exp(score)
    return z / (1.0 + z)


class CrossEncoderReranker:
    """Rerank candidate chunks with a cross-encoder model."""

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None) -> None:
        self.model_name = model_name or settings.RERANKER_MODEL
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        if not CROSS_ENCODER_AVAILABLE:
            logger.warning("sentence-transformers CrossEncoder not available; reranking disabled")
            return

        try:
            self._model = CrossEncoder(self.model_name, device=self.device)
            logger.info(f"Loaded reranker model: {self.model_name}")
        except Exception as exc:
            logger.error(f"Failed to load reranker model: {exc}", exc_info=True)
            self._model = None

    def rerank(
        self,
        query: str,
        candidates: Sequence[Tuple[str, str]],
        top_k: Optional[int] = None,
    ) -> List[Tuple[int, float, float]]:
        """
        Score (index, raw_score, normalized_score) tuples for query-chunk pairs.

        Args:
            query: User query
            candidates: Sequence of (chunk_id, chunk_text)
            top_k: Number of results to keep

        Returns:
            Ranked list of (candidate_index, raw_score, normalized_score)
        """
        if not candidates:
            return []

        top_k = top_k or settings.RERANKER_TOP_K

        if self._model is None:
            logger.warning("Reranker unavailable; returning fused-order fallback scores")
            fallback = []
            for idx in range(min(top_k, len(candidates))):
                normalized_score = max(0.5, 1.0 - (idx * 0.05))
                fallback.append((idx, normalized_score, normalized_score))
            return fallback

        pairs = [[query, text] for _, text in candidates]
        raw_scores = self._model.predict(pairs)
        scored = [
            (idx, float(raw_scores[idx]), sigmoid(float(raw_scores[idx])))
            for idx in range(len(candidates))
        ]
        scored.sort(key=lambda item: item[2], reverse=True)
        return scored[:top_k]
