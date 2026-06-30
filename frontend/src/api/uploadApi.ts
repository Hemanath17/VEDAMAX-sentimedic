/**
 * Calls the /upload endpoint for image files (PNG, JPG, WEBP).
 * OCR runs on the backend; the extracted text is stored as a user_doc chunk.
 * Distinct from ingestApi.ts which handles PDF/DOCX via the ETL pipeline.
 */

export interface UploadResponse {
  is_document: boolean;
  message: string;
  document_id: string | null;
  chunks_stored: number;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class UploadApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function uploadImage(
  file: File,
  userId: string,
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let detail = `Upload failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // keep generic message
    }
    throw new UploadApiError(detail, response.status);
  }

  return response.json() as Promise<UploadResponse>;
}
