#!/usr/bin/env python3
"""
Manual check for Phase 8 triage. Confirms:
  1. An emergency-phrased question bypasses retrieval AND generation entirely.
  2. A distressed-but-routine question still retrieves/generates, with a
     gentler persona.
  3. A plain routine question behaves exactly as it did before triage existed.

Run scripts/seed_kb.py first so the KB collection has content for cases 2/3.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.logging_config import setup_logging
from src.agentic.router.orchestrator import TriageOrchestrator
from src.agentic.router.triage_agent import TriageLevel

setup_logging()

CASES = [
    {
        "id": "t1_clear_emergency",
        "question": "I'm having sudden crushing chest pain and can't catch my breath.",
        "risk_level": 0.2,  # deliberately LOW emotional risk, to prove detection
                            # is content-based, not tone-based
        "expect_level": TriageLevel.EMERGENCY,
        "note": "Must NOT call retrieval or generation. Watch for the absence "
                "of a 'POST .../v1/messages' line tied to content generation "
                "(the triage classifier itself does call the LLM once, which "
                "is expected -- what must NOT happen is a second call for an "
                "answer, and RetrievalPipeline must not run at all).",
    },
    {
        "id": "t2_distressed_but_routine",
        "question": "I'm really scared, is a glucose of 180 going to kill me?",
        "risk_level": 0.75,
        "expect_level": TriageLevel.DISTRESSED,
        "note": "Should retrieve and generate normally, with a gentler tone "
                "than the plain version of this question.",
    },
    {
        "id": "t3_plain_routine",
        "question": "What is a normal fasting blood glucose level?",
        "risk_level": 0.1,
        "expect_level": TriageLevel.ROUTINE,
        "note": "Should behave identically to calling ResponseGenerator directly.",
    },
]


def main() -> None:
    orchestrator = TriageOrchestrator()

    for case in CASES:
        print("=" * 80)
        print(f"CASE: {case['id']}")
        print(f"Question: {case['question']}")
        print(f"Expected triage level: {case['expect_level'].value}")
        print(f"What to check: {case['note']}")
        print("-" * 80)

        result = orchestrator.handle(
            question=case["question"],
            session_id=f"test-{case['id']}",
            risk_level=case["risk_level"],
        )

        match = "MATCH" if result.triage_level == case["expect_level"] else "MISMATCH"
        print(f"Actual triage level: {result.triage_level.value}  [{match}]")
        print(f"Generation ran: {result.generated is not None}")
        print("\n--- Answer ---")
        print(result.answer_text)
        print()

    print("=" * 80)
    print("Done. For t1, manually confirm in the log above that the Anthropic ")
    print("API was called ONLY for the triage classification, never for a ")
    print("generated answer, and that no Qdrant retrieval calls appear.")


if __name__ == "__main__":
    main()