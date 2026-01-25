"""ETL pipeline for document ingestion and processing."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from src.ingestion.parsers.parser_factory import get_parser_factory, ParserError
from src.ingestion.chunkers.chunker_factory import get_chunker_factory, ChunkingError
from src.ingestion.processors.table_extractor import TableExtractor
from src.ingestion.processors.ocr_processor import OCRProcessor
from src.ingestion.chunk_metadata import ChunkMetadataManager, ChunkMetadata
from src.config.logging_config import get_logger
from src.config.settings import settings
from src.utils.file_utils import is_supported_file

logger = get_logger(__name__)


class ETLPipeline:
    """End-to-end ETL pipeline for document processing."""

    def __init__(
        self,
        chunk_strategy: str = "semantic",
        use_ocr: bool = False,
        extract_tables: bool = True,
    ):
        """
        Initialize ETL pipeline.

        Args:
            chunk_strategy: Chunking strategy ('semantic' or 'token')
            use_ocr: Whether to use OCR for scanned documents
            extract_tables: Whether to extract and process tables
        """
        self.chunk_strategy = chunk_strategy
        self.use_ocr = use_ocr
        self.extract_tables = extract_tables

        # Initialize components
        self.parser_factory = get_parser_factory()
        self.chunker_factory = get_chunker_factory()
        self.table_extractor = TableExtractor() if extract_tables else None
        self.ocr_processor = OCRProcessor() if use_ocr else None
        self.metadata_manager = ChunkMetadataManager()

        logger.info(
            f"Initialized ETL pipeline: strategy={chunk_strategy}, "
            f"ocr={use_ocr}, tables={extract_tables}"
        )

    def process_document(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a single document through the ETL pipeline.

        Args:
            file_path: Path to document file
            document_id: Optional document identifier
            chunk_size: Optional chunk size override
            chunk_overlap: Optional chunk overlap override
            metadata: Optional base metadata

        Returns:
            Dictionary with processing results:
            {
                "document_id": str,
                "chunks": List[Dict],
                "tables": List[Dict],
                "metadata": Dict,
                "processing_time": float,
                "status": str,
            }
        """
        start_time = datetime.utcnow()

        try:
            # Validate file
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if not is_supported_file(file_path):
                raise ValueError(f"Unsupported file type: {file_path}")

            logger.info(f"Processing document: {file_path}")

            # Generate document ID if not provided
            if not document_id:
                document_id = f"doc_{datetime.utcnow().timestamp()}"

            # Step 1: Parse document
            parser = self.parser_factory.get_parser(file_path)
            parsed_data = parser.parse_with_validation(file_path)

            # Step 2: Extract tables (if enabled)
            tables = []
            if self.extract_tables and self.table_extractor:
                tables = self.table_extractor.extract_tables(parsed_data)

            # Step 3: Process OCR (if enabled and needed)
            if self.use_ocr and self.ocr_processor:
                # Check if text is very short (might be scanned)
                if len(parsed_data.get("text", "")) < 100:
                    logger.info("Text is short, attempting OCR")
                    ocr_result = self.ocr_processor.process_pdf(file_path)
                    if ocr_result.get("ocr_processed"):
                        parsed_data["text"] = self.ocr_processor.merge_ocr_with_existing_text(
                            parsed_data.get("text", ""),
                            ocr_result.get("text", ""),
                            strategy="smart",
                        )

            # Step 4: Prepare base metadata
            base_metadata = {
                "document_id": document_id,
                "source_file_path": str(file_path.absolute()),
                "source_file_name": file_path.name,
                "source_file_type": file_path.suffix.lower(),
                "parser_type": parsed_data.get("parser_type"),
                "page_count": parsed_data.get("pages"),
            }

            if metadata:
                base_metadata.update(metadata)

            # Step 5: Chunk text
            chunker = self.chunker_factory.get_chunker(
                strategy=self.chunk_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            text_chunks = chunker.chunk(parsed_data.get("text", ""), base_metadata)

            # Step 6: Process table chunks
            table_chunks = []
            if tables:
                for table in tables:
                    table_chunk = self.table_extractor.convert_table_to_chunk(table)
                    # Add document metadata
                    table_chunk["metadata"].update(base_metadata)
                    table_chunk["metadata"]["chunk_id"] = str(
                        ChunkMetadata().chunk_id
                    )  # Generate new ID
                    table_chunks.append(table_chunk)

            # Step 7: Combine all chunks
            all_chunks = text_chunks + table_chunks

            # Step 8: Create metadata for all chunks
            processed_chunks = []
            for idx, chunk in enumerate(all_chunks):
                chunk_metadata = self.metadata_manager.create_metadata(
                    chunk.get("text", ""),
                    idx,
                    chunk.get("metadata", {}),
                    chunker_type=chunker.get_strategy_name(),
                )
                chunk["metadata"] = chunk_metadata.to_dict()
                processed_chunks.append(chunk)

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            result = {
                "document_id": document_id,
                "chunks": processed_chunks,
                "tables": tables,
                "metadata": {
                    **base_metadata,
                    "total_chunks": len(processed_chunks),
                    "text_chunks": len(text_chunks),
                    "table_chunks": len(table_chunks),
                    "processing_time": processing_time,
                    "processed_at": datetime.utcnow().isoformat(),
                },
                "processing_time": processing_time,
                "status": "success",
            }

            logger.info(
                f"Successfully processed document: {file_path} "
                f"({len(processed_chunks)} chunks, {processing_time:.2f}s)"
            )

            return result

        except ParserError as e:
            logger.error(f"Parser error processing {file_path}: {e}")
            return {
                "document_id": document_id,
                "chunks": [],
                "tables": [],
                "metadata": {},
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "status": "error",
                "error": str(e),
            }

        except ChunkingError as e:
            logger.error(f"Chunking error processing {file_path}: {e}")
            return {
                "document_id": document_id,
                "chunks": [],
                "tables": [],
                "metadata": {},
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "status": "error",
                "error": str(e),
            }

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
            return {
                "document_id": document_id,
                "chunks": [],
                "tables": [],
                "metadata": {},
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "status": "error",
                "error": str(e),
            }

    async def process_document_async(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Asynchronously process a document.

        Args:
            file_path: Path to document file
            document_id: Optional document identifier
            **kwargs: Additional arguments for process_document

        Returns:
            Processing results dictionary
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.process_document, file_path, document_id, **kwargs
        )

    def get_metadata_manager(self) -> ChunkMetadataManager:
        """
        Get the metadata manager instance.

        Returns:
            ChunkMetadataManager instance
        """
        return self.metadata_manager

