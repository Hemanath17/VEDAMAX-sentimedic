"""Base parser interface for document parsing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
from datetime import datetime

from src.config.logging_config import get_logger
from src.utils.file_utils import get_file_extension
from src.utils.validators import validate_file_path

logger = get_logger(__name__)


class ParserError(Exception):
    """Custom exception for parser errors."""

    pass


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a document file.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary containing parsed content and metadata with structure:
            {
                "text": str,           # Main text content
                "tables": List[Dict],   # Extracted tables
                "metadata": Dict,      # Document metadata
                "pages": int,          # Number of pages (if applicable)
                "parser_type": str     # Parser identifier
            }

        Raises:
            ParserError: If parsing fails
        """
        pass

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """
        Check if the parser supports the given file type.

        Args:
            file_path: Path to the document file

        Returns:
            True if the parser supports this file type
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of file extensions supported by this parser.

        Returns:
            List of supported file extensions (e.g., ['.pdf', '.PDF'])
        """
        pass

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate that the file exists and is readable.

        Args:
            file_path: Path to the document file

        Returns:
            True if file is valid

        Raises:
            ParserError: If file validation fails
        """
        if not file_path.exists():
            raise ParserError(f"File does not exist: {file_path}")

        if not file_path.is_file():
            raise ParserError(f"Path is not a file: {file_path}")

        if not file_path.stat().st_size > 0:
            raise ParserError(f"File is empty: {file_path}")

        return True

    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from the document.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary containing document metadata
        """
        metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path.absolute()),
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "file_type": get_file_extension(file_path),
            "parser_type": self.__class__.__name__,
            "parsed_at": datetime.utcnow().isoformat(),
        }

        # Add file hash for deduplication
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                    metadata["file_hash"] = file_hash
            except Exception as e:
                logger.warning(f"Could not compute file hash: {e}")

        return metadata

    def parse_with_validation(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a document with validation and error handling.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary containing parsed content and metadata

        Raises:
            ParserError: If parsing fails
        """
        try:
            # Validate file
            self.validate_file(file_path)

            # Check if parser supports this file type
            if not self.supports(file_path):
                raise ParserError(
                    f"Parser {self.__class__.__name__} does not support file type: {get_file_extension(file_path)}"
                )

            # Parse document
            logger.info(f"Parsing document: {file_path}")
            result = self.parse(file_path)

            # Validate result structure
            if not isinstance(result, dict):
                raise ParserError("Parser returned invalid result type")

            required_keys = ["text", "metadata"]
            for key in required_keys:
                if key not in result:
                    raise ParserError(f"Parser result missing required key: {key}")

            logger.info(f"Successfully parsed document: {file_path}")
            return result

        except ParserError:
            raise
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {e}", exc_info=True)
            raise ParserError(f"Failed to parse document: {str(e)}") from e

