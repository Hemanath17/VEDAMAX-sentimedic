export interface IngestResponse {
  document_id: string;
  filename: string;
  chunk_count: number;
  status: string;
  message: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class IngestApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function uploadDocument(
  file: File,
  userId: string,
): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);

  const response = await fetch(`${API_BASE_URL}/ingest`, {
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
    throw new IngestApiError(detail, response.status);
  }

  return response.json() as Promise<IngestResponse>;
}
