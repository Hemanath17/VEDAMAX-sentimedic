#!/usr/bin/env python3
"""
Run all hand-curated eval cases from data/evaluation/test_queries.json
through the real retrieval + generation pipeline, and print actual vs
expected status so each one can be eyeballed against its expected_behavior.

This is a manual inspection tool, not an automated pass/fail test suite.
Run scripts/seed_kb.py first so the KB collection is populated.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.logging_config import setup_logging, get_logger
from src.generation.response_generator import ResponseGenerator
from src.retrieval.pipeline import RetrievalPipeline
from src.retrieval.vector_store.vector_store import VectorStore

setup_logging()
logger = get_logger(__name__)

QUERIES_PATH = ROOT / "data" / "evaluation" / "test_queries.json"


def load_cases() -> list[dict]:
    """Load eval cases from the test_queries.json file."""
    with QUERIES_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data["queries"]


def run_case(store: VectorStore, pipeline: RetrievalPipeline, generator: ResponseGenerator, case: dict) -> None:
    """Seed an optional user_doc fixture, retrieve, generate, and print results."""
    case_id = case["id"]
    question = case["question"]
    user_id = case.get("user_id")
    user_doc_text = case.get("user_doc_text")
    expected_status = case["expected_status"]

    print("=" * 80)
    print(f"CASE: {case_id}")
    print(f"Question: {question}")
    print(f"Expected status: {expected_status}")
    print(f"Expected behavior: {case['expected_behavior']}")
    print("-" * 80)

    if user_doc_text:
        chunk = {
            "text": user_doc_text,
            "chunk_id": f"eval_{case_id}",
            "metadata": {
                "document_id": f"eval-doc-{case_id}",
                "source": "manual_eval",
                "chunk_type": "text",
            },
        }
        store.store_chunks([chunk], corpus="user_doc", user_id=user_id)

    retrieval_result = pipeline.retrieve(question, user_id=user_id)
    actual_status = retrieval_result.status.value
    status_match = "MATCH" if actual_status == expected_status else "MISMATCH"

    print(f"Actual status:   {actual_status}  [{status_match}]")
    print(f"Chunks retrieved: {len(retrieval_result.chunks)}")

    generated = generator.generate(question, retrieval_result)

    print("\n--- Answer ---")
    print(generated.answer)

    print("\n--- Citations ---")
    if generated.citations:
        for citation in generated.citations:
            print(f"  {citation.marker} ({citation.corpus.value}) -> {citation.source_ref}")
    else:
        print("  (none)")

    print(f"\nFlagged numbers: {generated.flagged_numbers or '(none)'}")
    print()


def main() -> None:
    """Run every case in test_queries.json and print results for manual review."""
    if not QUERIES_PATH.exists():
        raise FileNotFoundError(f"Eval queries file not found: {QUERIES_PATH}")

    cases = load_cases()
    store = VectorStore()
    pipeline = RetrievalPipeline()
    generator = ResponseGenerator()

    print(f"Running {len(cases)} eval case(s) from {QUERIES_PATH}\n")

    for case in cases:
        run_case(store, pipeline, generator, case)

    print("=" * 80)
    print("Done. Review each case's actual answer against its expected_behavior above.")


if __name__ == "__main__":
    main()