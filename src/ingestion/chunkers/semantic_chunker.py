"""Semantic chunker using topic shift detection."""

from typing import List, Dict, Any, Optional
import numpy as np

from src.ingestion.chunkers.chunk_strategy import ChunkStrategy, ChunkingError
from src.ingestion.chunkers.token_chunker import TokenChunker
from src.config.logging_config import get_logger
from src.config.constants import SEMANTIC_CHUNK_THRESHOLD
from src.config.settings import settings

logger = get_logger(__name__)

# Try to import sentence transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available for semantic chunking")


class SemanticChunker(ChunkStrategy):
    """Semantic chunker that detects topic shifts to create meaningful chunks."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        model_name: Optional[str] = None,
        fallback_to_token: bool = True,
    ):
        """
        Initialize semantic chunker.

        Args:
            chunk_size: Target chunk size (used as fallback and for validation)
            chunk_overlap: Overlap between chunks
            similarity_threshold: Threshold for topic shift detection (0.0-1.0)
            model_name: Sentence transformer model name
            fallback_to_token: Whether to fallback to token chunker if model unavailable
        """
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.similarity_threshold = similarity_threshold or SEMANTIC_CHUNK_THRESHOLD
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.fallback_to_token = fallback_to_token
        self._model = None
        self._token_chunker = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the sentence transformer model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available")
            if self.fallback_to_token:
                logger.info("Falling back to token-based chunking")
                self._token_chunker = TokenChunker(
                    chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
                )
            return

        try:
            logger.info(f"Loading semantic chunking model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Semantic chunking model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}", exc_info=True)
            if self.fallback_to_token:
                logger.info("Falling back to token-based chunking")
                self._token_chunker = TokenChunker(
                    chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
                )

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        import re

        # Simple sentence splitting (can be improved with NLTK/spaCy)
        sentences = re.split(r"[.!?]+\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # If no sentences found, split by newlines
        if not sentences:
            sentences = [s.strip() for s in text.split("\n") if s.strip()]

        # If still no sentences, split by periods
        if not sentences:
            sentences = [s.strip() for s in text.split(".") if s.strip()]

        return sentences

    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.warning(f"Error calculating similarity: {e}")
            return 0.0

    def _detect_topic_shifts(self, sentences: List[str]) -> List[int]:
        """
        Detect topic shift points in sentences.

        Args:
            sentences: List of sentences

        Returns:
            List of indices where topic shifts occur
        """
        if not self._model or len(sentences) < 2:
            return []

        try:
            # Generate embeddings for all sentences
            embeddings = self._model.encode(sentences, show_progress_bar=False)

            # Calculate similarities between consecutive sentences
            similarities = []
            for i in range(len(embeddings) - 1):
                similarity = self._calculate_similarity(embeddings[i], embeddings[i + 1])
                similarities.append(similarity)

            # Detect topic shifts (low similarity = topic shift)
            topic_shifts = []
            for i, similarity in enumerate(similarities):
                if similarity < self.similarity_threshold:
                    topic_shifts.append(i + 1)  # Shift occurs after sentence i

            logger.debug(
                f"Detected {len(topic_shifts)} topic shifts from {len(sentences)} sentences"
            )
            return topic_shifts

        except Exception as e:
            logger.error(f"Error detecting topic shifts: {e}", exc_info=True)
            return []

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text using semantic topic shift detection.

        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of chunk dictionaries

        Raises:
            ChunkingError: If chunking fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Fallback to token chunker if model not available
        if self._token_chunker and not self._model:
            logger.info("Using token-based chunking as fallback")
            return self._token_chunker.chunk(text, metadata)

        try:
            # Split text into sentences
            sentences = self._split_into_sentences(text)
            if not sentences:
                logger.warning("No sentences found in text")
                # Return single chunk
                chunk_metadata = self.create_chunk_metadata(metadata, 0, 0, len(text))
                return [{"text": text, **chunk_metadata}]

            # Detect topic shifts
            topic_shifts = self._detect_topic_shifts(sentences)

            # If no topic shifts detected, use token-based chunking
            if not topic_shifts:
                logger.info("No topic shifts detected, using token-based chunking")
                if self._token_chunker:
                    return self._token_chunker.chunk(text, metadata)
                # Create single chunk
                chunk_metadata = self.create_chunk_metadata(metadata, 0, 0, len(text))
                return [{"text": text, **chunk_metadata}]

            # Create chunks based on topic shifts
            chunks = []
            start_sentence = 0
            chunk_index = 0

            # Add end of text as final shift point
            shift_points = sorted(topic_shifts) + [len(sentences)]

            for shift_point in shift_points:
                # Get sentences for this chunk
                chunk_sentences = sentences[start_sentence:shift_point]
                chunk_text = " ".join(chunk_sentences)

                # Calculate character positions
                # Find start position in original text
                start_char = text.find(chunk_sentences[0]) if chunk_sentences else 0
                # Find end position
                end_char = start_char + len(chunk_text)
                end_char = min(end_char, len(text))

                # Validate chunk size
                chunk_length = len(chunk_text)
                if chunk_length > self.max_chunk_size:
                    # Chunk is too large, split it using token chunker
                    logger.warning(
                        f"Chunk {chunk_index} is too large ({chunk_length}), splitting further"
                    )
                    if self._token_chunker:
                        sub_chunks = self._token_chunker.chunk(chunk_text, metadata)
                        for sub_chunk in sub_chunks:
                            sub_chunk["chunk_index"] = chunk_index
                            sub_chunk["topic_shift"] = True
                            chunks.append(sub_chunk)
                            chunk_index += 1
                    else:
                        # Truncate chunk
                        chunk_text = chunk_text[: self.max_chunk_size]
                        chunk_metadata = self.create_chunk_metadata(
                            metadata, chunk_index, start_char, start_char + len(chunk_text)
                        )
                        chunk_metadata["topic_shift"] = True
                        chunks.append({"text": chunk_text, **chunk_metadata})
                        chunk_index += 1
                elif self.validate_chunk(chunk_text, chunk_index):
                    # Valid chunk
                    chunk_metadata = self.create_chunk_metadata(
                        metadata, chunk_index, start_char, end_char
                    )
                    chunk_metadata["topic_shift"] = True
                    chunk_metadata["sentence_count"] = len(chunk_sentences)
                    chunks.append({"text": chunk_text, **chunk_metadata})
                    chunk_index += 1

                start_sentence = shift_point

            if not chunks:
                logger.warning("No valid chunks created from semantic chunking")
                # Fallback to token chunker
                if self._token_chunker:
                    return self._token_chunker.chunk(text, metadata)
                # Return single chunk
                chunk_metadata = self.create_chunk_metadata(metadata, 0, 0, len(text))
                return [{"text": text, **chunk_metadata}]

            logger.info(f"Created {len(chunks)} semantic chunks from {len(sentences)} sentences")
            return chunks

        except Exception as e:
            logger.error(f"Error during semantic chunking: {e}", exc_info=True)
            # Fallback to token chunker on error
            if self._token_chunker:
                logger.info("Falling back to token-based chunking due to error")
                return self._token_chunker.chunk(text, metadata)
            raise ChunkingError(f"Failed to chunk text semantically: {str(e)}") from e

    def get_chunk_size(self) -> int:
        """
        Get the typical chunk size for this strategy.

        Returns:
            Typical chunk size (characters, approximate)
        """
        return self.chunk_size

