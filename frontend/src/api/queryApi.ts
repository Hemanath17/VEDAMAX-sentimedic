import type { QueryRequest, QueryResponse } from "../types/chat";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/**
 * Calls the backend /query endpoint. Throws ApiError on non-2xx responses
 * (including 422 validation errors and 429 rate-limit responses) so the
 * caller can show a specific message rather than a generic failure.
 */
export async function sendQuery(request: QueryRequest): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response body wasn't JSON; keep the generic message
    }
    throw new ApiError(detail, response.status);
  }

  return response.json() as Promise<QueryResponse>;
}
