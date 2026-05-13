# Contributing

Pull requests are welcome. This guide covers local setup, change-management conventions, and a few project-specific rules worth knowing before you open a PR.

## Local development

The recommended path is the Docker dev stack. It gives you the full pipeline (nginx → backend, agent, postgres, redis) with hot reload on both Python services and the React client.

```bash
git clone https://github.com/<you>/voiceagent.git
cd voiceagent

cp .env.example .env
cp backend/.env.example backend/.env
cp agent/.env.example agent/.env
cp client/.env.example client/.env

# Set OPENAI_API_KEY (or any LangChain-compatible provider) in agent/.env
docker compose -f docker-compose.dev.yml up -d
```

Open <http://localhost:8080>.

Rebuild from scratch after dependency changes:

```bash
docker compose -f docker-compose.dev.yml build --no-cache && docker compose -f docker-compose.dev.yml up -d --build
```

### Watching logs

```bash
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f agent
docker compose -f docker-compose.dev.yml logs -f client
```

### Restarting a single service

```bash
docker compose -f docker-compose.dev.yml restart backend
```

`restart` keeps the env from the last `up`. If you change a `.env` file, use `up -d backend` instead. That recreates the container and reloads `env_file`.

### Without Docker

You will need:

- Python 3.11 with `uv` recommended
- Node 18 or newer
- ffmpeg (`apt install ffmpeg` or `brew install ffmpeg`)
- PostgreSQL 16
- Redis 7

```bash
# Backend
cd backend
uv sync
uvicorn main:app --reload --port 8000

# Agent (in another terminal)
cd agent
uv sync
langgraph dev

# Client (in another terminal)
cd client
npm install
npm run dev
```

Without nginx, hit the client directly at <http://localhost:5173>. Backend lives at <http://localhost:8000>, agent at <http://localhost:8001>. Configure the client's `VITE_API_URL` to point at the backend.

## Branches and PRs

- `main` is the integration branch. Keep it green.
- Feature branches: `feature/<short-description>`.
- Bug fixes: `fix/<short-description>`.
- One logical change per PR. If your change touches both backend and frontend, that is fine. Split if it is hard to review together.

Before opening a PR:

1. Run the linters and tests for the area you touched.
2. Update docs if you changed user-visible behavior or env vars.
3. Make sure your commit history is readable. Squash merges are fine; no enforced history style.

## Code style

| Area | Tooling |
|---|---|
| Python | PEP 8 plus ruff. `cd backend && uv run ruff check .` and the same in `agent/`. |
| TypeScript / React | ESLint plus Prettier. `cd client && npm run lint && npm run type-check`. |
| Comments | Explain WHY, not WHAT. If removing a comment would not confuse a future reader, do not write it. |
| Tests | `pytest` for Python, `vitest` for the client. New hooks and components should ship with at least a smoke test. |

A few project-specific rules:

- Do not add migration-history banners to file headers (`# Migrated from X to Y`). Git history captures that.
- System prompts in `agent/assistant/prompt.py` are load-bearing. Changes there affect every conversation. Review carefully.
- Capability flags belong on TTS providers, not in routes. If you add a new TTS provider, override `supports_speed`, `supports_language`, and `supports_voice_cloning` on the class. The UI gates controls based on `/voice/config`.
- The voice WebSocket message types are part of the public protocol. Adding a new one is fine. Renaming or removing requires a coordinated client and backend change.

## Tests

```bash
# Backend
docker exec voiceagent-backend-dev pytest

# Frontend
docker exec voiceagent-client-dev npm test
docker exec voiceagent-client-dev npm run type-check
```

CI runs the same commands. PRs that fail CI will not merge.

## Reporting bugs

Open an issue with:

- What you did
- What you expected
- What actually happened
- Logs from the affected service (`docker compose logs <service>`)
- Browser console output if the bug is on the client

For latency or quality issues with the voice pipeline, also attach:

- The `[Latency]` lines from `docker compose logs backend`
- The `STT_PROVIDER`, `TTS_PROVIDER`, `WHISPER_MODEL`, and any non-default VAD settings from your `backend/.env`

## Reporting security vulnerabilities

Do not open a public issue. See [SECURITY.md](SECURITY.md) for the disclosure process.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
