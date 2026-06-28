#!/usr/bin/env python3
"""
evaluation.py -- full RAG evaluation: retrieval + generation metrics,
printed as a formatted table.

JUDGE INDEPENDENCE: the generator (ResponseGenerator) uses Claude via
AnthropicClient. The judge (Faithfulness/Relevancy/Correctness scoring)
uses OpenAI via OpenAIClient -- a genuinely different model, not the same
model grading its own work. This matters: a model judging its own output
can share blind spots with itself, which an independent judge avoids.

METRIC SOURCES (read this before trusting any number below):

  Context Precision / Context Recall
      Computed directly as ID-based set comparisons (retrieved document_ids
      vs. hand-labeled reference document_ids). No LLM involved -- pure math.
      This is the same formula Ragas's IDBasedContextPrecision/Recall use.

  Faithfulness / Answer Relevancy / Answer Correctness
      Computed via an LLM-as-judge call (OpenAI, through the project's own
      OpenAIClient) rather than the `ragas` package directly. The current
      ragas release (0.4.3) has a broken import chain through
      langchain-community's removed vertexai submodule that conflicts with
      other installed langchain packages -- these judge prompts implement
      the same metric definitions Ragas uses, without that dependency.
      Each score is 0.0-1.0, self-reported by the judge model.

  Hallucination Rate
      Derived from Faithfulness using the same threshold convention shown
      in the reference table: faithfulness < 0.5 counts as hallucinated.

  Source Recall
      NOT a standard Ragas metric. Defined here as: of the citation markers
      the model emitted, what fraction map to a real, supplied source chunk
      (i.e. survive validate_citations). Distinct from Context Recall, which
      is about whether the RIGHT chunks were retrieved at all.

  Avg Latency
      Wall-clock seconds for retrieval + generation combined, per question.

CAVEAT: LLM-judge scores are not deterministic or free, unlike the ID-based
retrieval metrics. Treat them as directional signals, re-run periodically,
and don't over-trust a single run the way you can trust the ID-based numbers.
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.logging_config import setup_logging, get_logger
from src.generation.llm_client import OpenAIClient, LLMError
from src.generation.response_generator import ResponseGenerator
from src.retrieval.pipeline import Corpus, RetrievalPipeline
from src.retrieval.vector_store.vector_store import VectorStore

setup_logging()
logger = get_logger(__name__)

HALLUCINATION_THRESHOLD = 0.5
GROUNDED_THRESHOLD = 0.8
JUDGE_MODEL = "gpt-4o-mini"  # OpenAI model for LLM-as-judge (independent of Claude generator)


@dataclass
class EvalCase:
    case_id: str
    question: str
    reference_document_ids: Set[str]
    reference_answer: str
    user_id: Optional[str] = None
    user_doc_text: Optional[str] = None


# Ground truth: kb document_ids confirmed from real retrieval traces, plus a
# short hand-written reference answer per question for answer_correctness.
EVAL_CASES: List[EvalCase] = [
    EvalCase(
        case_id="q1_general_kb_only",
        question="What is a normal fasting blood glucose level?",
        reference_document_ids={"blood-glucose-blood-sugar", "medlineplus-6121"},
        reference_answer=(
            "A normal fasting blood glucose level is 70 to 99 mg/dL. "
            "100-125 mg/dL suggests prediabetes, and 126 mg/dL or higher on "
            "two separate tests suggests diabetes."
        ),
    ),
    EvalCase(
        case_id="q2_patient_glucose_180",
        question="Is my glucose high?",
        reference_document_ids={"blood-glucose-blood-sugar", "medlineplus-6121"},
        reference_answer=(
            "Yes, 180 mg/dL is above the normal fasting range of 70-99 mg/dL "
            "and above the 126 mg/dL diabetes threshold. This should be "
            "discussed with a healthcare provider."
        ),
        user_id="eval_user_q2",
        user_doc_text="Lab Report - Fasting Glucose: 180 mg/dL",
    ),
    EvalCase(
        case_id="q3_blood_pressure_normal",
        question="Is my blood pressure okay?",
        reference_document_ids={
            "blood-pressure-and-hypertension",
            "what-is-hypertension-high-blood-pressure",
            "medlineplus-34",
        },
        reference_answer=(
            "118/76 mmHg is within the normal range, which is generally "
            "below 120/80 mmHg."
        ),
        user_id="eval_user_q3",
        user_doc_text="Blood Pressure Reading: 118/76 mmHg",
    ),
    EvalCase(
        case_id="q6_hba1c_explanation",
        question="What does an HbA1c test measure?",
        reference_document_ids={"hemoglobin-a1c-hba1c-test"},
        reference_answer=(
            "HbA1c measures average blood sugar over the past 2-3 months. "
            "Below 5.7% is normal, 5.7-6.4% is prediabetes, and 6.5% or "
            "higher indicates diabetes."
        ),
    ),
    EvalCase(
        case_id="q7_ldl_hdl",
        question="My LDL is 130 and my HDL is 38, what does that mean?",
        reference_document_ids={
            "cholesterol-ldl-and-hdl",
            "medlineplus-6783",
            "medlineplus-6785",
        },
        reference_answer=(
            "LDL of 130 mg/dL is above the desirable level of below 100 "
            "mg/dL. HDL of 38 mg/dL is below the protective level of 60 "
            "mg/dL and below the low-risk cutoff of 40 mg/dL. Both values "
            "are concerning in opposite directions and worth discussing "
            "with a healthcare provider."
        ),
        user_id="eval_user_q7",
        user_doc_text="Cholesterol Panel - LDL: 130 mg/dL, HDL: 38 mg/dL",
    ),
]


# ---------------------------------------------------------------------------
# Retrieval metrics (ID-based, no LLM)
# ---------------------------------------------------------------------------


def id_based_precision(retrieved: List[str], reference: Set[str]) -> float:
    if not retrieved:
        return 0.0
    retrieved_set = set(retrieved)
    return len(retrieved_set & reference) / len(retrieved_set)


def id_based_recall(retrieved: List[str], reference: Set[str]) -> float:
    if not reference:
        return 0.0
    retrieved_set = set(retrieved)
    return len(retrieved_set & reference) / len(reference)


# ---------------------------------------------------------------------------
# LLM-as-judge metrics (Faithfulness, Answer Relevancy, Answer Correctness)
# Judge model: OpenAI (independent of the Claude-based generator above).
# ---------------------------------------------------------------------------

_SCORE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")


def _extract_score(raw: str) -> Optional[float]:
    """Pull a 0.0-1.0 float out of a judge response. Returns None if unparseable."""
    match = _SCORE_PATTERN.search(raw)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    if value > 1.0:  # judge may have answered on a 0-10 scale by mistake
        value = value / 10.0
    return max(0.0, min(1.0, value))


def judge_faithfulness(judge: OpenAIClient, answer: str, context: str) -> Optional[float]:
    """Is every claim in the answer supported by the provided context?"""
    system = (
        "You are a strict evaluator. Score how well an ANSWER is grounded in "
        "the given CONTEXT. 1.0 means every claim in the answer is directly "
        "supported by the context. 0.0 means the answer contains claims with "
        "no support in the context at all. Respond with ONLY a number between "
        "0.0 and 1.0, nothing else."
    )
    user = f"CONTEXT:\n{context}\n\nANSWER:\n{answer}\n\nFaithfulness score:"
    try:
        raw = judge.generate(system, user)
    except LLMError:
        return None
    return _extract_score(raw)


def judge_answer_relevancy(judge: OpenAIClient, question: str, answer: str) -> Optional[float]:
    """Does the answer actually address the question asked?"""
    system = (
        "You are a strict evaluator. Score how relevant an ANSWER is to the "
        "QUESTION asked. 1.0 means the answer directly and completely "
        "addresses the question. 0.0 means it is off-topic or evasive. "
        "Respond with ONLY a number between 0.0 and 1.0, nothing else."
    )
    user = f"QUESTION:\n{question}\n\nANSWER:\n{answer}\n\nRelevancy score:"
    try:
        raw = judge.generate(system, user)
    except LLMError:
        return None
    return _extract_score(raw)


def judge_answer_correctness(
    judge: OpenAIClient, answer: str, reference_answer: str
) -> Optional[float]:
    """Does the answer match the reference answer factually?"""
    system = (
        "You are a strict evaluator. Score how factually consistent an ANSWER "
        "is with a REFERENCE answer. 1.0 means all key facts in the reference "
        "are present and not contradicted. 0.0 means the answer contradicts "
        "or omits the key facts in the reference. The answer is allowed to "
        "include MORE correct detail, formatting, disclaimers, or citations "
        "than the reference -- do NOT penalize extra correct elaboration, "
        "only penalize missing or contradicted key facts. Respond with ONLY "
        "a number between 0.0 and 1.0, nothing else."
    )
    user = f"REFERENCE:\n{reference_answer}\n\nANSWER:\n{answer}\n\nCorrectness score:"
    try:
        raw = judge.generate(system, user)
    except LLMError:
        return None
    return _extract_score(raw)


# ---------------------------------------------------------------------------
# Per-case runner
# ---------------------------------------------------------------------------


@dataclass
class CaseResult:
    case_id: str
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    answer_correctness: Optional[float] = None
    source_recall: Optional[float] = None
    latency_s: float = 0.0
    error: Optional[str] = None


def run_case(
    store: VectorStore,
    pipeline: RetrievalPipeline,
    generator: ResponseGenerator,
    judge: OpenAIClient,
    case: EvalCase,
) -> CaseResult:
    result = CaseResult(case_id=case.case_id)
    start = time.perf_counter()

    try:
        if case.user_doc_text:
            chunk = {
                "text": case.user_doc_text,
                "chunk_id": f"eval_{case.case_id}",
                "metadata": {"document_id": f"eval-doc-{case.case_id}", "source": "manual_eval"},
            }
            store.store_chunks([chunk], corpus="user_doc", user_id=case.user_id)

        retrieval_result = pipeline.retrieve(case.question, user_id=case.user_id)

        retrieved_ids = [
            c.metadata.get("document_id", "unknown")
            for c in retrieval_result.chunks
            if c.corpus == Corpus.KB
        ]
        result.context_precision = id_based_precision(retrieved_ids, case.reference_document_ids)
        result.context_recall = id_based_recall(retrieved_ids, case.reference_document_ids)

        generated = generator.generate(case.question, retrieval_result)
        result.latency_s = time.perf_counter() - start

        if retrieval_result.status.value != "ok":
            return result

        context_text = "\n\n".join(c.text for c in retrieval_result.chunks)

        result.faithfulness = judge_faithfulness(judge, generated.answer, context_text)
        result.answer_relevancy = judge_answer_relevancy(judge, case.question, generated.answer)
        result.answer_correctness = judge_answer_correctness(
            judge, generated.answer, case.reference_answer
        )

        total_markers_in_answer = len(re.findall(r"\[S\d+\]", generated.answer))
        if total_markers_in_answer == 0:
            result.source_recall = 1.0 if not generated.citations else None
        else:
            result.source_recall = min(1.0, len(generated.citations) / total_markers_in_answer)

    except Exception as exc:  # noqa: BLE001 -- evaluation must not crash on one bad case
        result.error = str(exc)
        logger.error(f"Case {case.case_id} failed: {exc}")
        if result.latency_s == 0.0:
            result.latency_s = time.perf_counter() - start

    return result


# ---------------------------------------------------------------------------
# Table formatting + aggregation
# ---------------------------------------------------------------------------


def _mean(values: List[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _non_zero_count(values: List[Optional[float]]) -> int:
    return sum(1 for v in values if v is not None)


def print_table(results: List[CaseResult]) -> None:
    n = len(results)
    faithfulness_vals = [r.faithfulness for r in results]
    relevancy_vals = [r.answer_relevancy for r in results]
    correctness_vals = [r.answer_correctness for r in results]
    precision_vals = [r.context_precision for r in results]
    recall_vals = [r.context_recall for r in results]
    source_recall_vals = [r.source_recall for r in results]
    latency_vals = [r.latency_s for r in results]
    error_count = sum(1 for r in results if r.error)

    mean_faith = _mean(faithfulness_vals)
    scored_faith = [v for v in faithfulness_vals if v is not None]
    halluc_count = sum(1 for v in scored_faith if v < HALLUCINATION_THRESHOLD)
    grounded_count = sum(1 for v in scored_faith if v >= GROUNDED_THRESHOLD)
    partial_count = sum(
        1 for v in scored_faith if HALLUCINATION_THRESHOLD <= v < GROUNDED_THRESHOLD
    )

    def fmt(label: str, value: Optional[float], non_zero_n: int) -> str:
        if value is None:
            return f"{label:<28}n/a"
        return f"{label:<28}{value:.2f} ({non_zero_n}/{n} non-zero)"

    print("=" * 70)
    print(f"{'Metric':<28}Value")
    print("-" * 70)
    print("--- PRIMARY METRICS ---")
    print(fmt("Faithfulness (mean)", mean_faith, _non_zero_count(faithfulness_vals)))
    if scored_faith:
        print(f"{'Hallucination Rate':<28}{halluc_count / len(scored_faith):.0%} "
              f"({halluc_count}/{len(scored_faith)} below {HALLUCINATION_THRESHOLD} faith.)")
        print(f"{'  Grounded (faith >= ' + str(GROUNDED_THRESHOLD) + ')':<28}"
              f"{grounded_count / len(scored_faith):.0%} ({grounded_count}/{len(scored_faith)})")
        print(f"{'  Partial':<28}{partial_count / len(scored_faith):.0%} "
              f"({partial_count}/{len(scored_faith)})")
    else:
        print(f"{'Hallucination Rate':<28}n/a")
    print(fmt("Answer Relevancy", _mean(relevancy_vals), _non_zero_count(relevancy_vals)))
    print(fmt("Context Precision", _mean(precision_vals), _non_zero_count(precision_vals)))
    print(fmt("Context Recall", _mean(recall_vals), _non_zero_count(recall_vals)))
    print(fmt("Answer Correctness", _mean(correctness_vals), _non_zero_count(correctness_vals)))
    mean_source_recall = _mean(source_recall_vals)
    if mean_source_recall is not None:
        print(f"{'Source Recall (mean)':<28}{mean_source_recall:.2f}")
    else:
        print(f"{'Source Recall (mean)':<28}n/a")
    print()
    print("--- PERFORMANCE ---")
    mean_latency = _mean(latency_vals)
    if mean_latency is not None:
        print(f"{'Avg Latency (s)':<28}{mean_latency:.1f}")
    else:
        print(f"{'Avg Latency (s)':<28}n/a")
    print(f"{'Errors':<28}{error_count}")
    print("=" * 70)
    print(
        f"Hallucination Rate is computed from judge Faithfulness "
        f"(answer < {HALLUCINATION_THRESHOLD} faith. = hallucinated)."
    )
    print(
        "Generator: Claude (AnthropicClient). Judge: OpenAI (OpenAIClient) -- "
        "an independent model, not the same one grading its own output."
    )


def main() -> None:
    store = VectorStore()
    pipeline = RetrievalPipeline()
    generator = ResponseGenerator()
    judge = OpenAIClient(model=JUDGE_MODEL)

    results = [run_case(store, pipeline, generator, judge, case) for case in EVAL_CASES]

    for r in results:
        if r.error:
            print(f"[ERROR] {r.case_id}: {r.error}")

    print_table(results)


if __name__ == "__main__":
    main()
