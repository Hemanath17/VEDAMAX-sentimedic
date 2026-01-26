"""
Step 3: Embedding Generation Pipeline

Simple Explanation:
This is like an assembly line for converting text into vectors.
It takes text chunks, cleans them up, converts them to embeddings,
and makes sure everything is ready for storage.

Why We Need It:
- Standardizes the embedding process
- Handles preprocessing (cleaning text)
- Manages batch processing for efficiency
- Validates outputs before storage
"""

from typing import List, Dict, Any, Optional
import numpy as np

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Fallback: create a dummy tqdm
    def tqdm(iterable=None, *args, **kwargs):
        return iterable if iterable is not None else range(0)

from src.retrieval.vector_store.embeddings import EmbeddingModel
from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingPipeline:
    """
    Pipeline for generating embeddings from text chunks.
    
    Simple Explanation:
    Takes text → cleans it → converts to embeddings → validates → returns ready-to-store vectors.
    """

    def __init__(
        self,
        model: Optional[EmbeddingModel] = None,
        max_text_length: int = 512,
        normalize: bool = True,
    ):
        """
        Initialize embedding pipeline.

        Args:
            model: EmbeddingModel instance (creates new if None)
            max_text_length: Maximum text length (truncate if longer)
            normalize: Whether to normalize embeddings
        """
        self.model = model or EmbeddingModel()
        self.max_text_length = max_text_length
        self.normalize = normalize

        logger.info(
            f"Initialized EmbeddingPipeline: "
            f"model={self.model.model_name}, max_length={max_text_length}"
        )

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before embedding.

        Simple Explanation:
        Cleans up text - removes extra spaces, truncates if too long,
        makes sure it's ready for the model.

        Args:
            text: Raw text

        Returns:
            Preprocessed text
        """
        # Remove extra whitespace
        text = " ".join(text.split())

        # Truncate if too long
        if len(text) > self.max_text_length:
            text = text[:self.max_text_length]
            logger.debug(f"Truncated text to {self.max_text_length} characters")

        return text.strip()

    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple texts.

        Simple Explanation:
        Main function - takes a list of texts and converts them all to embeddings.
        Does it in batches for efficiency.

        Args:
            texts: List of texts to embed
            batch_size: Batch size (defaults to settings)
            show_progress: Whether to show progress bar

        Returns:
            List of dictionaries with text, embedding, and metadata
        """
        if not texts:
            return []

        # Preprocess texts
        processed_texts = [self.preprocess_text(text) for text in texts]

        # Generate embeddings in batches
        batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE

        try:
            embeddings = self.model.encode_batch(
                processed_texts,
                batch_size=batch_size,
                normalize=self.normalize,
                show_progress=show_progress,
            )

            # Format results
            results = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                results.append({
                    "text": text,
                    "embedding": embedding.tolist(),  # Convert numpy to list
                    "embedding_numpy": embedding,  # Keep numpy for calculations
                    "metadata": {
                        "text_length": len(text),
                        "preprocessed_length": len(processed_texts[i]),
                        "vector_size": len(embedding),
                    },
                })

            logger.info(f"Generated {len(results)} embeddings")
            return results

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
            raise

    def generate_single(self, text: str) -> Dict[str, Any]:
        """
        Generate embedding for a single text (convenience method).

        Args:
            text: Text to embed

        Returns:
            Dictionary with text, embedding, and metadata
        """
        results = self.generate_embeddings([text], show_progress=False)
        return results[0] if results else None

    def validate_embeddings(
        self,
        embeddings: List[Dict[str, Any]],
        expected_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Validate generated embeddings.

        Simple Explanation:
        Checks that embeddings are correct - right size, not empty, valid numbers.

        Args:
            embeddings: List of embedding results
            expected_size: Expected vector size (defaults to model size)

        Returns:
            Validated embeddings (invalid ones removed)
        """
        if expected_size is None:
            expected_size = self.model.get_vector_size()

        valid_embeddings = []
        for emb in embeddings:
            embedding = emb.get("embedding_numpy")
            if embedding is None:
                logger.warning("Embedding missing numpy array, skipping")
                continue

            # Check size
            if len(embedding) != expected_size:
                logger.warning(
                    f"Embedding size mismatch: {len(embedding)} != {expected_size}, skipping"
                )
                continue

            # Check for NaN or Inf
            if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
                logger.warning("Embedding contains NaN or Inf, skipping")
                continue

            valid_embeddings.append(emb)

        if len(valid_embeddings) < len(embeddings):
            logger.warning(
                f"Validated {len(valid_embeddings)}/{len(embeddings)} embeddings"
            )

        return valid_embeddings

