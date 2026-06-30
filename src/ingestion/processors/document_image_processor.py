"""
Document image processor: wraps the existing OCRProcessor to safely extract
text from photographed documents (lab reports, printed results), while
detecting and routing away from non-document images (wounds, rashes, scans)
that OCR cannot meaningfully process.

This module exists because of two real findings:
1. OCRProcessor._post_process_ocr_text() blindly replaces every "0" with
   "O" and every "|" with "I" -- this corrupts numeric lab values (e.g.
   "180 mg/dL" becomes "18O mg/dL") and must never be used on medical
   numeric content. We bypass it entirely here.
2. OCR run on a non-document image (a wound photo, a rash) extracts little
   or no real text. That absence is a genuine signal -- not something to
   ignore, but something to route on: if it doesn't look like a document,
   we never claim to have visually interpreted the image. We fall back to
   general grounded guidance instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.ingestion.processors.ocr_processor import OCRProcessor, TESSERACT_AVAILABLE
from src.config.logging_config import get_logger

logger = get_logger(__name__)

# Below this many real word-like tokens, an image is treated as "not a
# document" rather than "a document OCR struggled with". This is
# deliberately about DETECTING DOCUMENT-NESS, not about scoring OCR
# confidence/quality -- a real document with poor OCR still has SOME
# extractable structure; a photo of a wound has essentially none.
MIN_TOKENS_FOR_DOCUMENT = 8

_WORD_PATTERN = re.compile(r"[A-Za-z]{2,}")

_NUMERIC_O_PATTERN = re.compile(r"\b(\d+)([O]+)(\d*)\b")


def _fix_ocr_digit_confusion(text: str) -> str:
    """
    Correct Tesseract's O/0 confusion in numeric contexts only.

    Tesseract frequently reads the digit zero as the letter O in
    high-contrast printed text. This is a targeted correction:
    only tokens that look like partially-numeric strings (digits
    mixed with capital O) are corrected. Standalone words and
    medical abbreviations are never touched.

    Examples:
      "18O mg/dL"  ->  "180 mg/dL"
      "7O-99"      ->  "70-99"
      "21O mg/dL"  ->  "210 mg/dL"
      "HIGH"       ->  "HIGH"       (untouched -- no digits adjacent)
      "Alc"        ->  "Alc"        (untouched)
    """
    return _NUMERIC_O_PATTERN.sub(
        lambda m: m.group(1) + ("0" * len(m.group(2))) + m.group(3),
        text,
    )


@dataclass
class ImageProcessingResult:
    is_document: bool
    text: str
    token_count: int
    error: Optional[str] = None


def _safe_clean(raw_text: str) -> str:
    """
    Whitespace/junk cleanup ONLY. Deliberately does NOT include the
    digit-corrupting replacements from OCRProcessor._post_process_ocr_text
    (no "0" -> "O", no "|" -> "I"). Those are unsafe for medical numeric
    content and are never applied here.
    """
    if not raw_text:
        return ""
    lines = [line.strip() for line in raw_text.split("\n")]
    lines = [line for line in lines if len(line) > 1]
    return "\n".join(lines)


def process_uploaded_image(image_path: Path) -> ImageProcessingResult:
    """
    Run OCR on an uploaded image and classify it as a document or not.

    Returns is_document=False (with whatever little text was found, if any)
    when the image does not look like a document -- callers MUST use this
    to route to a safe, non-visual fallback rather than attempting to
    interpret the image's actual visual content.
    """
    if not TESSERACT_AVAILABLE:
        return ImageProcessingResult(
            is_document=False,
            text="",
            token_count=0,
            error="OCR is not available in this environment.",
        )

    processor = OCRProcessor()
    try:
        raw_result = processor.process_image(image_path)
    except Exception as exc:  # noqa: BLE001 -- never let OCR failure crash the upload
        logger.error(f"OCR processing failed for {image_path}: {exc}")
        return ImageProcessingResult(is_document=False, text="", token_count=0, error=str(exc))

    raw_text = raw_result.get("text", "")
    cleaned = _safe_clean(raw_text)
    cleaned = _fix_ocr_digit_confusion(cleaned)
    token_count = len(_WORD_PATTERN.findall(cleaned))

    is_document = token_count >= MIN_TOKENS_FOR_DOCUMENT

    logger.info(
        f"Processed image {image_path.name}: {token_count} word-like tokens, "
        f"classified as {'document' if is_document else 'NOT a document'}"
    )

    return ImageProcessingResult(
        is_document=is_document,
        text=cleaned,
        token_count=token_count,
    )
