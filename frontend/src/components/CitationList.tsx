import { useState } from "react";
import type { Citation } from "../types/chat";

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  const [open, setOpen] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs font-medium text-baymax-accent hover:underline"
      >
        {open ? "Hide" : "Show"} sources ({citations.length})
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5 rounded-lg border border-white/10 bg-black/20 px-3 py-2">
          {citations.map((citation) => (
            <li key={citation.marker} className="text-xs text-baymax-textMuted">
              <span className="font-mono text-baymax-accent">{citation.marker}</span>{" "}
              {citation.source_ref}{" "}
              <span className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
                {citation.corpus === "kb" ? "general info" : "your document"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
