"""
Parser for MedlinePlus bulk Health Topic XML files.

Streams the file (does not load it fully into memory), filters topics to a
relevant allowlist, strips embedded HTML markup from the summary text,
chunks long topics using the existing chunker factory, and returns
chunk-dicts in the same shape seed_kb.py already uses for store_chunks.

Source format reference: https://medlineplus.gov/xmldescription.html
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set

from src.ingestion.chunkers.chunker_factory import get_chunker
from src.config.logging_config import get_logger

logger = get_logger(__name__)

_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Topics longer than this (characters) get split via the chunker; shorter
# topics are stored as a single chunk.
SINGLE_CHUNK_MAX_CHARS = 800


def load_topic_allowlist(path: Path) -> Set[str]:
    """Load relevant topic keywords from a plain-text file, one per line."""
    if not path.exists():
        raise FileNotFoundError(f"Topic allowlist not found: {path}")

    with path.open(encoding="utf-8") as handle:
        return {line.strip().lower() for line in handle if line.strip()}


def _is_relevant(title: str, allowlist: Set[str]) -> bool:
    """Return True if any allowlist keyword appears in the topic title."""
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in allowlist)


def _strip_markup(raw_html: str) -> str:
    """Remove embedded <p>, <ul>, <li>, <a> tags and collapse whitespace."""
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = _TAG_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def iter_relevant_topics(
    xml_path: Path,
    allowlist: Set[str],
) -> Iterator[Dict[str, str]]:
    """
    Stream-parse the MedlinePlus XML file, yielding only topics whose title
    matches the allowlist. Does not load the full file into memory at once.
    """
    context = ET.iterparse(str(xml_path), events=("end",))

    for _, elem in context:
        if elem.tag != "health-topic":
            continue

        title = elem.get("title", "")
        if not title or not _is_relevant(title, allowlist):
            elem.clear()
            continue

        full_summary_elem = elem.find("full-summary")
        raw_summary = (
            "".join(full_summary_elem.itertext())
            if full_summary_elem is not None
            else ""
        )

        yield {
            "id": elem.get("id", ""),
            "title": title,
            "url": elem.get("url", ""),
            "meta_desc": elem.get("meta-desc", ""),
            "summary_text": _strip_markup(raw_summary),
        }

        elem.clear()


def topic_to_chunks(topic: Dict[str, str]) -> List[Dict]:
    """
    Convert one parsed MedlinePlus topic into chunk-dicts matching the shape
    VectorStore.store_chunks expects (same shape as seed_kb.py produces).
    """
    text = topic["summary_text"] or topic["meta_desc"]
    if not text:
        logger.warning(f"Skipping topic with no content: {topic['title']}")
        return []

    base_metadata = {
        "document_id": f"medlineplus-{topic['id']}",
        "source": "MedlinePlus",
        "url": topic["url"],
        "title": topic["title"],
        "chunk_type": "text",
    }

    if len(text) <= SINGLE_CHUNK_MAX_CHARS:
        return [
            {
                "text": text,
                "chunk_id": f"medlineplus_{topic['id']}_0",
                "metadata": base_metadata,
            }
        ]

    # Token chunker splits purely by length and cannot reject a chunk as
    # "too large" the way semantic chunking can on text with poor sentence
    # boundaries -- this guarantees every long topic actually gets chunked
    # instead of silently dropped.
    chunker = get_chunker("token", use_cached=True)
    raw_chunks = chunker.chunk(text, metadata=base_metadata)

    if not raw_chunks:
        logger.error(f"Token chunker produced zero chunks for topic: {topic['title']}")
        return []

    chunks: List[Dict] = []
    for i, raw_chunk in enumerate(raw_chunks):
        chunk_text = raw_chunk.pop("text")
        chunks.append(
            {
                "text": chunk_text,
                "chunk_id": f"medlineplus_{topic['id']}_{i}",
                "metadata": {**base_metadata, **raw_chunk},
            }
        )

    return chunks


def parse_medlineplus_file(
    xml_path: Path,
    allowlist_path: Path,
) -> Iterator[List[Dict]]:
    """
    Top-level entry point: parse the XML file, filter by allowlist, and
    yield one list of chunk-dicts per relevant topic (caller batches these
    for storage).
    """
    allowlist = load_topic_allowlist(allowlist_path)
    logger.info(f"Loaded {len(allowlist)} allowlist keywords")

    topic_count = 0
    for topic in iter_relevant_topics(xml_path, allowlist):
        topic_count += 1
        chunks = topic_to_chunks(topic)
        if chunks:
            yield chunks

    logger.info(f"Parsed {topic_count} relevant topics from {xml_path}")
