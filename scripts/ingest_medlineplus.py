#!/usr/bin/env python3
"""
Download-and-run script: parses a local MedlinePlus Health Topic XML file,
filters to relevant topics, and stores the resulting chunks into the kb
corpus in batches.

Before running:
1. Download the MedlinePlus Health Topic XML file (compressed or full) from
   https://medlineplus.gov/xml.html and unzip it if needed.
2. Place it somewhere on disk and pass its path via --xml-path.
3. Ensure data/medlineplus_topics.txt exists with your allowlist keywords.

Usage:
    python scripts/ingest_medlineplus.py
    python scripts/ingest_medlineplus.py --xml-path data/mplus_topics_2026-06-27.xml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.logging_config import setup_logging, get_logger
from src.ingestion.parsers.medlineplus_parser import parse_medlineplus_file
from src.retrieval.vector_store.vector_store import VectorStore

setup_logging()
logger = get_logger(__name__)

DEFAULT_ALLOWLIST_PATH = ROOT / "data" / "medlineplus_topics.txt"
DEFAULT_XML_PATH = ROOT / "data" / "mplus_topics_2026-06-27.xml"
BATCH_SIZE = 50


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest MedlinePlus XML into the KB corpus.")
    parser.add_argument(
        "--xml-path",
        type=Path,
        default=DEFAULT_XML_PATH,
        help=f"Path to the MedlinePlus XML file (default: {DEFAULT_XML_PATH.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--allowlist-path",
        type=Path,
        default=DEFAULT_ALLOWLIST_PATH,
        help="Path to the topic keyword allowlist (default: data/medlineplus_topics.txt)",
    )
    args = parser.parse_args()

    if not args.xml_path.exists():
        raise FileNotFoundError(f"XML file not found: {args.xml_path}")

    store = VectorStore()
    batch: list[dict] = []
    total_chunks = 0
    total_topics = 0

    for topic_chunks in parse_medlineplus_file(args.xml_path, args.allowlist_path):
        total_topics += 1
        batch.extend(topic_chunks)

        if len(batch) >= BATCH_SIZE:
            store.store_chunks(batch, corpus="kb")
            total_chunks += len(batch)
            logger.info(f"Stored batch: {len(batch)} chunks ({total_chunks} total so far)")
            batch = []

    if batch:
        store.store_chunks(batch, corpus="kb")
        total_chunks += len(batch)

    print(f"Done. Ingested {total_topics} topics -> {total_chunks} chunks into the kb corpus.")


if __name__ == "__main__":
    main()
