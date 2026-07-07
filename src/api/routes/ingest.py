"""Document ingestion route: upload a file, parse/chunk, store in user_documents."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.config.logging_config import get_logger
from src.ingestion.etl_pipeline import ETLPipeline
from src.ingestion.parsers.parser_factory import get_parser_factory
from src.retrieval.vector_store.vector_store import VectorStore
from src.utils.file_utils import get_file_extension

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    status: str
    message: str


def _validate_user_id(user_id: Optional[str]) -> str:
    cleaned = (user_id or "").strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="user_id is required.")
    if len(cleaned) > 128:
        raise HTTPException(status_code=422, detail="user_id is too long.")
    return cleaned


@router.post("", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
) -> IngestResponse:
    """Upload a medical document, run ETL, and index chunks for this user."""
    normalized_user_id = _validate_user_id(user_id)

    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required.")

    extension = get_file_extension(Path(file.filename))
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{extension}'. Allowed: PDF, DOCX.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"File too large (max {MAX_FILE_BYTES // (1024 * 1024)} MB).",
        )

    suffix = extension
    tmp_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = Path(tmp.name)

        if not get_parser_factory().is_supported(tmp_path):
            raise HTTPException(status_code=422, detail="Unsupported file type.")

        pipeline = ETLPipeline(chunk_strategy="semantic")
        result = pipeline.process_document(
            tmp_path,
            metadata={
                "corpus": "user_doc",
                "user_id": normalized_user_id,
            },
        )

        if result.get("status") != "success":
            error = result.get("error", "Document processing failed.")
            raise HTTPException(status_code=422, detail=str(error))

        chunks = result.get("chunks", [])
        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from this document.",
            )

        store = VectorStore()
        store.store_chunks(chunks, corpus="user_doc", user_id=normalized_user_id)

        document_id = result.get("document_id", "")
        chunk_count = len(chunks)
        logger.info(
            "Ingested document %s for user %s (%s chunks)",
            file.filename,
            normalized_user_id,
            chunk_count,
        )

        return IngestResponse(
            document_id=document_id,
            filename=file.filename,
            chunk_count=chunk_count,
            status="success",
            message=(
                f"Uploaded {file.filename} ({chunk_count} sections indexed). "
                "You can now ask questions about this document."
            ),
        )
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
