"""PDF parser using Docling library."""

from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import tempfile
import shutil

from src.ingestion.parsers.base_parser import BaseParser, ParserError
from src.config.logging_config import get_logger
from src.utils.file_utils import get_file_extension

logger = get_logger(__name__)

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None  # type: ignore
    logger.warning("Docling not available. PDF parsing will be limited.")


class PDFParser(BaseParser):
    """PDF parser using Docling for advanced document processing."""

    def __init__(self, use_ocr: bool = True, ocr_language: str = "eng"):
        """
        Initialize PDF parser.

        Args:
            use_ocr: Whether to use OCR for scanned PDFs
            ocr_language: OCR language code
        """
        self.use_ocr = use_ocr
        self.ocr_language = ocr_language
        self._converter: Optional[Any] = None  # DocumentConverter when available

    def _get_converter(self) -> Any:  # DocumentConverter when available
        """
        Get or create Docling converter instance.

        Returns:
            DocumentConverter instance
        """
        if self._converter is None:
            if not DOCLING_AVAILABLE:
                raise ParserError(
                    "Docling library is not installed. Install it with: pip install docling"
                )

            try:
                # Initialize converter with OCR support
                self._converter = DocumentConverter(
                    format=InputFormat.PDF,
                    enable_ocr=self.use_ocr,
                    ocr_language=self.ocr_language,
                )
                logger.info("Initialized Docling PDF converter")
            except Exception as e:
                logger.error(f"Failed to initialize Docling converter: {e}")
                raise ParserError(f"Failed to initialize converter: {e}")

        return self._converter

    def supports(self, file_path: Path) -> bool:
        """
        Check if the parser supports the given file type.

        Args:
            file_path: Path to the document file

        Returns:
            True if the parser supports this file type
        """
        return get_file_extension(file_path) in [".pdf"]

    def get_supported_extensions(self) -> List[str]:
        """
        Get list of file extensions supported by this parser.

        Returns:
            List of supported file extensions
        """
        return [".pdf"]

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a PDF file using Docling.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing parsed content and metadata:
            {
                "text": str,           # Main text content
                "tables": List[Dict],   # Extracted tables
                "metadata": Dict,       # Document metadata
                "pages": int,          # Number of pages
                "parser_type": str     # Parser identifier
            }

        Raises:
            ParserError: If parsing fails
        """
        if not DOCLING_AVAILABLE:
            # Fallback to PyPDF2 if Docling is not available
            return self._parse_with_pypdf2(file_path)

        try:
            converter = self._get_converter()

            # Convert PDF document
            logger.info(f"Converting PDF with Docling: {file_path}")
            doc = converter.convert(str(file_path))

            # Extract text content
            text_content = doc.document.export_to_text() if hasattr(doc.document, "export_to_text") else str(doc.document)

            # Extract tables
            tables = []
            if hasattr(doc.document, "tables") and doc.document.tables:
                for table in doc.document.tables:
                    table_data = self._extract_table_data(table)
                    if table_data:
                        tables.append(table_data)

            # Extract metadata
            metadata = self.extract_metadata(file_path)
            metadata.update({
                "title": getattr(doc.document, "title", None),
                "author": getattr(doc.document, "author", None),
                "subject": getattr(doc.document, "subject", None),
                "pages": getattr(doc.document, "page_count", None),
            })

            # Get page count
            page_count = metadata.get("pages") or self._get_page_count_fallback(file_path)

            result = {
                "text": text_content,
                "tables": tables,
                "metadata": metadata,
                "pages": page_count,
                "parser_type": "PDFParser",
            }

            logger.info(f"Successfully parsed PDF: {file_path} ({page_count} pages, {len(tables)} tables)")
            return result

        except Exception as e:
            logger.error(f"Error parsing PDF with Docling: {e}", exc_info=True)
            # Fallback to PyPDF2
            logger.info("Falling back to PyPDF2")
            return self._parse_with_pypdf2(file_path)

    def _extract_table_data(self, table) -> Optional[Dict[str, Any]]:
        """
        Extract data from a table object.

        Args:
            table: Table object from Docling

        Returns:
            Dictionary with table data or None
        """
        try:
            # Try to extract table as structured data
            if hasattr(table, "to_dict"):
                return table.to_dict()
            elif hasattr(table, "rows"):
                rows = []
                for row in table.rows:
                    if hasattr(row, "cells"):
                        cells = [str(cell) if hasattr(cell, "__str__") else cell for cell in row.cells]
                        rows.append(cells)
                return {"rows": rows, "type": "table"}
            else:
                # Convert table to text
                table_text = str(table)
                return {"text": table_text, "type": "table"}
        except Exception as e:
            logger.warning(f"Could not extract table data: {e}")
            return None

    def _get_page_count_fallback(self, file_path: Path) -> int:
        """
        Get page count using fallback method.

        Args:
            file_path: Path to PDF file

        Returns:
            Number of pages
        """
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                return len(pdf_reader.pages)
        except Exception:
            return 0

    def _parse_with_pypdf2(self, file_path: Path) -> Dict[str, Any]:
        """
        Fallback PDF parser using PyPDF2.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing parsed content and metadata
        """
        try:
            import PyPDF2

            logger.info(f"Parsing PDF with PyPDF2: {file_path}")

            text_parts = []
            pages = 0

            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pages = len(pdf_reader.pages)

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            text_parts.append(text)
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num}: {e}")

            text_content = "\n\n".join(text_parts)

            metadata = self.extract_metadata(file_path)
            metadata.update({
                "title": pdf_reader.metadata.get("/Title", None) if pdf_reader.metadata else None,
                "author": pdf_reader.metadata.get("/Author", None) if pdf_reader.metadata else None,
            })

            result = {
                "text": text_content,
                "tables": [],  # PyPDF2 doesn't extract tables
                "metadata": metadata,
                "pages": pages,
                "parser_type": "PDFParser_PyPDF2",
            }

            logger.info(f"Successfully parsed PDF with PyPDF2: {file_path} ({pages} pages)")
            return result

        except ImportError:
            raise ParserError("PyPDF2 is not installed. Install it with: pip install PyPDF2")
        except Exception as e:
            logger.error(f"Error parsing PDF with PyPDF2: {e}", exc_info=True)
            raise ParserError(f"Failed to parse PDF: {str(e)}") from e

