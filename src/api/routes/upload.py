"""Upload route: accepts an image (e.g. a photo of a lab report), runs OCR,
and either stores it as a user document or returns a safe non-diagnostic
fallback if the image doesn't look like a document at all."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.ingestion.processors.document_image_processor import process_uploaded_image
from src.retrieval.vector_store.vector_store import VectorStore
from src.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

_store = VectorStore()

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Shown when an uploaded image does not look like a document. Deliberately
# makes NO claim about having examined the image's visual content -- we
# never interpret wounds, rashes, scans, or other physical/medical images.
NOT_A_DOCUMENT_MESSAGE = (
    "I can see you've uploaded an image, but I'm not able to examine wounds, "
    "rashes, scans, or other physical symptoms directly from a photo. "
    "If you're injured, please consider basic first aid (clean the area, "
    "apply pressure to stop bleeding, keep it covered) and see a doctor or "
    "urgent care promptly -- especially if it's deep, won't stop bleeding, "
    "or shows signs of infection (increasing redness, warmth, swelling, or "
    "pus). If you'd like general health information, feel free to ask me a "
    "question in text, or upload a clear photo of a lab report or document "
    "and I can help you understand it."
)


class UploadResponse(BaseModel):
    is_document: bool
    message: str
    document_id: str | None = None
    chunks_stored: int = 0


@router.post("", response_model=UploadResponse)
async def upload_image(
    user_id: str = Form(...),
    file: UploadFile = File(...),
) -> UploadResponse:
    """Accept an image upload, OCR it, and store or fall back accordingly."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="File too large (max 10 MB).")
    if len(contents) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / (file.filename or "upload.png")
        with tmp_path.open("wb") as f:
            f.write(contents)

        result = process_uploaded_image(tmp_path)

    if not result.is_document:
        logger.info(f"Upload from user_id={user_id} classified as non-document image")
        return UploadResponse(is_document=False, message=NOT_A_DOCUMENT_MESSAGE)

    document_id = f"upload-{user_id}-{file.filename or 'image'}".replace(" ", "_")
    chunk = {
        "text": result.text,
        "chunk_id": f"{document_id}_0",
        "metadata": {
            "document_id": document_id,
            "source": "ocr_upload",
            "chunk_type": "text",
        },
    }

    try:
        _store.store_chunks([chunk], corpus="user_doc", user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to store OCR'd chunk for user_id={user_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to store the uploaded document.")

    return UploadResponse(
        is_document=True,
        message="Document received and processed. You can now ask me about it.",
        document_id=document_id,
        chunks_stored=1,
    )
