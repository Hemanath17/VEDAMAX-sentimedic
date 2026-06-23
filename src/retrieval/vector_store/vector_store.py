"""
Step 8: Vector Storage Integration (Main Orchestrator)

Provides a single interface for storing and searching vectors across two Qdrant
collections partitioned by corpus:
  - medical_knowledge_base  -> corpus="kb"
  - user_documents          -> corpus="user_doc" (scoped by user_id)
"""

from typing import List, Dict, Any, Optional
from uuid import uuid4

try:
    from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
except ImportError:
    PointStruct = None  # type: ignore
    Filter = None  # type: ignore
    FieldCondition = None  # type: ignore
    MatchValue = None  # type: ignore

from src.retrieval.vector_store.qdrant_client import QdrantClient
from src.retrieval.vector_store.embeddings import EmbeddingModel
from src.retrieval.vector_store.embedding_pipeline import EmbeddingPipeline
from src.retrieval.vector_store.embedding_cache import EmbeddingCache
from src.retrieval.vector_store.collection_manager import CollectionManager
from src.config.settings import settings
from src.config.constants import CORPUS_KB, CORPUS_USER_DOC, VALID_CORPORA
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    Main vector store orchestrator with dual-corpus partitioning.

    Chunks are stored in one of two Qdrant collections based on ``corpus``:
    - ``kb``        -> general medical knowledge base
    - ``user_doc``  -> patient-specific uploads, filtered by ``user_id`` at query time

    Every stored point includes payload tags ``corpus`` and ``user_id``.
    """

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        use_cache: bool = True,
    ):
        """
        Initialize vector store and ensure both corpus collections exist.

        Args:
            qdrant_client: QdrantClient instance (creates new if None)
            embedding_model: EmbeddingModel instance (creates new if None)
            use_cache: Whether to use embedding cache
        """
        self.qdrant = qdrant_client or QdrantClient()
        self.embedding_model = embedding_model or EmbeddingModel()
        self.pipeline = EmbeddingPipeline(model=self.embedding_model)
        self.collection_manager = CollectionManager(qdrant_client=self.qdrant)
        self.cache = EmbeddingCache() if use_cache else None

        self._collection_by_corpus = {
            CORPUS_KB: settings.QDRANT_KB_COLLECTION_NAME,
            CORPUS_USER_DOC: settings.QDRANT_USER_COLLECTION_NAME,
        }

        vector_size = self.embedding_model.get_vector_size()
        for corpus, collection_name in self._collection_by_corpus.items():
            if not self.collection_manager.collection_exists(collection_name):
                logger.info(
                    f"Collection '{collection_name}' does not exist, creating for corpus='{corpus}'..."
                )
                self.collection_manager.create_collection(
                    collection_name,
                    vector_size=vector_size,
                )

        logger.info(
            "Initialized VectorStore with collections: "
            f"kb='{self._collection_by_corpus[CORPUS_KB]}', "
            f"user_doc='{self._collection_by_corpus[CORPUS_USER_DOC]}'"
        )

    def get_collection_name(self, corpus: str) -> str:
        """Resolve Qdrant collection name for a corpus type."""
        self._validate_corpus(corpus)
        return self._collection_by_corpus[corpus]

    def store_chunks(
        self,
        chunks: List[Dict[str, Any]],
        corpus: str,
        user_id: Optional[str] = None,
        batch_size: Optional[int] = None,
        show_progress: bool = True,
    ) -> List[str]:
        """
        Store text chunks as vectors in the corpus-appropriate Qdrant collection.

        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
            corpus: ``kb`` or ``user_doc``
            user_id: Required for ``user_doc``; use empty string or None for ``kb``
            batch_size: Batch size for embedding generation
            show_progress: Whether to show progress bar

        Returns:
            List of point IDs that were stored
        """
        if not chunks:
            return []

        self._validate_corpus(corpus)
        normalized_user_id = self._normalize_user_id(corpus, user_id)
        collection_name = self.get_collection_name(corpus)

        texts = [chunk.get("text", "") for chunk in chunks]

        embeddings_to_generate = []
        cached_embeddings: Dict[int, Any] = {}

        if self.cache:
            for i, text in enumerate(texts):
                cached = self.cache.get(text)
                if cached is not None:
                    cached_embeddings[i] = cached
                else:
                    embeddings_to_generate.append((i, text))
        else:
            embeddings_to_generate = [(i, text) for i, text in enumerate(texts)]

        if embeddings_to_generate:
            texts_to_embed = [text for _, text in embeddings_to_generate]
            embedding_results = self.pipeline.generate_embeddings(
                texts_to_embed,
                batch_size=batch_size,
                show_progress=show_progress,
            )

            for (idx, _), result in zip(embeddings_to_generate, embedding_results):
                embedding = result["embedding_numpy"]
                cached_embeddings[idx] = embedding
                if self.cache:
                    self.cache.set(texts[idx], embedding)

        points = []
        point_ids = []

        for i, chunk in enumerate(chunks):
            chunk_metadata = chunk.get("metadata", {}) or {}
            point_id = (
                chunk.get("chunk_id")
                or chunk_metadata.get("chunk_id")
                or str(uuid4())
            )
            embedding = cached_embeddings[i]

            payload = {
                "text": chunk.get("text", ""),
                "chunk_id": point_id,
                "corpus": corpus,
                "user_id": normalized_user_id,
                "document_id": chunk_metadata.get("document_id", ""),
                "chunk_type": chunk_metadata.get("chunk_type", "text"),
                "page_number": chunk_metadata.get("page_number", 0),
                "created_at": chunk_metadata.get("created_at", ""),
                **{
                    k: v
                    for k, v in chunk_metadata.items()
                    if k
                    not in [
                        "document_id",
                        "chunk_type",
                        "page_number",
                        "created_at",
                        "corpus",
                        "user_id",
                    ]
                },
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=payload,
                )
            )
            point_ids.append(point_id)

        if points:
            self.qdrant.upsert_points(
                collection_name=collection_name,
                points=points,
            )

        logger.info(
            f"Stored {len(point_ids)} chunks in collection '{collection_name}' "
            f"(corpus='{corpus}', user_id='{normalized_user_id or 'n/a'}')"
        )
        return point_ids

    def scroll_chunks(
        self,
        corpus: str,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Scroll all chunks in a corpus partition (for BM25 index building).

        Args:
            corpus: ``kb`` or ``user_doc``
            user_id: Required for ``user_doc``
            document_id: Optional document filter
            limit: Page size per scroll request

        Returns:
            List of chunk dicts with chunk_id, text, corpus, user_id, metadata
        """
        self._validate_corpus(corpus)
        normalized_user_id = self._normalize_user_id(corpus, user_id)
        collection_name = self.get_collection_name(corpus)
        scroll_filter = self._build_search_filter(
            corpus, normalized_user_id, document_id=document_id
        )

        chunks: List[Dict[str, Any]] = []
        offset = None

        while True:
            batch = self.qdrant.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                filter=scroll_filter,
            )
            points = batch.get("points", [])
            if not points:
                break

            for point in points:
                payload = point.get("payload") or {}
                chunks.append({
                    "chunk_id": point["id"],
                    "text": payload.get("text", ""),
                    "corpus": payload.get("corpus", corpus),
                    "user_id": payload.get("user_id", ""),
                    "metadata": {
                        k: v
                        for k, v in payload.items()
                        if k not in {"text", "corpus", "user_id"}
                    },
                })

            offset = batch.get("next_offset")
            if offset is None:
                break

        return chunks

    def search(
        self,
        query: str,
        corpus: str,
        user_id: Optional[str] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks within a single corpus partition.

        Args:
            query: Query text
            corpus: ``kb`` or ``user_doc``
            user_id: Required for ``user_doc`` searches
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            document_id: Optional document filter

        Returns:
            List of search results with text, score, metadata, and corpus tags
        """
        self._validate_corpus(corpus)
        normalized_user_id = self._normalize_user_id(corpus, user_id)
        collection_name = self.get_collection_name(corpus)
        query_filter = self._build_search_filter(
            corpus, normalized_user_id, document_id=document_id
        )

        query_embedding = self.pipeline.generate_single(query)["embedding_numpy"]

        results = self.qdrant.search(
            collection_name=collection_name,
            query_vector=query_embedding.tolist(),
            top_k=top_k,
            filter=query_filter,
            score_threshold=score_threshold,
        )

        formatted_results = []
        for result in results:
            payload = result["payload"] or {}
            formatted_results.append({
                "chunk_id": result["id"],
                "text": payload.get("text", ""),
                "score": result["score"],
                "corpus": payload.get("corpus", corpus),
                "user_id": payload.get("user_id", ""),
                "metadata": {
                    k: v
                    for k, v in payload.items()
                    if k not in {"text", "corpus", "user_id"}
                },
            })

        logger.debug(
            f"Search in '{collection_name}' (corpus='{corpus}') "
            f"returned {len(formatted_results)} results"
        )
        return formatted_results

    def delete_chunks(
        self,
        chunk_ids: List[str],
        corpus: str,
    ) -> bool:
        """
        Delete chunks by ID from the corpus-appropriate collection.

        Args:
            chunk_ids: List of chunk IDs to delete
            corpus: ``kb`` or ``user_doc``

        Returns:
            True if successful
        """
        collection_name = self.get_collection_name(corpus)
        return self.qdrant.delete_points(
            collection_name=collection_name,
            point_ids=chunk_ids,
        )

    def delete_document_chunks(
        self,
        document_id: str,
        corpus: str,
        user_id: Optional[str] = None,
    ) -> int:
        """
        Delete all chunks belonging to a document within a corpus partition.

        Args:
            document_id: Document identifier stored in chunk payload
            corpus: ``kb`` or ``user_doc``
            user_id: Required for ``user_doc``

        Returns:
            Number of deleted points
        """
        if Filter is None or FieldCondition is None or MatchValue is None:
            raise RuntimeError("Qdrant filter models are not available")

        self._validate_corpus(corpus)
        normalized_user_id = self._normalize_user_id(corpus, user_id)
        collection_name = self.get_collection_name(corpus)

        conditions = [
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
            FieldCondition(key="corpus", match=MatchValue(value=corpus)),
        ]
        if corpus == CORPUS_USER_DOC:
            conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=normalized_user_id))
            )

        scroll_filter = Filter(must=conditions)
        deleted = 0
        offset = None

        while True:
            batch = self.qdrant.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                filter=scroll_filter,
            )
            points = batch.get("points", [])
            if not points:
                break

            point_ids = [point["id"] for point in points]
            self.qdrant.delete_points(collection_name=collection_name, point_ids=point_ids)
            deleted += len(point_ids)

            offset = batch.get("next_offset")
            if offset is None:
                break

        logger.info(
            f"Deleted {deleted} chunks for document_id='{document_id}' "
            f"from '{collection_name}'"
        )
        return deleted

    def update_chunk_metadata(
        self,
        chunk_id: str,
        corpus: str,
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Update metadata for a chunk in the corpus-appropriate collection.

        Args:
            chunk_id: ID of the chunk
            corpus: ``kb`` or ``user_doc``
            metadata: Metadata to update (must not change corpus/user_id semantics)

        Returns:
            True if successful
        """
        collection_name = self.get_collection_name(corpus)
        return self.qdrant.update_payload(
            collection_name=collection_name,
            payload=metadata,
            points=[chunk_id],
        )

    def get_collection_info(self, corpus: str) -> Optional[Dict[str, Any]]:
        """Get information about the collection for a corpus partition."""
        collection_name = self.get_collection_name(corpus)
        info = self.collection_manager.get_collection_info(collection_name)
        if info:
            info["corpus"] = corpus
        return info

    def _validate_corpus(self, corpus: str) -> None:
        if corpus not in VALID_CORPORA:
            raise ValueError(
                f"Invalid corpus '{corpus}'. Expected one of: {sorted(VALID_CORPORA)}"
            )

    def _normalize_user_id(self, corpus: str, user_id: Optional[str]) -> str:
        if corpus == CORPUS_USER_DOC:
            if not user_id or not str(user_id).strip():
                raise ValueError("user_id is required when corpus='user_doc'")
            return str(user_id).strip()
        return ""

    def _build_search_filter(
        self,
        corpus: str,
        user_id: str,
        document_id: Optional[str] = None,
    ) -> Optional["Filter"]:
        if Filter is None or FieldCondition is None or MatchValue is None:
            return None

        conditions = [FieldCondition(key="corpus", match=MatchValue(value=corpus))]

        if corpus == CORPUS_USER_DOC:
            conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )

        if document_id:
            conditions.append(
                FieldCondition(key="document_id", match=MatchValue(value=document_id))
            )

        return Filter(must=conditions)
