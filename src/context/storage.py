"""PostgreSQL storage layer for user context and memory."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import contextmanager
import hashlib
import uuid

from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)

Base = declarative_base()


# SQLAlchemy Models
class UserProfileModel(Base):
    """User profile database model."""
    __tablename__ = "user_profiles"

    user_id = Column(String(64), primary_key=True, index=True)
    age_range = Column(String(10), nullable=True)
    conditions = Column(JSON, default=list)
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ConversationMessageModel(Base):
    """Conversation message database model."""
    __tablename__ = "conversation_messages"

    message_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), index=True)
    session_id = Column(String(64), index=True)
    role = Column(String(20))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    message_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' (reserved in SQLAlchemy)

    __table_args__ = (
        Index('idx_user_session_timestamp', 'user_id', 'session_id', 'timestamp'),
    )


class EmotionRecordModel(Base):
    """Emotion record database model."""
    __tablename__ = "emotion_records"

    record_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), index=True)
    session_id = Column(String(64), index=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    emotion_bucket = Column(String(50))
    anxiety_level = Column(Float)
    risk_level = Column(Float)
    sentiment_score = Column(Float)

    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )


class SessionStateModel(Base):
    """Session state database model."""
    __tablename__ = "session_states"

    session_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), index=True)
    started_at = Column(DateTime, default=datetime.now)
    baseline_risk = Column(Float, default=0.0)
    current_risk = Column(Float, default=0.0)
    message_count = Column(Integer, default=0)
    escalation_detected = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class UserMemoryModel(Base):
    """User memory database model."""
    __tablename__ = "user_memories"

    memory_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), index=True)
    memory_type = Column(String(20), index=True)  # session, user, clinical
    content = Column(Text)
    source = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_accessed = Column(DateTime, default=datetime.now)
    access_count = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_user_type', 'user_id', 'memory_type'),
    )


class StorageManager:
    """Manages PostgreSQL database connections and operations."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize storage manager.

        Args:
            database_url: PostgreSQL connection URL (defaults to settings)
        """
        self.database_url = database_url or settings.DATABASE_URL

        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL logging
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

        logger.info(f"Initialized StorageManager with database: {self.database_url}")

    @contextmanager
    def get_session(self):
        """
        Get database session context manager.

        Usage:
            with storage_manager.get_session() as session:
                # Use session
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}", exc_info=True)
            raise

    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}", exc_info=True)
            raise

    def hash_user_id(self, raw_id: str) -> str:
        """
        Hash user ID for anonymization.

        Args:
            raw_id: Raw user identifier

        Returns:
            Hashed user ID
        """
        salt = settings.USER_ID_HASH_SALT.encode()
        raw_bytes = raw_id.encode()
        hash_obj = hashlib.sha256(salt + raw_bytes)
        return hash_obj.hexdigest()

    def generate_id(self) -> str:
        """Generate a unique ID."""
        return str(uuid.uuid4())

    def cleanup_old_data(self, retention_days: int = 30):
        """
        Clean up old data based on retention policy.

        Args:
            retention_days: Number of days to retain data
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        with self.get_session() as session:
            # Delete old conversation messages
            deleted_messages = session.query(ConversationMessageModel).filter(
                ConversationMessageModel.timestamp < cutoff_date
            ).delete()

            # Delete old emotion records
            deleted_emotions = session.query(EmotionRecordModel).filter(
                EmotionRecordModel.timestamp < cutoff_date
            ).delete()

            # Delete old session states (keep only active sessions)
            deleted_sessions = session.query(SessionStateModel).filter(
                SessionStateModel.last_updated < cutoff_date
            ).delete()

            logger.info(
                f"Cleaned up old data: {deleted_messages} messages, "
                f"{deleted_emotions} emotions, {deleted_sessions} sessions"
            )


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager

