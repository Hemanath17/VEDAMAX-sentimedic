"""Data processors for table extraction and OCR."""

from src.ingestion.processors.table_extractor import TableExtractor
from src.ingestion.processors.ocr_processor import OCRProcessor

__all__ = [
    "TableExtractor",
    "OCRProcessor",
]

