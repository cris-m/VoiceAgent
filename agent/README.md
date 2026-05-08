# Agent

LangGraph reasoning service. Receives user messages from the backend, calls tools, streams tokens back. Layered on top of `deepagents` with a middleware stack for prompt selection, token counting, retries, context editing, human-in-the-loop, and skills.

For overall architecture see [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). For full-stack setup see the [project README](../README.md).

## What it ships with

- **Tools** under `assistant/tools/`: `web_search` and `fetch_url` (web), `news_search` (news), `get_weather` (Open-Meteo), `get_exchange_rate` (finance), and a memory tool family (store, retrieve, search, delete).
- **Skills** under `assistant/skills/`: information-retrieval, time-management, task-management, memory, daily-summary. Each is a Markdown SKILL document loaded at runtime by `SkillsMiddleware`.
- **Two prompts** in `assistant/prompt.py`: `VOICE_SYSTEM_PROMPT` (terse, conversational, no markdown) and `CHAT_SYSTEM_PROMPT` (full-fat). Mode is selected per request via `select_prompt`.
- **Time MCP server** at `assistant/mcp/time_server/`: a small MCP-protocol server exposing timezone-aware helpers.

## Configuration

`agent/.env` (copy from `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_MODEL` | `openai:gpt-4o-mini` | LangChain `init_chat_model` spec. Examples: `openai:gpt-4o`, `anthropic:claude-3-5-haiku-20241022`, `ollama:llama3`, `nvidia:moonshotai/kimi-k2.5`. |
| `AGENT_TEMPERATURE` | `0.7` | Sampling temperature. |
| `MAX_RESULTS` | `5` | Default cap on Tavily and web-search results. |
| `OPENAI_API_KEY` | required for OpenAI | |
| `ANTHROPIC_API_KEY` | required for Anthropic | |
| `NVIDIA_API_KEY` | required for NVIDIA NIM | |
| `GOOGLE_API_KEY` | required for Google models | |
| `TAVILY_API_KEY` | required for `web_search` and `fetch_url` | |
| `HF_TOKEN` | optional | For HF-gated models if you switch to one. |
| `LANGSMITH_API_KEY` | optional | Enables LangSmith tracing. |
| `LANGSMITH_TRACING` | `false` | Set to `true` together with the API key. |
| `LANGCHAIN_PROJECT` | `voiceagent` | LangSmith project name. |

The provider selection is the only meaningful change you usually make. `init_chat_model` resolves the rest.

## Run it

Inside the dev stack:

```bash
docker compose -f ../docker-compose.dev.yml up -d agent
# LangGraph Studio at http://localhost:8001
```

Standalone:

```bash
cd agent
uv sync
langgraph dev --port 8001
```

LangGraph Studio shows the live state machine, runs, threads, and tool calls. Useful for debugging tool-loop pathology.

## Code layout

```
agent/
├── assistant/
│   ├── graph.py              create_deep_agent factory + middleware stack
│   ├── prompt.py             VOICE_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
│   ├── config.py             Configuration dataclass
│   ├── state.py              Agent state schema
│   ├── tools/                web, news, weather, finance, memory
│   ├── skills/               SKILL.md files (loaded by SkillsMiddleware)
│   ├── middlewares/          token_count_middleware
│   ├── backend/memory.py     Per-user-namespaced memory backend factory
│   └── mcp/time_server/      Standalone Time MCP server
├── langgraph.json            Graph and assistant manifest
├── pyproject.toml
└── uv.lock
```

## Middleware stack

Order matters. Defined in `graph.py`:

```
select_prompt
TokenCountMiddleware
ToolCallLimitMiddleware
retry middleware (×2, agent + tool)
ContextEditingMiddleware
HumanInTheLoopMiddleware(interrupt_on={memory_*})
SkillsMiddleware
```

Each layer wraps the next. `HumanInTheLoopMiddleware` is the reason memory writes and deletions pause until the client confirms.

## Adding a tool

```python
# agent/assistant/tools/my_tool.py
from langchain_core.tools import tool

@tool
def get_thing(query: str) -> str:
    """One-line description.

    The LLM reads this docstring to decide when to call this tool.
    Be specific about what the tool does, what arguments it accepts,
    and what the return value looks like. This is load-bearing.
    """
    return f"got: {query}"
```

Register it in `assistant/tools/__init__.py`. The `@tool` docstring becomes part of the tool description sent to the model on every call, so write it like documentation, not like a comment.

## Memory

Memories are namespaced per-user via `assistant/backend/memory.py::backend_factory(user_id)`. The agent can `memory_store`, `memory_retrieve`, `memory_search`, `memory_delete`. Destructive operations (`memory_delete`, sometimes `memory_store`) hit the `HumanInTheLoopMiddleware` interrupt list, which surfaces a confirmation event the client can render.

## Token counting

`TokenCountMiddleware` updates the agent state with prompt and response token counts on every LLM call. The state is exposed through the LangGraph SDK so the client can render running totals. See `assistant/middlewares/token_count_middleware.py`.

## Health

```bash
curl http://localhost:8001/ok
# 200 OK from LangGraph's built-in health endpoint
```

## Common gotchas

- **`ModuleNotFoundError: No module named 'assistant'`**. You ran `langgraph dev` from the wrong directory. Run it from `agent/`.
- **Recursion limit hit**. The agent is looping on a tool. Open LangGraph Studio at <http://localhost:8001> and check the trace. Common causes: a tool that returns the same string regardless of input, or a system prompt that requires a tool call that always fails.
- **`Tool execution requires approval` and nothing happens**. The agent called a memory tool that's gated by `HumanInTheLoopMiddleware`. The client needs to send the approval event. This is intentional and is the only safety gate on memory writes.
- **Rate limits on OpenAI**. Switch to `gpt-4o-mini` (`AGENT_MODEL=openai:gpt-4o-mini`) or to Ollama (`AGENT_MODEL=ollama:llama3`) for free local inference.

## Tracing

`LANGSMITH_API_KEY=...` plus `LANGSMITH_TRACING=true` plus `LANGCHAIN_PROJECT=voiceagent` and every run shows up at <https://smith.langchain.com>. Useful for understanding token spend per turn, retry behavior, and tool-call latency.
