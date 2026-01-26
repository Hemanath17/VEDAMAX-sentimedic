"""Emotion trend tracking for safety and personalization."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from statistics import mean

from src.context.storage import get_storage_manager, EmotionRecordModel
from src.context.models import EmotionRecord, EmotionTrend
from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class EmotionTracker:
    """
    Tracks emotion patterns over time for safety monitoring and personalization.
    
    Personalization: Adjusts empathy based on trends (e.g., increasing anxiety → higher empathy).
    """

    def __init__(self):
        """Initialize emotion tracker."""
        self.storage = get_storage_manager()
        logger.info("Initialized EmotionTracker")

    def record_emotion(
        self,
        user_id: str,
        session_id: str,
        emotion_bucket: str,
        anxiety_level: float,
        risk_level: float,
        sentiment_score: float,
    ) -> EmotionRecord:
        """
        Record emotion analysis result (called for every message).

        Args:
            user_id: User ID
            session_id: Session ID
            emotion_bucket: VEDAMAX emotion bucket
            anxiety_level: Anxiety level (0-1)
            risk_level: Risk level (0-1)
            sentiment_score: Sentiment score (-1 to 1)

        Returns:
            EmotionRecord object
        """
        record_id = self.storage.generate_id()
        record = EmotionRecord(
            record_id=record_id,
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.now(),
            emotion_bucket=emotion_bucket,
            anxiety_level=anxiety_level,
            risk_level=risk_level,
            sentiment_score=sentiment_score,
        )

        with self.storage.get_session() as session:
            record_model = EmotionRecordModel(
                record_id=record.record_id,
                user_id=record.user_id,
                session_id=record.session_id,
                timestamp=record.timestamp,
                emotion_bucket=record.emotion_bucket,
                anxiety_level=record.anxiety_level,
                risk_level=record.risk_level,
                sentiment_score=record.sentiment_score,
            )
            session.add(record_model)

        logger.debug(
            f"Recorded emotion for user {user_id}: {emotion_bucket}, "
            f"anxiety={anxiety_level:.2f}, risk={risk_level:.2f}"
        )
        return record

    def get_recent_emotions(
        self,
        user_id: str,
        hours: int = 24,
        limit: Optional[int] = None,
    ) -> List[EmotionRecord]:
        """
        Get recent emotion records.

        Args:
            user_id: User ID
            hours: Number of hours to look back
            limit: Maximum number of records

        Returns:
            List of EmotionRecord objects
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self.storage.get_session() as session:
            query = session.query(EmotionRecordModel).filter(
                EmotionRecordModel.user_id == user_id,
                EmotionRecordModel.timestamp >= cutoff_time,
            ).order_by(
                EmotionRecordModel.timestamp.desc()
            )

            if limit:
                query = query.limit(limit)

            records = query.all()

            return [
                EmotionRecord(
                    record_id=rec.record_id,
                    user_id=rec.user_id,
                    session_id=rec.session_id,
                    timestamp=rec.timestamp,
                    emotion_bucket=rec.emotion_bucket,
                    anxiety_level=rec.anxiety_level,
                    risk_level=rec.risk_level,
                    sentiment_score=rec.sentiment_score,
                )
                for rec in records
            ]

    def calculate_anxiety_trend(
        self,
        user_id: str,
        hours: int = 24,
    ) -> EmotionTrend:
        """
        Calculate anxiety trend over time.

        Args:
            user_id: User ID
            hours: Time period to analyze

        Returns:
            EmotionTrend object
        """
        records = self.get_recent_emotions(user_id, hours=hours)

        if len(records) < 2:
            # Not enough data
            return EmotionTrend(
                user_id=user_id,
                trend_type="stable",
                current_value=0.0,
                previous_value=0.0,
                change_percentage=0.0,
                time_period=f"{hours}h",
                samples_count=len(records),
            )

        # Split into two halves
        mid_point = len(records) // 2
        recent = records[:mid_point]
        previous = records[mid_point:]

        recent_avg = mean([r.anxiety_level for r in recent])
        previous_avg = mean([r.anxiety_level for r in previous])

        change = recent_avg - previous_avg
        change_percentage = (change / previous_avg * 100) if previous_avg > 0 else 0.0

        # Determine trend
        if change_percentage > 10:
            trend_type = "increasing"
        elif change_percentage < -10:
            trend_type = "decreasing"
        else:
            trend_type = "stable"

        return EmotionTrend(
            user_id=user_id,
            trend_type=trend_type,
            current_value=recent_avg,
            previous_value=previous_avg,
            change_percentage=change_percentage,
            time_period=f"{hours}h",
            samples_count=len(records),
        )

    def calculate_risk_trend(
        self,
        user_id: str,
        hours: int = 24,
    ) -> EmotionTrend:
        """
        Calculate risk trend over time.

        Args:
            user_id: User ID
            hours: Time period to analyze

        Returns:
            EmotionTrend object
        """
        records = self.get_recent_emotions(user_id, hours=hours)

        if len(records) < 2:
            return EmotionTrend(
                user_id=user_id,
                trend_type="stable",
                current_value=0.0,
                previous_value=0.0,
                change_percentage=0.0,
                time_period=f"{hours}h",
                samples_count=len(records),
            )

        mid_point = len(records) // 2
        recent = records[:mid_point]
        previous = records[mid_point:]

        recent_avg = mean([r.risk_level for r in recent])
        previous_avg = mean([r.risk_level for r in previous])

        change = recent_avg - previous_avg
        change_percentage = (change / previous_avg * 100) if previous_avg > 0 else 0.0

        if change_percentage > 10:
            trend_type = "increasing"
        elif change_percentage < -10:
            trend_type = "decreasing"
        else:
            trend_type = "stable"

        return EmotionTrend(
            user_id=user_id,
            trend_type=trend_type,
            current_value=recent_avg,
            previous_value=previous_avg,
            change_percentage=change_percentage,
            time_period=f"{hours}h",
            samples_count=len(records),
        )

    def detect_anxiety_spike(
        self,
        user_id: str,
        threshold: float = 0.7,
        hours: int = 1,
    ) -> bool:
        """
        Detect if there's an anxiety spike.

        Args:
            user_id: User ID
            threshold: Anxiety threshold
            hours: Time window

        Returns:
            True if spike detected
        """
        records = self.get_recent_emotions(user_id, hours=hours, limit=10)

        if not records:
            return False

        # Check if any recent record exceeds threshold
        for record in records[:5]:  # Check last 5
            if record.anxiety_level >= threshold:
                return True

        return False

    def get_emotion_summary(
        self,
        user_id: str,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get emotion summary for user.

        Args:
            user_id: User ID
            hours: Time period

        Returns:
            Summary dictionary
        """
        records = self.get_recent_emotions(user_id, hours=hours)

        if not records:
            return {
                "total_records": 0,
                "average_anxiety": 0.0,
                "average_risk": 0.0,
                "dominant_bucket": None,
            }

        anxiety_trend = self.calculate_anxiety_trend(user_id, hours=hours)
        risk_trend = self.calculate_risk_trend(user_id, hours=hours)

        # Count emotion buckets
        bucket_counts = {}
        for record in records:
            bucket = record.emotion_bucket
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        dominant_bucket = max(bucket_counts.items(), key=lambda x: x[1])[0] if bucket_counts else None

        return {
            "total_records": len(records),
            "average_anxiety": mean([r.anxiety_level for r in records]),
            "average_risk": mean([r.risk_level for r in records]),
            "dominant_bucket": dominant_bucket,
            "anxiety_trend": anxiety_trend.trend_type,
            "risk_trend": risk_trend.trend_type,
            "anxiety_spike": self.detect_anxiety_spike(user_id),
        }

