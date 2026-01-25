#!/usr/bin/env python3
"""Script for ingesting documents into the system."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.ingestion.etl_pipeline import ETLPipeline
from src.config.settings import settings
from src.config.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    """Main ingestion function."""
    import argparse

    parser = argparse.ArgumentParser(description="Ingest documents into SentiMedical-RAG")
    parser.add_argument("file_path", type=str, help="Path to document file")
    parser.add_argument(
        "--chunk-strategy",
        type=str,
        default="semantic",
        choices=["semantic", "token"],
        help="Chunking strategy to use",
    )
    parser.add_argument(
        "--metadata",
        type=str,
        help="JSON string with metadata",
    )

    args = parser.parse_args()

    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    logger.info(f"Ingesting document: {file_path}")

    # TODO: Implement ETLPipeline
    # pipeline = ETLPipeline()
    # result = pipeline.process_document(file_path, chunk_strategy=args.chunk_strategy)
    # logger.info(f"Ingestion complete: {result}")

    logger.info("Ingestion script placeholder - implement ETLPipeline to use")


if __name__ == "__main__":
    main()

