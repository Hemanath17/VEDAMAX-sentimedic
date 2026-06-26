#!/usr/bin/env python3
"""Manual end-to-end check: seed KB (run seed_kb.py first), retrieve, generate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.logging_config import setup_logging
from src.generation.response_generator import ResponseGenerator
from src.retrieval.pipeline import RetrievalPipeline
from src.retrieval.vector_store.vector_store import VectorStore

setup_logging()

USER_ID = "testuser"
QUESTION = "Is my glucose high?"


def main() -> None:
    """Store a fake user lab chunk, retrieve evidence, and generate an answer."""
    store = VectorStore()
    user_chunks = [
        {
            "text": "Glucose: 180 mg/dL",
            "chunk_id": "user_testuser_glucose_1",
            "metadata": {
                "document_id": "test-lab-report",
                "source": "manual_test",
                "chunk_type": "text",
            },
        }
    ]
    store.store_chunks(user_chunks, corpus="user_doc", user_id=USER_ID)
    print(f"Stored {len(user_chunks)} user_doc chunk(s) for user_id={USER_ID!r}.")

    pipeline = RetrievalPipeline()
    retrieval_result = pipeline.retrieve(QUESTION, user_id=USER_ID)
    print(f"\nRetrieval status: {retrieval_result.status.value}")
    print(f"Chunks retrieved: {len(retrieval_result.chunks)}")

    generator = ResponseGenerator()
    generated = generator.generate(QUESTION, retrieval_result)

    print("\n--- Final answer ---")
    print(generated.answer)

    print("\n--- Citations ---")
    if generated.citations:
        for citation in generated.citations:
            print(f"  {citation.marker} ({citation.corpus.value}) -> {citation.source_ref}")
    else:
        print("  (none)")

    print("\n--- Flagged numbers ---")
    print(generated.flagged_numbers if generated.flagged_numbers else "(none)")

    print("\n--- Disclaimer ---")
    print(generated.disclaimer)


if __name__ == "__main__":
    main()
