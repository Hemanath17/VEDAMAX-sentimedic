"""Text processing utility functions."""

import re
from typing import List


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing.

    Args:
        text: Input text

    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    # Simple sentence splitting (can be improved with NLTK/spaCy)
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip()]


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix

