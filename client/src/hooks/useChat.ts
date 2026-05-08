import { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import { useStream } from '@langchain/langgraph-sdk/react';
import { v4 as uuidv4 } from 'uuid';
import { useDispatch } from 'react-redux';
import { useParams } from 'react-router';
import { createClient } from '@/lib/client';
import { useAuth } from './useAuth';
import type {
  AIMessage,
  Checkpoint,
  Client,
  DefaultToolCall,
  Message as SdkMessage,
  Thread,
} from '@langchain/langgraph-sdk';
import { setMessages } from '@store';
import type { Message } from '@/types';

interface AgentStateType extends Record<string, unknown> {
  messages: unknown[];
}

interface UseChatOptions {
  mode?: 'chat' | 'voice';
  onError?: (error: Error) => void;
  onThreadCreated?: (threadId: string) => void;
}

export function useThreads(client: Client | undefined) {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentThread, setCurrentThread] = useState<Thread | null>(null);
  const [isThreadReady, setIsThreadReady] = useState(false);
  const pendingSwitchRef = useRef<string | null>(null);
  const isLoadingThreadsRef = useRef(false);

  const loadThreads = useCallback(async () => {
    if (!client) return;
    if (isLoadingThreadsRef.current) return;
    isLoadingThreadsRef.current = true;
    try {
      const result = await client.threads.search({ limit: 50 });
      setThreads(result);
    } catch (err) {
      void err;
    } finally {
      isLoadingThreadsRef.current = false;
    }
  }, [client]);

  const createThread = useCallback(
    async (title?: string): Promise<Thread | null> => {
      if (!client) return null;
      try {
        setIsThreadReady(false);
        const thread = await client.threads.create({
          metadata: title ? { name: title } : undefined,
        });
        setThreads((prev) => [thread, ...prev]);
        setCurrentThread(thread);
        setIsThreadReady(true);
        return thread;
      } catch (err) {
        void err;
        setIsThreadReady(false);
        return null;
      }
    },
    [client],
  );

  const getThread = useCallback(
    async (threadId: string): Promise<Thread | null> => {
      if (!client) return null;
      try {
        return await client.threads.get(threadId);
      } catch (err) {
        void err;
        return null;
      }
    },
    [client],
  );

  const switchToThread = useCallback(
    async (thread: Thread): Promise<boolean> => {
      const { thread_id } = thread;
      pendingSwitchRef.current = thread_id;
      setIsThreadReady(false);
      const resolved = threads.find((t) => t.thread_id === thread_id) ?? thread;
      if (pendingSwitchRef.current !== thread_id) return false;
      setCurrentThread(resolved);
      setIsThreadReady(true);
      return true;
    },
    [threads],
  );

  const deleteThread = useCallback(
    async (threadId: string) => {
      if (!client) return { success: false, switchedToThread: null };
      try {
        await client.threads.delete(threadId);
        const updated = threads.filter((t) => t.thread_id !== threadId);
        setThreads(updated);
        let switchedTo: Thread | null = null;
        if (currentThread?.thread_id === threadId) {
          switchedTo = updated[0] ?? null;
          setCurrentThread(switchedTo);
          setIsThreadReady(switchedTo !== null);
        }
        return { success: true, switchedToThread: switchedTo };
      } catch (err) {
        void err;
        return { success: false, switchedToThread: null };
      }
    },
    [client, currentThread, threads],
  );

  const updateThreadMetadata = useCallback(
    async (threadId: string, metadata: Record<string, unknown>): Promise<boolean> => {
      if (!client) return false;
      try {
        await client.threads.update(threadId, { metadata });
        setThreads((prev) =>
          prev.map((t) =>
            t.thread_id === threadId
              ? { ...t, metadata: { ...t.metadata, ...metadata } }
              : t,
          ),
        );
        setCurrentThread((prev) =>
          prev?.thread_id === threadId
            ? { ...prev, metadata: { ...prev.metadata, ...metadata } }
            : prev,
        );
        return true;
      } catch (err) {
        void err;
        return false;
      }
    },
    [client],
  );

  const clearCurrentThread = useCallback(() => {
    setCurrentThread(null);
    setIsThreadReady(false);
  }, []);

  return useMemo(
    () => ({
      threads,
      currentThread,
      isThreadReady,
      setCurrentThread,
      loadThreads,
      createThread,
      getThread,
      switchToThread,
      deleteThread,
      updateThreadMetadata,
      clearCurrentThread,
    }),
    [
      threads,
      currentThread,
      isThreadReady,
      setCurrentThread,
      loadThreads,
      createThread,
      getThread,
      switchToThread,
      deleteThread,
      updateThreadMetadata,
      clearCurrentThread,
    ],
  );
}

export function useStreamState(stream: ReturnType<typeof useStream<AgentStateType>>) {
  const [stableIsLoading, setStableIsLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (stream.isLoading) {
      if (timerRef.current) clearTimeout(timerRef.current);
      setStableIsLoading(true);
    } else {
      timerRef.current = setTimeout(() => setStableIsLoading(false), 300);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [stream.isLoading]);

  const stopStream = useCallback(() => stream.stop(), [stream]);

  return {
    isLoading: stableIsLoading,
    isStreaming: stream.isLoading,
    stopStream,
  };
}

export function useChat(options: UseChatOptions = {}) {
  const { mode = 'chat', onError, onThreadCreated } = options;
  const { threadId: urlThreadId } = useParams<{ threadId?: string }>();
  const dispatch = useDispatch();

  const titleSetRef = useRef(false);
  const threadCacheRef = useRef<Map<string, AgentStateType>>(new Map());
  const threadsMgrRef = useRef<ReturnType<typeof useThreads> | undefined>(undefined);
  const submissionTimeRef = useRef<number | null>(null);
  const messageTimingsRef = useRef<Map<string, number>>(new Map<string, number>());

  const client = useMemo(() => {
    try {
      return createClient();
    } catch {
      return undefined;
    }
  }, []);

  const threadsMgr = useThreads(client);

  const [streamThreadId, setStreamThreadId] = useState<string | null>(
    () => threadsMgr.currentThread?.thread_id ?? null,
  );
  const streamThreadIdRef = useRef(streamThreadId);

  useEffect(() => {
    streamThreadIdRef.current = streamThreadId;
  }, [streamThreadId]);

  useEffect(() => {
    threadsMgrRef.current = threadsMgr;
  }, [threadsMgr]);

  // Sync streamThreadId when currentThread changes (e.g. sidebar switch)
  useEffect(() => {
    const extId = threadsMgr.currentThread?.thread_id ?? null;
    setStreamThreadId((prev) => (prev === extId ? prev : extId));
  }, [threadsMgr.currentThread?.thread_id]);

  useEffect(() => {
    titleSetRef.current = false;
  }, [streamThreadId]);

  const cachedValues = streamThreadId
    ? (threadCacheRef.current.get(streamThreadId) ?? null)
    : null;

  const stream = useStream<AgentStateType>({
    client,
    assistantId: 'voice_agent',
    threadId: streamThreadId,
    initialValues: cachedValues,
    fetchStateHistory: { limit: 50 },
    reconnectOnMount: true,
    onThreadId: (newThreadId: string) => {
      setStreamThreadId(newThreadId);
      const alreadyKnown = threadsMgr.threads.some((t) => t.thread_id === newThreadId);
      client
        ?.threads.get(newThreadId)
        .then((thread) => {
          threadsMgr.setCurrentThread(thread);
          if (!alreadyKnown) {
            threadsMgr.loadThreads();
          }
        })
        .catch(() => {});
    },
    onFinish: (state: { values: AgentStateType }, run?: { thread_id?: string }) => {
      const tid = run?.thread_id ?? streamThreadId;
      if (tid && state?.values) {
        threadCacheRef.current.set(tid, state.values);
      }
    },
  });

  const editMessage = useCallback(
    async (messageId: string, newText: string) => {
      const rawMessages: SdkMessage[] = stream.messages ?? [];
      const originalMsg = rawMessages.find((m) => m.id === messageId);
      if (!originalMsg) {
        await sendMessage(newText);
        return;
      }

      const metadata = stream.getMessagesMetadata?.(originalMsg);
      // `parent_checkpoint` is present on the underlying ThreadState but is not
      // typed on the SDK's `firstSeenState`; narrow via the SDK Checkpoint shape.
      const firstSeenState = metadata?.firstSeenState as
        | { parent_checkpoint?: Checkpoint; values?: AgentStateType }
        | undefined;
      const parentCheckpoint = firstSeenState?.parent_checkpoint;

      if (!parentCheckpoint) {
        await sendMessage(newText);
        return;
      }

      const rootCheckpoint = { ...parentCheckpoint, checkpoint_ns: '' };
      const updatedMessage = { ...originalMsg, content: newText };
      const firstSeenValues = firstSeenState?.values;

      await stream.submit(
        { messages: [updatedMessage] },
        {
          checkpoint: rootCheckpoint,
          streamSubgraphs: true,
          optimisticValues: (prev) =>
            firstSeenValues
              ? {
                  ...firstSeenValues,
                  messages: [...(firstSeenValues.messages ?? []), updatedMessage],
                }
              : prev,
          config: { recursion_limit: 100, configurable: { mode } },
        },
      );
    },
    [stream, mode],
  );

  const retryMessage = useCallback(
    async (messageId: string) => {
      const rawMessages: SdkMessage[] = stream.messages ?? [];
      const targetMsg = rawMessages.find((m) => m.id === messageId);
      if (!targetMsg) return;

      const metadata = stream.getMessagesMetadata?.(targetMsg);
      const firstSeenState = metadata?.firstSeenState as
        | { parent_checkpoint?: Checkpoint }
        | undefined;
      const parentCheckpoint = firstSeenState?.parent_checkpoint;
      if (!parentCheckpoint) return;

      const rootCheckpoint = { ...parentCheckpoint, checkpoint_ns: '' };

      await stream.submit(undefined, {
        checkpoint: rootCheckpoint,
        streamSubgraphs: true,
        config: { recursion_limit: 100, configurable: { mode } },
      });
    },
    [stream, mode],
  );

  const streamState = useStreamState(stream);

  const reduxMessages = useMemo(() => {
    const messages: SdkMessage[] = stream.messages ?? [];
    if (!Array.isArray(messages)) {
      console.warn('stream.messages is not an array:', messages);
      return [];
    }

    const toolResultMap = new Map<string, string | Record<string, unknown>>();
    messages.forEach((msg) => {
      if (msg.type === 'tool' && msg.tool_call_id) {
        // ToolMessage.content can be a complex MessageContent, but downstream
        // consumers (the tool-call panel) accept string | object.
        toolResultMap.set(
          msg.tool_call_id,
          msg.content as string | Record<string, unknown>,
        );
      }
    });

    return messages
      .filter((msg) => msg.type !== 'tool')
      .map((msg) => {
        const msgType = typeof msg.type === 'string' ? msg.type : 'human';
        const role: 'user' | 'assistant' = msgType === 'human' ? 'user' : 'assistant';

        let content = '';
        if (typeof msg.content === 'string') {
          content = msg.content;
        } else if (msg.content !== null && msg.content !== undefined) {
          content = String(msg.content);
        }

        // SDK BaseMessage doesn't carry a timestamp, but some transports attach
        // one ad-hoc. Read it through `unknown` and narrow.
        const rawTimestamp = (msg as { timestamp?: unknown }).timestamp;
        let timestamp: string;
        if (rawTimestamp instanceof Date) {
          timestamp = rawTimestamp.toISOString();
        } else if (typeof rawTimestamp === 'string') {
          timestamp = rawTimestamp;
        } else if (typeof rawTimestamp === 'number') {
          timestamp = new Date(rawTimestamp).toISOString();
        } else {
          timestamp = new Date().toISOString();
        }

        const aiMsg = msg as AIMessage<DefaultToolCall>;
        let toolCalls: Message['toolCalls'] = [];
        if (Array.isArray(aiMsg.tool_calls)) {
          toolCalls = aiMsg.tool_calls.map((tc) => ({
            id: tc.id ?? '',
            name: tc.name,
            args: tc.args,
            result: tc.id ? toolResultMap.get(tc.id) : undefined,
          }));
        }

        if (role === 'assistant' && !content.trim() && toolCalls.length === 0) {
          return null;
        }

        const tokenCount = aiMsg.usage_metadata?.total_tokens;

        let elapsedMs: number | undefined;
        const isLastMessage = msg === messages[messages.length - 1];
        if (isLastMessage && role === 'assistant' && submissionTimeRef.current !== null) {
          const currentTime = performance.now();
          elapsedMs = currentTime - submissionTimeRef.current;
          if (!streamState.isStreaming) {
            messageTimingsRef.current.set(msg.id || '', elapsedMs);
          }
        } else if (role === 'assistant' && messageTimingsRef.current.has(msg.id || '')) {
          elapsedMs = messageTimingsRef.current.get(msg.id || '');
        }

        const result: Message = {
          id: msg.id || uuidv4(),
          role,
          content,
          timestamp,
          isStreaming: streamState.isStreaming && msgType === 'ai',
          toolCalls,
          ...(tokenCount !== undefined && { tokenCount }),
          ...(elapsedMs !== undefined && { elapsedMs }),
        };
        return result;
      })
      .filter((msg): msg is Message => msg !== null);
  }, [stream.messages, streamState.isStreaming, messageTimingsRef]);

  useEffect(() => {
    dispatch(setMessages({ messages: reduxMessages }));
  }, [reduxMessages, dispatch]);

  useEffect(() => {
    let isMounted = true;

    const resumeSession = async () => {
      if (!client || !threadsMgrRef.current) return;

      try {
        await threadsMgrRef.current.loadThreads();
        if (!isMounted) return;

        let selectedId = urlThreadId;
        if (!selectedId && threadsMgrRef.current.threads.length > 0) {
          selectedId = threadsMgrRef.current.threads[0]?.thread_id;
        }

        if (selectedId && selectedId !== streamThreadIdRef.current) {
          const thread = await client.threads.get(selectedId);
          if (!isMounted) return;
          threadsMgrRef.current.setCurrentThread(thread);
          setStreamThreadId(thread.thread_id);
        }
      } catch (err) {
        onError?.(err instanceof Error ? err : new Error('Failed to load'));
      }
    };

    resumeSession();

    return () => {
      isMounted = false;
    };
  }, [client, urlThreadId, onError]);

  const { userId } = useAuth();

  const sendMessage = useCallback(
    async (text: string) => {
      const humanMessage = { id: uuidv4(), type: 'human', content: text };
      const isFirstMessage = !stream.values?.messages?.length;

      submissionTimeRef.current = performance.now();

      const submitOptions = {
        streamSubgraphs: true,
        optimisticValues: (prev: AgentStateType) => ({
          ...prev,
          messages: [...(prev.messages ?? []), humanMessage],
        }),
        config: {
          recursion_limit: 100,
          configurable: {
            mode,
            user_id: userId || 'unknown',
          }
        },
      };

      await stream.submit({ messages: [humanMessage] }, submitOptions);

      if (isFirstMessage && !titleSetRef.current) {
        titleSetRef.current = true;
        const tid = streamThreadId;
        if (tid) {
          const title = text.trim().slice(0, 45) + (text.trim().length > 45 ? '…' : '');
          client
            ?.threads.update(tid, { metadata: { name: title } })
            .then(() => threadsMgr.loadThreads())
            .catch(() => {
              titleSetRef.current = false;
            });
          onThreadCreated?.(tid);
        }
      }
    },
    [stream, streamThreadId, client, threadsMgr.loadThreads, onThreadCreated, mode, userId],
  );

  return {
    threads: threadsMgr.threads,
    currentThread: threadsMgr.currentThread,
    isThreadReady: threadsMgr.isThreadReady,
    loadThreads: threadsMgr.loadThreads,
    createThread: threadsMgr.createThread,
    getThread: threadsMgr.getThread,
    switchToThread: threadsMgr.switchToThread,
    deleteThread: threadsMgr.deleteThread,
    updateThreadMetadata: threadsMgr.updateThreadMetadata,
    clearCurrentThread: threadsMgr.clearCurrentThread,
    messages: reduxMessages,
    currentThreadId: streamThreadId,
    isLoading: streamState.isLoading,
    isStreaming: streamState.isStreaming,
    error: stream.error,
    sendMessage,
    editMessage,
    retryMessage,
    stopStream: streamState.stopStream,
  };
}
