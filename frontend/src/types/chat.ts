// Mirrors the FastAPI QueryResponse shape exactly (src/api/routes/query.py)

export type TriageLevel = "emergency" | "distressed" | "routine";

export interface Citation {
  marker: string;
  source_ref: string;
  corpus: "kb" | "user_doc";
}

export interface QueryRequest {
  question: string;
  user_id?: string | null;
  risk_level?: number;
  session_summary?: string | null;
}

export interface QueryResponse {
  answer: string;
  triage_level: TriageLevel;
  citations: Citation[];
  disclaimer: string;
  flagged_numbers: string[];
}

export type MessageRole = "user" | "assistant" | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  triageLevel?: TriageLevel;
  citations?: Citation[];
  disclaimer?: string;
  flaggedNumbers?: string[];
  timestamp: number;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}
