#!/usr/bin/env python3
"""Seed the medical knowledge base from data/kb_seed.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.logging_config import get_logger, setup_logging
from src.retrieval.vector_store.vector_store import VectorStore

setup_logging()
logger = get_logger(__name__)

SEED_PATH = ROOT / "data" / "kb_seed.json"


def slug(title: str) -> str:
    """Convert a title into a stable document/chunk slug."""
    normalized = title.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def load_seed_entries() -> list[dict]:
    """Load KB seed entries from JSON."""
    with SEED_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {SEED_PATH}")
    return data


def entries_to_chunks(entries: list[dict]) -> list[dict]:
    """Convert seed entries into chunk dicts for VectorStore.store_chunks."""
    chunks: list[dict] = []
    for entry in entries:
        title = entry["title"]
        doc_slug = slug(title)
        chunks.append(
            {
                "text": entry["text"],
                "chunk_id": f"kb_{doc_slug}",
                "metadata": {
                    "document_id": doc_slug,
                    "source": entry["source"],
                    "chunk_type": "text",
                    "title": title,
                },
            }
        )
    return chunks


def main() -> None:
    """Load seed data and store chunks in the KB corpus."""
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_PATH}")

    entries = load_seed_entries()
    chunks = entries_to_chunks(entries)

    logger.info("Seeding %s KB chunks from %s", len(chunks), SEED_PATH)
    store = VectorStore()
    point_ids = store.store_chunks(chunks, corpus="kb")
    print(f"Stored {len(point_ids)} KB chunks in Qdrant.")


if __name__ == "__main__":
    main()
