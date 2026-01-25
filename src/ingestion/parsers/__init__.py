"""Document parsers for PDF and DOCX files."""

from src.ingestion.parsers.base_parser import BaseParser, ParserError
from src.ingestion.parsers.pdf_parser import PDFParser
from src.ingestion.parsers.docx_parser import DOCXParser
from src.ingestion.parsers.parser_factory import (
    ParserFactory,
    get_parser_factory,
    get_parser,
)

__all__ = [
    "BaseParser",
    "ParserError",
    "PDFParser",
    "DOCXParser",
    "ParserFactory",
    "get_parser_factory",
    "get_parser",
]

