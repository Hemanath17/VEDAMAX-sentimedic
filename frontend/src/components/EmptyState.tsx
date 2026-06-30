import { ChatComposer } from "./ChatComposer";

const SUGGESTIONS = [
  "What is a normal fasting blood glucose level?",
  "Is my glucose level high?",
  "What does an HbA1c test measure?",
];

interface EmptyStateProps {
  onSend: (text: string) => void;
  onUpload?: (file: File) => void;
  disabled?: boolean;
  isUploading?: boolean;
}

export function EmptyState({ onSend, onUpload, disabled, isUploading }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 pb-8">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-semibold text-baymax-text">
          How can I help with your health today?
        </h1>
        <p className="mt-2 text-sm text-baymax-textMuted">
          Upload a lab report or ask a general health question.
        </p>
      </div>

      <div className="w-full max-w-2xl">
        <ChatComposer
          onSend={onSend}
          onUpload={onUpload}
          disabled={disabled}
          isUploading={isUploading}
        />
      </div>

      <div className="mt-6 flex w-full max-w-2xl flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            disabled={disabled || isUploading}
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
