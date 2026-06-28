export function TypingIndicator() {
  return (
    <div className="w-full border-b border-white/5 bg-baymax-bg">
      <div className="mx-auto flex max-w-3xl gap-4 px-4 py-6 md:px-6">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-sm bg-baymax-accentSoft text-xs font-bold text-baymax-accent">
          V
        </div>
        <div className="flex items-center gap-1 pt-2">
          <span className="h-2 w-2 animate-bounce rounded-full bg-baymax-accent [animation-delay:-0.3s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-baymax-accent [animation-delay:-0.15s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-baymax-accent" />
        </div>
      </div>
    </div>
  );
}
