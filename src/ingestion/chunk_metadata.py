"""Chunk metadata management."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import uuid

from src.config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkMetadata:
    """Structured metadata for document chunks."""

    # Core identifiers
    chunk_id: str
    document_id: Optional[str] = None
    chunk_index: int = 0

    # Source information
    source_file_path: Optional[str] = None
    source_file_name: Optional[str] = None
    source_file_type: Optional[str] = None
    page_number: Optional[int] = None

    # Position information
    start_index: int = 0
    end_index: int = 0
    chunk_size: int = 0

    # Processing information
    parser_type: Optional[str] = None
    chunker_type: Optional[str] = None
    created_at: Optional[str] = None

    # Content information
    token_count: Optional[int] = None
    has_table: bool = False
    has_image: bool = False
    topic_label: Optional[str] = None

    # Medical-specific
    medical_table_type: Optional[str] = None
    contains_lab_results: bool = False
    contains_medications: bool = False

    # Additional metadata
    custom_metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.chunk_id is None:
            self.chunk_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.chunk_size == 0 and self.end_index > self.start_index:
            self.chunk_size = self.end_index - self.start_index

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert metadata to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkMetadata":
        """Create ChunkMetadata from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "ChunkMetadata":
        """Create ChunkMetadata from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def merge(self, other: "ChunkMetadata") -> "ChunkMetadata":
        """
        Merge with another metadata object.

        Args:
            other: Other metadata to merge

        Returns:
            New merged metadata
        """
        merged_dict = self.to_dict()
        other_dict = other.to_dict()

        # Merge custom metadata
        if self.custom_metadata and other.custom_metadata:
            merged_dict["custom_metadata"] = {
                **self.custom_metadata,
                **other.custom_metadata,
            }
        elif other.custom_metadata:
            merged_dict["custom_metadata"] = other.custom_metadata

        # Update with other's values (non-None values take precedence)
        for key, value in other_dict.items():
            if value is not None and key != "chunk_id":  # Preserve original chunk_id
                merged_dict[key] = value

        return ChunkMetadata.from_dict(merged_dict)

    def validate(self) -> bool:
        """
        Validate metadata completeness.

        Returns:
            True if metadata is valid
        """
        if not self.chunk_id:
            logger.warning("Chunk metadata missing chunk_id")
            return False

        if self.chunk_size <= 0:
            logger.warning(f"Chunk metadata has invalid chunk_size: {self.chunk_size}")
            return False

        return True


class ChunkMetadataManager:
    """Manager for chunk metadata operations."""

    def __init__(self):
        """Initialize metadata manager."""
        self._metadata_store: Dict[str, ChunkMetadata] = {}

    def create_metadata(
        self,
        chunk_text: str,
        chunk_index: int,
        base_metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ChunkMetadata:
        """
        Create chunk metadata from parameters.

        Args:
            chunk_text: Chunk text content
            chunk_index: Index of chunk
            base_metadata: Base metadata dictionary
            **kwargs: Additional metadata fields

        Returns:
            ChunkMetadata object
        """
        # Extract common fields from base_metadata
        metadata_dict = {
            "chunk_index": chunk_index,
            "chunk_size": len(chunk_text),
            "start_index": kwargs.get("start_index", 0),
            "end_index": kwargs.get("end_index", len(chunk_text)),
        }

        # Add base metadata
        if base_metadata:
            metadata_dict.update(base_metadata)

        # Override with kwargs
        metadata_dict.update(kwargs)

        # Ensure chunk_id is set
        if "chunk_id" not in metadata_dict:
            metadata_dict["chunk_id"] = str(uuid.uuid4())

        metadata = ChunkMetadata.from_dict(metadata_dict)

        # Store metadata
        self._metadata_store[metadata.chunk_id] = metadata

        return metadata

    def get_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """
        Get metadata by chunk ID.

        Args:
            chunk_id: Chunk identifier

        Returns:
            ChunkMetadata or None if not found
        """
        return self._metadata_store.get(chunk_id)

    def update_metadata(self, chunk_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update metadata for a chunk.

        Args:
            chunk_id: Chunk identifier
            updates: Dictionary of updates

        Returns:
            True if update successful
        """
        metadata = self._metadata_store.get(chunk_id)
        if not metadata:
            logger.warning(f"Metadata not found for chunk_id: {chunk_id}")
            return False

        # Update fields
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

        return True

    def get_all_metadata(self) -> List[ChunkMetadata]:
        """
        Get all stored metadata.

        Returns:
            List of all ChunkMetadata objects
        """
        return list(self._metadata_store.values())

    def get_metadata_by_document(self, document_id: str) -> List[ChunkMetadata]:
        """
        Get all metadata for a specific document.

        Args:
            document_id: Document identifier

        Returns:
            List of ChunkMetadata for the document
        """
        return [
            metadata
            for metadata in self._metadata_store.values()
            if metadata.document_id == document_id
        ]

    def clear(self) -> None:
        """Clear all stored metadata."""
        self._metadata_store.clear()
        logger.debug("Cleared all metadata")

    def export_to_json(self, file_path: str) -> None:
        """
        Export all metadata to JSON file.

        Args:
            file_path: Path to output JSON file
        """
        data = [metadata.to_dict() for metadata in self._metadata_store.values()]
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Exported {len(data)} metadata records to {file_path}")

    def import_from_json(self, file_path: str) -> None:
        """
        Import metadata from JSON file.

        Args:
            file_path: Path to input JSON file
        """
        with open(file_path, "r") as f:
            data = json.load(f)

        for item in data:
            metadata = ChunkMetadata.from_dict(item)
            self._metadata_store[metadata.chunk_id] = metadata

        logger.info(f"Imported {len(data)} metadata records from {file_path}")

