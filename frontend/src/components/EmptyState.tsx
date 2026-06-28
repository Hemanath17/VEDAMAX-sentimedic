import { ChatComposer } from "./ChatComposer";

const SUGGESTIONS = [
  "What is a normal fasting blood glucose level?",
  "What does an HbA1c test measure?",
  "What are common symptoms of type 2 diabetes?",
];

interface EmptyStateProps {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function EmptyState({ onSend, disabled }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 pb-8">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-semibold text-baymax-text">How can I help with your health today?</h1>
        <p className="mt-2 text-sm text-baymax-textMuted">
          Ask about labs, vitals, or general health topics.
        </p>
      </div>

      <div className="w-full max-w-2xl">
        <ChatComposer onSend={onSend} disabled={disabled} />
      </div>

      <div className="mt-6 flex w-full max-w-2xl flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            disabled={disabled}
            onClick={() => onSend(suggestion)}
            className="rounded-full border border-white/10 bg-baymax-surface px-3 py-1.5 text-xs text-baymax-textMuted transition hover:bg-baymax-surfaceAlt hover:text-baymax-text disabled:opacity-50"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
