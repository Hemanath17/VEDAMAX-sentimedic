"""Post-generation validation: citations, patient numbers, disclaimers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.retrieval.pipeline import Corpus, RetrievalResult, RetrievalStatus, RetrievedChunk

_CITATION_PATTERN = re.compile(r"\[S(\d+)\]")
_NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(\d+(?:\.\d+)?(?:\s*(?:%|mg/dL|mmol/L|g/dL|mEq/L|mmHg|bpm|kg|lb|lbs|cm|mm|mL|L|IU|U))?"
    r")"
    r"(?![A-Za-z0-9])",
    re.IGNORECASE,
)


@dataclass
class Citation:
    """A validated source reference tied to a citation marker."""

    marker: str
    source_ref: str
    corpus: Corpus


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


def verify_numbers(answer: str, retrieval_result: RetrievalResult) -> List[str]:
    """
    Flag numeric values in the answer that do not appear in patient document chunks.

    Only numbers found in USER_DOC chunk text are considered allowed. General
    knowledge numbers are not treated as patient-specific values.

    Args:
        answer: Generated answer text to inspect.
        retrieval_result: Retrieval output containing evidence chunks.

    Returns:
        List of numeric strings from the answer that are not grounded in patient docs.
    """
    if not answer:
        return []

    user_text = " ".join(
        chunk.text for chunk in retrieval_result.chunks if chunk.corpus == Corpus.USER_DOC
    )
    if not user_text.strip():
        return []

    flagged: List[str] = []
    for match in _NUMBER_PATTERN.finditer(answer):
        raw = match.group(1).strip()
        numeric_match = re.match(r"(\d+(?:\.\d+)?)", raw)
        if not numeric_match:
            continue
        number = numeric_match.group(1)
        if number not in user_text and number not in flagged:
            flagged.append(number)
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
