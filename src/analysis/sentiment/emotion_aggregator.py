"""Emotion aggregation layer: Maps GoEmotions (28 labels) to VEDAMAX buckets (7)."""

from typing import Dict, List, Any, Optional
from enum import Enum

from src.config.constants import GO_EMOTIONS_LABELS, VEDAMAX_EMOTION_BUCKETS
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class VEDAMAXEmotionBucket(str, Enum):
    """VEDAMAX emotion buckets for clinical interpretation."""

    NEUTRAL = "NEUTRAL"
    LOW_CONCERN = "LOW_CONCERN"
    ANTICIPATORY_STRESS = "ANTICIPATORY_STRESS"
    HIGH_ANXIETY = "HIGH_ANXIETY"
    SADNESS_GRIEF = "SADNESS_GRIEF"
    FRUSTRATION_ANGER = "FRUSTRATION_ANGER"
    HIGH_RISK = "HIGH_RISK"


class EmotionAggregator:
    """Aggregates fine-grained GoEmotions (28 labels) to VEDAMAX buckets (7)."""

    # Mapping from GoEmotions labels to VEDAMAX buckets
    # Maps all 28 GoEmotions labels to 7 clinically interpretable buckets
    GO_EMOTIONS_TO_BUCKET = {
        # NEUTRAL bucket - Pure info, positive/neutral states
        "neutral": VEDAMAXEmotionBucket.NEUTRAL,
        "curiosity": VEDAMAXEmotionBucket.NEUTRAL,
        "realization": VEDAMAXEmotionBucket.NEUTRAL,
        "approval": VEDAMAXEmotionBucket.NEUTRAL,
        "optimism": VEDAMAXEmotionBucket.NEUTRAL,
        "pride": VEDAMAXEmotionBucket.NEUTRAL,
        "relief": VEDAMAXEmotionBucket.NEUTRAL,
        "gratitude": VEDAMAXEmotionBucket.NEUTRAL,
        "admiration": VEDAMAXEmotionBucket.NEUTRAL,
        "joy": VEDAMAXEmotionBucket.NEUTRAL,  # Positive emotion -> neutral bucket
        "excitement": VEDAMAXEmotionBucket.NEUTRAL,
        "amusement": VEDAMAXEmotionBucket.NEUTRAL,
        "love": VEDAMAXEmotionBucket.NEUTRAL,
        "caring": VEDAMAXEmotionBucket.NEUTRAL,
        "desire": VEDAMAXEmotionBucket.NEUTRAL,
        
        # LOW_CONCERN bucket - Mild unease
        "nervousness": VEDAMAXEmotionBucket.LOW_CONCERN,
        "confusion": VEDAMAXEmotionBucket.LOW_CONCERN,
        "surprise": VEDAMAXEmotionBucket.LOW_CONCERN,
        
        # ANTICIPATORY_STRESS bucket - Waiting anxiety
        "disappointment": VEDAMAXEmotionBucket.ANTICIPATORY_STRESS,
        "embarrassment": VEDAMAXEmotionBucket.ANTICIPATORY_STRESS,
        "disapproval": VEDAMAXEmotionBucket.ANTICIPATORY_STRESS,
        
        # HIGH_ANXIETY bucket - Health fear
        "fear": VEDAMAXEmotionBucket.HIGH_ANXIETY,
        
        # SADNESS_GRIEF bucket - Emotional pain
        "sadness": VEDAMAXEmotionBucket.SADNESS_GRIEF,
        "grief": VEDAMAXEmotionBucket.SADNESS_GRIEF,
        "remorse": VEDAMAXEmotionBucket.SADNESS_GRIEF,
        
        # FRUSTRATION_ANGER bucket - System friction
        "anger": VEDAMAXEmotionBucket.FRUSTRATION_ANGER,
        "annoyance": VEDAMAXEmotionBucket.FRUSTRATION_ANGER,
        "disgust": VEDAMAXEmotionBucket.FRUSTRATION_ANGER,
        
        # HIGH_RISK bucket - Detected through pattern analysis
        # (No direct mapping, detected via _detect_high_risk method)
    }

    # Positive emotions that don't require special handling
    POSITIVE_EMOTIONS = [
        "joy", "excitement", "amusement", "love", "caring", "desire"
    ]

    @classmethod
    def aggregate_to_bucket(
        cls, 
        go_emotions_scores: Dict[str, float],
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Aggregate GoEmotions scores to VEDAMAX emotion buckets.

        Args:
            go_emotions_scores: Dictionary of GoEmotions label -> confidence score
            threshold: Minimum score threshold for consideration

        Returns:
            Dictionary with bucket scores and dominant bucket:
            {
                "buckets": Dict[str, float],  # bucket -> aggregated score
                "dominant_bucket": str,       # Highest scoring bucket
                "dominant_score": float,       # Score of dominant bucket
                "go_emotions": Dict[str, float],  # Original GoEmotions scores
                "risk_level": float,           # Overall risk level (0.0-1.0)
                "anxiety_level": float,        # Anxiety-specific score
            }
        """
        # Initialize bucket scores
        bucket_scores = {
            bucket.value: 0.0 for bucket in VEDAMAXEmotionBucket
        }

        # Aggregate scores by bucket
        for emotion, score in go_emotions_scores.items():
            if score < threshold:
                continue

            emotion_lower = emotion.lower()
            
            # Map to bucket
            bucket = cls.GO_EMOTIONS_TO_BUCKET.get(emotion_lower)
            
            if bucket:
                bucket_scores[bucket.value] += score
            elif emotion_lower in cls.POSITIVE_EMOTIONS:
                # Positive emotions contribute to NEUTRAL or LOW_CONCERN
                bucket_scores[VEDAMAXEmotionBucket.NEUTRAL.value] += score * 0.5
            else:
                # Unknown emotions default to LOW_CONCERN
                bucket_scores[VEDAMAXEmotionBucket.LOW_CONCERN.value] += score * 0.3

        # Normalize bucket scores (sum to 1.0)
        total_score = sum(bucket_scores.values())
        if total_score > 0:
            bucket_scores = {
                bucket: score / total_score 
                for bucket, score in bucket_scores.items()
            }

        # Find dominant bucket
        dominant_bucket = max(bucket_scores.items(), key=lambda x: x[1])
        
        # Calculate risk level based on high-risk buckets
        risk_level = (
            bucket_scores.get(VEDAMAXEmotionBucket.HIGH_RISK.value, 0.0) * 0.95 +
            bucket_scores.get(VEDAMAXEmotionBucket.HIGH_ANXIETY.value, 0.0) * 0.6 +
            bucket_scores.get(VEDAMAXEmotionBucket.SADNESS_GRIEF.value, 0.0) * 0.5
        )
        risk_level = min(risk_level, 1.0)

        # Calculate anxiety level
        anxiety_level = (
            bucket_scores.get(VEDAMAXEmotionBucket.HIGH_ANXIETY.value, 0.0) * 0.7 +
            bucket_scores.get(VEDAMAXEmotionBucket.ANTICIPATORY_STRESS.value, 0.0) * 0.5 +
            bucket_scores.get(VEDAMAXEmotionBucket.LOW_CONCERN.value, 0.0) * 0.3
        )
        anxiety_level = min(anxiety_level, 1.0)

        # Detect HIGH_RISK through extreme patterns
        if cls._detect_high_risk(go_emotions_scores, bucket_scores):
            bucket_scores[VEDAMAXEmotionBucket.HIGH_RISK.value] = max(
                bucket_scores.get(VEDAMAXEmotionBucket.HIGH_RISK.value, 0.0),
                0.8
            )
            risk_level = max(risk_level, 0.9)

        return {
            "buckets": bucket_scores,
            "dominant_bucket": dominant_bucket[0],
            "dominant_score": dominant_bucket[1],
            "go_emotions": go_emotions_scores,
            "risk_level": risk_level,
            "anxiety_level": anxiety_level,
            "bucket_metadata": cls._get_bucket_metadata(dominant_bucket[0]),
        }

    @classmethod
    def _detect_high_risk(
        cls, 
        go_emotions_scores: Dict[str, float],
        bucket_scores: Dict[str, float]
    ) -> bool:
        """
        Detect high-risk emotional patterns.

        Args:
            go_emotions_scores: Original GoEmotions scores
            bucket_scores: Current bucket scores

        Returns:
            True if high-risk pattern detected
        """
        # High intensity fear + sadness + anger
        fear_score = go_emotions_scores.get("fear", 0.0)
        sadness_score = go_emotions_scores.get("sadness", 0.0)
        anger_score = go_emotions_scores.get("anger", 0.0)
        grief_score = go_emotions_scores.get("grief", 0.0)

        # Multiple high-intensity negative emotions
        high_negative_count = sum([
            fear_score > 0.7,
            sadness_score > 0.7,
            anger_score > 0.7,
            grief_score > 0.7,
        ])

        if high_negative_count >= 2:
            return True

        # Extreme fear or grief
        if fear_score > 0.9 or grief_score > 0.9:
            return True

        return False

    @classmethod
    def _get_bucket_metadata(cls, bucket_name: str) -> Dict[str, Any]:
        """
        Get metadata for a VEDAMAX bucket.

        Args:
            bucket_name: Bucket name

        Returns:
            Bucket metadata
        """
        bucket_info = VEDAMAX_EMOTION_BUCKETS.get(bucket_name, {})
        return {
            "bucket": bucket_name,
            "purpose": bucket_info.get("purpose", ""),
            "empathy_level": bucket_info.get("empathy_level", 0.5),
            "risk_level": bucket_info.get("risk_level", 0.0),
            "emotions": bucket_info.get("emotions", []),
        }

