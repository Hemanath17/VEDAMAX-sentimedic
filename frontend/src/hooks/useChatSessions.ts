import { useCallback, useEffect, useMemo, useState } from "react";
import { uploadDocument, IngestApiError } from "../api/ingestApi";
import { uploadImage, UploadApiError } from "../api/uploadApi";
import { sendQuery, ApiError } from "../api/queryApi";
import type { ChatMessage, ChatSession } from "../types/chat";
import {
  loadSessions,
  makeMessageId,
  makeSessionId,
  saveSessions,
  sortSessionsByRecent,
  titleFromMessage,
} from "../utils/chatStorage";
import { useAuth } from "./useAuth";

function createEmptySession(id?: string): ChatSession {
  const now = Date.now();
  return {
    id: id ?? makeSessionId(),
    title: "New chat",
    messages: [],
    uploadedDocuments: [],
    createdAt: now,
    updatedAt: now,
  };
}

function getInitialState(): { sessions: ChatSession[]; activeSessionId: string } {
  const stored = loadSessions();
  if (stored.length > 0) {
    const sorted = sortSessionsByRecent(stored);
    return { sessions: sorted, activeSessionId: sorted[0].id };
  }
  const session = createEmptySession();
  return { sessions: [session], activeSessionId: session.id };
}

interface UseChatSessionsOptions {
  userId?: string;
}

const ACCEPTED_DOCUMENT_EXTENSIONS = [".pdf", ".docx"];
const ACCEPTED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"];
const ACCEPTED_EXTENSIONS = [
  ...ACCEPTED_DOCUMENT_EXTENSIONS,
  ...ACCEPTED_IMAGE_EXTENSIONS,
];

export function useChatSessions({ userId }: UseChatSessionsOptions = {}) {
  const { user } = useAuth();
  const effectiveUserId = useMemo(
    () => userId ?? user?.id ?? "anonymous",
    [userId, user?.id],
  );
  const [initial] = useState(getInitialState);
  const [sessions, setSessions] = useState<ChatSession[]>(initial.sessions);
  const [activeSessionId, setActiveSessionId] = useState<string>(initial.activeSessionId);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    saveSessions(sessions);
  }, [sessions]);

  const activeSession =
    sessions.find((s) => s.id === activeSessionId) ?? sessions[0] ?? createEmptySession();

  const updateSession = useCallback(
    (sessionId: string, updater: (session: ChatSession) => ChatSession) => {
      setSessions((prev) => {
        const updated = prev.map((s) => (s.id === sessionId ? updater(s) : s));
        return sortSessionsByRecent(updated);
      });
    },
    [],
  );

  const createNewChat = useCallback(() => {
    const empty = sessions.find((s) => s.messages.length === 0);
    if (empty) {
      setActiveSessionId(empty.id);
      return;
    }

    const session = createEmptySession();
    setSessions((prev) => sortSessionsByRecent([session, ...prev]));
    setActiveSessionId(session.id);
  }, [sessions]);

  const selectChat = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
  }, []);

  const deleteChat = useCallback(
    (sessionId: string) => {
      setSessions((prev) => {
        const filtered = prev.filter((s) => s.id !== sessionId);
        if (filtered.length === 0) {
          const fresh = createEmptySession();
          setActiveSessionId(fresh.id);
          return [fresh];
        }

        if (sessionId === activeSessionId) {
          setActiveSessionId(filtered[0].id);
        }

        return sortSessionsByRecent(filtered);
      });
    },
    [activeSessionId],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading || isUploading) return;

      const sessionId = activeSessionId;
      const session = sessions.find((s) => s.id === sessionId);

      if (!session) return;

      const userMessage: ChatMessage = {
        id: makeMessageId(),
        role: "user",
        text: trimmed,
        timestamp: Date.now(),
      };

      const isFirstMessage = session.messages.length === 0;

      updateSession(sessionId, (s) => ({
        ...s,
        title: isFirstMessage ? titleFromMessage(trimmed) : s.title,
        messages: [...s.messages, userMessage],
        updatedAt: Date.now(),
      }));

      setIsLoading(true);

      try {
        const result = await sendQuery({
          question: trimmed,
          session_id: sessionId,
          user_id: effectiveUserId,
        });

        const assistantMessage: ChatMessage = {
          id: makeMessageId(),
          role: "assistant",
          text: result.answer,
          triageLevel: result.triage_level,
          citations: result.citations,
          disclaimer: result.disclaimer,
          flaggedNumbers: result.flagged_numbers,
          timestamp: Date.now(),
        };

        updateSession(sessionId, (s) => ({
          ...s,
          messages: [...s.messages, assistantMessage],
          updatedAt: Date.now(),
        }));
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : "Something went wrong reaching the assistant. Please try again.";

        const errorMessage: ChatMessage = {
          id: makeMessageId(),
          role: "error",
          text: message,
          timestamp: Date.now(),
        };

        updateSession(sessionId, (s) => ({
          ...s,
          messages: [...s.messages, errorMessage],
          updatedAt: Date.now(),
        }));
      } finally {
        setIsLoading(false);
      }
    },
    [activeSessionId, effectiveUserId, isLoading, isUploading, sessions, updateSession],
  );

  const uploadFile = useCallback(
    async (file: File) => {
      if (isLoading || isUploading) return;

      const ext = file.name.includes(".")
        ? `.${file.name.split(".").pop()?.toLowerCase()}`
        : "";

      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        updateSession(activeSessionId, (s) => ({
          ...s,
          messages: [
            ...s.messages,
            {
              id: makeMessageId(),
              role: "error" as const,
              text: "Supported formats: PDF, DOCX (documents) or PNG, JPG, WEBP (lab report photos).",
              timestamp: Date.now(),
            },
          ],
          updatedAt: Date.now(),
        }));
        return;
      }

      setIsUploading(true);

      try {
        const isImage = ACCEPTED_IMAGE_EXTENSIONS.includes(ext);

        let documentId: string;
        let message: string;
        let chunkCount: number;

        if (isImage) {
          const result = await uploadImage(file, effectiveUserId);
          documentId = result.document_id ?? `img-${Date.now()}`;
          chunkCount = result.chunks_stored;
          message = result.message;
        } else {
          const result = await uploadDocument(file, effectiveUserId);
          documentId = result.document_id;
          chunkCount = result.chunk_count;
          message = result.message;
        }

        updateSession(activeSessionId, (s) => ({
          ...s,
          uploadedDocuments: [
            ...(s.uploadedDocuments ?? []),
            {
              documentId,
              filename: file.name,
              chunkCount,
              type: isImage ? "image" : "document",
            },
          ],
          messages: [
            ...s.messages,
            {
              id: makeMessageId(),
              role: "assistant" as const,
              text: message,
              timestamp: Date.now(),
            },
          ],
          updatedAt: Date.now(),
        }));
      } catch (err) {
        const message =
          err instanceof IngestApiError || err instanceof UploadApiError
            ? (err as Error).message
            : "Failed to upload. Please try again.";

        updateSession(activeSessionId, (s) => ({
          ...s,
          messages: [
            ...s.messages,
            {
              id: makeMessageId(),
              role: "error" as const,
              text: message,
              timestamp: Date.now(),
            },
          ],
          updatedAt: Date.now(),
        }));
      } finally {
        setIsUploading(false);
      }
    },
    [activeSessionId, effectiveUserId, isLoading, isUploading, updateSession],
  );

  return {
    sessions: sortSessionsByRecent(sessions),
    activeSession,
    activeSessionId,
    isLoading,
    isUploading,
    userId: effectiveUserId,
    createNewChat,
    selectChat,
    deleteChat,
    sendMessage,
    uploadFile,
  };
}
