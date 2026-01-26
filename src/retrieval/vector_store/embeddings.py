"""
Step 2: BGE-M3 Embedding Model Integration

Simple Explanation:
BGE-M3 is a smart model that converts text into numbers (vectors).
Think of it like a translator: text in → numbers out.
These numbers represent the meaning of the text, so similar texts have similar numbers.

Why We Need It:
- Converts medical text into searchable vectors
- Enables semantic search (finding meaning, not just keywords)
- BGE-M3 is one of the best models for this task
"""

from typing import List, Union, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingModel:
    """
    BGE-M3 embedding model wrapper.
    
    Simple Explanation:
    This class loads the BGE-M3 model and uses it to convert text into vectors.
    It's like a factory that takes text and produces embedding vectors.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize embedding model.

        Args:
            model_name: Model name (defaults to BAAI/bge-m3)
            device: Device to use ('cpu' or 'cuda')
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not available. Install with: pip install sentence-transformers"
            )

        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the BGE-M3 model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
            logger.info(
                f"Embedding model loaded successfully on {self.device}. "
                f"Vector size: {self.get_vector_size()}"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}", exc_info=True)
            raise

    def get_vector_size(self) -> int:
        """
        Get the dimension of vectors produced by this model.

        Simple Explanation:
        BGE-M3 produces vectors with 1024 numbers. This tells us that size.

        Returns:
            Vector dimension (1024 for BGE-M3)
        """
        if self._model is None:
            return 0
        # BGE-M3 produces 1024-dimensional vectors
        return self._model.get_sentence_embedding_dimension()

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: Optional[int] = None,
        normalize: bool = True,
        show_progress: bool = False,
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Convert text(s) to embedding vector(s).

        Simple Explanation:
        This is the main function - it takes text and converts it to numbers.
        Input: "What is diabetes?"
        Output: [0.123, -0.456, 0.789, ...] (1024 numbers)

        Args:
            texts: Single text or list of texts
            batch_size: Number of texts to process at once
            normalize: Whether to normalize vectors (recommended)
            show_progress: Whether to show progress bar

        Returns:
            Numpy array of embeddings (or list if single text)
        """
        if self._model is None:
            raise RuntimeError("Model not loaded")

        if isinstance(texts, str):
            texts = [texts]

        batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE

        try:
            # Generate embeddings
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
            )

            logger.debug(f"Generated embeddings for {len(texts)} texts")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
            raise

    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Encode a single text (convenience method).

        Simple Explanation:
        Same as encode(), but specifically for one piece of text.

        Args:
            text: Text to encode
            normalize: Whether to normalize the vector

        Returns:
            Embedding vector as numpy array
        """
        embeddings = self.encode([text], normalize=normalize, show_progress=False)
        return embeddings[0]

    def encode_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        normalize: bool = True,
        show_progress: bool = True,
    ) -> np.ndarray:
        """
        Encode multiple texts in batches.

        Simple Explanation:
        Processes many texts efficiently by doing them in groups (batches).
        Like washing dishes - you do a few at a time, not one by one.

        Args:
            texts: List of texts to encode
            batch_size: Number of texts per batch
            normalize: Whether to normalize vectors
            show_progress: Whether to show progress bar

        Returns:
            Numpy array of embeddings
        """
        return self.encode(
            texts,
            batch_size=batch_size,
            normalize=normalize,
            show_progress=show_progress,
        )

    def similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Simple Explanation:
        Measures how similar two vectors are (0 = different, 1 = identical).
        Like comparing two fingerprints - higher score = more similar.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0 and 1
        """
        # Cosine similarity: dot product of normalized vectors
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

