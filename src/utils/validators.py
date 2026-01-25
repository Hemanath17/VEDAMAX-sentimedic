"""Data validation utilities."""

from typing import Any, Dict, List
from pathlib import Path


def validate_file_path(file_path: Path) -> bool:
    """
    Validate that file path exists and is a file.

    Args:
        file_path: Path to validate

    Returns:
        True if valid
    """
    return file_path.exists() and file_path.is_file()


def validate_query(query: str, max_length: int = 5000) -> bool:
    """
    Validate user query.

    Args:
        query: Query string
        max_length: Maximum allowed length

    Returns:
        True if valid
    """
    if not query or not isinstance(query, str):
        return False
    if len(query.strip()) == 0:
        return False
    if len(query) > max_length:
        return False
    return True


def validate_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Validate metadata dictionary.

    Args:
        metadata: Metadata dictionary

    Returns:
        True if valid
    """
    if not isinstance(metadata, dict):
        return False
    # Add specific validation rules as needed
    return True

