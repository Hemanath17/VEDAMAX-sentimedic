import { useCallback, useEffect, useState } from "react";
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

function createEmptySession(id?: string): ChatSession {
  const now = Date.now();
  return {
    id: id ?? makeSessionId(),
    title: "New chat",
    messages: [],
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

export function useChatSessions({ userId }: UseChatSessionsOptions = {}) {
  const [initial] = useState(getInitialState);
  const [sessions, setSessions] = useState<ChatSession[]>(initial.sessions);
  const [activeSessionId, setActiveSessionId] = useState<string>(initial.activeSessionId);
  const [isLoading, setIsLoading] = useState(false);

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
      if (!trimmed || isLoading) return;

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
        const result = await sendQuery({ question: trimmed, user_id: userId });

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
    [activeSessionId, isLoading, sessions, updateSession, userId],
  );

  return {
    sessions: sortSessionsByRecent(sessions),
    activeSession,
    activeSessionId,
    isLoading,
    createNewChat,
    selectChat,
    deleteChat,
    sendMessage,
  };
}
