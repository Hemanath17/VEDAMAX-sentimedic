"""
Step 4: Collection Management

Simple Explanation:
Qdrant organizes vectors into "collections" (like folders).
This manager helps us create, configure, and manage these collections.
Think of it like a file manager, but for vector collections.

Why We Need It:
- Sets up collections with correct settings
- Manages collection lifecycle (create, update, delete)
- Configures indexes for fast search
"""

from typing import Dict, Any, Optional, List
from qdrant_client.models import (
    Distance,
    VectorParams,
    CollectionStatus,
    OptimizersConfigDiff,
    HnswConfigDiff,
)

from src.retrieval.vector_store.qdrant_client import QdrantClient
from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class CollectionManager:
    """
    Manages Qdrant collections.
    
    Simple Explanation:
    Handles creating and managing collections in Qdrant.
    Like a librarian organizing books into different sections.
    """

    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """
        Initialize collection manager.

        Args:
            qdrant_client: QdrantClient instance (creates new if None)
        """
        self.client = qdrant_client or QdrantClient()
        logger.info("Initialized CollectionManager")

    def create_collection(
        self,
        collection_name: str,
        vector_size: Optional[int] = None,
        distance: Distance = Distance.COSINE,
        recreate: bool = False,
    ) -> bool:
        """
        Create a new collection.

        Simple Explanation:
        Creates a new "folder" in Qdrant to store vectors.
        Configures it with the right size (1024 for BGE-M3) and distance metric.

        Args:
            collection_name: Name of the collection
            vector_size: Size of vectors (defaults to 1024 for BGE-M3)
            distance: Distance metric (COSINE for embeddings)
            recreate: Whether to delete and recreate if exists

        Returns:
            True if successful
        """
        vector_size = vector_size or settings.QDRANT_VECTOR_SIZE

        try:
            # Check if collection exists
            collections = self.client.client.get_collections().collections
            collection_exists = any(c.name == collection_name for c in collections)

            if collection_exists:
                if recreate:
                    logger.info(f"Recreating collection '{collection_name}'")
                    self.delete_collection(collection_name)
                else:
                    logger.info(f"Collection '{collection_name}' already exists")
                    return True

            # Create collection with optimized settings
            self.client.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                ),
                # Optimize for medical document retrieval
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=10000,  # Start indexing after 10k points
                ),
                hnsw_config=HnswConfigDiff(
                    m=16,  # Number of connections (balance between speed and accuracy)
                    ef_construct=200,  # Search accuracy during construction
                ),
            )

            logger.info(
                f"Created collection '{collection_name}' with vector size {vector_size}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create collection: {e}", exc_info=True)
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.

        Simple Explanation:
        Removes a collection and all its vectors (like deleting a folder).

        Args:
            collection_name: Name of the collection

        Returns:
            True if successful
        """
        try:
            self.client.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}", exc_info=True)
            return False

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists
        """
        try:
            collections = self.client.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection.

        Simple Explanation:
        Gets stats about a collection - how many vectors, size, configuration.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information
        """
        try:
            collection_info = self.client.client.get_collection(collection_name)

            return {
                "name": collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": collection_info.status,
                "config": {
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance,
                },
                "optimizer_status": collection_info.optimizer_status,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}", exc_info=True)
            return None

    def list_collections(self) -> List[str]:
        """
        List all collections.

        Returns:
            List of collection names
        """
        try:
            collections = self.client.client.get_collections().collections
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}", exc_info=True)
            return []

    def update_collection_index(
        self,
        collection_name: str,
        indexing_threshold: Optional[int] = None,
        m: Optional[int] = None,
        ef_construct: Optional[int] = None,
    ) -> bool:
        """
        Update collection indexing settings (Step 7: Vector Indexing Optimization).

        Simple Explanation:
        Optimizes how Qdrant indexes vectors for faster search.
        Like tuning a car engine - we adjust settings for better performance.

        Args:
            collection_name: Name of the collection
            indexing_threshold: When to start indexing (number of points)
            m: HNSW parameter - number of connections (higher = more accurate, slower)
            ef_construct: HNSW parameter - search accuracy during construction

        Returns:
            True if successful
        """
        try:
            optimizers_config = None
            hnsw_config = None

            if indexing_threshold is not None:
                optimizers_config = OptimizersConfigDiff(
                    indexing_threshold=indexing_threshold,
                )

            if m is not None or ef_construct is not None:
                hnsw_config = HnswConfigDiff(
                    m=m,
                    ef_construct=ef_construct,
                )

            self.client.client.update_collection(
                collection_name=collection_name,
                optimizers_config=optimizers_config,
                hnsw_config=hnsw_config,
            )
            logger.info(f"Updated indexing for collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to update collection index: {e}", exc_info=True)
            return False

    def optimize_collection(
        self,
        collection_name: str,
        points_count: Optional[int] = None,
    ) -> bool:
        """
        Optimize collection based on data size (Step 7: Vector Indexing Optimization).

        Simple Explanation:
        Automatically tunes collection settings based on how much data we have.
        Small collections need different settings than large ones.

        Args:
            collection_name: Name of the collection
            points_count: Number of points (auto-detected if None)

        Returns:
            True if successful
        """
        try:
            if points_count is None:
                info = self.get_collection_info(collection_name)
                if info:
                    points_count = info.get("points_count", 0)
                else:
                    logger.warning("Could not get collection info for optimization")
                    return False

            # Optimize based on size
            if points_count < 1000:
                # Small collection - faster indexing
                indexing_threshold = 100
                m = 8
                ef_construct = 100
            elif points_count < 100000:
                # Medium collection - balanced
                indexing_threshold = 10000
                m = 16
                ef_construct = 200
            else:
                # Large collection - optimize for speed
                indexing_threshold = 50000
                m = 32
                ef_construct = 400

            return self.update_collection_index(
                collection_name=collection_name,
                indexing_threshold=indexing_threshold,
                m=m,
                ef_construct=ef_construct,
            )

        except Exception as e:
            logger.error(f"Failed to optimize collection: {e}", exc_info=True)
            return False

