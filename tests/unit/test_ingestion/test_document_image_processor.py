"""
Tests for src/ingestion/processors/document_image_processor.py

Coverage:
- _fix_ocr_digit_confusion: targeted O/0 correction in numeric contexts
- _safe_clean: whitespace cleanup without digit corruption
- process_uploaded_image: document detection + pipeline integration
  - lab report image -> is_document=True, numerics correct
  - non-document image -> is_document=False, safe fallback
  - missing Tesseract -> is_document=False, informative error
  - OCR exception -> is_document=False, no crash

Run:
    pytest tests/unit/test_ingestion/test_document_image_processor.py -v
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.processors.document_image_processor import (
    TESSERACT_AVAILABLE,
    _fix_ocr_digit_confusion,
    _safe_clean,
    process_uploaded_image,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LAB_REPORT_IMAGE = Path("tests/fixtures/images/sample_lab_report.png")
NON_DOCUMENT_IMAGE = Path("tests/fixtures/images/sample_non_document.png")


# ---------------------------------------------------------------------------
# Unit: _fix_ocr_digit_confusion
# ---------------------------------------------------------------------------


class TestFixOcrDigitConfusion:

    def test_simple_trailing_O(self):
        """18O -> 180 -- the most common Tesseract error on lab reports."""
        assert _fix_ocr_digit_confusion("18O mg/dL") == "180 mg/dL"

    def test_multiple_trailing_Os(self):
        """21OO -> 2100 -- multiple consecutive O replacements."""
        assert _fix_ocr_digit_confusion("21OO units") == "2100 units"

    def test_range_with_O_confusion(self):
        """7O-99 -> 70-99 -- reference range OCR error."""
        assert _fix_ocr_digit_confusion("7O-99 mg/dL") == "70-99 mg/dL"

    def test_multiple_values_in_one_string(self):
        """Multiple corrections in a single line."""
        result = _fix_ocr_digit_confusion("18O mg/dL 7O-99 mg/dL. HIGH")
        assert "18O" not in result
        assert "7O-" not in result
        assert "180" in result
        assert "70" in result

    def test_real_words_untouched(self):
        """HIGH, LOW, mg/dL -- standalone words must not be changed."""
        original = "HIGH LOW NORMAL mg/dL mmol/L"
        assert _fix_ocr_digit_confusion(original) == original

    def test_medical_abbreviations_untouched(self):
        """Alc (for HbA1c), HDL, LDL -- abbreviations must survive."""
        original = "Hemoglobin Alc HDL LDL"
        assert _fix_ocr_digit_confusion(original) == original

    def test_no_digits_adjacent_to_O(self):
        """Lone O not adjacent to digits is untouched."""
        assert _fix_ocr_digit_confusion("O positive blood type") == "O positive blood type"

    def test_210_cholesterol(self):
        """21O -> 210 -- real value from the synthetic lab report."""
        assert _fix_ocr_digit_confusion("21O mg/dL") == "210 mg/dL"

    def test_empty_string(self):
        assert _fix_ocr_digit_confusion("") == ""

    def test_no_correction_needed(self):
        """String with correct digits is passed through unchanged."""
        clean = "Glucose 180 mg/dL 70-99 mg/dL"
        assert _fix_ocr_digit_confusion(clean) == clean


# ---------------------------------------------------------------------------
# Unit: _safe_clean
# ---------------------------------------------------------------------------


class TestSafeClean:

    def test_strips_whitespace(self):
        result = _safe_clean("  hello  \n  world  ")
        assert result == "hello\nworld"

    def test_removes_single_char_lines(self):
        """Single character lines (stray OCR noise) are dropped."""
        result = _safe_clean("a\nhello\nb\nworld")
        assert "hello" in result
        assert "world" in result

    def test_zero_not_replaced_with_O(self):
        """The old dangerous replacement must NOT be present."""
        result = _safe_clean("Glucose 180 mg/dL")
        assert "18O" not in result
        assert "180" in result

    def test_pipe_not_replaced_with_I(self):
        """The second old dangerous replacement must NOT be present."""
        result = _safe_clean("A | B")
        assert "A | B" in result

    def test_empty_string(self):
        assert _safe_clean("") == ""


# ---------------------------------------------------------------------------
# Integration: process_uploaded_image against real fixture images
# (requires Tesseract installed + fixture images present)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not Path("tests/fixtures/images/sample_lab_report.png").exists(),
    reason="Fixture image not present (run scripts/generate_test_fixtures.py first)",
)
@pytest.mark.skipif(
    not TESSERACT_AVAILABLE,
    reason="Tesseract OCR not installed in this environment",
)
class TestProcessUploadedImageIntegration:

    def test_lab_report_classified_as_document(self):
        result = process_uploaded_image(LAB_REPORT_IMAGE)
        assert result.is_document is True
        assert result.error is None

    def test_lab_report_extracts_meaningful_text(self):
        result = process_uploaded_image(LAB_REPORT_IMAGE)
        assert result.token_count >= 20
        assert len(result.text) > 50

    def test_glucose_180_not_corrupted(self):
        """The critical safety check: 180 must survive as 180, not 18O."""
        result = process_uploaded_image(LAB_REPORT_IMAGE)
        assert "18O" not in result.text, "OCR O/0 corruption reached stored text"
        assert "180" in result.text, "Glucose value 180 was not extracted"

    def test_all_key_numeric_values_present(self):
        """Every clinical value on the synthetic report must be readable."""
        result = process_uploaded_image(LAB_REPORT_IMAGE)
        required = ["180", "7.2", "210", "130", "38", "150", "140", "4.1"]
        missing = [v for v in required if v not in result.text]
        assert not missing, f"Missing clinical values after OCR: {missing}"

    def test_no_digit_corruption_in_reference_ranges(self):
        """Reference range '70-99' must not become '7O-99'."""
        result = process_uploaded_image(LAB_REPORT_IMAGE)
        assert "7O" not in result.text
        assert "70" in result.text

    def test_non_document_image_classified_correctly(self):
        result = process_uploaded_image(NON_DOCUMENT_IMAGE)
        assert result.is_document is False

    def test_non_document_has_minimal_tokens(self):
        result = process_uploaded_image(NON_DOCUMENT_IMAGE)
        assert result.token_count < 8


# ---------------------------------------------------------------------------
# Unit: process_uploaded_image with mocked OCR
# (these run without Tesseract or fixture images)
# ---------------------------------------------------------------------------


class TestProcessUploadedImageMocked:

    def test_returns_not_a_document_when_tesseract_unavailable(self, tmp_path):
        dummy = tmp_path / "test.png"
        dummy.write_bytes(b"fake image data")
        with patch(
            "src.ingestion.processors.document_image_processor.TESSERACT_AVAILABLE",
            False,
        ):
            result = process_uploaded_image(dummy)
        assert result.is_document is False
        assert result.error is not None
        assert "not available" in result.error.lower()

    def test_ocr_exception_returns_safe_result(self, tmp_path):
        """If OCR itself throws, we must not crash -- return is_document=False."""
        dummy = tmp_path / "test.png"
        dummy.write_bytes(b"fake image data")
        with patch(
            "src.ingestion.processors.document_image_processor.TESSERACT_AVAILABLE",
            True,
        ):
            mock_processor = MagicMock()
            mock_processor.process_image.side_effect = RuntimeError("tesseract crashed")
            with patch(
                "src.ingestion.processors.document_image_processor.OCRProcessor",
                return_value=mock_processor,
            ):
                result = process_uploaded_image(dummy)
        assert result.is_document is False
        assert result.error is not None

    def test_short_extracted_text_is_not_a_document(self, tmp_path):
        """Very little text -> is_document=False regardless of error state."""
        dummy = tmp_path / "test.png"
        dummy.write_bytes(b"fake image data")
        with patch(
            "src.ingestion.processors.document_image_processor.TESSERACT_AVAILABLE",
            True,
        ):
            mock_processor = MagicMock()
            mock_processor.process_image.return_value = {"text": "hi"}
            with patch(
                "src.ingestion.processors.document_image_processor.OCRProcessor",
                return_value=mock_processor,
            ):
                result = process_uploaded_image(dummy)
        assert result.is_document is False

    def test_rich_text_extracted_is_a_document(self, tmp_path):
        """Sufficient real text -> is_document=True."""
        dummy = tmp_path / "test.png"
        dummy.write_bytes(b"fake image data")
        rich_text = (
            "Patient Name: Jane Doe\n"
            "Glucose Fasting 180 mg/dL HIGH\n"
            "HbA1c 7.2% HIGH\n"
            "Cholesterol 210 mg/dL HIGH\n"
            "Ordered by Dr. Smith\n"
        )
        with patch(
            "src.ingestion.processors.document_image_processor.TESSERACT_AVAILABLE",
            True,
        ):
            mock_processor = MagicMock()
            mock_processor.process_image.return_value = {"text": rich_text}
            with patch(
                "src.ingestion.processors.document_image_processor.OCRProcessor",
                return_value=mock_processor,
            ):
                result = process_uploaded_image(dummy)
        assert result.is_document is True
        assert "180" in result.text
        assert "18O" not in result.text
