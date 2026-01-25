"""Table extractor for medical documents."""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
import json
import csv
from io import StringIO

from src.config.logging_config import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    import pandas as pd

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None  # type: ignore
    logger.warning("pandas not available, table processing will be limited")


class TableExtractor:
    """Extract and process tables from parsed documents."""

    def __init__(self, preserve_structure: bool = True):
        """
        Initialize table extractor.

        Args:
            preserve_structure: Whether to preserve table structure (rows/columns)
        """
        self.preserve_structure = preserve_structure

    def extract_tables(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tables from parsed document data.

        Args:
            parsed_data: Dictionary from parser containing 'tables' key

        Returns:
            List of extracted and processed tables
        """
        tables = parsed_data.get("tables", [])
        if not tables:
            logger.debug("No tables found in parsed data")
            return []

        extracted_tables = []
        for idx, table in enumerate(tables):
            try:
                processed_table = self._process_table(table, idx)
                if processed_table:
                    extracted_tables.append(processed_table)
            except Exception as e:
                logger.warning(f"Error processing table {idx}: {e}")
                continue

        logger.info(f"Extracted {len(extracted_tables)} tables from document")
        return extracted_tables

    def _process_table(self, table: Any, table_index: int) -> Optional[Dict[str, Any]]:
        """
        Process a single table.

        Args:
            table: Table data (can be dict, list, or other format)
            table_index: Index of table in document

        Returns:
            Processed table dictionary or None
        """
        try:
            # Handle different table formats
            if isinstance(table, dict):
                return self._process_dict_table(table, table_index)
            elif isinstance(table, list):
                return self._process_list_table(table, table_index)
            elif PANDAS_AVAILABLE and isinstance(table, pd.DataFrame):
                return self._process_dataframe_table(table, table_index)
            else:
                # Try to convert to string
                table_text = str(table)
                return self._process_text_table(table_text, table_index)

        except Exception as e:
            logger.error(f"Error processing table {table_index}: {e}", exc_info=True)
            return None

    def _process_dict_table(self, table: Dict[str, Any], table_index: int) -> Dict[str, Any]:
        """Process table in dictionary format."""
        result = {
            "table_id": f"table_{table_index}",
            "table_index": table_index,
            "type": "structured",
        }

        # Handle different dict structures
        if "rows" in table:
            rows = table["rows"]
            result["rows"] = rows
            result["row_count"] = len(rows)
            result["column_count"] = len(rows[0]) if rows else 0

            # Extract header if available
            if "header_row" in table:
                result["headers"] = table["header_row"]
            elif rows:
                # Use first row as header if it looks like headers
                first_row = rows[0]
                if all(isinstance(cell, str) and len(cell) < 50 for cell in first_row):
                    result["headers"] = first_row
                    result["data_rows"] = rows[1:]
                else:
                    result["data_rows"] = rows

            # Convert to text format
            result["text"] = self._table_to_text(rows, result.get("headers"))

        elif "text" in table:
            result["text"] = table["text"]
            result["type"] = "text"

        else:
            # Try to extract any data
            result["raw_data"] = table
            result["text"] = json.dumps(table, indent=2)

        return result

    def _process_list_table(self, table: List, table_index: int) -> Dict[str, Any]:
        """Process table in list format (list of rows)."""
        if not table:
            return None

        result = {
            "table_id": f"table_{table_index}",
            "table_index": table_index,
            "type": "structured",
            "rows": table,
            "row_count": len(table),
            "column_count": len(table[0]) if table else 0,
        }

        # Convert to text
        result["text"] = self._table_to_text(table)

        return result

    def _process_dataframe_table(self, table: Any, table_index: int) -> Dict[str, Any]:  # pd.DataFrame when available
        """Process pandas DataFrame table."""
        result = {
            "table_id": f"table_{table_index}",
            "table_index": table_index,
            "type": "dataframe",
            "row_count": len(table),
            "column_count": len(table.columns),
            "headers": table.columns.tolist(),
        }

        # Convert to rows
        result["rows"] = table.values.tolist()
        result["data_rows"] = result["rows"]

        # Convert to text
        result["text"] = self._dataframe_to_text(table)

        return result

    def _process_text_table(self, table_text: str, table_index: int) -> Dict[str, Any]:
        """Process table as plain text."""
        return {
            "table_id": f"table_{table_index}",
            "table_index": table_index,
            "type": "text",
            "text": table_text,
        }

    def _table_to_text(self, rows: List[List[Any]], headers: Optional[List[str]] = None) -> str:
        """
        Convert table rows to readable text format.

        Args:
            rows: List of table rows
            headers: Optional header row

        Returns:
            Text representation of table
        """
        if not rows:
            return ""

        text_parts = []

        # Add headers if available
        if headers:
            header_text = " | ".join(str(h) for h in headers)
            text_parts.append(header_text)
            text_parts.append("-" * len(header_text))

        # Add rows
        for row in rows:
            row_text = " | ".join(str(cell) for cell in row)
            text_parts.append(row_text)

        return "\n".join(text_parts)

    def _dataframe_to_text(self, df: Any) -> str:  # pd.DataFrame when available
        """Convert pandas DataFrame to text."""
        if not PANDAS_AVAILABLE:
            return str(df)

        # Convert to CSV string
        output = StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    def identify_medical_table_type(self, table: Dict[str, Any]) -> Optional[str]:
        """
        Identify the type of medical table (lab results, vitals, medications, etc.).

        Args:
            table: Processed table dictionary

        Returns:
            Table type identifier or None
        """
        text = table.get("text", "").lower()
        headers = table.get("headers", [])

        # Check for lab results
        lab_keywords = ["glucose", "cholesterol", "hemoglobin", "wbc", "rbc", "platelet"]
        if any(keyword in text for keyword in lab_keywords):
            return "lab_results"

        # Check for vital signs
        vital_keywords = ["blood pressure", "heart rate", "temperature", "respiratory"]
        if any(keyword in text for keyword in vital_keywords):
            return "vital_signs"

        # Check for medications
        med_keywords = ["medication", "dosage", "frequency", "prescription"]
        if any(keyword in text for keyword in med_keywords):
            return "medications"

        # Check for allergies
        allergy_keywords = ["allergy", "allergen", "reaction"]
        if any(keyword in text for keyword in allergy_keywords):
            return "allergies"

        return None

    def convert_table_to_chunk(self, table: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a table to a chunk format for vector storage.

        Args:
            table: Processed table dictionary

        Returns:
            Chunk dictionary with table data
        """
        chunk = {
            "text": table.get("text", ""),
            "metadata": {
                "chunk_type": "table",
                "table_id": table.get("table_id"),
                "table_index": table.get("table_index"),
                "table_type": table.get("type"),
                "medical_table_type": self.identify_medical_table_type(table),
                "row_count": table.get("row_count"),
                "column_count": table.get("column_count"),
            },
        }

        # Add structured data if available
        if "rows" in table:
            chunk["metadata"]["has_structured_data"] = True

        return chunk

