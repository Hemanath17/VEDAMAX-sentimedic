"""Emotion-to-persona mapping for empathetic response generation."""

from typing import Dict, Any, Optional

from src.analysis.sentiment.emotion_aggregator import VEDAMAXEmotionBucket
from src.config.constants import PERSONA_LEVELS
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class PersonaMapper:
    """
    Maps detected emotions to persona levels for response generation.
    
    Architecture:
    VEDAMAX Emotion Buckets (7)
        ↓
    Persona Level Calculation
        ↓
    Empathy & Formality Adjustment
        ↓
    Agent Routing + Persona Control
    """

    # Mapping from VEDAMAX buckets to persona levels
    BUCKET_TO_PERSONA = {
        VEDAMAXEmotionBucket.NEUTRAL: "LOW",
        VEDAMAXEmotionBucket.LOW_CONCERN: "LOW",
        VEDAMAXEmotionBucket.ANTICIPATORY_STRESS: "MEDIUM",
        VEDAMAXEmotionBucket.HIGH_ANXIETY: "HIGH",
        VEDAMAXEmotionBucket.SADNESS_GRIEF: "HIGH",
        VEDAMAXEmotionBucket.FRUSTRATION_ANGER: "MEDIUM",
        VEDAMAXEmotionBucket.HIGH_RISK: "HIGH",
    }

    def __init__(self):
        """Initialize persona mapper."""
        logger.info("Initialized PersonaMapper")

    def map_to_persona(
        self,
        emotion_result: Dict[str, Any],
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Map emotion analysis to persona parameters.

        Args:
            emotion_result: Emotion classification result from EmotionClassifier
            custom_mapping: Optional custom bucket-to-persona mapping

        Returns:
            Dictionary with persona parameters:
            {
                "persona_level": str,          # "LOW", "MEDIUM", "HIGH"
                "empathy_level": float,        # 0.0 to 1.0
                "formality_level": float,       # 0.0 to 1.0
                "tone": str,                   # Tone description
                "response_style": str,         # Response style guidance
                "safety_priority": bool,       # Whether safety is priority
            }
        """
        # Get dominant bucket
        dominant_bucket = emotion_result.get("dominant_bucket")
        if not dominant_bucket:
            return self._default_persona()

        # Map bucket to persona level
        bucket_enum = VEDAMAXEmotionBucket(dominant_bucket)
        mapping = custom_mapping or self.BUCKET_TO_PERSONA
        persona_level = mapping.get(bucket_enum, "MEDIUM")

        # Get base persona parameters
        base_persona = PERSONA_LEVELS.get(persona_level, PERSONA_LEVELS["MEDIUM"])

        # Adjust based on risk and anxiety levels
        risk_level = emotion_result.get("risk_level", 0.0)
        anxiety_level = emotion_result.get("anxiety_level", 0.0)
        bucket_score = emotion_result.get("bucket_score", 0.0)

        # Calculate adjusted empathy (higher for high risk/anxiety)
        base_empathy = base_persona["empathy"]
        empathy_adjustment = (risk_level * 0.3) + (anxiety_level * 0.2)
        empathy_level = min(1.0, base_empathy + empathy_adjustment)

        # Calculate formality (lower for high emotion)
        base_formality = base_persona["formality"]
        formality_adjustment = -(risk_level * 0.2) - (anxiety_level * 0.15)
        formality_level = max(0.0, base_formality + formality_adjustment)

        # Determine tone and response style
        tone, response_style = self._determine_tone_and_style(
            bucket_enum, risk_level, anxiety_level
        )

        # Safety priority for high-risk buckets
        safety_priority = (
            bucket_enum == VEDAMAXEmotionBucket.HIGH_RISK
            or risk_level >= 0.8
            or bucket_enum == VEDAMAXEmotionBucket.HIGH_ANXIETY
        )

        return {
            "persona_level": persona_level,
            "empathy_level": empathy_level,
            "formality_level": formality_level,
            "tone": tone,
            "response_style": response_style,
            "safety_priority": safety_priority,
            "risk_level": risk_level,
            "anxiety_level": anxiety_level,
            "dominant_bucket": dominant_bucket,
            "bucket_score": bucket_score,
        }

    def _determine_tone_and_style(
        self,
        bucket: VEDAMAXEmotionBucket,
        risk_level: float,
        anxiety_level: float,
    ) -> tuple[str, str]:
        """
        Determine tone and response style based on emotion bucket.

        Args:
            bucket: VEDAMAX emotion bucket
            risk_level: Risk level (0.0-1.0)
            anxiety_level: Anxiety level (0.0-1.0)

        Returns:
            Tuple of (tone, response_style)
        """
        if bucket == VEDAMAXEmotionBucket.HIGH_RISK:
            return (
                "calm_reassuring",
                "immediate_support_with_clinical_grounding",
            )
        elif bucket == VEDAMAXEmotionBucket.HIGH_ANXIETY:
            return (
                "empathetic_reassuring",
                "validate_concerns_provide_clarity",
            )
        elif bucket == VEDAMAXEmotionBucket.SADNESS_GRIEF:
            return (
                "compassionate_supportive",
                "acknowledge_emotions_provide_comfort",
            )
        elif bucket == VEDAMAXEmotionBucket.FRUSTRATION_ANGER:
            return (
                "patient_understanding",
                "acknowledge_frustration_provide_solutions",
            )
        elif bucket == VEDAMAXEmotionBucket.ANTICIPATORY_STRESS:
            return (
                "supportive_informative",
                "address_concerns_provide_guidance",
            )
        elif bucket == VEDAMAXEmotionBucket.LOW_CONCERN:
            return (
                "friendly_helpful",
                "provide_information_address_questions",
            )
        else:  # NEUTRAL
            return (
                "professional_clear",
                "direct_informative_response",
            )

    def _default_persona(self) -> Dict[str, Any]:
        """Return default persona parameters."""
        return {
            "persona_level": "MEDIUM",
            "empathy_level": 0.5,
            "formality_level": 0.5,
            "tone": "professional_clear",
            "response_style": "direct_informative_response",
            "safety_priority": False,
            "risk_level": 0.0,
            "anxiety_level": 0.0,
            "dominant_bucket": VEDAMAXEmotionBucket.NEUTRAL.value,
            "bucket_score": 1.0,
        }

    def get_persona_for_bucket(self, bucket: VEDAMAXEmotionBucket) -> Dict[str, Any]:
        """
        Get persona parameters for a specific bucket.

        Args:
            bucket: VEDAMAX emotion bucket

        Returns:
            Persona parameters dictionary
        """
        mock_emotion_result = {
            "dominant_bucket": bucket.value,
            "risk_level": 0.5 if bucket in [
                VEDAMAXEmotionBucket.HIGH_ANXIETY,
                VEDAMAXEmotionBucket.SADNESS_GRIEF,
                VEDAMAXEmotionBucket.HIGH_RISK,
            ] else 0.2,
            "anxiety_level": 0.7 if bucket == VEDAMAXEmotionBucket.HIGH_ANXIETY else 0.3,
            "bucket_score": 0.8,
        }
        return self.map_to_persona(mock_emotion_result)

