"""Base chunking strategy interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from src.config.logging_config import get_logger
from src.config.constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

logger = get_logger(__name__)


class ChunkingError(Exception):
    """Custom exception for chunking errors."""

    pass


class ChunkStrategy(ABC):
    """Abstract base class for text chunking strategies."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        min_chunk_size: Optional[int] = None,
        max_chunk_size: Optional[int] = None,
    ):
        """
        Initialize chunking strategy.

        Args:
            chunk_size: Target chunk size (tokens or characters)
            chunk_overlap: Overlap between chunks
            min_chunk_size: Minimum chunk size
            max_chunk_size: Maximum chunk size
        """
        self.chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or DEFAULT_CHUNK_OVERLAP
        self.min_chunk_size = min_chunk_size or (self.chunk_size // 4)
        self.max_chunk_size = max_chunk_size or (self.chunk_size * 2)

        # Validate parameters
        if self.chunk_overlap >= self.chunk_size:
            raise ChunkingError(
                f"Chunk overlap ({self.chunk_overlap}) must be less than chunk size ({self.chunk_size})"
            )

        if self.min_chunk_size > self.max_chunk_size:
            raise ChunkingError(
                f"Min chunk size ({self.min_chunk_size}) must be <= max chunk size ({self.max_chunk_size})"
            )

    @abstractmethod
    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text into smaller pieces.

        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of chunk dictionaries with structure:
            {
                "text": str,              # Chunk text content
                "chunk_id": str,          # Unique chunk identifier
                "metadata": Dict,         # Chunk metadata
                "chunk_index": int,       # Index of chunk in sequence
                "start_index": int,       # Start position in original text
                "end_index": int,         # End position in original text
                "token_count": int,       # Number of tokens (if applicable)
            }

        Raises:
            ChunkingError: If chunking fails
        """
        pass

    @abstractmethod
    def get_chunk_size(self) -> int:
        """
        Get the typical chunk size for this strategy.

        Returns:
            Typical chunk size in tokens or characters
        """
        pass

    def calculate_overlap(self, chunk_size: int) -> int:
        """
        Calculate overlap size based on chunk size.

        Args:
            chunk_size: Size of the chunk

        Returns:
            Overlap size
        """
        return min(self.chunk_overlap, chunk_size // 4)

    def validate_chunk(self, chunk_text: str, chunk_index: int) -> bool:
        """
        Validate that a chunk meets size requirements.

        Args:
            chunk_text: Chunk text to validate
            chunk_index: Index of the chunk

        Returns:
            True if chunk is valid
        """
        if not chunk_text or not chunk_text.strip():
            logger.warning(f"Empty chunk at index {chunk_index}")
            return False

        chunk_length = len(chunk_text)
        if chunk_length < self.min_chunk_size:
            logger.warning(
                f"Chunk {chunk_index} is too small: {chunk_length} < {self.min_chunk_size}"
            )
            return False

        if chunk_length > self.max_chunk_size:
            logger.warning(
                f"Chunk {chunk_index} is too large: {chunk_length} > {self.max_chunk_size}"
            )
            return False

        return True

    def create_chunk_metadata(
        self,
        base_metadata: Optional[Dict[str, Any]],
        chunk_index: int,
        start_index: int,
        end_index: int,
        token_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create metadata for a chunk.

        Args:
            base_metadata: Base metadata from document
            chunk_index: Index of chunk in sequence
            start_index: Start position in original text
            end_index: End position in original text
            token_count: Number of tokens in chunk

        Returns:
            Complete chunk metadata dictionary
        """
        chunk_metadata = {
            "chunk_id": str(uuid.uuid4()),
            "chunk_index": chunk_index,
            "start_index": start_index,
            "end_index": end_index,
            "chunk_size": end_index - start_index,
            "created_at": datetime.utcnow().isoformat(),
            "chunker_type": self.__class__.__name__,
        }

        if token_count is not None:
            chunk_metadata["token_count"] = token_count

        # Merge with base metadata
        if base_metadata:
            chunk_metadata.update(base_metadata)

        return chunk_metadata

    def get_strategy_name(self) -> str:
        """
        Get the name of this chunking strategy.

        Returns:
            Strategy name
        """
        return self.__class__.__name__

    def get_chunk_quality_score(self, chunk_text: str) -> float:
        """
        Calculate a quality score for a chunk (0.0 to 1.0).

        Args:
            chunk_text: Chunk text to score

        Returns:
            Quality score between 0.0 and 1.0
        """
        if not chunk_text or not chunk_text.strip():
            return 0.0

        score = 1.0

        # Penalize chunks that are too small or too large
        chunk_length = len(chunk_text)
        if chunk_length < self.min_chunk_size:
            score *= 0.5
        elif chunk_length > self.max_chunk_size:
            score *= 0.7

        # Bonus for chunks that are close to target size
        if abs(chunk_length - self.chunk_size) < self.chunk_size * 0.2:
            score *= 1.1
            score = min(score, 1.0)

        return score

