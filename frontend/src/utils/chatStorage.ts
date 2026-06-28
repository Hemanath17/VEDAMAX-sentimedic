import type { ChatSession } from "../types/chat";

const STORAGE_KEY = "vedamax_chats";

export function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatSession[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveSessions(sessions: ChatSession[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function makeSessionId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function makeMessageId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function titleFromMessage(text: string): string {
  const trimmed = text.trim();
  if (trimmed.length <= 40) return trimmed;
  return `${trimmed.slice(0, 40)}…`;
}

export function sortSessionsByRecent(sessions: ChatSession[]): ChatSession[] {
  return [...sessions].sort((a, b) => b.updatedAt - a.updatedAt);
}
