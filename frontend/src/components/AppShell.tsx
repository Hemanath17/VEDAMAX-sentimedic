import { useState } from "react";
import { useChatSessions } from "../hooks/useChatSessions";
import { MainChat } from "./layout/MainChat";
import { Sidebar } from "./layout/Sidebar";

export function AppShell() {
  const {
    sessions,
    activeSession,
    activeSessionId,
    isLoading,
    createNewChat,
    selectChat,
    deleteChat,
    sendMessage,
  } = useChatSessions();

  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-baymax-bg">
      {/* Desktop sidebar */}
      <div className="hidden md:flex">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onNewChat={createNewChat}
          onSelectChat={selectChat}
          onDeleteChat={deleteChat}
        />
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <button
            type="button"
            aria-label="Close sidebar"
            className="absolute inset-0 bg-black/50"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="relative z-50 h-full shadow-xl">
            <Sidebar
              sessions={sessions}
              activeSessionId={activeSessionId}
              onNewChat={createNewChat}
              onSelectChat={selectChat}
              onDeleteChat={deleteChat}
              onClose={() => setSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      <MainChat
        activeSession={activeSession}
        isLoading={isLoading}
        sendMessage={sendMessage}
        onOpenSidebar={() => setSidebarOpen(true)}
      />
    </div>
  );
}
