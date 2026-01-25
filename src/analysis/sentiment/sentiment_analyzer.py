"""Sentiment analyzer wrapper combining emotion and sentiment analysis."""

from typing import Dict, Any, Optional

from src.analysis.sentiment.emotion_classifier import EmotionClassifier
from src.analysis.sentiment.emotion_aggregator import VEDAMAXEmotionBucket
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class SentimentAnalyzer:
    """Sentiment analyzer that combines emotion classification with sentiment scoring."""

    def __init__(
        self,
        emotion_classifier: Optional[EmotionClassifier] = None,
    ):
        """
        Initialize sentiment analyzer.

        Args:
            emotion_classifier: EmotionClassifier instance (creates new if None)
        """
        self.emotion_classifier = emotion_classifier or EmotionClassifier()
        logger.info("Initialized SentimentAnalyzer")

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Perform comprehensive sentiment and emotion analysis.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary with sentiment analysis:
            {
                "sentiment": str,              # "positive", "negative", "neutral"
                "sentiment_score": float,      # -1.0 to 1.0
                "emotion_analysis": Dict,      # Full emotion classification result
                "dominant_bucket": str,         # VEDAMAX emotion bucket
                "risk_level": float,           # Risk level (0.0-1.0)
                "anxiety_level": float,        # Anxiety level (0.0-1.0)
            }
        """
        if not text or not text.strip():
            return self._empty_result()

        try:
            # Get emotion classification
            emotion_result = self.emotion_classifier.classify(text)

            # Calculate sentiment from emotions
            sentiment_score = self._calculate_sentiment_score(emotion_result)
            sentiment_label = self._get_sentiment_label(sentiment_score)

            return {
                "sentiment": sentiment_label,
                "sentiment_score": sentiment_score,
                "emotion_analysis": emotion_result,
                "dominant_bucket": emotion_result.get("dominant_bucket"),
                "bucket_score": emotion_result.get("bucket_score", 0.0),
                "risk_level": emotion_result.get("risk_level", 0.0),
                "anxiety_level": emotion_result.get("anxiety_level", 0.0),
                "go_emotions": emotion_result.get("go_emotions", {}),
            }

        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}", exc_info=True)
            return self._empty_result()

    def _calculate_sentiment_score(self, emotion_result: Dict[str, Any]) -> float:
        """
        Calculate sentiment score from emotion analysis.

        Args:
            emotion_result: Emotion classification result

        Returns:
            Sentiment score from -1.0 (negative) to 1.0 (positive)
        """
        buckets = emotion_result.get("buckets", {})
        go_emotions = emotion_result.get("go_emotions", {})

        # Positive sentiment indicators
        positive_emotions = ["joy", "excitement", "amusement", "love", "caring", "gratitude", "pride", "relief"]
        positive_score = sum(go_emotions.get(emotion, 0.0) for emotion in positive_emotions)

        # Negative sentiment indicators
        negative_emotions = ["sadness", "anger", "fear", "grief", "disappointment", "annoyance", "disgust"]
        negative_score = sum(go_emotions.get(emotion, 0.0) for emotion in negative_emotions)

        # Calculate sentiment score
        total = positive_score + negative_score
        if total == 0:
            return 0.0  # Neutral

        sentiment_score = (positive_score - negative_score) / total
        return max(-1.0, min(1.0, sentiment_score))

    def _get_sentiment_label(self, sentiment_score: float) -> str:
        """
        Get sentiment label from score.

        Args:
            sentiment_score: Sentiment score (-1.0 to 1.0)

        Returns:
            Sentiment label: "positive", "negative", or "neutral"
        """
        if sentiment_score > 0.2:
            return "positive"
        elif sentiment_score < -0.2:
            return "negative"
        else:
            return "neutral"

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty sentiment analysis result."""
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "emotion_analysis": {},
            "dominant_bucket": VEDAMAXEmotionBucket.NEUTRAL.value,
            "bucket_score": 1.0,
            "risk_level": 0.0,
            "anxiety_level": 0.0,
            "go_emotions": {},
        }

    def is_negative_sentiment(self, analysis_result: Dict[str, Any]) -> bool:
        """
        Check if sentiment is negative.

        Args:
            analysis_result: Result from analyze() method

        Returns:
            True if sentiment is negative
        """
        return analysis_result.get("sentiment") == "negative"

    def is_high_risk(self, analysis_result: Dict[str, Any], threshold: float = 0.8) -> bool:
        """
        Check if analysis indicates high risk.

        Args:
            analysis_result: Result from analyze() method
            threshold: Risk threshold

        Returns:
            True if risk level exceeds threshold
        """
        return analysis_result.get("risk_level", 0.0) >= threshold

