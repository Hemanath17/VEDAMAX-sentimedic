"""Parser factory for automatic parser selection based on file type."""

from pathlib import Path
from typing import Dict, Type, Optional, List

from src.ingestion.parsers.base_parser import BaseParser, ParserError
from src.ingestion.parsers.pdf_parser import PDFParser
from src.ingestion.parsers.docx_parser import DOCXParser
from src.config.logging_config import get_logger
from src.utils.file_utils import get_file_extension

logger = get_logger(__name__)


class ParserFactory:
    """Factory class for creating appropriate parsers based on file type."""

    def __init__(self):
        """Initialize parser factory with default parsers."""
        self._parsers: Dict[str, Type[BaseParser]] = {}
        self._parser_instances: Dict[str, BaseParser] = {}
        self._register_default_parsers()

    def _register_default_parsers(self) -> None:
        """Register default parsers (PDF, DOCX)."""
        self.register_parser(PDFParser, create_instance=True)
        self.register_parser(DOCXParser, create_instance=True)
        logger.info("Registered default parsers: PDF, DOCX")

    def register_parser(
        self,
        parser_class: Type[BaseParser],
        create_instance: bool = False,
        extensions: Optional[List[str]] = None,
    ) -> None:
        """
        Register a parser class with the factory.

        Args:
            parser_class: Parser class to register
            create_instance: Whether to create and cache an instance
            extensions: Optional list of extensions to register.
                       If None, uses parser's get_supported_extensions()
        """
        try:
            # Get supported extensions from parser if not provided
            if extensions is None:
                # Create temporary instance to get extensions
                temp_instance = parser_class()
                extensions = temp_instance.get_supported_extensions()
            else:
                # Validate extensions format
                extensions = [ext.lower() if not ext.startswith(".") else ext.lower() for ext in extensions]

            # Register parser for each extension
            for ext in extensions:
                self._parsers[ext] = parser_class
                logger.debug(f"Registered parser {parser_class.__name__} for extension: {ext}")

            # Create and cache instance if requested
            if create_instance:
                instance_key = parser_class.__name__
                if instance_key not in self._parser_instances:
                    self._parser_instances[instance_key] = parser_class()
                    logger.debug(f"Cached instance of {parser_class.__name__}")

        except Exception as e:
            logger.error(f"Failed to register parser {parser_class.__name__}: {e}")
            raise ParserError(f"Failed to register parser: {e}") from e

    def get_parser(self, file_path: Path, use_cached: bool = True) -> BaseParser:
        """
        Get appropriate parser for the given file.

        Args:
            file_path: Path to the file to parse
            use_cached: Whether to use cached parser instances

        Returns:
            Appropriate parser instance

        Raises:
            ParserError: If no parser is found for the file type
        """
        # Get file extension
        file_ext = get_file_extension(file_path)

        if not file_ext:
            raise ParserError(f"File has no extension: {file_path}")

        # Check if parser is registered for this extension
        parser_class = self._parsers.get(file_ext)
        if not parser_class:
            supported = ", ".join(self._parsers.keys())
            raise ParserError(
                f"No parser found for file type '{file_ext}'. "
                f"Supported extensions: {supported}"
            )

        # Return cached instance if available and requested
        if use_cached:
            instance_key = parser_class.__name__
            if instance_key in self._parser_instances:
                logger.debug(f"Using cached parser instance: {instance_key}")
                return self._parser_instances[instance_key]

        # Create new instance
        try:
            parser_instance = parser_class()
            logger.debug(f"Created new parser instance: {parser_class.__name__}")

            # Cache instance if caching is enabled
            if use_cached:
                instance_key = parser_class.__name__
                self._parser_instances[instance_key] = parser_instance

            return parser_instance

        except Exception as e:
            logger.error(f"Failed to create parser instance {parser_class.__name__}: {e}")
            raise ParserError(f"Failed to create parser: {e}") from e

    def get_parser_for_extension(self, extension: str, use_cached: bool = True) -> BaseParser:
        """
        Get parser for a specific file extension.

        Args:
            extension: File extension (with or without leading dot)
            use_cached: Whether to use cached parser instances

        Returns:
            Parser instance for the extension

        Raises:
            ParserError: If no parser is found for the extension
        """
        # Normalize extension
        if not extension.startswith("."):
            extension = f".{extension}"
        extension = extension.lower()

        parser_class = self._parsers.get(extension)
        if not parser_class:
            supported = ", ".join(self._parsers.keys())
            raise ParserError(
                f"No parser found for extension '{extension}'. "
                f"Supported extensions: {supported}"
            )

        # Return cached instance if available
        if use_cached:
            instance_key = parser_class.__name__
            if instance_key in self._parser_instances:
                return self._parser_instances[instance_key]

        # Create new instance
        parser_instance = parser_class()
        if use_cached:
            instance_key = parser_class.__name__
            self._parser_instances[instance_key] = parser_instance

        return parser_instance

    def get_supported_extensions(self) -> List[str]:
        """
        Get list of all supported file extensions.

        Returns:
            List of supported file extensions
        """
        return sorted(list(self._parsers.keys()))

    def is_supported(self, file_path: Path) -> bool:
        """
        Check if a file type is supported.

        Args:
            file_path: Path to the file

        Returns:
            True if file type is supported
        """
        file_ext = get_file_extension(file_path)
        return file_ext in self._parsers

    def get_parser_info(self) -> Dict[str, str]:
        """
        Get information about registered parsers.

        Returns:
            Dictionary mapping extensions to parser class names
        """
        return {
            ext: parser_class.__name__
            for ext, parser_class in self._parsers.items()
        }

    def clear_cache(self) -> None:
        """Clear cached parser instances."""
        self._parser_instances.clear()
        logger.debug("Cleared parser instance cache")

    def unregister_parser(self, extension: str) -> None:
        """
        Unregister a parser for a specific extension.

        Args:
            extension: File extension to unregister
        """
        extension = extension.lower()
        if not extension.startswith("."):
            extension = f".{extension}"

        if extension in self._parsers:
            parser_class = self._parsers.pop(extension)
            logger.info(f"Unregistered parser {parser_class.__name__} for extension: {extension}")

            # Also remove cached instance if it exists
            instance_key = parser_class.__name__
            if instance_key in self._parser_instances:
                del self._parser_instances[instance_key]
        else:
            logger.warning(f"Extension {extension} not registered, nothing to unregister")


# Global factory instance
_default_factory: Optional[ParserFactory] = None


def get_parser_factory() -> ParserFactory:
    """
    Get the default global parser factory instance.

    Returns:
        Global ParserFactory instance
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ParserFactory()
    return _default_factory


def get_parser(file_path: Path) -> BaseParser:
    """
    Convenience function to get a parser for a file using the default factory.

    Args:
        file_path: Path to the file

    Returns:
        Appropriate parser instance
    """
    factory = get_parser_factory()
    return factory.get_parser(file_path)

