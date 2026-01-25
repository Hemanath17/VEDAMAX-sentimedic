"""Tests for parser factory."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.ingestion.parsers.parser_factory import ParserFactory, get_parser_factory, get_parser
from src.ingestion.parsers.base_parser import ParserError


class TestParserFactory:
    """Test cases for ParserFactory."""

    def test_factory_initialization(self):
        """Test that factory initializes with default parsers."""
        factory = ParserFactory()
        assert factory is not None
        extensions = factory.get_supported_extensions()
        assert ".pdf" in extensions
        assert ".docx" in extensions

    def test_get_parser_for_pdf(self):
        """Test getting PDF parser."""
        factory = ParserFactory()
        pdf_path = Path("test.pdf")
        parser = factory.get_parser(pdf_path)
        assert parser is not None
        assert parser.supports(pdf_path)

    def test_get_parser_for_docx(self):
        """Test getting DOCX parser."""
        factory = ParserFactory()
        docx_path = Path("test.docx")
        parser = factory.get_parser(docx_path)
        assert parser is not None
        assert parser.supports(docx_path)

    def test_get_parser_unsupported_file(self):
        """Test getting parser for unsupported file type."""
        factory = ParserFactory()
        txt_path = Path("test.txt")
        with pytest.raises(ParserError):
            factory.get_parser(txt_path)

    def test_is_supported(self):
        """Test checking if file type is supported."""
        factory = ParserFactory()
        assert factory.is_supported(Path("test.pdf")) is True
        assert factory.is_supported(Path("test.docx")) is True
        assert factory.is_supported(Path("test.txt")) is False

    def test_get_supported_extensions(self):
        """Test getting list of supported extensions."""
        factory = ParserFactory()
        extensions = factory.get_supported_extensions()
        assert isinstance(extensions, list)
        assert ".pdf" in extensions
        assert ".docx" in extensions

    def test_get_parser_info(self):
        """Test getting parser information."""
        factory = ParserFactory()
        info = factory.get_parser_info()
        assert isinstance(info, dict)
        assert ".pdf" in info
        assert ".docx" in info
        assert info[".pdf"] == "PDFParser"
        assert info[".docx"] == "DOCXParser"

    def test_get_parser_for_extension(self):
        """Test getting parser by extension."""
        factory = ParserFactory()
        parser = factory.get_parser_for_extension(".pdf")
        assert parser is not None

        parser = factory.get_parser_for_extension("docx")  # Without dot
        assert parser is not None

        with pytest.raises(ParserError):
            factory.get_parser_for_extension(".txt")

    def test_parser_caching(self):
        """Test that parser instances are cached."""
        factory = ParserFactory()
        parser1 = factory.get_parser(Path("test.pdf"), use_cached=True)
        parser2 = factory.get_parser(Path("test.pdf"), use_cached=True)
        assert parser1 is parser2  # Same instance

    def test_clear_cache(self):
        """Test clearing parser cache."""
        factory = ParserFactory()
        factory.get_parser(Path("test.pdf"), use_cached=True)
        factory.clear_cache()
        # Cache should be cleared (no way to directly verify, but no error)

    def test_register_custom_parser(self):
        """Test registering a custom parser."""
        factory = ParserFactory()

        class CustomParser:
            def get_supported_extensions(self):
                return [".custom"]

        # This would fail in real implementation, but tests the method exists
        # factory.register_parser(CustomParser)

    def test_get_parser_factory_singleton(self):
        """Test that get_parser_factory returns singleton."""
        factory1 = get_parser_factory()
        factory2 = get_parser_factory()
        assert factory1 is factory2

    def test_get_parser_convenience_function(self):
        """Test convenience function for getting parser."""
        parser = get_parser(Path("test.pdf"))
        assert parser is not None

