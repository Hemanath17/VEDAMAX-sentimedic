"""Pydantic models for user context and memory."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class MemoryType(str, Enum):
    """Types of memory."""
    SESSION = "session"  # Short-term: last 10 messages
    USER = "user"  # Persistent: user preferences/traits
    CLINICAL = "clinical"  # Health-related history


class UserProfile(BaseModel):
    """User profile model (anonymized)."""
    user_id: str = Field(..., description="Anonymized hash-based user ID")
    age_range: Optional[str] = Field(None, description="Age range: 18-25, 26-35, 36-50, 51-65, 65+")
    conditions: List[str] = Field(default_factory=list, description="Medical conditions (anonymized)")
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences: communication_style, detail_level, language"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "a1b2c3d4e5f6...",
                "age_range": "26-35",
                "conditions": ["diabetes", "hypertension"],
                "preferences": {
                    "communication_style": "casual",
                    "detail_level": "simple",
                    "language": "en"
                }
            }
        }
    )


class ConversationMessage(BaseModel):
    """Conversation message model."""
    message_id: str = Field(..., description="Unique message ID")
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata: emotion, entities, etc."
    )


class EmotionRecord(BaseModel):
    """Emotion tracking record."""
    record_id: str = Field(..., description="Unique record ID")
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    emotion_bucket: str = Field(..., description="VEDAMAX emotion bucket")
    anxiety_level: float = Field(..., ge=0.0, le=1.0, description="Anxiety level 0-1")
    risk_level: float = Field(..., ge=0.0, le=1.0, description="Risk level 0-1")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score -1 to 1")


class SessionState(BaseModel):
    """Session state model."""
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    started_at: datetime = Field(default_factory=datetime.now)
    baseline_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    current_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    message_count: int = Field(default=0)
    escalation_detected: bool = Field(default=False)
    last_updated: datetime = Field(default_factory=datetime.now)


class UserMemory(BaseModel):
    """User memory entry (persistent traits)."""
    memory_id: str = Field(..., description="Unique memory ID")
    user_id: str = Field(..., description="User ID")
    memory_type: MemoryType = Field(..., description="Type of memory")
    content: str = Field(..., description="Memory content")
    source: Optional[str] = Field(None, description="Source of memory (e.g., conversation)")
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    access_count: int = Field(default=0, description="How many times accessed")


class EmotionTrend(BaseModel):
    """Emotion trend analysis result."""
    user_id: str
    trend_type: str = Field(..., description="'increasing', 'decreasing', 'stable'")
    current_value: float
    previous_value: float
    change_percentage: float
    time_period: str = Field(..., description="Time period analyzed")
    samples_count: int


class RiskEscalationAlert(BaseModel):
    """Risk escalation alert."""
    alert_id: str
    session_id: str
    user_id: str
    escalation_type: str = Field(..., description="'threshold', 'sustained', 'spike'")
    baseline_risk: float
    current_risk: float
    increase_percentage: float
    detected_at: datetime = Field(default_factory=datetime.now)
    triggered: bool = Field(default=False, description="Whether safety protocol was triggered")

