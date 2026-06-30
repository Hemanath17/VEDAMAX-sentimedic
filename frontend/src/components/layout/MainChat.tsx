import { AttachmentBar } from "../AttachmentBar";
import { ChatComposer } from "../ChatComposer";
import { EmptyState } from "../EmptyState";
import { MessageList } from "../MessageList";
import type { ChatSession } from "../../types/chat";

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

interface MainChatProps {
  activeSession: ChatSession;
  isLoading: boolean;
  isUploading: boolean;
  sendMessage: (text: string) => void;
  uploadFile: (file: File) => void;
  onOpenSidebar: () => void;
}

export function MainChat({
  activeSession,
  isLoading,
  isUploading,
  sendMessage,
  uploadFile,
  onOpenSidebar,
}: MainChatProps) {
  const isEmpty = activeSession.messages.length === 0 && !isLoading && !isUploading;
  const busy = isLoading || isUploading;
  const uploadedDocuments = activeSession.uploadedDocuments ?? [];

  return (
    <div className="flex h-full flex-1 flex-col bg-baymax-bg">
      <header className="flex items-center gap-3 border-b border-white/10 px-4 py-3 md:hidden">
        <button
          type="button"
          onClick={onOpenSidebar}
          aria-label="Open sidebar"
          className="rounded-lg p-1.5 text-baymax-textMuted hover:bg-baymax-surface"
        >
          <MenuIcon />
        </button>
        <span className="truncate text-sm font-medium text-baymax-text">{activeSession.title}</span>
      </header>

      {isEmpty ? (
        <EmptyState
          onSend={sendMessage}
          onUpload={uploadFile}
          disabled={isLoading}
          isUploading={isUploading}
        />
      ) : (
        <>
          <MessageList messages={activeSession.messages} isLoading={isLoading} />
          <div className="border-t border-white/10 bg-baymax-bg px-4 py-4">
            <div className="mx-auto max-w-3xl">
              <AttachmentBar documents={uploadedDocuments} />
              <ChatComposer
                onSend={sendMessage}
                onUpload={uploadFile}
                disabled={busy}
                isUploading={isUploading}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
