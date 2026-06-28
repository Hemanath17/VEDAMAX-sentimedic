"""Post-generation validation: citations, patient numbers, disclaimers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.retrieval.pipeline import Corpus, RetrievalResult, RetrievalStatus, RetrievedChunk

_CITATION_PATTERN = re.compile(r"\[S(\d+)\]")
_BARE_NUMBER_PATTERN = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)(?![\d.])")

_MIN_FLAGGABLE_DIGITS = 2

@dataclass
class Citation:
    """A validated source reference tied to a citation marker."""

    marker: str
    source_ref: str
    corpus: Corpus

def _is_flaggable_number(number: str) -> bool:
    """Return True if a numeric token is substantial enough to verify."""
    if "." in number:
        return True
    return len(number) >= _MIN_FLAGGABLE_DIGITS

def validate_citations(
    answer: str,
    marker_to_chunk: Dict[str, RetrievedChunk],
) -> Tuple[str, List[Citation]]:
    """
    Keep only citation markers that map to supplied chunks; drop invented ones.

    Scans the answer for [S#] markers. Markers absent from ``marker_to_chunk``
    are removed from the answer text. Valid markers produce ``Citation`` entries.

    Args:
        answer: Raw LLM answer text.
        marker_to_chunk: Mapping from markers like ``[S1]`` to evidence chunks.

    Returns:
        Tuple of (cleaned answer, list of validated citations in order of appearance).
    """
    if not answer:
        return answer, []

    seen: set[str] = set()
    citations: List[Citation] = []

    def _replace(match: re.Match[str]) -> str:
        marker = f"[S{match.group(1)}]"
        chunk = marker_to_chunk.get(marker)
        if chunk is None:
            return ""
        if marker not in seen:
            seen.add(marker)
            citations.append(
                Citation(
                    marker=marker,
                    source_ref=chunk.source_ref,
                    corpus=chunk.corpus,
                )
            )
        return marker

    cleaned = _CITATION_PATTERN.sub(_replace, answer)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned, citations


def _extract_number_tokens(text: str) -> set[str]:
    """Extract bare numeric tokens from text using boundary-safe matching."""
    if not text:
        return set()
    return set(_BARE_NUMBER_PATTERN.findall(text))


def verify_numbers(answer: str, retrieval_result: RetrievalResult) -> List[str]:
    """
    Flag numeric values in the answer that appear in neither evidence corpus.

    Numbers are tokenized with boundary-safe matching so substrings like ``25``
    do not match inside ``250``. A number is allowed if it appears as a full
    token in USER_DOC chunks, KB chunks, or both.

    Args:
        answer: Generated answer text to inspect.
        retrieval_result: Retrieval output containing evidence chunks.

    Returns:
        List of numeric strings from the answer that are not grounded in any chunk.
    """
    if not answer:
        return []

    user_text = " ".join(
        chunk.text for chunk in retrieval_result.chunks if chunk.corpus == Corpus.USER_DOC
    )
    kb_text = " ".join(
        chunk.text for chunk in retrieval_result.chunks if chunk.corpus == Corpus.KB
    )
    allowed = _extract_number_tokens(user_text) | _extract_number_tokens(kb_text)

    

    flagged: List[str] = []
    seen: set[str] = set()
    for match in _BARE_NUMBER_PATTERN.finditer(answer):
        number = match.group(1)
        if not _is_flaggable_number(number):
            continue
        if number not in allowed and number not in seen:
            flagged.append(number)
            seen.add(number)

    
    return flagged

    


def build_disclaimer(status: RetrievalStatus | str) -> str:
    """
    Return a context-aware disclaimer for the generated answer.

    Args:
        status: Retrieval or generation status string.

    Returns:
        Disclaimer text appropriate for the outcome.
    """
    normalized = str(status).lower()

    if normalized == RetrievalStatus.OK.value:
        return (
            "This information is for educational purposes only and is not medical advice. "
            "Always consult a qualified healthcare professional about your results and concerns."
        )
    if normalized == RetrievalStatus.NO_USER_DOCS.value:
        return (
            "No personal lab report or uploaded document was found for your account. "
            "This response cannot include your specific results. "
            "Please upload your report or consult your clinician."
        )
    if normalized == RetrievalStatus.BELOW_THRESHOLD.value:
        return (
            "Available evidence was not strong enough to answer this question safely. "
            "Please rephrase your question or speak with a healthcare professional."
        )
    if normalized == RetrievalStatus.EMPTY.value:
        return (
            "No matching medical evidence was found for this question. "
            "Please try a different question or consult a healthcare professional."
        )
    if normalized == "llm_error":
        return (
            "A response could not be generated at this time. "
            "Please try again later or contact support if the issue persists."
        )
    return (
        "This information is for educational purposes only and is not medical advice. "
        "Consult a qualified healthcare professional for personal guidance."
    )
