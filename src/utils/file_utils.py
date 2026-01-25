"""File utility functions."""

from pathlib import Path
from typing import List, Optional
import mimetypes


def get_file_extension(file_path: Path) -> str:
    """
    Get file extension in lowercase.

    Args:
        file_path: Path to file

    Returns:
        File extension (e.g., '.pdf')
    """
    return file_path.suffix.lower()


def is_supported_file(file_path: Path, supported_extensions: Optional[List[str]] = None) -> bool:
    """
    Check if file is supported.

    Args:
        file_path: Path to file
        supported_extensions: List of supported extensions (default: common document types)

    Returns:
        True if file is supported
    """
    if supported_extensions is None:
        supported_extensions = [".pdf", ".docx", ".doc", ".txt"]

    return get_file_extension(file_path) in supported_extensions


def get_mime_type(file_path: Path) -> Optional[str]:
    """
    Get MIME type of file.

    Args:
        file_path: Path to file

    Returns:
        MIME type string or None
    """
    return mimetypes.guess_type(str(file_path))[0]


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path

