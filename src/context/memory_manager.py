"""Memory management for conversation history and user traits."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from src.context.storage import get_storage_manager, ConversationMessageModel, UserMemoryModel
from src.context.models import ConversationMessage, UserMemory, MemoryType
from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """
    Manages three types of memory:
    
    1. Session Memory: Last 10 user messages (short-term context)
    2. User Memory: Persistent traits (e.g., "prefers simple explanations")
    3. Clinical Memory: Health-related history (e.g., "asked about cholesterol twice")
    
    Personalization: Uses past conversations to tailor responses.
    """

    def __init__(self):
        """Initialize memory manager."""
        self.storage = get_storage_manager()
        self.session_size = settings.MEMORY_SESSION_SIZE
        logger.info(f"Initialized MemoryManager (session_size={self.session_size})")

    def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        """
        Add message to conversation history.

        Args:
            user_id: User ID
            session_id: Session ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Additional metadata (emotion, entities, etc.)

        Returns:
            ConversationMessage object
        """
        message_id = self.storage.generate_id()
        message = ConversationMessage(
            message_id=message_id,
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        with self.storage.get_session() as session:
            message_model = ConversationMessageModel(
                message_id=message.message_id,
                user_id=message.user_id,
                session_id=message.session_id,
                role=message.role,
                content=message.content,
                timestamp=message.timestamp,
                message_metadata=message.metadata,  # Use message_metadata column
            )
            session.add(message_model)

        logger.debug(f"Added {role} message to session {session_id}")
        return message

    def get_session_memory(
        self,
        user_id: str,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[ConversationMessage]:
        """
        Get session memory (last N user messages).

        Args:
            user_id: User ID
            session_id: Session ID
            limit: Number of messages (defaults to settings.MEMORY_SESSION_SIZE)

        Returns:
            List of ConversationMessage objects
        """
        limit = limit or self.session_size

        with self.storage.get_session() as session:
            messages = session.query(ConversationMessageModel).filter(
                ConversationMessageModel.user_id == user_id,
                ConversationMessageModel.session_id == session_id,
                ConversationMessageModel.role == "user",  # Only user messages
            ).order_by(
                ConversationMessageModel.timestamp.desc()
            ).limit(limit).all()

            # Convert to Pydantic models (reverse to get chronological order)
            result = []
            for msg in reversed(messages):
                result.append(ConversationMessage(
                    message_id=msg.message_id,
                    user_id=msg.user_id,
                    session_id=msg.session_id,
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.message_metadata or {},
                ))

            return result

    def get_conversation_history(
        self,
        user_id: str,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[ConversationMessage]:
        """
        Get full conversation history (user + assistant messages).

        Args:
            user_id: User ID
            session_id: Session ID
            limit: Number of message pairs (defaults to settings.MEMORY_SESSION_SIZE)

        Returns:
            List of ConversationMessage objects (chronological)
        """
        limit = limit or self.session_size

        with self.storage.get_session() as session:
            messages = session.query(ConversationMessageModel).filter(
                ConversationMessageModel.user_id == user_id,
                ConversationMessageModel.session_id == session_id,
            ).order_by(
                ConversationMessageModel.timestamp.asc()
            ).limit(limit * 2).all()  # *2 for user+assistant pairs

            return [
                ConversationMessage(
                    message_id=msg.message_id,
                    user_id=msg.user_id,
                    session_id=msg.session_id,
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.message_metadata or {},  # Use message_metadata column
                )
                for msg in messages
            ]

    def add_user_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: str,
        source: Optional[str] = None,
    ) -> UserMemory:
        """
        Add persistent user memory (user or clinical type).

        Args:
            user_id: User ID
            memory_type: MemoryType.USER or MemoryType.CLINICAL
            content: Memory content
            source: Source of memory (e.g., "conversation", "profile")

        Returns:
            UserMemory object
        """
        memory_id = self.storage.generate_id()
        memory = UserMemory(
            memory_id=memory_id,
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            source=source,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=0,
        )

        with self.storage.get_session() as session:
            memory_model = UserMemoryModel(
                memory_id=memory.memory_id,
                user_id=memory.user_id,
                memory_type=memory.memory_type.value,
                content=memory.content,
                source=memory.source,
                created_at=memory.created_at,
                last_accessed=memory.last_accessed,
                access_count=memory.access_count,
            )
            session.add(memory_model)

        logger.info(f"Added {memory_type.value} memory for user {user_id}: {content[:50]}...")
        return memory

    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
    ) -> List[UserMemory]:
        """
        Get user memories (persistent traits).

        Args:
            user_id: User ID
            memory_type: Filter by type (None for all)

        Returns:
            List of UserMemory objects
        """
        with self.storage.get_session() as session:
            query = session.query(UserMemoryModel).filter(
                UserMemoryModel.user_id == user_id
            )

            if memory_type:
                query = query.filter(UserMemoryModel.memory_type == memory_type.value)

            memories = query.order_by(
                UserMemoryModel.last_accessed.desc()
            ).all()

            # Update access count and timestamp
            for mem in memories:
                mem.access_count += 1
                mem.last_accessed = datetime.now()

            session.commit()

            return [
                UserMemory(
                    memory_id=mem.memory_id,
                    user_id=mem.user_id,
                    memory_type=MemoryType(mem.memory_type),
                    content=mem.content,
                    source=mem.source,
                    created_at=mem.created_at,
                    last_accessed=mem.last_accessed,
                    access_count=mem.access_count,
                )
                for mem in memories
            ]

    def extract_clinical_memory(
        self,
        user_id: str,
        entities: List[Dict[str, Any]],
        query: str,
    ) -> None:
        """
        Extract and store clinical memory from entities.

        Args:
            user_id: User ID
            entities: Extracted medical entities
            query: User query
        """
        # Track entity mentions
        entity_counts = defaultdict(int)
        for entity in entities:
            entity_type = entity.get("entity_type", "unknown")
            entity_text = entity.get("text", "")
            key = f"{entity_type}:{entity_text.lower()}"
            entity_counts[key] += 1

        # Store clinical memories for frequently mentioned entities
        for key, count in entity_counts.items():
            if count >= 2:  # Mentioned at least twice
                memory_content = f"User has asked about {key} {count} times"
                self.add_user_memory(
                    user_id=user_id,
                    memory_type=MemoryType.CLINICAL,
                    content=memory_content,
                    source="entity_extraction",
                )

    def get_memory_context(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Get complete memory context for personalization.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            Memory context dictionary
        """
        # Session memory (last 10 user messages)
        session_memory = self.get_session_memory(user_id, session_id)

        # User memory (persistent traits)
        user_memories = self.get_user_memories(user_id, MemoryType.USER)

        # Clinical memory (health history)
        clinical_memories = self.get_user_memories(user_id, MemoryType.CLINICAL)

        return {
            "session_memory": [msg.content for msg in session_memory],
            "user_memories": [mem.content for mem in user_memories],
            "clinical_memories": [mem.content for mem in clinical_memories],
            "session_message_count": len(session_memory),
        }

    def cleanup_old_memories(self, retention_days: int = None):
        """
        Clean up old conversation messages based on retention policy.

        Args:
            retention_days: Retention days (defaults to settings)
        """
        retention_days = retention_days or settings.MEMORY_RETENTION_DAYS
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        with self.storage.get_session() as session:
            deleted = session.query(ConversationMessageModel).filter(
                ConversationMessageModel.timestamp < cutoff_date
            ).delete()

            logger.info(f"Cleaned up {deleted} old conversation messages")
            return deleted

