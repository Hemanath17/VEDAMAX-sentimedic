#!/usr/bin/env python3
"""
Hallucination-rate summary: runs the existing 7-case eval set end-to-end
(retrieval + generation) and reports what fraction of answers had zero
flagged (ungrounded) numbers.

This deliberately reuses ResponseGenerator's existing verify_numbers check
rather than a Ragas faithfulness/judge metric -- it's free, deterministic,
boundary-safe, and already running on every real request, so this script
is just an aggregator over a check you already have, not a new one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.logging_config import setup_logging
from src.generation.response_generator import ResponseGenerator
from src.retrieval.pipeline import RetrievalPipeline
from src.retrieval.vector_store.vector_store import VectorStore

setup_logging()

QUERIES_PATH = ROOT / "data" / "evaluation" / "test_queries.json"


def main() -> None:
    with QUERIES_PATH.open(encoding="utf-8") as handle:
        cases = json.load(handle)["queries"]

    store = VectorStore()
    pipeline = RetrievalPipeline()
    generator = ResponseGenerator()

    clean_count = 0
    flagged_total = 0
    scored_cases = 0

    for case in cases:
        question = case["question"]
        user_id = case.get("user_id")
        user_doc_text = case.get("user_doc_text")

        if user_doc_text:
            chunk = {
                "text": user_doc_text,
                "chunk_id": f"halluc_{case['id']}",
                "metadata": {"document_id": f"halluc-doc-{case['id']}", "source": "manual_eval"},
            }
            store.store_chunks([chunk], corpus="user_doc", user_id=user_id)

        retrieval_result = pipeline.retrieve(question, user_id=user_id)
        generated = generator.generate(question, retrieval_result)

        # Only score cases where generation actually ran -- no_user_docs /
        # below_threshold cases never call the LLM, so there's nothing to
        # check for hallucinated numbers.
        if generated.flagged_numbers is None:
            continue
        if retrieval_result.status.value not in ("ok",):
            continue

        scored_cases += 1
        if generated.flagged_numbers:
            flagged_total += len(generated.flagged_numbers)
            print(f"FLAGGED in {case['id']}: {generated.flagged_numbers}")
        else:
            clean_count += 1

    hallucination_rate = 1 - (clean_count / scored_cases) if scored_cases else 0.0

    print("=" * 80)
    print(f"Scored cases (generation ran):      {scored_cases}")
    print(f"Clean (zero flagged numbers):        {clean_count}")
    print(f"Cases with >=1 flagged number:        {scored_cases - clean_count}")
    print(f"Hallucination rate (by case):         {hallucination_rate:.0%}")


if __name__ == "__main__":
    main()
