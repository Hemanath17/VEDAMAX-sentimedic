#!/usr/bin/env python3
"""Script for running evaluation on the system."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    """Main evaluation function."""
    import argparse

    parser = argparse.ArgumentParser(description="Run evaluation on SentiMedical-RAG")
    parser.add_argument(
        "--queries-file",
        type=str,
        default="data/evaluation/test_queries.json",
        help="Path to test queries JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to output results JSON file",
    )
    parser.add_argument(
        "--metrics",
        type=str,
        nargs="+",
        default=["faithfulness", "relevancy", "answer_correctness"],
        help="Metrics to compute",
    )

    args = parser.parse_args()

    queries_file = Path(args.queries_file)
    if not queries_file.exists():
        logger.error(f"Queries file not found: {queries_file}")
        sys.exit(1)

    with open(queries_file) as f:
        data = json.load(f)

    queries = data.get("queries", [])
    ground_truth = data.get("ground_truth", [])

    logger.info(f"Running evaluation on {len(queries)} queries")

    # TODO: Implement EvaluationPipeline
    # evaluator = EvaluationPipeline()
    # results = evaluator.evaluate(queries, ground_truth, metrics=args.metrics)
    # logger.info(f"Evaluation complete: {results}")

    logger.info("Evaluation script placeholder - implement EvaluationPipeline to use")


if __name__ == "__main__":
    main()

