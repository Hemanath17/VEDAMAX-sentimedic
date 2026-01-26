"""
Step 8: Vector Storage Integration (Main Orchestrator)

Simple Explanation:
This is the main class that brings everything together.
It combines the Qdrant client, embedding model, pipeline, cache, and collection manager.
Think of it as the conductor of an orchestra - it coordinates all the pieces.

Why We Need It:
- Provides a single, simple interface for storing and searching vectors
- Hides complexity from the rest of the system
- Manages the entire workflow: text → embedding → storage → search
"""

from typing import List, Dict, Any, Optional, Union
from uuid import uuid4
try:
    from qdrant_client.models import PointStruct, Filter
except ImportError:
    PointStruct = None  # type: ignore
    Filter = None  # type: ignore

from src.retrieval.vector_store.qdrant_client import QdrantClient
from src.retrieval.vector_store.embeddings import EmbeddingModel
from src.retrieval.vector_store.embedding_pipeline import EmbeddingPipeline
from src.retrieval.vector_store.embedding_cache import EmbeddingCache
from src.retrieval.vector_store.collection_manager import CollectionManager
from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    Main vector store orchestrator.
    
    Simple Explanation:
    This is your main interface for working with vectors.
    You give it text, it stores it as vectors. You give it a query, it finds similar vectors.
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        qdrant_client: Optional[QdrantClient] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        use_cache: bool = True,
    ):
        """
        Initialize vector store.

        Args:
            collection_name: Name of the collection (defaults to settings)
            qdrant_client: QdrantClient instance (creates new if None)
            embedding_model: EmbeddingModel instance (creates new if None)
            use_cache: Whether to use embedding cache
        """
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME

        # Initialize components
        self.qdrant = qdrant_client or QdrantClient()
        self.embedding_model = embedding_model or EmbeddingModel()
        self.pipeline = EmbeddingPipeline(model=self.embedding_model)
        self.collection_manager = CollectionManager(qdrant_client=self.qdrant)
        self.cache = EmbeddingCache() if use_cache else None

        # Ensure collection exists
        if not self.collection_manager.collection_exists(self.collection_name):
            logger.info(f"Collection '{self.collection_name}' does not exist, creating...")
            self.collection_manager.create_collection(
                self.collection_name,
                vector_size=self.embedding_model.get_vector_size(),
            )

        logger.info(f"Initialized VectorStore with collection '{self.collection_name}'")

    def store_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: Optional[int] = None,
        show_progress: bool = True,
    ) -> List[str]:
        """
        Store text chunks as vectors in Qdrant.

        Simple Explanation:
        Takes chunks of text, converts them to embeddings, and stores them.
        Like scanning documents and filing them in a smart filing cabinet.

        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
            batch_size: Batch size for embedding generation
            show_progress: Whether to show progress bar

        Returns:
            List of point IDs that were stored
        """
        if not chunks:
            return []

        # Extract texts
        texts = [chunk.get("text", "") for chunk in chunks]

        # Generate embeddings (with cache if enabled)
        embeddings_to_generate = []
        cached_embeddings = {}

        if self.cache:
            # Check cache first
            for i, text in enumerate(texts):
                cached = self.cache.get(text)
                if cached is not None:
                    cached_embeddings[i] = cached
                else:
                    embeddings_to_generate.append((i, text))
        else:
            embeddings_to_generate = [(i, text) for i, text in enumerate(texts)]

        # Generate missing embeddings
        if embeddings_to_generate:
            texts_to_embed = [text for _, text in embeddings_to_generate]
            embedding_results = self.pipeline.generate_embeddings(
                texts_to_embed,
                batch_size=batch_size,
                show_progress=show_progress,
            )

            # Store in cache and map back to indices
            for (idx, _), result in zip(embeddings_to_generate, embedding_results):
                embedding = result["embedding_numpy"]
                cached_embeddings[idx] = embedding
                if self.cache:
                    self.cache.set(texts[idx], embedding)

        # Prepare points for Qdrant
        points = []
        point_ids = []

        for i, chunk in enumerate(chunks):
            point_id = chunk.get("chunk_id") or str(uuid4())
            embedding = cached_embeddings[i]

            # Prepare payload (metadata) - Step 9: Metadata Payload Management
            # Standard payload structure for medical documents
            chunk_metadata = chunk.get("metadata", {})
            payload = {
                "text": chunk.get("text", ""),
                "chunk_id": point_id,
                "document_id": chunk_metadata.get("document_id", ""),
                "chunk_type": chunk_metadata.get("chunk_type", "text"),
                "page_number": chunk_metadata.get("page_number", 0),
                "created_at": chunk_metadata.get("created_at", ""),
                # Include any additional metadata
                **{k: v for k, v in chunk_metadata.items() 
                   if k not in ["document_id", "chunk_type", "page_number", "created_at"]},
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=payload,
                )
            )
            point_ids.append(point_id)

        # Store in Qdrant
        if points:
            self.qdrant.upsert_points(
                collection_name=self.collection_name,
                points=points,
            )

        logger.info(f"Stored {len(point_ids)} chunks in collection '{self.collection_name}'")
        return point_ids

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter: Optional[Filter] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks.

        Simple Explanation:
        Takes a query text, converts it to an embedding, and finds the most similar stored chunks.
        Like asking "find me documents similar to this question".

        Args:
            query: Query text
            top_k: Number of results to return
            filter: Optional metadata filter
            score_threshold: Minimum similarity score

        Returns:
            List of search results with text, score, and metadata
        """
        # Generate query embedding
        query_embedding = self.pipeline.generate_single(query)["embedding_numpy"]

        # Search in Qdrant
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            top_k=top_k,
            filter=filter,
            score_threshold=score_threshold,
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "chunk_id": result["id"],
                "text": result["payload"].get("text", ""),
                "score": result["score"],
                "metadata": {
                    k: v for k, v in result["payload"].items() if k != "text"
                },
            })

        logger.debug(f"Search returned {len(formatted_results)} results")
        return formatted_results

    def delete_chunks(self, chunk_ids: List[str]) -> bool:
        """
        Delete chunks by ID.

        Args:
            chunk_ids: List of chunk IDs to delete

        Returns:
            True if successful
        """
        return self.qdrant.delete_points(
            collection_name=self.collection_name,
            point_ids=chunk_ids,
        )

    def update_chunk_metadata(
        self,
        chunk_id: str,
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Update metadata for a chunk.

        Args:
            chunk_id: ID of the chunk
            metadata: Metadata to update

        Returns:
            True if successful
        """
        return self.qdrant.update_payload(
            collection_name=self.collection_name,
            payload=metadata,
            points=[chunk_id],
        )

    def get_collection_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the collection."""
        return self.collection_manager.get_collection_info(self.collection_name)

