import type { FormEvent, KeyboardEvent } from "react";

interface ChatComposerProps {
  onSend: (text: string) => void;
  disabled: boolean;
  placeholder?: string;
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8z"
        fill="currentColor"
      />
    </svg>
  );
}

export function ChatComposer({
  onSend,
  disabled,
  placeholder = "Message VEDAMAX…",
}: ChatComposerProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const textarea = form.elements.namedItem("message") as HTMLTextAreaElement;
    const value = textarea.value.trim();
    if (!value || disabled) return;
    onSend(value);
    textarea.value = "";
    textarea.style.height = "auto";
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative flex items-end rounded-2xl border border-white/10 bg-baymax-surfaceAlt shadow-lg">
        <textarea
          name="message"
          rows={1}
          disabled={disabled}
          placeholder={placeholder}
          onKeyDown={handleKeyDown}
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = "auto";
            el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
          }}
          className="max-h-[200px] min-h-[52px] flex-1 resize-none bg-transparent px-4 py-3.5 text-sm text-baymax-text placeholder:text-baymax-textMuted focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled}
          aria-label="Send message"
          className="mb-2 mr-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-baymax-accent text-baymax-bg transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <SendIcon />
        </button>
      </div>
      <p className="mt-2 text-center text-xs text-baymax-textMuted">
        VEDAMAX provides educational information, not medical advice.
      </p>
    </form>
  );
}
