import type { ChatSession } from "../../types/chat";
import { supabase } from "../../lib/supabase";
import { useAuth } from "../../hooks/useAuth";

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
  onClose?: () => void;
}

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Sidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onClose,
}: SidebarProps) {
  const { user } = useAuth();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  const handleSelect = (id: string) => {
    onSelectChat(id);
    onClose?.();
  };

  const handleNew = () => {
    onNewChat();
    onClose?.();
  };

  return (
    <aside className="flex h-full w-[260px] shrink-0 flex-col bg-baymax-surface">
      <div className="flex items-center gap-2 border-b border-white/10 px-3 py-3">
        <span className="flex-1 text-sm font-semibold tracking-wide text-baymax-text">VEDAMAX</span>
      </div>

      <div className="p-2">
        <button
          type="button"
          onClick={handleNew}
          className="flex w-full items-center gap-2 rounded-lg border border-white/10 px-3 py-2.5 text-sm text-baymax-text transition hover:bg-baymax-surfaceAlt"
        >
          <PlusIcon />
          New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <p className="px-2 py-2 text-xs font-medium uppercase tracking-wide text-baymax-textMuted">
          Recent chats
        </p>
        <ul className="space-y-0.5">
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <li key={session.id} className="group relative">
                <button
                  type="button"
                  onClick={() => handleSelect(session.id)}
                  className={`w-full truncate rounded-lg px-3 py-2 pr-8 text-left text-sm transition ${
                    isActive
                      ? "bg-baymax-surfaceAlt text-baymax-text"
                      : "text-baymax-textMuted hover:bg-baymax-surfaceAlt/60 hover:text-baymax-text"
                  }`}
                  title={session.title}
                >
                  {session.title}
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteChat(session.id);
                  }}
                  aria-label={`Delete ${session.title}`}
                  className="absolute right-1 top-1/2 hidden -translate-y-1/2 rounded p-1 text-baymax-textMuted hover:bg-baymax-bg hover:text-baymax-danger group-hover:block"
                >
                  <TrashIcon />
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="border-t border-white/10 p-3">
        <div className="mb-2 truncate text-xs text-baymax-textMuted">
          {user?.email}
        </div>
        <button
          type="button"
          onClick={handleSignOut}
          className="w-full rounded-lg px-3 py-2 text-left text-xs text-baymax-textMuted transition hover:bg-baymax-surfaceAlt hover:text-baymax-text"
        >
          Sign out
        </button>
        <p className="mt-3 text-[11px] leading-relaxed text-baymax-textMuted">
          Educational health information — not a substitute for professional medical advice.
        </p>
      </div>
    </aside>
  );
}
