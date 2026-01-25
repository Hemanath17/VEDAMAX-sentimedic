"""Emotion classifier using GoEmotions model (SamLowe/roberta-base-go_emotions)."""

from typing import List, Dict, Any, Optional
import numpy as np

from src.analysis.sentiment.emotion_aggregator import EmotionAggregator, VEDAMAXEmotionBucket
from src.config.logging_config import get_logger
from src.config.settings import settings
from src.config.constants import GO_EMOTIONS_LABELS

logger = get_logger(__name__)

# Try to import transformers
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers/torch not available, emotion classification will be limited")


class EmotionClassifier:
    """
    Emotion classification using GoEmotions model (28 labels).
    
    Architecture:
    SamLowe/roberta-base-go_emotions (28 labels)
        ↓
    Emotion Aggregation Layer
        ↓
    VEDAMAX Emotion Buckets (7)
        ↓
    Agent Routing + Persona Control
    """

    def __init__(
        self,
        model_name: str = "SamLowe/roberta-base-go_emotions",
        device: Optional[str] = None,
        batch_size: int = 16,
        use_aggregation: bool = True,
    ):
        """
        Initialize GoEmotions-based emotion classifier.

        Args:
            model_name: HuggingFace model name (default: SamLowe/roberta-base-go_emotions)
            device: Device to run on ('cpu' or 'cuda')
            batch_size: Batch size for processing
            use_aggregation: Whether to aggregate to VEDAMAX buckets
        """
        self.model_name = model_name
        self.device = device or settings.SENTIMENT_DEVICE
        self.batch_size = batch_size
        self.use_aggregation = use_aggregation
        self._pipeline = None
        self._tokenizer = None
        self._model = None
        self._aggregator = EmotionAggregator() if use_aggregation else None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the GoEmotions model."""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("transformers not available, emotion classification disabled")
            return

        try:
            logger.info(f"Loading GoEmotions model: {self.model_name}")
            
            # Initialize pipeline for multi-label classification
            self._pipeline = pipeline(
                "text-classification",
                model=self.model_name,
                device=0 if self.device == "cuda" and torch.cuda.is_available() else -1,
                return_all_scores=True,
                function_to_apply="sigmoid",  # Multi-label classification
            )
            
            logger.info(f"Successfully loaded GoEmotions model: {self.model_name}")

        except Exception as e:
            logger.error(f"Error loading GoEmotions model: {e}", exc_info=True)
            self._pipeline = None

    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify emotions in text using GoEmotions model.

        Args:
            text: Input text to classify

        Returns:
            Dictionary with emotion classifications:
            {
                "go_emotions": Dict[str, float],  # 28 GoEmotions labels -> scores
                "dominant_emotion": str,           # Highest confidence GoEmotion
                "dominant_confidence": float,     # Confidence of dominant emotion
                "buckets": Dict[str, float],       # VEDAMAX buckets -> scores (if aggregation)
                "dominant_bucket": str,            # Dominant VEDAMAX bucket
                "risk_level": float,               # Overall risk level (0.0-1.0)
                "anxiety_level": float,            # Anxiety-specific score
                "model": str,                      # Model name
            }
        """
        if not text or not text.strip():
            return self._empty_result()

        if not self._pipeline:
            logger.warning("GoEmotions model not available, returning default")
            return self._empty_result()

        try:
            # Run GoEmotions classification (28 labels)
            results = self._pipeline(text)

            # Process GoEmotions results
            go_emotions_scores = {}
            for result in results:
                label = result.get("label", "").lower()
                score = result.get("score", 0.0)
                go_emotions_scores[label] = score

            # Find dominant GoEmotion
            dominant_emotion = max(go_emotions_scores.items(), key=lambda x: x[1]) if go_emotions_scores else ("neutral", 0.5)

            # Base result with GoEmotions
            result = {
                "go_emotions": go_emotions_scores,
                "dominant_emotion": dominant_emotion[0],
                "dominant_confidence": dominant_emotion[1],
                "model": self.model_name,
            }

            # Aggregate to VEDAMAX buckets if enabled
            if self.use_aggregation and self._aggregator:
                aggregated = self._aggregator.aggregate_to_bucket(go_emotions_scores)
                result.update({
                    "buckets": aggregated["buckets"],
                    "dominant_bucket": aggregated["dominant_bucket"],
                    "bucket_score": aggregated["dominant_score"],
                    "risk_level": aggregated["risk_level"],
                    "anxiety_level": aggregated["anxiety_level"],
                    "bucket_metadata": aggregated["bucket_metadata"],
                })
            else:
                # Calculate basic anxiety level from GoEmotions
                result["anxiety_level"] = self._calculate_anxiety_from_go_emotions(go_emotions_scores)
                result["risk_level"] = 0.0

            return result

        except Exception as e:
            logger.error(f"Error classifying emotions: {e}", exc_info=True)
            return self._empty_result()

    def _calculate_anxiety_from_go_emotions(self, go_emotions_scores: Dict[str, float]) -> float:
        """
        Calculate anxiety level from GoEmotions scores.

        Args:
            go_emotions_scores: GoEmotions label -> score dictionary

        Returns:
            Anxiety level (0.0-1.0)
        """
        anxiety_indicators = {
            "fear": 0.7,
            "nervousness": 0.6,
            "worry": 0.5,  # If present in model
            "anxiety": 0.8,  # If present in model
        }

        anxiety_score = 0.0
        for emotion, weight in anxiety_indicators.items():
            score = go_emotions_scores.get(emotion, 0.0)
            anxiety_score += score * weight

        return min(anxiety_score, 1.0)

    def classify_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Classify emotions for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of classification results
        """
        results = []
        for text in texts:
            result = self.classify(text)
            results.append(result)
        return results

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty/default classification result."""
        return {
            "go_emotions": {"neutral": 1.0},
            "dominant_emotion": "neutral",
            "dominant_confidence": 1.0,
            "buckets": {VEDAMAXEmotionBucket.NEUTRAL.value: 1.0} if self.use_aggregation else {},
            "dominant_bucket": VEDAMAXEmotionBucket.NEUTRAL.value if self.use_aggregation else None,
            "risk_level": 0.0,
            "anxiety_level": 0.0,
            "model": None,
        }

    def get_emotion_categories(self) -> List[str]:
        """
        Get list of supported GoEmotions categories (28 labels).

        Returns:
            List of GoEmotions label names
        """
        return GO_EMOTIONS_LABELS.copy()

    def get_vedamax_buckets(self) -> List[str]:
        """
        Get list of VEDAMAX emotion buckets.

        Returns:
            List of bucket names
        """
        return [bucket.value for bucket in VEDAMAXEmotionBucket]

    def is_high_anxiety(self, classification_result: Dict[str, Any], threshold: float = 0.7) -> bool:
        """
        Check if classification indicates high anxiety.

        Args:
            classification_result: Result from classify() method
            threshold: Anxiety threshold (default 0.7)

        Returns:
            True if anxiety level exceeds threshold
        """
        anxiety_level = classification_result.get("anxiety_level", 0.0)
        return anxiety_level >= threshold

    def is_high_risk(self, classification_result: Dict[str, Any], threshold: float = 0.8) -> bool:
        """
        Check if classification indicates high risk.

        Args:
            classification_result: Result from classify() method
            threshold: Risk threshold (default 0.8)

        Returns:
            True if risk level exceeds threshold
        """
        risk_level = classification_result.get("risk_level", 0.0)
        dominant_bucket = classification_result.get("dominant_bucket", "")
        return risk_level >= threshold or dominant_bucket == VEDAMAXEmotionBucket.HIGH_RISK.value

