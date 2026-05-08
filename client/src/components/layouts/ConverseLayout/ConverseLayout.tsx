import { useCallback, useState } from 'react';
import { useNavigate, Outlet, useOutletContext } from 'react-router';
import { ThreadHistorySidebar } from '@components/Chat';
import { useChat } from '@hooks/index';

export interface ConverseContextType {
  chat: ReturnType<typeof useChat>;
  mode: 'chat' | 'voice';
  setMode: (mode: 'chat' | 'voice') => void;
}

export function ConverseLayout() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'chat' | 'voice'>('chat');

  const chat = useChat({
    mode,
    onThreadCreated: (threadId) => {
      navigate(`/thread/${threadId}`, { replace: true });
    },
  });

  const handlePinThread = useCallback(
    async (threadId: string, currentPinned: boolean) => {
      await chat.updateThreadMetadata(threadId, { pinned: !currentPinned });
    },
    [chat],
  );

  const handleCreateNewThread = useCallback(async () => {
    const newThread = await chat.createThread();
    if (newThread) {
      navigate(`/thread/${newThread.thread_id}`, { replace: true });
    }
  }, [chat, navigate]);

  return (
    <div className="flex-1 flex h-full min-h-0 overflow-hidden">
      <ThreadHistorySidebar
        threads={chat.threads}
        currentThreadId={chat.currentThreadId}
        onSelectThread={(threadId) => {
          navigate(`/thread/${threadId}`, { replace: true });
        }}
        onCreateThread={handleCreateNewThread}
        updateThreadMetadata={chat.updateThreadMetadata}
        deleteThread={chat.deleteThread}
        onPinThread={handlePinThread}
      />

      <Outlet context={{ chat, mode, setMode }} />
    </div>
  );
}

export function useConverseContext() {
  return useOutletContext<ConverseContextType>();
}
