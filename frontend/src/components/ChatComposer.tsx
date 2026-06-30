import { useRef, type ChangeEvent, type FormEvent, type KeyboardEvent } from "react";

interface ChatComposerProps {
  onSend: (text: string) => void;
  onUpload?: (file: File) => void;
  disabled?: boolean;
  isUploading?: boolean;
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

function AttachIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ChatComposer({
  onSend,
  onUpload,
  disabled = false,
  isUploading = false,
  placeholder = "Message VEDAMAX…",
}: ChatComposerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const busy = disabled || isUploading;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const textarea = form.elements.namedItem("message") as HTMLTextAreaElement;
    const value = textarea.value.trim();
    if (!value || busy) return;
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

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && onUpload) {
      onUpload(file);
    }
    event.target.value = "";
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative flex items-end rounded-2xl border border-white/10 bg-baymax-surfaceAlt shadow-lg">
        {onUpload && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleFileChange}
            />
            <button
              type="button"
              disabled={busy}
              aria-label="Attach document"
              title="Upload lab report (PDF, DOCX, or photo)"
              onClick={() => fileInputRef.current?.click()}
              className="mb-2 ml-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-baymax-textMuted transition hover:bg-baymax-surface hover:text-baymax-text disabled:cursor-not-allowed disabled:opacity-30"
            >
              {isUploading ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-baymax-accent border-t-transparent" />
              ) : (
                <AttachIcon />
              )}
            </button>
          </>
        )}
        <textarea
          name="message"
          rows={1}
          disabled={busy}
          placeholder={isUploading ? "Uploading document…" : placeholder}
          onKeyDown={handleKeyDown}
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = "auto";
            el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
          }}
          className="max-h-[200px] min-h-[52px] flex-1 resize-none bg-transparent px-2 py-3.5 text-sm text-baymax-text placeholder:text-baymax-textMuted focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy}
          aria-label="Send message"
          className="mb-2 mr-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-baymax-accent text-baymax-bg transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <SendIcon />
        </button>
      </div>
      <p className="mt-2 text-center text-xs text-baymax-textMuted">
        Attach a lab report (PDF, DOCX, or photo) or ask a health question.
      </p>
    </form>
  );
}
