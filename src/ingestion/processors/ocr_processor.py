"""OCR processor for scanned documents."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile
import shutil

from src.config.logging_config import get_logger

logger = get_logger(__name__)

# Try to import OCR libraries
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract/PIL not available, OCR will not work")

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available, PDF OCR will be limited")


class OCRProcessor:
    """OCR processor for extracting text from scanned documents and images."""

    def __init__(self, ocr_language: str = "eng", ocr_config: Optional[str] = None):
        """
        Initialize OCR processor.

        Args:
            ocr_language: OCR language code (e.g., 'eng', 'spa')
            ocr_config: Tesseract OCR configuration string
        """
        self.ocr_language = ocr_language
        self.ocr_config = ocr_config or "--psm 6"
        self._check_tesseract_availability()

    def _check_tesseract_availability(self) -> None:
        """Check if Tesseract OCR is available."""
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract OCR not available")
            return

        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR version: {version}")
        except Exception as e:
            logger.warning(f"Tesseract OCR not properly configured: {e}")

    def process_pdf(self, pdf_path: Path, dpi: int = 300) -> Dict[str, Any]:
        """
        Process PDF file with OCR.

        Args:
            pdf_path: Path to PDF file
            dpi: DPI for image conversion

        Returns:
            Dictionary with OCR results
        """
        if not TESSERACT_AVAILABLE:
            raise ValueError("Tesseract OCR is not available")

        if not PDF2IMAGE_AVAILABLE:
            logger.warning("pdf2image not available, cannot process PDF")
            return {"text": "", "pages": [], "error": "pdf2image not available"}

        try:
            logger.info(f"Processing PDF with OCR: {pdf_path}")

            # Convert PDF to images
            images = pdf2image.convert_from_path(str(pdf_path), dpi=dpi)
            logger.info(f"Converted PDF to {len(images)} images")

            # Process each page
            all_text = []
            page_results = []

            for page_num, image in enumerate(images, 1):
                try:
                    page_text = self._process_image(image, page_num)
                    all_text.append(page_text)
                    page_results.append({
                        "page": page_num,
                        "text": page_text,
                        "confidence": 0.8,  # Placeholder
                    })
                except Exception as e:
                    logger.warning(f"Error processing page {page_num}: {e}")
                    page_results.append({
                        "page": page_num,
                        "text": "",
                        "error": str(e),
                    })

            full_text = "\n\n".join(all_text)

            return {
                "text": full_text,
                "pages": page_results,
                "page_count": len(images),
                "ocr_processed": True,
            }

        except Exception as e:
            logger.error(f"Error processing PDF with OCR: {e}", exc_info=True)
            return {
                "text": "",
                "pages": [],
                "error": str(e),
                "ocr_processed": False,
            }

    def process_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Process image file with OCR.

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with OCR results
        """
        if not TESSERACT_AVAILABLE:
            raise ValueError("Tesseract OCR is not available")

        try:
            logger.info(f"Processing image with OCR: {image_path}")

            # Open image
            image = Image.open(str(image_path))

            # Process image
            text = self._process_image(image, 1)

            return {
                "text": text,
                "ocr_processed": True,
                "confidence": 0.8,  # Placeholder
            }

        except Exception as e:
            logger.error(f"Error processing image with OCR: {e}", exc_info=True)
            return {
                "text": "",
                "error": str(e),
                "ocr_processed": False,
            }

    def _process_image(self, image: "Image.Image", page_num: int) -> str:
        """
        Process a single image with OCR.

        Args:
            image: PIL Image object
            page_num: Page number for logging

        Returns:
            Extracted text
        """
        try:
            # Run OCR
            text = pytesseract.image_to_string(
                image,
                lang=self.ocr_language,
                config=self.ocr_config,
            )

            # Post-process text
            text = self._post_process_ocr_text(text)

            logger.debug(f"Extracted {len(text)} characters from page {page_num}")
            return text

        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            return ""

    def _post_process_ocr_text(self, text: str) -> str:
        """
        Post-process OCR text to clean it up.

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Remove lines with only whitespace or very short lines
            cleaned_line = line.strip()
            if cleaned_line and len(cleaned_line) > 2:
                cleaned_lines.append(cleaned_line)

        # Join lines
        cleaned_text = "\n".join(cleaned_lines)

        # Fix common OCR errors
        # Add more specific fixes as needed
        cleaned_text = cleaned_text.replace("|", "I")  # Common OCR error
        cleaned_text = cleaned_text.replace("0", "O")  # Context-dependent, use carefully

        return cleaned_text

    def merge_ocr_with_existing_text(
        self, existing_text: str, ocr_text: str, strategy: str = "append"
    ) -> str:
        """
        Merge OCR text with existing extracted text.

        Args:
            existing_text: Text already extracted from document
            ocr_text: Text extracted via OCR
            strategy: Merge strategy ('append', 'replace', 'smart')

        Returns:
            Merged text
        """
        if strategy == "replace":
            return ocr_text
        elif strategy == "append":
            if existing_text:
                return f"{existing_text}\n\n--- OCR Text ---\n\n{ocr_text}"
            return ocr_text
        elif strategy == "smart":
            # Smart merge: only add OCR text if existing text is very short
            if len(existing_text) < 100:
                return f"{existing_text}\n\n{ocr_text}" if existing_text else ocr_text
            return existing_text
        else:
            return existing_text

    def extract_images_from_pdf(self, pdf_path: Path, output_dir: Optional[Path] = None) -> List[Path]:
        """
        Extract images from PDF for OCR processing.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save extracted images

        Returns:
            List of paths to extracted images
        """
        if not PDF2IMAGE_AVAILABLE:
            logger.warning("pdf2image not available")
            return []

        try:
            if output_dir is None:
                output_dir = Path(tempfile.mkdtemp())

            output_dir.mkdir(parents=True, exist_ok=True)

            # Convert PDF to images
            images = pdf2image.convert_from_path(str(pdf_path))

            image_paths = []
            for idx, image in enumerate(images):
                image_path = output_dir / f"page_{idx + 1}.png"
                image.save(str(image_path), "PNG")
                image_paths.append(image_path)

            logger.info(f"Extracted {len(image_paths)} images from PDF")
            return image_paths

        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}", exc_info=True)
            return []

