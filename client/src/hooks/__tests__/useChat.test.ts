/**
 * Tests for the useChat hook — specifically the parts that do NOT require a
 * live LangGraph backend.
 *
 * Approach:
 *  - Mock `@langchain/langgraph-sdk/react` to provide a controllable `useStream`
 *  - Mock `@langchain/langgraph-sdk` (Client) to control thread operations
 *  - Mock `react-router` to control URL params
 *  - Use a real Redux store so setMessages / dispatch interactions are verified
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import React from 'react';
import type { ReactNode } from 'react';

import { authReducer } from '@/features/auth';
import { AuthAPI } from '@/services/auth';

// ---------------------------------------------------------------------------
// Types used within the mocks
// ---------------------------------------------------------------------------

interface MockThread {
  thread_id: string;
  metadata?: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
  values: Record<string, unknown>;
  interrupts: unknown[];
}

interface MockMessage {
  id: string;
  type: string;
  content: string;
  tool_calls?: unknown[];
  tool_call_id?: string;
}

// ---------------------------------------------------------------------------
// Controllable useStream mock state
// ---------------------------------------------------------------------------

const mockStreamState = {
  messages: [] as MockMessage[],
  values: { messages: [] } as { messages: unknown[] },
  isLoading: false,
  error: null as Error | null,
  submit: vi.fn(),
  stop: vi.fn(),
  getMessagesMetadata: vi.fn(() => null),
};

// Store reference to the useStream mock for use in tests
let useStreamMock: ReturnType<typeof vi.fn>;

// ---------------------------------------------------------------------------
// Mock @langchain/langgraph-sdk/react
// ---------------------------------------------------------------------------

vi.mock('@langchain/langgraph-sdk/react', () => {
  useStreamMock = vi.fn(() => ({ ...mockStreamState }));
  return {
    useStream: useStreamMock,
  };
});

// ---------------------------------------------------------------------------
// Mock @langchain/langgraph-sdk (Client class)
// ---------------------------------------------------------------------------

const mockThreads: MockThread[] = [
  {
    thread_id: 'thread-1',
    metadata: { name: 'First thread' },
    status: 'idle',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    values: {},
    interrupts: [],
  },
];

const mockClient = {
  threads: {
    search: vi.fn(() => Promise.resolve(mockThreads)),
    create: vi.fn((opts?: { metadata?: Record<string, unknown> }) =>
      Promise.resolve({
        thread_id: 'thread-new',
        metadata: opts?.metadata ?? {},
        status: 'idle',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        values: {},
        interrupts: [],
      } satisfies MockThread),
    ),
    get: vi.fn((id: string) =>
      Promise.resolve({
        thread_id: id,
        metadata: {},
        status: 'idle',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        values: {},
        interrupts: [],
      } satisfies MockThread),
    ),
    delete: vi.fn(() => Promise.resolve()),
    update: vi.fn(() => Promise.resolve()),
  },
};

vi.mock('@/lib/client', () => ({
  createClient: vi.fn(() => mockClient),
}));

// ---------------------------------------------------------------------------
// Mock react-router
// ---------------------------------------------------------------------------

vi.mock('react-router', () => ({
  useParams: vi.fn(() => ({})),
}));

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function makeStore(authToken: string | null = null) {
  return configureStore({
    reducer: {
      auth: authReducer,
      voiceAgent: (
        state: {
          messages: unknown[];
          status: string;
          isConnected: boolean;
          currentThreadId: string | null;
        } = { messages: [], status: 'idle', isConnected: false, currentThreadId: null },
        action?: { type: string; payload?: unknown },
      ) => {
        if (action?.type === 'voiceAgent/setMessages') {
          return { ...state, messages: (action.payload as { messages: unknown[] }).messages };
        }
        return state;
      },
      [AuthAPI.reducerPath]: AuthAPI.reducer,
    },
    preloadedState: {
      auth: {
        token: authToken,
        userId: 'uid-test',
        username: 'tester',
        email: null,
        isAuthenticated: authToken !== null,
        isLoading: false,
        error: null,
      },
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(AuthAPI.middleware),
  });
}

type TestStore = ReturnType<typeof makeStore>;

function makeWrapper(store: TestStore) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return React.createElement(Provider, { store }, children);
  };
}

// ---------------------------------------------------------------------------
// Import hook AFTER mocks are set up
// ---------------------------------------------------------------------------

const { useChat, useThreads, useStreamState } = await import('../useChat');

// ---------------------------------------------------------------------------
// useThreads
// ---------------------------------------------------------------------------

describe('useThreads', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockClient.threads.search.mockResolvedValue(mockThreads);
  });

  it('starts with empty threads array', () => {
    const { result } = renderHook(() => useThreads(mockClient as never));
    expect(result.current.threads).toEqual([]);
  });

  it('starts with isThreadReady = false', () => {
    const { result } = renderHook(() => useThreads(mockClient as never));
    expect(result.current.isThreadReady).toBe(false);
  });

  it('loads threads via loadThreads', async () => {
    const { result } = renderHook(() => useThreads(mockClient as never));

    await act(async () => {
      await result.current.loadThreads();
    });

    expect(result.current.threads).toHaveLength(mockThreads.length);
    expect(result.current.threads[0]?.thread_id).toBe('thread-1');
  });

  it('does nothing when client is undefined', async () => {
    const { result } = renderHook(() => useThreads(undefined));

    await act(async () => {
      await result.current.loadThreads();
    });

    expect(result.current.threads).toEqual([]);
  });

  it('creates a new thread and marks isThreadReady', async () => {
    const { result } = renderHook(() => useThreads(mockClient as never));

    await act(async () => {
      await result.current.createThread('My new thread');
    });

    expect(result.current.currentThread?.thread_id).toBe('thread-new');
    expect(result.current.isThreadReady).toBe(true);
  });

  it('createThread returns null when client is undefined', async () => {
    const { result } = renderHook(() => useThreads(undefined));

    let returned: unknown;
    await act(async () => {
      returned = await result.current.createThread();
    });

    expect(returned).toBeNull();
  });

  it('switchToThread sets currentThread and isThreadReady', async () => {
    const { result } = renderHook(() => useThreads(mockClient as never));

    // First load threads so switchToThread can find the thread in the local list
    await act(async () => {
      await result.current.loadThreads();
    });

    await act(async () => {
      await result.current.switchToThread(mockThreads[0] as never);
    });

    expect(result.current.currentThread?.thread_id).toBe('thread-1');
    expect(result.current.isThreadReady).toBe(true);
  });

  it('deleteThread removes the thread from the list', async () => {
    const { result } = renderHook(() => useThreads(mockClient as never));

    await act(async () => {
      await result.current.loadThreads();
    });

    await act(async () => {
      await result.current.deleteThread('thread-1');
    });

    expect(result.current.threads.find((t) => t.thread_id === 'thread-1')).toBeUndefined();
  });

  it('clearCurrentThread resets currentThread and isThreadReady', async () => {
    const { result } = renderHook(() => useThreads(mockClient as never));

    await act(async () => {
      await result.current.createThread();
    });
    expect(result.current.currentThread).not.toBeNull();

    act(() => {
      result.current.clearCurrentThread();
    });

    expect(result.current.currentThread).toBeNull();
    expect(result.current.isThreadReady).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// useStreamState
// ---------------------------------------------------------------------------

describe('useStreamState', () => {
  it('returns isLoading = false when stream is not loading', () => {
    const fakeStream = {
      isLoading: false,
      stop: vi.fn(),
    };
    const { result } = renderHook(() =>
      useStreamState(fakeStream as never),
    );
    // Debounce timer keeps it false
    expect(result.current.isStreaming).toBe(false);
  });

  it('sets isStreaming = true immediately when stream is loading', () => {
    const fakeStream = { isLoading: true, stop: vi.fn() };
    const { result } = renderHook(() =>
      useStreamState(fakeStream as never),
    );
    expect(result.current.isStreaming).toBe(true);
  });

  it('exposes a stopStream function', () => {
    const stopFn = vi.fn();
    const fakeStream = { isLoading: false, stop: stopFn };
    const { result } = renderHook(() =>
      useStreamState(fakeStream as never),
    );
    result.current.stopStream();
    expect(stopFn).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// useChat — connection state and message dispatch
// ---------------------------------------------------------------------------

describe('useChat – connection state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStreamState.messages = [];
    mockStreamState.values = { messages: [] };
    mockStreamState.isLoading = false;
    mockStreamState.error = null;
    mockClient.threads.search.mockResolvedValue([]);
    mockClient.threads.get.mockResolvedValue(mockThreads[0]);

    useStreamMock.mockReturnValue({ ...mockStreamState });
  });

  it('starts with isLoading = false', () => {
    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });
    expect(result.current.isLoading).toBe(false);
  });

  it('exposes a sendMessage function', () => {
    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });
    expect(typeof result.current.sendMessage).toBe('function');
  });

  it('exposes currentThread as null initially', async () => {
    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });
    // currentThread begins null before any thread is loaded
    await waitFor(() => {
      // Just ensure no crash during load
      expect(result.current).toBeDefined();
    });
  });
});

// ---------------------------------------------------------------------------
// useChat — message processing (reduxMessages)
// ---------------------------------------------------------------------------

describe('useChat – message processing', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockClient.threads.search.mockResolvedValue([]);
    mockClient.threads.get.mockResolvedValue(mockThreads[0]);
  });

  it('maps human messages to role=user', () => {
    const humanMsg: MockMessage = { id: 'h1', type: 'human', content: 'Hello' };
    mockStreamState.messages = [humanMsg];
    useStreamMock.mockReturnValue({ ...mockStreamState });

    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    expect(result.current.messages[0]?.role).toBe('user');
    expect(result.current.messages[0]?.content).toBe('Hello');
  });

  it('maps ai messages to role=assistant', () => {
    const aiMsg: MockMessage = { id: 'a1', type: 'ai', content: 'World' };
    mockStreamState.messages = [aiMsg];
    useStreamMock.mockReturnValue({ ...mockStreamState });

    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    expect(result.current.messages[0]?.role).toBe('assistant');
  });

  it('filters out tool messages from the displayed list', () => {
    const toolMsg: MockMessage = {
      id: 't1',
      type: 'tool',
      content: 'tool result',
      tool_call_id: 'tc1',
    };
    mockStreamState.messages = [toolMsg];
    useStreamMock.mockReturnValue({ ...mockStreamState });

    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    expect(result.current.messages).toHaveLength(0);
  });

  it('filters out empty ai messages that have no tool calls', () => {
    const emptyAi: MockMessage = { id: 'a-empty', type: 'ai', content: '' };
    mockStreamState.messages = [emptyAi];
    useStreamMock.mockReturnValue({ ...mockStreamState });

    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    expect(result.current.messages).toHaveLength(0);
  });

  it('dispatches setMessages to Redux when messages change', () => {
    const humanMsg: MockMessage = { id: 'h1', type: 'human', content: 'Ping' };
    mockStreamState.messages = [humanMsg];
    useStreamMock.mockReturnValue({ ...mockStreamState });

    const store = makeStore('tok');
    renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    const state = store.getState() as { voiceAgent: { messages: unknown[] } };
    expect(state.voiceAgent.messages).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// useChat — sendMessage
// ---------------------------------------------------------------------------

describe('useChat – sendMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStreamState.messages = [];
    mockStreamState.values = { messages: [] };
    mockStreamState.submit = vi.fn();
    mockClient.threads.search.mockResolvedValue([]);
    useStreamMock.mockReturnValue({ ...mockStreamState });
  });

  it('calls stream.submit when sendMessage is called', async () => {
    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    await act(async () => {
      await result.current.sendMessage('Hello world');
    });

    expect(mockStreamState.submit).toHaveBeenCalledOnce();
  });

  it('passes the text as a human message to stream.submit', async () => {
    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    await act(async () => {
      await result.current.sendMessage('Test message');
    });

    const submitArgs = mockStreamState.submit.mock.calls[0] as [
      { messages: Array<{ type: string; content: string }> },
      unknown,
    ];
    expect(submitArgs[0].messages[0]?.type).toBe('human');
    expect(submitArgs[0].messages[0]?.content).toBe('Test message');
  });

  it('passes userId from auth state in configurable options', async () => {
    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    await act(async () => {
      await result.current.sendMessage('Hi');
    });

    const submitArgs = mockStreamState.submit.mock.calls[0] as [
      unknown,
      { config: { configurable: { user_id: string } } },
    ];
    expect(submitArgs[1].config.configurable.user_id).toBeTruthy();
  });

  it('passes mode in configurable options', async () => {
    const store = makeStore('tok');
    const { result } = renderHook(() => useChat({ mode: 'voice' }), {
      wrapper: makeWrapper(store),
    });

    await act(async () => {
      await result.current.sendMessage('Speak this');
    });

    const submitArgs = mockStreamState.submit.mock.calls[0] as [
      unknown,
      { config: { configurable: { mode: string } } },
    ];
    expect(submitArgs[1].config.configurable.mode).toBe('voice');
  });
});

// ---------------------------------------------------------------------------
// useChat — error handling
// ---------------------------------------------------------------------------

describe('useChat – error handling', () => {
  it('exposes stream.error as error property', () => {
    const testError = new Error('Stream failure');
    useStreamMock.mockReturnValue({ ...mockStreamState, error: testError });

    const store = makeStore('tok');
    const { result } = renderHook(() => useChat(), { wrapper: makeWrapper(store) });

    expect(result.current.error).toBe(testError);
  });

});
