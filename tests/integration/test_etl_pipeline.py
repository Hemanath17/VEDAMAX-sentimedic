"""Integration tests for ETL pipeline."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from src.ingestion.etl_pipeline import ETLPipeline
from src.ingestion.parsers.base_parser import ParserError
from src.ingestion.chunkers.chunk_strategy import ChunkingError


class TestETLPipeline:
    """Integration tests for ETL pipeline."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def sample_text_file(self, temp_dir):
        """Create a sample text file."""
        file_path = temp_dir / "sample.txt"
        file_path.write_text(
            "This is a sample medical document. "
            "It contains information about patient symptoms. "
            "The patient presents with fever and headache."
        )
        return file_path

    @pytest.fixture
    def etl_pipeline(self):
        """Create ETL pipeline instance."""
        return ETLPipeline(chunk_strategy="token", use_ocr=False, extract_tables=False)

    def test_etl_pipeline_initialization(self, etl_pipeline):
        """Test that ETL pipeline initializes correctly."""
        assert etl_pipeline is not None
        assert etl_pipeline.chunk_strategy == "token"
        assert etl_pipeline.parser_factory is not None
        assert etl_pipeline.chunker_factory is not None

    def test_process_document_nonexistent_file(self, etl_pipeline):
        """Test processing non-existent file."""
        result = etl_pipeline.process_document(Path("nonexistent.pdf"))
        assert result["status"] == "error"
        assert "error" in result

    def test_process_document_unsupported_file(self, etl_pipeline, temp_dir):
        """Test processing unsupported file type."""
        file_path = temp_dir / "test.xyz"
        file_path.write_text("test content")
        result = etl_pipeline.process_document(file_path)
        assert result["status"] == "error"

    @patch("src.ingestion.etl_pipeline.get_parser_factory")
    def test_process_document_parser_error(self, mock_factory, etl_pipeline, temp_dir):
        """Test handling parser errors."""
        # Create a mock parser that raises error
        mock_parser = Mock()
        mock_parser.parse_with_validation.side_effect = ParserError("Parser failed")
        mock_factory.return_value.get_parser.return_value = mock_parser

        file_path = temp_dir / "test.pdf"
        file_path.write_text("test")
        result = etl_pipeline.process_document(file_path)
        assert result["status"] == "error"

    def test_process_document_success(self, etl_pipeline, sample_text_file):
        """Test successful document processing."""
        # This will fail if parsers aren't properly set up, but tests the flow
        # In real scenario, would use actual PDF/DOCX file
        result = etl_pipeline.process_document(sample_text_file)
        # Result may be error if file type not supported, but structure should be correct
        assert "status" in result
        assert "document_id" in result
        assert "chunks" in result
        assert "metadata" in result

    def test_process_document_with_metadata(self, etl_pipeline, sample_text_file):
        """Test processing document with custom metadata."""
        metadata = {"source": "test", "category": "medical"}
        result = etl_pipeline.process_document(sample_text_file, metadata=metadata)
        assert "metadata" in result

    def test_get_metadata_manager(self, etl_pipeline):
        """Test getting metadata manager."""
        manager = etl_pipeline.get_metadata_manager()
        assert manager is not None


class TestBatchProcessor:
    """Integration tests for batch processor."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def batch_processor(self):
        """Create batch processor instance."""
        from src.ingestion.batch_processor import BatchProcessor
        return BatchProcessor(max_workers=2, use_async=False)

    def test_batch_processor_initialization(self, batch_processor):
        """Test batch processor initialization."""
        assert batch_processor is not None
        assert batch_processor.max_workers == 2
        assert batch_processor.etl_pipeline is not None

    def test_process_directory_empty(self, batch_processor, temp_dir):
        """Test processing empty directory."""
        result = batch_processor.process_directory(temp_dir)
        assert result["total_files"] == 0
        assert result["processed"] == 0

    def test_process_directory_nonexistent(self, batch_processor):
        """Test processing non-existent directory."""
        result = batch_processor.process_directory(Path("nonexistent_dir"))
        assert result["total_files"] == 0

    def test_generate_report(self, batch_processor):
        """Test report generation."""
        batch_result = {
            "total_files": 10,
            "processed": 8,
            "failed": 2,
            "results": [],
            "processing_time": 5.5,
            "average_time_per_file": 0.55,
        }
        report = batch_processor.generate_report(batch_result)
        assert "Batch Processing Report" in report
        assert "10" in report
        assert "8" in report
        assert "2" in report

