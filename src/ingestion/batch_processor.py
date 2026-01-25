"""Batch processor for processing multiple documents."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.ingestion.etl_pipeline import ETLPipeline
from src.config.logging_config import get_logger
from src.utils.file_utils import is_supported_file

logger = get_logger(__name__)


class BatchProcessor:
    """Batch processor for processing multiple documents."""

    def __init__(
        self,
        etl_pipeline: Optional[ETLPipeline] = None,
        max_workers: int = 4,
        use_async: bool = False,
    ):
        """
        Initialize batch processor.

        Args:
            etl_pipeline: ETL pipeline instance (creates new if None)
            max_workers: Maximum number of parallel workers
            use_async: Whether to use async processing
        """
        self.etl_pipeline = etl_pipeline or ETLPipeline()
        self.max_workers = max_workers
        self.use_async = use_async

    def process_directory(
        self,
        directory: Path,
        recursive: bool = True,
        file_pattern: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Process all supported files in a directory.

        Args:
            directory: Directory path to process
            recursive: Whether to process subdirectories
            file_pattern: Optional file pattern to match
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with batch processing results
        """
        start_time = datetime.utcnow()

        # Find all files
        files = self._find_files(directory, recursive, file_pattern)
        total_files = len(files)

        if total_files == 0:
            logger.warning(f"No supported files found in {directory}")
            return {
                "total_files": 0,
                "processed": 0,
                "failed": 0,
                "results": [],
                "processing_time": 0.0,
            }

        logger.info(f"Processing {total_files} files from {directory}")

        # Process files
        if self.use_async:
            results = self._process_files_async(files, progress_callback)
        else:
            results = self._process_files_parallel(files, progress_callback)

        # Calculate statistics
        processed = sum(1 for r in results if r.get("status") == "success")
        failed = total_files - processed

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        batch_result = {
            "total_files": total_files,
            "processed": processed,
            "failed": failed,
            "results": results,
            "processing_time": processing_time,
            "average_time_per_file": processing_time / total_files if total_files > 0 else 0,
        }

        logger.info(
            f"Batch processing complete: {processed}/{total_files} successful, "
            f"{processing_time:.2f}s total"
        )

        return batch_result

    def process_file_list(
        self,
        file_paths: List[Path],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Process a list of files.

        Args:
            file_paths: List of file paths to process
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with batch processing results
        """
        start_time = datetime.utcnow()

        # Filter to supported files
        files = [f for f in file_paths if is_supported_file(f) and f.exists()]

        if not files:
            logger.warning("No valid files to process")
            return {
                "total_files": len(file_paths),
                "processed": 0,
                "failed": 0,
                "results": [],
                "processing_time": 0.0,
            }

        logger.info(f"Processing {len(files)} files")

        # Process files
        if self.use_async:
            results = self._process_files_async(files, progress_callback)
        else:
            results = self._process_files_parallel(files, progress_callback)

        # Calculate statistics
        processed = sum(1 for r in results if r.get("status") == "success")
        failed = len(files) - processed

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "total_files": len(files),
            "processed": processed,
            "failed": failed,
            "results": results,
            "processing_time": processing_time,
            "average_time_per_file": processing_time / len(files) if files else 0,
        }

    def _find_files(
        self, directory: Path, recursive: bool, file_pattern: Optional[str]
    ) -> List[Path]:
        """
        Find all supported files in directory.

        Args:
            directory: Directory to search
            recursive: Whether to search recursively
            file_pattern: Optional file pattern

        Returns:
            List of file paths
        """
        files = []

        if recursive:
            pattern = "**/*" if not file_pattern else f"**/{file_pattern}"
            files = list(directory.glob(pattern))
        else:
            pattern = "*" if not file_pattern else file_pattern
            files = list(directory.glob(pattern))

        # Filter to supported files
        supported_files = [f for f in files if f.is_file() and is_supported_file(f)]

        return supported_files

    def _process_files_parallel(
        self,
        files: List[Path],
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> List[Dict[str, Any]]:
        """
        Process files in parallel using ThreadPoolExecutor.

        Args:
            files: List of files to process
            progress_callback: Optional progress callback

        Returns:
            List of processing results
        """
        results = []
        total = len(files)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.etl_pipeline.process_document, file_path): file_path
                for file_path in files
            }

            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    result["file_path"] = str(file_path)
                    results.append(result)
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, total)

                    logger.debug(f"Completed processing: {file_path}")

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                    results.append({
                        "file_path": str(file_path),
                        "status": "error",
                        "error": str(e),
                    })
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, total)

        return results

    async def _process_files_async(
        self,
        files: List[Path],
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> List[Dict[str, Any]]:
        """
        Process files asynchronously.

        Args:
            files: List of files to process
            progress_callback: Optional progress callback

        Returns:
            List of processing results
        """
        tasks = [
            self.etl_pipeline.process_document_async(file_path) for file_path in files
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing {files[idx]}: {result}")
                processed_results.append({
                    "file_path": str(files[idx]),
                    "status": "error",
                    "error": str(result),
                })
            else:
                result["file_path"] = str(files[idx])
                processed_results.append(result)

            if progress_callback:
                progress_callback(len(processed_results), len(files))

        return processed_results

    def generate_report(self, batch_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable processing report.

        Args:
            batch_result: Batch processing results

        Returns:
            Report string
        """
        report_lines = [
            "=" * 60,
            "Batch Processing Report",
            "=" * 60,
            f"Total Files: {batch_result['total_files']}",
            f"Successfully Processed: {batch_result['processed']}",
            f"Failed: {batch_result['failed']}",
            f"Total Processing Time: {batch_result['processing_time']:.2f}s",
            f"Average Time per File: {batch_result.get('average_time_per_file', 0):.2f}s",
            "",
        ]

        # Add failed files if any
        failed_files = [
            r for r in batch_result["results"] if r.get("status") != "success"
        ]
        if failed_files:
            report_lines.extend([
                "Failed Files:",
                "-" * 60,
            ])
            for result in failed_files:
                report_lines.append(f"  - {result.get('file_path', 'unknown')}")
                if "error" in result:
                    report_lines.append(f"    Error: {result['error']}")

        report_lines.append("=" * 60)

        return "\n".join(report_lines)

