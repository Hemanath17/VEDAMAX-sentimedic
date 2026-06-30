import type { UploadedDocument } from "../types/chat";

interface AttachmentBarProps {
  documents: UploadedDocument[];
}

function DocumentIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path d="M14 2v6h6" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function ImageIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2" />
      <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" />
      <path d="M21 15l-5-5L5 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function AttachmentBar({ documents }: AttachmentBarProps) {
  if (!documents.length) return null;

  return (
    <div className="mx-auto mb-2 flex max-w-3xl flex-wrap gap-2 px-1">
      {documents.map((doc) => (
        <span
          key={doc.documentId}
          className="inline-flex items-center gap-1.5 rounded-full border border-baymax-accent/30 bg-baymax-accent/10 px-3 py-1 text-xs text-baymax-accent"
          title={`${doc.chunkCount} sections indexed`}
        >
          {doc.type === "image" ? <ImageIcon /> : <DocumentIcon />}
          {doc.filename}
        </span>
      ))}
    </div>
  );
}
