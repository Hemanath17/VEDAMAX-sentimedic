"""Token-based chunker using tiktoken or transformers tokenizer."""

from pathlib import Path
from typing import List, Dict, Any, Optional

from src.ingestion.chunkers.chunk_strategy import ChunkStrategy, ChunkingError
from src.config.logging_config import get_logger

logger = get_logger(__name__)

# Try to import tokenizers
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, will try transformers tokenizer")

try:
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not available for tokenization")


class TokenChunker(ChunkStrategy):
    """Token-based chunker that splits text by token count."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        model_name: str = "gpt-3.5-turbo",
        encoding_name: Optional[str] = None,
    ):
        """
        Initialize token-based chunker.

        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            model_name: Model name for tiktoken (e.g., "gpt-3.5-turbo")
            encoding_name: Encoding name for tiktoken (e.g., "cl100k_base")
        """
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.model_name = model_name
        self.encoding_name = encoding_name
        self._tokenizer = None
        self._initialize_tokenizer()

    def _initialize_tokenizer(self) -> None:
        """Initialize the tokenizer."""
        if TIKTOKEN_AVAILABLE:
            try:
                if self.encoding_name:
                    self._tokenizer = tiktoken.get_encoding(self.encoding_name)
                else:
                    self._tokenizer = tiktoken.encoding_for_model(self.model_name)
                logger.info(f"Initialized tiktoken tokenizer: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken: {e}, falling back to transformers")
                self._tokenizer = None

        if self._tokenizer is None and TRANSFORMERS_AVAILABLE:
            try:
                # Use a simple tokenizer as fallback
                self._tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
                logger.info("Initialized transformers tokenizer as fallback")
            except Exception as e:
                logger.warning(f"Failed to initialize transformers tokenizer: {e}")

        if self._tokenizer is None:
            logger.warning(
                "No tokenizer available. TokenChunker will use character-based estimation."
            )

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if self._tokenizer is None:
            # Fallback: rough estimation (4 characters per token)
            return len(text) // 4

        try:
            if TIKTOKEN_AVAILABLE and isinstance(self._tokenizer, tiktoken.Encoding):
                return len(self._tokenizer.encode(text))
            elif TRANSFORMERS_AVAILABLE:
                return len(self._tokenizer.encode(text, add_special_tokens=False))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}, using character estimation")
            return len(text) // 4

        return len(text) // 4

    def _encode_tokens(self, text: str) -> List[int]:
        """
        Encode text to token IDs.

        Args:
            text: Text to encode

        Returns:
            List of token IDs
        """
        if self._tokenizer is None:
            return list(range(len(text) // 4))  # Dummy tokens

        try:
            if TIKTOKEN_AVAILABLE and isinstance(self._tokenizer, tiktoken.Encoding):
                return self._tokenizer.encode(text)
            elif TRANSFORMERS_AVAILABLE:
                return self._tokenizer.encode(text, add_special_tokens=False)
        except Exception as e:
            logger.warning(f"Error encoding tokens: {e}")
            return list(range(len(text) // 4))

        return list(range(len(text) // 4))

    def _decode_tokens(self, token_ids: List[int]) -> str:
        """
        Decode token IDs to text.

        Args:
            token_ids: List of token IDs

        Returns:
            Decoded text
        """
        if self._tokenizer is None:
            return ""

        try:
            if TIKTOKEN_AVAILABLE and isinstance(self._tokenizer, tiktoken.Encoding):
                return self._tokenizer.decode(token_ids)
            elif TRANSFORMERS_AVAILABLE:
                return self._tokenizer.decode(token_ids, skip_special_tokens=True)
        except Exception as e:
            logger.warning(f"Error decoding tokens: {e}")
            return ""

        return ""

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by token count.

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

        try:
            # Encode text to tokens
            token_ids = self._encode_tokens(text)
            total_tokens = len(token_ids)

            if total_tokens <= self.chunk_size:
                # Text fits in one chunk
                chunk_text = text
                chunk_metadata = self.create_chunk_metadata(
                    metadata, 0, 0, len(text), token_count=total_tokens
                )
                return [{"text": chunk_text, **chunk_metadata}]

            chunks = []
            overlap_tokens = self.calculate_overlap(self.chunk_size)
            start_token = 0
            chunk_index = 0

            while start_token < total_tokens:
                # Calculate end token position
                end_token = min(start_token + self.chunk_size, total_tokens)

                # Extract tokens for this chunk
                chunk_token_ids = token_ids[start_token:end_token]

                # Decode tokens to text
                chunk_text = self._decode_tokens(chunk_token_ids)

                # Calculate character positions (approximate)
                # This is an approximation since token boundaries != character boundaries
                start_char = int((start_token / total_tokens) * len(text))
                end_char = int((end_token / total_tokens) * len(text))
                end_char = min(end_char, len(text))

                # Validate chunk
                if self.validate_chunk(chunk_text, chunk_index):
                    chunk_metadata = self.create_chunk_metadata(
                        metadata,
                        chunk_index,
                        start_char,
                        end_char,
                        token_count=len(chunk_token_ids),
                    )
                    chunks.append({"text": chunk_text, **chunk_metadata})
                    chunk_index += 1

                # Move to next chunk with overlap
                if end_token >= total_tokens:
                    break
                start_token = end_token - overlap_tokens

            if not chunks:
                logger.warning("No valid chunks created")
                # Return at least one chunk with full text
                chunk_metadata = self.create_chunk_metadata(
                    metadata, 0, 0, len(text), token_count=total_tokens
                )
                return [{"text": text, **chunk_metadata}]

            logger.info(f"Created {len(chunks)} chunks from {total_tokens} tokens")
            return chunks

        except Exception as e:
            logger.error(f"Error during token chunking: {e}", exc_info=True)
            raise ChunkingError(f"Failed to chunk text: {str(e)}") from e

    def get_chunk_size(self) -> int:
        """
        Get the typical chunk size for this strategy.

        Returns:
            Typical chunk size in tokens
        """
        return self.chunk_size

