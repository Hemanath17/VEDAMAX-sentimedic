"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from typing import Generator
import tempfile
import shutil

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_text() -> str:
    """Sample text for testing."""
    return """
    This is a sample medical document. It contains information about
    patient symptoms, medications, and lab results. The patient presents
    with fever and headache. Prescribed medication: Ibuprofen 200mg.
    Lab results show elevated white blood cell count.
    """


@pytest.fixture
def sample_metadata() -> dict:
    """Sample metadata for testing."""
    return {
        "file_name": "test_document.pdf",
        "file_path": "/path/to/test_document.pdf",
        "file_type": ".pdf",
        "file_size": 1024,
    }


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("QDRANT_HOST", "localhost")
    monkeypatch.setenv("QDRANT_PORT", "6333")
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    monkeypatch.setenv("LLM_MODEL", "gpt-4-turbo-preview")
    monkeypatch.setenv("DEBUG", "true")

