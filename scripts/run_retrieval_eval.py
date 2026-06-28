#!/usr/bin/env python3
"""
Retrieval-only evaluation: ID-based context precision and recall, plus
per-query latency.

Implements the same formulas as Ragas's IDBasedContextPrecision and
IDBasedContextRecall directly (no ragas/langchain dependency) -- those
metrics are pure set comparisons with no LLM involved, and the current
ragas release pulls in a broken, conflicting langchain dependency chain
just to import them. The math is simple enough to own directly:

    precision = |retrieved ∩ reference| / |retrieved|
    recall    = |retrieved ∩ reference| / |reference|

This evaluates retrieval ALONE -- no LLM is called, no generation happens.
Recall is treated as the primary metric: a chunk never retrieved is
information the generator can never use, and nothing downstream can
recover from a true miss the way a score floor can filter out noise.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.logging_config import setup_logging, get_logger
from src.retrieval.pipeline import Corpus, RetrievalPipeline

setup_logging()
logger = get_logger(__name__)


@dataclass
class RetrievalEvalCase:
    case_id: str
    question: str
    reference_document_ids: Set[str]  # ground truth: the correct kb document_ids


# Ground-truth labels, derived from confirmed real document_id values in the
# kb corpus (see medical_knowledge_base scroll dump). Only kb-corpus
# questions are scored here -- q4/q5 have no "correct chunk" (correct
# behavior is retrieving nothing) and are validated by status-gate tests
# instead, not precision/recall.
EVAL_CASES = [
    RetrievalEvalCase(
        case_id="q1_general_kb_only",
        question="What is a normal fasting blood glucose level?",
        reference_document_ids={"blood-glucose-blood-sugar", "medlineplus-6121"},
    ),
    RetrievalEvalCase(
        case_id="q3_blood_pressure",
        question="Is my blood pressure okay?",
        reference_document_ids={
            "blood-pressure-and-hypertension",
            "what-is-hypertension-high-blood-pressure",
            "medlineplus-34",
        },
    ),
    RetrievalEvalCase(
        case_id="q6_hba1c_explanation",
        question="What does an HbA1c test measure?",
        reference_document_ids={"hemoglobin-a1c-hba1c-test"},
    ),
    RetrievalEvalCase(
        case_id="q7_ldl_hdl",
        question="My LDL is 130 and my HDL is 38, what does that mean?",
        reference_document_ids={
            "cholesterol-ldl-and-hdl",
            "medlineplus-6783",
            "medlineplus-6785",
        },
    ),
]


def id_based_precision(retrieved: List[str], reference: Set[str]) -> float:
    """Proportion of retrieved IDs that are actually relevant."""
    if not retrieved:
        return 0.0
    retrieved_set = set(retrieved)
    hits = len(retrieved_set & reference)
    return hits / len(retrieved_set)


def id_based_recall(retrieved: List[str], reference: Set[str]) -> float:
    """Proportion of reference IDs that were successfully retrieved."""
    if not reference:
        return 0.0
    retrieved_set = set(retrieved)
    hits = len(retrieved_set & reference)
    return hits / len(reference)


def run_case(pipeline: RetrievalPipeline, case: RetrievalEvalCase) -> dict:
    """Run retrieval for one case and score it against ground truth."""
    start = time.perf_counter()
    result = pipeline.retrieve(case.question, corpora=[Corpus.KB])
    latency_ms = (time.perf_counter() - start) * 1000

    retrieved_ids = [
        chunk.metadata.get("document_id", "unknown") for chunk in result.chunks
    ]

    precision = id_based_precision(retrieved_ids, case.reference_document_ids)
    recall = id_based_recall(retrieved_ids, case.reference_document_ids)

    return {
        "case_id": case.case_id,
        "question": case.question,
        "retrieved_ids": retrieved_ids,
        "reference_ids": sorted(case.reference_document_ids),
        "precision": precision,
        "recall": recall,
        "latency_ms": latency_ms,
    }


def main() -> None:
    pipeline = RetrievalPipeline()
    results = [run_case(pipeline, case) for case in EVAL_CASES]

    print("=" * 80)
    for r in results:
        print(f"CASE: {r['case_id']}")
        print(f"  Question:     {r['question']}")
        print(f"  Retrieved:    {r['retrieved_ids']}")
        print(f"  Reference:    {r['reference_ids']}")
        print(f"  Precision:    {r['precision']:.2f}")
        print(f"  Recall:       {r['recall']:.2f}  <- primary metric")
        print(f"  Latency:      {r['latency_ms']:.0f} ms")
        print("-" * 80)

    avg_precision = sum(r["precision"] for r in results) / len(results)
    avg_recall = sum(r["recall"] for r in results) / len(results)
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)

    print("=" * 80)
    print(f"Average precision: {avg_precision:.2f}")
    print(f"Average recall:    {avg_recall:.2f}  <- primary metric")
    print(f"Average latency:   {avg_latency:.0f} ms")


if __name__ == "__main__":
    main()
