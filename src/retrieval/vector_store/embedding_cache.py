"""
Step 6: Embedding Cache Management

Simple Explanation:
Caching is like keeping a copy of something you've already done.
If we've converted "What is diabetes?" to an embedding before,
we save it so we don't have to do it again. Saves time and money!

Why We Need It:
- Avoids recomputing embeddings for the same text
- Speeds up repeated operations
- Reduces compute costs
- Enables incremental updates
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np

from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """
    Cache for embeddings to avoid recomputation.
    
    Simple Explanation:
    Stores embeddings we've already computed, so we can reuse them.
    Like a notebook where we write down answers we've already figured out.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize embedding cache.

        Args:
            cache_dir: Directory to store cache files (defaults to settings)
        """
        self.cache_dir = Path(cache_dir or settings.EMBEDDINGS_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for fast access
        self._memory_cache: Dict[str, np.ndarray] = {}

        logger.info(f"Initialized EmbeddingCache at {self.cache_dir}")

    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key from text.

        Simple Explanation:
        Creates a unique ID for each text by hashing it.
        Like a fingerprint - same text = same hash.

        Args:
            text: Text to hash

        Returns:
            Hash string (cache key)
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for a cache key."""
        return self.cache_dir / f"{cache_key}.pkl"

    def get(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding from cache.

        Simple Explanation:
        Checks if we've computed this embedding before.
        If yes, returns it. If no, returns None.

        Args:
            text: Text to look up

        Returns:
            Embedding vector if found, None otherwise
        """
        cache_key = self._get_cache_key(text)

        # Check memory cache first
        if cache_key in self._memory_cache:
            logger.debug(f"Cache hit (memory) for text: {text[:50]}...")
            return self._memory_cache[cache_key]

        # Check file cache
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    embedding = pickle.load(f)
                # Store in memory cache for next time
                self._memory_cache[cache_key] = embedding
                logger.debug(f"Cache hit (file) for text: {text[:50]}...")
                return embedding
            except Exception as e:
                logger.warning(f"Failed to load cache file: {e}")

        logger.debug(f"Cache miss for text: {text[:50]}...")
        return None

    def set(self, text: str, embedding: np.ndarray) -> bool:
        """
        Store embedding in cache.

        Simple Explanation:
        Saves an embedding so we can reuse it later.

        Args:
            text: Text that was embedded
            embedding: Embedding vector to cache

        Returns:
            True if successful
        """
        cache_key = self._get_cache_key(text)

        try:
            # Store in memory cache
            self._memory_cache[cache_key] = embedding

            # Store in file cache
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, "wb") as f:
                pickle.dump(embedding, f)

            logger.debug(f"Cached embedding for text: {text[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to cache embedding: {e}", exc_info=True)
            return False

    def get_batch(
        self,
        texts: List[str],
    ) -> Dict[str, Optional[np.ndarray]]:
        """
        Get multiple embeddings from cache.

        Args:
            texts: List of texts to look up

        Returns:
            Dictionary mapping text to embedding (None if not found)
        """
        results = {}
        for text in texts:
            results[text] = self.get(text)
        return results

    def invalidate(self, text: str) -> bool:
        """
        Remove embedding from cache.

        Simple Explanation:
        Deletes a cached embedding (useful if text changed).

        Args:
            text: Text to remove from cache

        Returns:
            True if successful
        """
        cache_key = self._get_cache_key(text)

        # Remove from memory cache
        self._memory_cache.pop(cache_key, None)

        # Remove from file cache
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.debug(f"Invalidated cache for text: {text[:50]}...")
                return True
            except Exception as e:
                logger.error(f"Failed to invalidate cache: {e}")
                return False

        return True

    def clear(self) -> bool:
        """
        Clear all cached embeddings.

        Returns:
            True if successful
        """
        try:
            # Clear memory cache
            self._memory_cache.clear()

            # Clear file cache
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()

            logger.info("Cleared embedding cache")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}", exc_info=True)
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        file_count = len(list(self.cache_dir.glob("*.pkl")))
        memory_count = len(self._memory_cache)

        return {
            "memory_cache_size": memory_count,
            "file_cache_size": file_count,
            "cache_dir": str(self.cache_dir),
        }

