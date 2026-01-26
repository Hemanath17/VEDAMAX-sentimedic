"""Utility functions for context management."""

import hashlib
from typing import Optional
from datetime import datetime, timedelta

from src.config.settings import settings


def hash_user_id(raw_id: str) -> str:
    """
    Hash user ID for anonymization (Privacy by Design).

    Args:
        raw_id: Raw user identifier

    Returns:
        Hashed user ID
    """
    salt = settings.USER_ID_HASH_SALT.encode()
    raw_bytes = raw_id.encode()
    hash_obj = hashlib.sha256(salt + raw_bytes)
    return hash_obj.hexdigest()


def validate_age_range(age_range: Optional[str]) -> bool:
    """
    Validate age range format.

    Args:
        age_range: Age range string

    Returns:
        True if valid
    """
    if not age_range:
        return True  # Optional field

    valid_ranges = ["18-25", "26-35", "36-50", "51-65", "65+"]
    return age_range in valid_ranges


def should_retain_data(created_at: datetime, retention_days: int = 30) -> bool:
    """
    Check if data should be retained based on retention policy.

    Args:
        created_at: Creation timestamp
        retention_days: Retention period in days

    Returns:
        True if should retain
    """
    cutoff = datetime.now() - timedelta(days=retention_days)
    return created_at >= cutoff


def anonymize_condition(condition: str) -> str:
    """
    Anonymize medical condition (basic normalization).

    Args:
        condition: Medical condition

    Returns:
        Anonymized condition
    """
    # Normalize to lowercase
    return condition.lower().strip()


def format_memory_for_prompt(memory: str, max_length: int = 100) -> str:
    """
    Format memory for prompt injection.

    Args:
        memory: Memory content
        max_length: Maximum length

    Returns:
        Formatted memory string
    """
    if len(memory) <= max_length:
        return memory
    return memory[:max_length - 3] + "..."

