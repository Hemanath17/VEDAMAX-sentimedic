"""Integration tests for table extractor."""

import pytest
from src.ingestion.processors.table_extractor import TableExtractor


class TestTableExtractor:
    """Integration tests for table extractor."""

    @pytest.fixture
    def table_extractor(self):
        """Create table extractor instance."""
        return TableExtractor()

    def test_extract_tables_empty(self, table_extractor):
        """Test extracting tables from empty parsed data."""
        parsed_data = {"text": "Some text", "tables": []}
        tables = table_extractor.extract_tables(parsed_data)
        assert tables == []

    def test_extract_tables_dict_format(self, table_extractor):
        """Test extracting tables in dictionary format."""
        parsed_data = {
            "text": "Some text",
            "tables": [
                {
                    "rows": [
                        ["Header1", "Header2"],
                        ["Value1", "Value2"],
                    ],
                    "header_row": ["Header1", "Header2"],
                }
            ],
        }
        tables = table_extractor.extract_tables(parsed_data)
        assert len(tables) == 1
        assert tables[0]["type"] == "structured"
        assert "rows" in tables[0]

    def test_extract_tables_list_format(self, table_extractor):
        """Test extracting tables in list format."""
        parsed_data = {
            "text": "Some text",
            "tables": [
                [
                    ["Header1", "Header2"],
                    ["Value1", "Value2"],
                ]
            ],
        }
        tables = table_extractor.extract_tables(parsed_data)
        assert len(tables) == 1

    def test_identify_medical_table_type_lab_results(self, table_extractor):
        """Test identifying lab results table."""
        table = {
            "text": "Glucose: 100 mg/dL\nCholesterol: 200 mg/dL",
            "headers": ["Test", "Value"],
        }
        table_type = table_extractor.identify_medical_table_type(table)
        assert table_type == "lab_results"

    def test_identify_medical_table_type_vital_signs(self, table_extractor):
        """Test identifying vital signs table."""
        table = {
            "text": "Blood Pressure: 120/80\nHeart Rate: 72 bpm",
            "headers": ["Vital", "Value"],
        }
        table_type = table_extractor.identify_medical_table_type(table)
        assert table_type == "vital_signs"

    def test_convert_table_to_chunk(self, table_extractor):
        """Test converting table to chunk format."""
        table = {
            "table_id": "table_1",
            "table_index": 0,
            "text": "Header1 | Header2\nValue1 | Value2",
            "type": "structured",
            "row_count": 2,
            "column_count": 2,
        }
        chunk = table_extractor.convert_table_to_chunk(table)
        assert "text" in chunk
        assert "metadata" in chunk
        assert chunk["metadata"]["chunk_type"] == "table"
        assert chunk["metadata"]["table_id"] == "table_1"

