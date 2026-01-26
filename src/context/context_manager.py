"""Context manager orchestrates all context components for personalization."""

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.context.user_profile import UserProfileManager
from src.context.memory_manager import MemoryManager
from src.context.emotion_tracker import EmotionTracker
from src.context.risk_escalation import RiskEscalationDetector
from src.context.storage import get_storage_manager
from src.context.models import UserProfile, ConversationMessage, MemoryType
from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class ContextManager:
    """
    Orchestrates all context components for personalization.
    
    Personalization Flow:
    1. Load user profile → Get preferences, conditions, age
    2. Load conversation history → Get session/user/clinical memory
    3. Track emotions → Get trends and adjust empathy
    4. Monitor risk → Detect escalation and trigger safety
    5. Combine all → Provide unified context for response generation
    
    The system remembers:
    - User traits (preferences, conditions, age)
    - Conversation patterns (what they ask about)
    - Emotion trends (anxiety, risk over time)
    - Clinical history (frequently mentioned conditions)
    """

    def __init__(self):
        """Initialize context manager."""
        self.profile_manager = UserProfileManager()
        self.memory_manager = MemoryManager()
        self.emotion_tracker = EmotionTracker()
        self.risk_detector = RiskEscalationDetector()
        self.storage = get_storage_manager()
        logger.info("Initialized ContextManager")

    def initialize_user_context(
        self,
        raw_user_id: str,
        session_id: str,
        initial_risk: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Initialize user context for a new session.

        Args:
            raw_user_id: Raw user identifier (will be hashed)
            session_id: Session ID
            initial_risk: Initial risk level

        Returns:
            Context dictionary
        """
        # Hash user ID for anonymization
        user_id = self.storage.hash_user_id(raw_user_id)

        # Initialize session state
        self.risk_detector.initialize_session(session_id, user_id, initial_risk)

        # Load user profile
        profile = self.profile_manager.get_profile(user_id)

        # Get personalization context
        context = {
            "user_id": user_id,
            "session_id": session_id,
            "profile": profile.model_dump() if profile else {},
            "personalization": self.profile_manager.get_personalization_context(user_id),
            "session_memory": [],
            "user_memories": [],
            "clinical_memories": [],
            "emotion_summary": {},
            "risk_state": {
                "baseline_risk": initial_risk,
                "current_risk": initial_risk,
                "escalation_detected": False,
            },
        }

        logger.info(f"Initialized context for user {user_id}, session {session_id}")
        return context

    def process_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        analysis_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a message and update context.

        Args:
            user_id: Hashed user ID
            session_id: Session ID
            role: 'user' or 'assistant'
            content: Message content
            analysis_result: InputAnalyzer result (emotion, entities, etc.)

        Returns:
            Updated context dictionary
        """
        # Add message to memory
        metadata = {}
        if analysis_result:
            metadata = {
                "emotion": analysis_result.get("sentiment", {}),
                "entities": [e.model_dump() if hasattr(e, "model_dump") else (e.dict() if hasattr(e, "dict") else e) for e in analysis_result.get("entities", [])],
            }

        message = self.memory_manager.add_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
        )

        # If user message, process emotion and entities
        if role == "user" and analysis_result:
            sentiment = analysis_result.get("sentiment", {})
            emotion_analysis = sentiment.get("emotion_analysis", {})
            dominant_bucket = emotion_analysis.get("dominant_bucket", "NEUTRAL")
            anxiety_level = sentiment.get("anxiety_level", 0.0)
            risk_level = sentiment.get("risk_level", 0.0)
            sentiment_score = sentiment.get("sentiment_score", 0.0)

            # Record emotion (track every message)
            self.emotion_tracker.record_emotion(
                user_id=user_id,
                session_id=session_id,
                emotion_bucket=dominant_bucket,
                anxiety_level=anxiety_level,
                risk_level=risk_level,
                sentiment_score=sentiment_score,
            )

            # Update risk in session
            self.risk_detector.update_risk(session_id, risk_level)

            # Extract clinical memory from entities
            entities = analysis_result.get("entities", [])
            if entities:
                self.memory_manager.extract_clinical_memory(
                    user_id=user_id,
                    entities=[e.model_dump() if hasattr(e, "model_dump") else (e.dict() if hasattr(e, "dict") else e) for e in entities],
                    query=content,
                )

        # Get updated context
        return self.get_context(user_id, session_id)

    def get_context(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Get complete context for personalization.

        Args:
            user_id: Hashed user ID
            session_id: Session ID

        Returns:
            Complete context dictionary
        """
        # Get user profile
        profile = self.profile_manager.get_profile(user_id)
        personalization = self.profile_manager.get_personalization_context(user_id)

        # Get memory context
        memory_context = self.memory_manager.get_memory_context(user_id, session_id)

        # Get emotion summary
        emotion_summary = self.emotion_tracker.get_emotion_summary(user_id, hours=24)

        # Get emotion trends
        anxiety_trend = self.emotion_tracker.calculate_anxiety_trend(user_id, hours=24)
        risk_trend = self.emotion_tracker.calculate_risk_trend(user_id, hours=24)

        # Get session state
        session_state = self.risk_detector.get_session_state(session_id)
        risk_state = {
            "baseline_risk": session_state.baseline_risk if session_state else 0.0,
            "current_risk": session_state.current_risk if session_state else 0.0,
            "escalation_detected": session_state.escalation_detected if session_state else False,
            "message_count": session_state.message_count if session_state else 0,
        }

        # Check for escalation
        escalation_alert = self.risk_detector.detect_escalation(session_id)

        # Build complete context
        context = {
            "user_id": user_id,
            "session_id": session_id,
            "profile": profile.model_dump() if profile else {},
            "personalization": personalization,
            "session_memory": memory_context["session_memory"],
            "user_memories": memory_context["user_memories"],
            "clinical_memories": memory_context["clinical_memories"],
            "emotion_summary": emotion_summary,
            "emotion_trends": {
                "anxiety": {
                    "trend": anxiety_trend.trend_type,
                    "current": anxiety_trend.current_value,
                    "change": anxiety_trend.change_percentage,
                },
                "risk": {
                    "trend": risk_trend.trend_type,
                    "current": risk_trend.current_value,
                    "change": risk_trend.change_percentage,
                },
            },
            "risk_state": risk_state,
            "escalation_alert": escalation_alert.model_dump() if escalation_alert else None,
        }

        return context

    def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
    ) -> UserProfile:
        """
        Update user preferences (for profile editing).

        Args:
            user_id: Hashed user ID
            preferences: Preferences to update

        Returns:
            Updated UserProfile
        """
        return self.profile_manager.update_preferences(user_id, preferences)

    def add_user_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: str,
        source: Optional[str] = None,
    ):
        """
        Add persistent user memory.

        Args:
            user_id: Hashed user ID
            memory_type: MemoryType.USER or MemoryType.CLINICAL
            content: Memory content
            source: Source of memory
        """
        self.memory_manager.add_user_memory(user_id, memory_type, content, source)

    def get_personalization_prompt_context(
        self,
        user_id: str,
        session_id: str,
    ) -> str:
        """
        Get personalization context formatted for prompt injection.

        Args:
            user_id: Hashed user ID
            session_id: Session ID

        Returns:
            Formatted prompt string
        """
        context = self.get_context(user_id, session_id)

        parts = []

        # User profile
        if context["profile"]:
            profile = context["profile"]
            if profile.get("age_range"):
                parts.append(f"User age range: {profile['age_range']}")
            if profile.get("conditions"):
                parts.append(f"User conditions: {', '.join(profile['conditions'])}")

        # User preferences
        personalization = context["personalization"]
        if personalization.get("communication_style"):
            parts.append(f"Communication style: {personalization['communication_style']}")
        if personalization.get("detail_level"):
            parts.append(f"Detail level: {personalization['detail_level']}")

        # User memories
        if context["user_memories"]:
            parts.append("User preferences:")
            for mem in context["user_memories"][:3]:  # Top 3
                parts.append(f"  - {mem}")

        # Clinical memories
        if context["clinical_memories"]:
            parts.append("Clinical history:")
            for mem in context["clinical_memories"][:3]:  # Top 3
                parts.append(f"  - {mem}")

        # Emotion context
        emotion_summary = context["emotion_summary"]
        if emotion_summary.get("anxiety_trend") == "increasing":
            parts.append("Note: User anxiety is increasing - use higher empathy")
        if emotion_summary.get("anxiety_spike"):
            parts.append("Note: Anxiety spike detected - prioritize reassurance")

        # Risk escalation
        if context["escalation_alert"]:
            parts.append("⚠️ RISK ESCALATION DETECTED - Use safety protocols")

        return "\n".join(parts) if parts else ""

    def delete_user_data(self, user_id: str) -> Dict[str, int]:
        """
        Delete all user data (Privacy by Design - Right to Deletion).

        Args:
            user_id: Hashed user ID

        Returns:
            Dictionary with deletion counts
        """
        from src.context.storage import (
            ConversationMessageModel,
            EmotionRecordModel,
            SessionStateModel,
            UserMemoryModel,
        )

        counts = {}

        with self.storage.get_session() as session:
            # Delete profile
            counts["profile"] = self.profile_manager.delete_profile(user_id) and 1 or 0

            # Delete messages
            counts["messages"] = session.query(ConversationMessageModel).filter(
                ConversationMessageModel.user_id == user_id
            ).delete()

            # Delete emotion records
            counts["emotions"] = session.query(EmotionRecordModel).filter(
                EmotionRecordModel.user_id == user_id
            ).delete()

            # Delete session states
            counts["sessions"] = session.query(SessionStateModel).filter(
                SessionStateModel.user_id == user_id
            ).delete()

            # Delete memories
            counts["memories"] = session.query(UserMemoryModel).filter(
                UserMemoryModel.user_id == user_id
            ).delete()

            session.commit()

        logger.info(f"Deleted all data for user {user_id}: {counts}")
        return counts

