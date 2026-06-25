"""User prompt assembly from retrieval evidence and conversation context."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from src.retrieval.pipeline import Corpus, RetrievalResult, RetrievedChunk

_MARKER_PREFIX = "[S"


def _format_chunk_block(
    chunks: list[RetrievedChunk],
    start_index: int,
    marker_to_chunk: Dict[str, RetrievedChunk],
) -> Tuple[str, int]:
    """Format chunks with sequential [S#] markers and record the mapping."""
    lines: list[str] = []
    index = start_index
    for chunk in chunks:
        marker = f"S{index}"
        marker_key = f"{_MARKER_PREFIX}{index}]"
        marker_to_chunk[marker_key] = chunk
        corpus_label = chunk.corpus.value
        lines.append(f"{marker_key} ({corpus_label}) {chunk.text}")
        index += 1
    return "\n".join(lines), index


def build_user_prompt(
    question: str,
    retrieval_result: RetrievalResult,
    session_summary: Optional[str] = None,
) -> Tuple[str, Dict[str, RetrievedChunk]]:
    """
    Build the user prompt with labeled evidence blocks and citation markers.

    KB chunks appear under [GENERAL KNOWLEDGE]; user document chunks under
    [PATIENT DOCUMENTS]. Each chunk is prefixed with [S1], [S2], etc.

    Args:
        question: The user's health question.
        retrieval_result: Retrieval output containing evidence chunks.
        session_summary: Optional condensed conversation history.

    Returns:
        Tuple of (prompt string, mapping from marker like "[S1]" to RetrievedChunk).
    """
    marker_to_chunk: Dict[str, RetrievedChunk] = {}
    kb_chunks = [c for c in retrieval_result.chunks if c.corpus == Corpus.KB]
    user_chunks = [c for c in retrieval_result.chunks if c.corpus == Corpus.USER_DOC]

    next_index = 1
    kb_block, next_index = _format_chunk_block(kb_chunks, next_index, marker_to_chunk)
    user_block, _ = _format_chunk_block(user_chunks, next_index, marker_to_chunk)

    summary = (session_summary or "").strip() or "No prior conversation."

    parts = [
        "[GENERAL KNOWLEDGE]",
        kb_block or "(No general knowledge evidence provided.)",
        "",
        "[PATIENT DOCUMENTS]",
        user_block or "(No patient document evidence provided.)",
        "",
        f"CONVERSATION SO FAR: {summary}",
        "",
        f"QUESTION: {question.strip()}",
    ]
    return "\n".join(parts), marker_to_chunk
