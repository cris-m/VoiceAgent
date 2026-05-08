# VoiceAgent

A reference implementation showing how to integrate AI into modern applications: real-time voice, streaming chat, narration, transcription, voice cloning, and music generation in one codebase.

It is meant to be read, modified, and copied from. It is not a library and not a hosted service.

## Why this exists

Most AI tutorials stop at `openai.chat.completions.create(...)`. Production systems need much more: streaming, real-time voice, interrupts, branching, persistent memory, multiple providers, and a UI built around all of them. This repository puts those concepts in one place so engineers can study a working example instead of stitching one together from blog posts.

## What it demonstrates

| Capability | What you get |
|---|---|
| Real-time voice | Two-way spoken conversation with barge-in, pause, and resume. |
| Streaming chat | Token-level streaming into the React UI, sharing memory with voice mode. |
| Branching | Edit any past message and re-run from that point; the original branch is preserved. |
| Persistent memory | Conversations and user preferences survive restarts. |
| Tool calling | Web search, news, weather, exchange rates, tasks, notes. |
| Provider swapping | One environment variable selects between OpenAI, Anthropic, Ollama, NVIDIA NIM, or anything else `init_chat_model` supports. |
| Narration | Text input to a clean audio file with chunked synthesis and capability-driven UI. |
| Transcription | Audio uploads (WAV, MP3, M4A, WebM, OGG, FLAC, MP4) to text. |
| Voice cloning | Reference clip to a custom voice usable across the app. |
| Music generation | Text prompt to audio file with background model warmup. |

```
You speak  →  Silero VAD detects end-of-turn  →  Whisper transcribes  →
LangGraph agent reasons + streams tokens  →  Pocket / Kokoro TTS  →  You hear
```

Every feature is plain code with no hidden SaaS at the bottom of the call stack.

## Where to read what

| To learn how to... | Open... |
|---|---|
| Run a voice pipeline (mic, VAD, STT, LLM, TTS, speaker) | [`backend/api/routes/v1/voice.py`](backend/api/routes/v1/voice.py). Four asyncio tasks decoupled by queues. |
| Stream LLM tokens to a browser over WebSocket | Same file (`response_orchestrator`, `tts_streamer`). |
| Integrate Silero VAD with proper hysteresis | [`backend/services/vad/silero.py`](backend/services/vad/silero.py) |
| Detect barge-in cleanly | Two-phase confirmation in `voice.py` plus the BufferSource cleanup in [`client/src/hooks/useVoiceAgent.ts`](client/src/hooks/useVoiceAgent.ts) |
| Build a LangGraph agent with tools, skills, memory | [`agent/assistant/graph.py`](agent/assistant/graph.py) and the middleware stack |
| Switch system prompts between voice and chat | [`agent/assistant/prompt.py`](agent/assistant/prompt.py) and `select_prompt` in `graph.py` |
| Run Whisper for low-latency STT on CPU | [`backend/services/stt/whisper.py`](backend/services/stt/whisper.py) (greedy decoding, warmup) |
| Put two TTS providers behind a capability flag | [`backend/services/tts/base.py`](backend/services/tts/base.py) plus the Kokoro and Pocket TTS files |
| Auto 401, refresh, retry with RTK Query | [`client/src/services/auth/baseQuery.ts`](client/src/services/auth/baseQuery.ts) |
| Design a WebSocket protocol for a voice agent | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Gate UI controls on backend capabilities | The page components read `/voice/config` flags before rendering. |
| Reverse-proxy a multi-service stack with WebSocket upgrade | [`nginx/config/nginx-dev.conf`](nginx/config/nginx-dev.conf) |
| Run Python and Node services in Docker with hot reload | [`docker-compose.dev.yml`](docker-compose.dev.yml) |

The full walkthrough of the voice pipeline (VAD state machine, AEC, latency budget, barge-in, agent integration, complete WebSocket protocol) lives in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Status

All features run end-to-end: voice, chat, narration, transcription, music, voice cloning. The repository is intended for learning rather than direct production deployment. The API surface and configuration schema may still change. Known limitations:

- Multi-user isolation is partial. The LangGraph thread store is shared.
- The personality system is wired through the UI but not yet plumbed into the agent prompt.
- A few legacy environment entries (e.g. `STT_PROVIDER=kyutai`) are not active.

If you adopt code from this repository, pin to a commit and review the production checklist below.

## Services

| Service | Stack | Purpose |
|---|---|---|
| `backend/` | FastAPI, uvicorn | HTTP and WebSocket APIs for voice, narrate, transcribe, music, voice cloning, auth, file storage. |
| `agent/` | LangGraph, DeepAgents | Reasoning agent with tools, skills, persistent memory, provider-agnostic LLM selection. |
| `client/` | React 19, Vite, RTK Query | Real-time UI: streaming chat, voice with waveform, capability-driven settings. |
| `nginx/` | nginx 1.27 | Reverse proxy with WebSocket upgrade. |
| `postgres` | PostgreSQL 16 | LangGraph checkpoints, threads, accounts. |
| `redis` | Redis 7 | Token blacklist, rate-limit counters. |

## Run it locally

```bash
git clone https://github.com/<you>/voiceagent.git
cd voiceagent

# Copy every env example. None of the .env files are tracked by git.
cp .env.example .env
cp backend/.env.example backend/.env
cp agent/.env.example agent/.env
cp client/.env.example client/.env

# Minimum edit: open agent/.env and set OPENAI_API_KEY (or any other
# provider supported by LangChain init_chat_model).

docker compose -f docker-compose.dev.yml up -d
```

Open <http://localhost:8080>.

First boot pulls model weights (~2 GB Whisper plus ~80 MB Kokoro or ~500 MB Pocket TTS). Subsequent starts use the cache and complete in seconds.

## Configuration

Each service has its own `.env`. The project-root `.env` is intentionally minimal; service configuration lives in `backend/.env` and `agent/.env`.

### `backend/.env`

| Variable | Default | Purpose |
|---|---|---|
| `STT_PROVIDER` | `whisper` | Speech-to-text. Only `whisper` is wired today. |
| `WHISPER_MODEL` | `distil-large-v3` | `tiny`, `base`, `small`, `medium`, `large-v3`, `distil-large-v3`. Distil-large-v3 is the best speed and accuracy tradeoff on CPU. |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda`. |
| `TTS_PROVIDER` | `kokoro` | `kokoro` (8 voices, supports speed and language) or `pocket_tts` (27 voices, supports cloning). |
| `KOKORO_VOICE` | `af_heart` | Default voice for Kokoro. |
| `POCKET_TTS_VOICE` | `alba` | Default voice for Pocket TTS. |
| `POCKET_TTS_LANGUAGE` | `english` | Language is selected at model load. `english`, `french`, `german`, `spanish`, `italian`, `portuguese`. |
| `MUSIC_PROVIDER` | `ace_step` | `ace_step` (uses MusicGen-small) or `disabled`. |
| `VAD_THRESHOLD` | `0.5` | Silero activation threshold (range 0.0 to 1.0). |
| `VAD_MIN_SILENCE_DURATION_MS` | `300` | Required silence before VAD calls end-of-turn. Lower is snappier; higher reduces premature cutoffs. |
| `LANGGRAPH_URL` | `http://voiceagent-agent-dev:8000` | URL the backend uses to reach the agent. |
| `SECRET_KEY` | dev placeholder | **Set in production.** 32+ random characters. |
| `JWT_EXPIRATION_MINUTES` | `30` | Access token lifetime. |
| `HF_TOKEN` | empty | Required for voice cloning only. Generate at <https://huggingface.co/settings/tokens> and accept the gated model terms at <https://huggingface.co/kyutai/pocket-tts>. |
| `API_KEY` | empty | If set, every API call requires `Authorization: Bearer <key>`. |
| `CORS_ORIGINS` | localhost:5173, :3000, :8080, :80 | Add your production domain here. |

### `agent/.env`

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_MODEL` | `openai:gpt-4o-mini` | LangChain `init_chat_model` spec. Examples: `openai:gpt-4o-mini`, `anthropic:claude-3-5-haiku-20241022`, `ollama:llama3`. |
| `AGENT_TEMPERATURE` | `0.7` | Sampling temperature. |
| `MAX_RESULTS` | `5` | Default cap on Tavily and web-search results. |
| `OPENAI_API_KEY` | required for OpenAI | |
| `TAVILY_API_KEY` | required for `web_search` | |
| `LANGSMITH_API_KEY` | optional | Enables LangSmith tracing. |

The full annotated lists live in each `.env.example`.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (React)                         │
│   AudioWorklet capture (16 kHz int16)   ◀──── Web Audio playback│
└────────────────────────────┬────────────────────────────────────┘
                             │ WebSocket + HTTP
                             ▼
                    ┌─────────────────┐
                    │   nginx :8080   │
                    └────────┬────────┘
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   /api/v1/* (HTTP)      /api/v1/voice/ws     /api/* (HTTP, LangGraph SDK)
        │                    │                    │
        ▼                    ▼                    │
┌─────────────────────────────────────────────┐   │
│            backend (FastAPI :8000)          │   │
│ ─────────────────────────────────────────── │   │
│                                             │   │
│  Voice WebSocket pipeline:                  │   │
│                                             │   │
│   ┌────────┐                                │   │
│   │  mic   │ ─PCM─┐                         │   │
│   └────────┘      ▼                         │   │
│              ┌─────────┐   is_echo flag    │   │
│              │   AEC   │ ◀──────┐          │   │
│              │ (state) │        │          │   │
│              └────┬────┘        │          │   │
│                   ▼             │          │   │
│              ┌─────────┐        │          │   │
│              │  VAD    │        │          │   │
│              │(Silero) │        │          │   │
│              └────┬────┘        │          │   │
│                   ▼ end-of-turn │          │   │
│              ┌─────────┐        │          │   │
│              │  STT    │        │          │   │
│              │(Whisper)│        │          │   │
│              └────┬────┘        │          │   │
│                   ▼             │          │   │
│            agent.stream_events ─┼──────────┼──▶│
│                   │             │          │   │
│                   ▼             │          │ ◀─┤ tokens
│              ┌─────────┐        │          │   │
│              │  TTS    │ ───────┘          │   │
│              │(Kokoro/ │  (mark playing)   │   │
│              │ Pocket) │                   │   │
│              └────┬────┘                   │   │
│                   └────── PCM out ─────────┼───┼──▶ browser plays
│                                            │   │
│  HTTP routes:                              │   │
│   /narrate  /transcribe  /music  /clone    │   │
│   /auth     /personality                   │   │
└─────────────────────────────────────────────┘   │
                                                  ▼
                                       ┌──────────────────┐
                                       │   agent :8000    │
                                       │   (LangGraph)    │
                                       │ ──────────────── │
                                       │ tools:           │
                                       │   web, news,     │
                                       │   weather,       │
                                       │   finance,       │
                                       │   memory         │
                                       │ skills:          │
                                       │   time, task,    │
                                       │   info, ...      │
                                       └────────┬─────────┘
                                                │
        ┌───────────────────────────────────────┘
        ▼
┌──────────────────────────┐
│   Postgres   +   Redis   │
│   users, threads,        │
│   checkpoints, blobs     │
└──────────────────────────┘
```

The AEC box is a state flag rather than a DSP filter. It tracks whether TTS is currently playing so that VAD can decide whether incoming microphone audio is the agent's own voice bleeding back through the speaker. Real echo cancellation runs in the browser via `getUserMedia({ echoCancellation: true })`. The full explanation lives in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Anatomy of one voice turn

```
  user starts speaking
        │
        ▼
  AudioWorklet captures 16-kHz int16 PCM in 100 ms chunks
        │
        ▼
  WebSocket sends each chunk to the backend
        │
        ▼
  per-connection Silero VAD updates state
   (SILENCE → SPEECH_START → SPEAKING → SPEECH_END)
        │
        ▼   end-of-utterance after 300 ms of silence
        ▼
  Whisper (greedy, beam=1) transcribes accumulated audio
        │
        ▼
  semantic-turn check: if the last word is hanging (modal,
  conjunction, preposition, disfluency) hold for 700 ms
        │
        ▼
  agent.stream_events(thread_id, text, mode="voice", voice_name=...)
        │
        ▼   tokens stream back as the LLM produces them
        ▼
  sentence-boundary splitter pushes complete sentences
  (or first comma break for low first-byte latency) into a TTS queue
        │
        ▼
  Pocket TTS or Kokoro streams audio chunks
        │
        ▼
  WebSocket sends int16 PCM back to the browser
        │
        ▼
  AudioWorklet decodes and plays via the Web Audio scheduler
```

While the agent is speaking, the same VAD watches for the user starting again. After 200 ms of confirmed speech, an `interrupt` message is sent, the TTS queue drains, the audio context is recreated, and the orchestrator stops.

## Voice WebSocket protocol

Endpoint: `ws://<host>/api/v1/voice/ws`

### Client to server

| Message | Notes |
|---|---|
| binary frame (Int16Array) | 16-kHz mono PCM. The browser captures at 48 kHz and resamples client-side. |
| `{type: "config", voice_id, personality_id, speed, language}` | Sent on connect and on any change. `speed` and `language` are honored only if the active TTS provider supports them. |
| `{type: "text_input", text}` | Bypasses STT and sends text directly to the agent. |

### Server to client

| Message | When |
|---|---|
| `{type: "thread", thread_id}` | Once, immediately after connect. |
| `{type: "thread_title", thread_id, title}` | After the first user transcript; auto-titles the conversation. |
| `{type: "vad", state, probability, is_speaking, is_echo, is_responding}` | On VAD state changes (rate-limited). |
| `{type: "partial_transcript", text, is_final}` | Live transcript updates. Final fires when end-of-turn is confirmed. |
| `{type: "text_stream", text, done}` | LLM token stream for the in-progress AI message bubble. |
| `{type: "spoken_text", text}` | Sentence-by-sentence record of what TTS will speak (post-sanitization). |
| `{type: "audio_info", sample_rate}` | Once per response; the sample rate of the upcoming audio frames. |
| binary frame (Int16Array) | TTS audio. |
| `{type: "interrupt"}` | Server confirmed barge-in. The client should drop its playback queue. |
| `{type: "error", message}` | Pipeline error. |

## Development

Hot-reload stack:

```bash
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml logs -f backend
```

Restart a single service:

```bash
docker compose -f docker-compose.dev.yml restart backend
docker compose -f docker-compose.dev.yml restart agent
```

Tests:

```bash
docker exec voiceagent-backend-dev pytest
docker exec voiceagent-client-dev npm test
docker exec voiceagent-client-dev npm run type-check
```

For a non-Docker setup, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Production checklist

The repository is shaped for learning. To adapt it for production:

1. Replace `docker-compose.dev.yml` with a production compose. No bind mounts. Only nginx exposed. Set `ENVIRONMENT=production`.
2. Generate a real `SECRET_KEY` with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`.
3. Use a strong Postgres password and managed Redis.
4. Put nginx behind TLS (Let's Encrypt via Certbot, Cloudflare, or a load balancer).
5. Set `CORS_ORIGINS` to your real domain.
6. Pin Docker image tags so deploys are reproducible.

The full hardening checklist lives in [SECURITY.md](SECURITY.md).

## Project layout

```
voiceagent/
├── agent/                      LangGraph reasoning service
│   ├── assistant/
│   │   ├── graph.py            agent factory + middleware stack
│   │   ├── prompt.py           CHAT_SYSTEM_PROMPT, VOICE_SYSTEM_PROMPT
│   │   ├── config.py
│   │   ├── tools/              web, news, weather, finance, memory
│   │   └── skills/             time-management, task-management, ...
│   └── pyproject.toml
├── backend/                    FastAPI voice/narrate/music/auth API
│   ├── api/routes/v1/
│   │   ├── voice.py            voice WS + narrate + transcribe + clone
│   │   ├── agent.py            LangGraph thread CRUD passthrough
│   │   ├── music.py            music generation
│   │   ├── auth.py             login / register / refresh
│   │   └── personality.py
│   ├── services/
│   │   ├── voice_pipeline.py   STT + TTS + VAD orchestration
│   │   ├── stt/whisper.py
│   │   ├── tts/kokoro.py
│   │   ├── tts/pocket_tts.py
│   │   ├── vad/silero.py
│   │   ├── audio/aec.py
│   │   ├── agent/client.py     LangGraph SDK wrapper
│   │   └── music/ace_step.py
│   └── pyproject.toml
├── client/                     React 19 + Vite + RTK Query
│   ├── src/
│   │   ├── pages/              Converse, Narrate, Transcribe, Music
│   │   ├── components/
│   │   ├── hooks/              useVoiceAgent, useChat, useAudioPlayer
│   │   ├── services/           RTK Query APIs (auth, voice, music, personality)
│   │   ├── store/              Redux slice
│   │   └── context/            VoiceConfigContext
│   └── package.json
├── nginx/
│   ├── Dockerfile
│   └── config/                 nginx-dev.conf, nginx.conf, proxy.conf
├── docker-compose.dev.yml
├── docs/
│   └── ARCHITECTURE.md         deep dive on the voice pipeline
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

## Contributing

Pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, branch conventions, and the test harness.

## Security

Vulnerability reports go through [SECURITY.md](SECURITY.md).

## Acknowledgments

This project depends on work by several open-source teams:

- [LangChain and LangGraph](https://github.com/langchain-ai/langgraph). The agent runtime, checkpointing, and tool framework that the entire `agent/` service is built on.
- [Kyutai](https://kyutai.org/). [Pocket TTS](https://huggingface.co/kyutai/pocket-tts) provides 27 voices, voice cloning, and sub-200 ms first-byte latency on CPU.
- [Hexgrad / Kokoro](https://github.com/thewh1teagle/kokoro-onnx). The 82M-parameter ONNX TTS model used as the fast default voice without a GPU.
- [SYSTRAN / faster-whisper](https://github.com/SYSTRAN/faster-whisper). CTranslate2-optimized Whisper, roughly six times faster than the reference implementation on CPU.
- [Silero Team](https://github.com/snakers4/silero-vad). The 1.5 MB neural voice activity detector used for turn-taking and barge-in.
- [Open-Meteo](https://open-meteo.com/). Free, no-key weather API used by the agent's `get_weather` tool.
- [Tavily](https://tavily.com/). Web search and content extraction.

The research and models above are theirs. This repository shows one way to integrate them.

## License

[MIT](LICENSE).
