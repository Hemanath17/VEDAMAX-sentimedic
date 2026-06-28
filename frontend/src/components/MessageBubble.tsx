import type { ChatMessage } from "../types/chat";
import { TriageBanner } from "./TriageBanner";
import { CitationList } from "./CitationList";

interface MessageBubbleProps {
  message: ChatMessage;
}

function Avatar({ role }: { role: ChatMessage["role"] }) {
  const isUser = role === "user";
  return (
    <div
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-sm text-xs font-bold ${
        isUser
          ? "bg-baymax-accent text-baymax-bg"
          : role === "error"
            ? "bg-baymax-danger/20 text-baymax-danger"
            : "bg-baymax-accentSoft text-baymax-accent"
      }`}
    >
      {isUser ? "U" : role === "error" ? "!" : "V"}
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isError = message.role === "error";

  return (
    <div
      className={`w-full border-b border-white/5 ${
        isUser ? "bg-baymax-surfaceAlt/40" : "bg-baymax-bg"
      }`}
    >
      <div className="mx-auto flex max-w-3xl gap-4 px-4 py-6 md:px-6">
        <Avatar role={message.role} />
        <div className="min-w-0 flex-1 pt-0.5">
          {!isUser && message.triageLevel && <TriageBanner level={message.triageLevel} />}

          <p
            className={`whitespace-pre-wrap text-sm leading-7 ${
              isError ? "text-baymax-danger" : "text-baymax-text"
            }`}
          >
            {message.text}
          </p>

          {!isUser && message.flaggedNumbers && message.flaggedNumbers.length > 0 && (
            <p className="mt-2 text-xs text-baymax-warn">
              Unverified figures: {message.flaggedNumbers.join(", ")}
            </p>
          )}

          {!isUser && message.citations && <CitationList citations={message.citations} />}

          {!isUser && message.disclaimer && (
            <p className="mt-3 text-xs italic text-baymax-textMuted">{message.disclaimer}</p>
          )}
        </div>
      </div>
    </div>
  );
}
