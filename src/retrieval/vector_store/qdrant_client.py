"""
Step 1: Qdrant Client Wrapper

Simple Explanation:
Think of Qdrant as a special database that stores vectors (lists of numbers) instead of text.
This wrapper is like a helper that makes it easy to talk to Qdrant - it handles connecting,
saving vectors, searching for similar vectors, and managing errors.

Why We Need It:
- Makes Qdrant operations simple and consistent
- Handles connection errors automatically
- Provides a clean interface for the rest of our code
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
import time

from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)

try:
    from qdrant_client import QdrantClient as QdrantClientSDK
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PointStruct,
        Filter,
        SearchParams,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClientSDK = None
    logger.warning("Qdrant client not available")


class QdrantClient:
    """
    Wrapper around Qdrant client for easy vector operations.
    
    Simple Explanation:
    This class wraps the Qdrant library to make it easier to use.
    Instead of calling Qdrant directly, we call methods on this class.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize Qdrant client.

        Args:
            host: Qdrant server host (defaults to settings)
            port: Qdrant server port (defaults to settings)
            api_key: API key for cloud Qdrant (optional)
            timeout: Connection timeout in seconds
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "Qdrant client not available. Install with: pip install qdrant-client"
            )

        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.timeout = timeout

        # Initialize client
        try:
            if self.api_key:
                # Cloud Qdrant
                self.client = QdrantClientSDK(
                    url=f"https://{self.host}",
                    api_key=self.api_key,
                    timeout=self.timeout,
                )
                logger.info(f"Connected to Qdrant cloud at {self.host}")
            else:
                # Local Qdrant
                self.client = QdrantClientSDK(
                    host=self.host,
                    port=self.port,
                    timeout=self.timeout,
                )
                logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}", exc_info=True)
            raise

    def health_check(self) -> bool:
        """
        Check if Qdrant is healthy and accessible.

        Simple Explanation:
        Like checking if a light switch works - we ping Qdrant to see if it responds.

        Returns:
            True if Qdrant is accessible, False otherwise
        """
        try:
            collections = self.client.get_collections()
            logger.debug("Qdrant health check passed")
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    def upsert_points(
        self,
        collection_name: str,
        points: List[Any],  # PointStruct when Qdrant available
        wait: bool = True,
    ) -> bool:
        """
        Insert or update vectors in a collection.

        Simple Explanation:
        Like putting books on a shelf - we're storing vectors (embeddings) in Qdrant.
        If a vector already exists, we update it. If not, we add it.

        Args:
            collection_name: Name of the collection
            points: List of points (vectors with IDs and metadata)
            wait: Whether to wait for operation to complete

        Returns:
            True if successful
        """
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points,
                wait=wait,
            )
            logger.info(f"Upserted {len(points)} points to collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert points: {e}", exc_info=True)
            return False

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Any] = None,  # Filter when Qdrant available
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Simple Explanation:
        Like asking "find me the 10 most similar vectors to this one".
        We give Qdrant a query vector, and it finds the closest matches.

        Args:
            collection_name: Name of the collection to search
            query_vector: The vector to search for (embedding of query text)
            top_k: Number of results to return
            filter: Optional metadata filter
            score_threshold: Minimum similarity score

        Returns:
            List of search results with scores and metadata
        """
        try:
            if hasattr(self.client, "search"):
                search_results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=filter,
                    score_threshold=score_threshold,
                )
            elif hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=top_k,
                    query_filter=filter,
                    score_threshold=score_threshold,
                )
                search_results = response.points
            else:
                raise AttributeError(
                    "Installed qdrant-client has neither search nor query_points."
                )

            # Format results
            results = []
            for result in search_results:
                results.append({
                    "id": str(result.id),
                    "score": result.score,
                    "payload": result.payload or {},
                })

            logger.debug(
                f"Search in '{collection_name}' returned {len(results)} results"
            )
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []

    def get_point(
        self,
        collection_name: str,
        point_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific vector by ID.

        Simple Explanation:
        Like looking up a specific book by its ID number.

        Args:
            collection_name: Name of the collection
            point_id: ID of the point to retrieve

        Returns:
            Point data if found, None otherwise
        """
        try:
            point = self.client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
            )
            if point:
                return {
                    "id": str(point[0].id),
                    "vector": point[0].vector,
                    "payload": point[0].payload or {},
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get point: {e}", exc_info=True)
            return None

    def delete_points(
        self,
        collection_name: str,
        point_ids: List[str],
        wait: bool = True,
    ) -> bool:
        """
        Delete vectors by ID.

        Simple Explanation:
        Like removing books from a shelf by their ID numbers.

        Args:
            collection_name: Name of the collection
            point_ids: List of point IDs to delete
            wait: Whether to wait for operation to complete

        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=point_ids,
                wait=wait,
            )
            logger.info(
                f"Deleted {len(point_ids)} points from collection '{collection_name}'"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete points: {e}", exc_info=True)
            return False

    def update_payload(
        self,
        collection_name: str,
        payload: Dict[str, Any],
        points: List[str],
        wait: bool = True,
    ) -> bool:
        """
        Update metadata (payload) for vectors.

        Simple Explanation:
        Like updating the tags on a book without changing the book itself.
        We update the metadata (like document name, page number) for vectors.

        Args:
            collection_name: Name of the collection
            payload: Metadata to update
            points: List of point IDs to update
            wait: Whether to wait for operation to complete

        Returns:
            True if successful
        """
        try:
            self.client.set_payload(
                collection_name=collection_name,
                payload=payload,
                points=points,
                wait=wait,
            )
            logger.info(
                f"Updated payload for {len(points)} points in '{collection_name}'"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update payload: {e}", exc_info=True)
            return False

    def scroll(
        self,
        collection_name: str,
        limit: int = 100,
        offset: Optional[str] = None,
        filter: Optional[Any] = None,  # Filter when Qdrant available
    ) -> Dict[str, Any]:
        """
        Scroll through vectors in a collection (for batch operations).

        Simple Explanation:
        Like reading through a book page by page - we get vectors in batches.

        Args:
            collection_name: Name of the collection
            limit: Number of points to return
            offset: Offset for pagination
            filter: Optional metadata filter

        Returns:
            Dictionary with points and next_offset
        """
        try:
            result = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                scroll_filter=filter,
            )

            points = []
            for point in result[0]:
                points.append({
                    "id": str(point.id),
                    "vector": point.vector,
                    "payload": point.payload or {},
                })

            return {
                "points": points,
                "next_offset": result[1],
            }
        except Exception as e:
            logger.error(f"Scroll failed: {e}", exc_info=True)
            return {"points": [], "next_offset": None}

