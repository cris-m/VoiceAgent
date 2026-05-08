# Client

React 19 + Vite + RTK Query frontend. Voice mode (WebSocket plus AudioWorklet), streaming chat (LangGraph SDK), narration, transcription, and music generation.

For overall architecture see [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). For full-stack setup see the [project README](../README.md).

## Stack

- React 19 with strict mode
- TypeScript with `paths` aliases (`@/`, `@components/`, `@hooks/`, etc.)
- Vite for dev server and production build
- RTK Query for HTTP and Redux Toolkit for state
- Tailwind CSS
- Vitest in jsdom for tests

## Layout

```
src/
├── components/
│   ├── Alert/, Chat/, ErrorBoundary/, ProtectedRoute.tsx, VoiceSettings/
│   ├── layouts/   AppNavigationSidebar/, ConverseLayout/, MainLayout/
│   └── ui/        AudioWaveform/, VoiceOrb/
├── pages/         Converse/, Login/, Music/, Narrate/, Register/, Transcribe/
├── hooks/         useAuth, useChat, useVoiceAgent, useAudioPlayer, useMusic, useNarrate, useVoiceClone
├── services/      auth/, voice/, music/, personality/  (RTK Query API slices)
├── store/         single Redux slice for voice state
├── features/auth/ Redux slice + selectors for the auth session
├── context/       VoiceConfigContext
├── routes/        route table
├── schemas/       Zod schemas (login, register)
├── lib/           API client wrapper
├── types/         shared TS types
├── utils/         formatTime, formatFileSize
└── test/          Vitest setup (mocks AudioContext, WebSocket, etc.)
```

Every folder has an `index.ts` barrel. Tests live under each folder's `__tests__/` subdirectory.

## Configuration

`client/.env` (copy from `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `VITE_LANGGRAPH_API_URL` | `/api` | LangGraph SDK base URL (proxied by nginx). |
| `VITE_API_URL` | `http://localhost:8000` | Backend HTTP base URL. |
| `VITE_AGENT_API_BASE` | `/api/v1/agent` | Agent thread CRUD passthrough. |
| `VITE_CHAT_API_ENDPOINT` | `/api/runs/stream` | LangGraph streaming endpoint. |

These are inlined into the public bundle at build time. No secrets here.

## Run it

Inside the dev stack:

```bash
docker compose -f ../docker-compose.dev.yml up -d
# Open http://localhost:8080 (nginx) or http://localhost:3000 (direct Vite)
```

Standalone (requires backend and agent running on `localhost:8000` and `localhost:8001`):

```bash
npm install
npm run dev
```

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Vite dev server with HMR on port 3000. |
| `npm run build` | Type-check via project references and produce `dist/`. |
| `npm run preview` | Serve the production build locally. |
| `npm run lint` | ESLint over `src/`. |
| `npm run type-check` | `tsc -b` without emit. |
| `npm test` | Vitest in watch mode. |
| `npm test -- --run` | Single-shot test run (used by CI). |
| `npm run coverage` | Vitest with coverage report. |

## Key hooks

- **`useChat`**. Wraps `useStream` from `@langchain/langgraph-sdk/react`. Owns thread CRUD, streaming, branching (edit and retry), and the Redux mirror of messages.
- **`useVoiceAgent`**. Owns the WebSocket lifecycle, the AudioWorklet capture pipeline, barge-in handling (per-source `BufferSourceNode.stop`), and the StrictMode double-connect guard.
- **`useAudioPlayer`**. Element-level audio playback for narration, music, and transcription pages. Handles the once-per-element `createMediaElementSource` constraint.
- **`useMusic`, `useNarrate`, `useVoiceClone`**. Page-specific RTK Query wrappers.

## RTK Query and auth

`services/auth/baseQuery.ts` wraps RTK Query's base query with:

- A mutex that serializes refresh attempts so a thundering herd of 401s only triggers one refresh.
- An auto-refresh-and-retry on 401.
- Error normalization. Backend returns `{ error: { code, message } }`; the base query reshapes it into a stable client-side `NormalizedError` type.

Every API slice (`authApi`, `voiceApi`, `musicApi`, `personalityApi`) consumes this base query.

## Testing

Vitest with jsdom and `@testing-library/react`. Setup file at `src/test/setup.ts` mocks `AudioContext`, `MediaRecorder`, `getUserMedia`, `AudioWorkletNode`, `localStorage`, and `WebSocket` so tests run without a browser.

```bash
npm test -- --run               # full suite, no watch
npm test -- --run useChat       # filter by name
```

The 16 test files cover all hooks, the Redux slice, the auth flow, every RTK Query slice, the AudioWaveform component, and the auth integration path.

## Production build

```bash
npm run build
```

Outputs `dist/`. Vite splits the LangGraph SDK into its own chunk (`langgraph.js`) via `rollupOptions.output.manualChunks`. The 500 kB chunk warning is informational (the main bundle is ~760 kB raw, ~236 kB gzip).

## Useful tips

- If your editor shows phantom `Cannot find module '@/...'` errors, restart the TypeScript server. The path config has `paths` without `baseUrl` (modern bundler resolution); some editors cache the old shape.
- Voice mode requires the backend WebSocket at `/api/v1/voice/ws`. If the orb stays stuck on "connecting", check `docker compose logs backend` for the connection.
- Microphone access requires HTTPS in production (or `localhost` in dev). The browser blocks `getUserMedia` on plain HTTP.
