# VoiceAgent Agents - Instructions for AI Agents

This document provides guidance for AI agents working with the LangGraph agent implementation.

## Project Overview

VoiceAgent's **agents** folder contains the LangGraph-based AI agent orchestration:
- **Framework**: LangGraph (agent orchestration)
- **Agent Type**: Deep agent with tool access
- **Model**: Claude (via LangChain)
- **Tools**: Web search, news, weather, market data, finance + MCP tools
- **MCP Integration**: Time server (timezones, conversions)

**Stack**:
- Python 3.11+
- LangGraph + LangChain
- FastAPI (via LangGraph SDK)
- MCP (Model Context Protocol) servers
- PostgreSQL (for state persistence)

---

## User Memory & Learning

VoiceAgent learns and remembers user preferences across conversations via `/memories/user/AGENTS.md`.

### How User Memory Works

1. **Bootstrap**: Each user gets their own `/memories/user/AGENTS.md` seeded from `agent/user/AGENTS.md` template on first interaction
2. **Load**: At the start of every conversation, the agent reads the user's memory file
3. **Learn**: When you discover user preferences or patterns, update the file using `edit_file()` tool
4. **Persist**: Memory persists across all future conversations with that user

### What to Store in User Memory

- **Communication Style**: Tone, detail level, language preferences, format (bullets, examples, etc.)
- **Domain Expertise**: What the user knows, skill level, experience areas
- **Behavioral Patterns**: What approaches work best, successful interaction patterns
- **Important Context**: Background, constraints, goals, special requirements
- **Preferences**: Tool preferences, domain preferences, workflow preferences

### When to Update User Memory

Update `/memories/user/AGENTS.md` when:
- User explicitly states a preference: "I prefer...", "I like...", "I hate..."
- User validates your approach: "Yes, exactly!", "Perfect", "That's what I needed"
- You recognize a successful pattern across multiple interactions
- User's needs contradict what you'd normally assume
- User teaches you about their domain, background, or constraints

### Example Update

```python
# When you learn a user preference
edit_file(
    path="/memories/user/AGENTS.md",
    operation="append",
    content="""

## Learned: Communication Style
User prefers technical depth with real code examples and benchmark data.
Appreciates concise explanations but with full context provided.
"""
)
```

### Best Practices

DO:
- Read user memory at conversation start to understand them
- Be proactive about learning and remembering
- Update memory when you discover patterns
- Incorporate user context into all responses
- Assume the user memory is accurate

DON'T:
- Store information that changes rapidly (session state, temporary decisions)
- Overwrite existing memory without reason
- Store sensitive data (passwords, keys)
- Make memory updates without confidence in learning

---

## Setup Commands

### Install Dependencies
```bash
cd agents
uv sync                    # Install from pyproject.toml
```

### Start Agent Server (Development)
```bash
cd agents
uv run langgraph dev       # Starts at http://localhost:8123
```

### Run Specific Graph
```bash
cd agents
uv run python -c "from flopsy.graph import agent; print(agent)"
```

### Test MCP Tools
```bash
cd agents
python -c "from flopsy.mcp import get_mcp_tools; tools = get_mcp_tools(); print([t.name for t in tools])"
```

### Test MCP Server (Time)
```bash
cd agent/flopsy/mcp/time_server
uv run server.py --timezone=UTC
```

---

## Project Structure

```
agent/
├── mcp.json                    # MCP server configuration
├── AGENTS.md                   # This file
├── pyproject.toml              # Dependencies
├── langgraph.json              # LangGraph deployment config
├── flopsy/
│   ├── __init__.py
│   ├── graph.py                # Agent graph definition 
│   ├── config.py               # Agent configuration
│   ├── prompt.py               # System prompt
│   ├── state.py                # State schema (if used)
│   ├── tools/
│   │   ├── __init__.py         # Tool exports
│   │   ├── web.py              # Web search, fetch_url
│   │   ├── news.py             # News tools
│   │   ├── weather.py          # Weather data
│   │   ├── finance.py           # Currency exchange
│   │   └── market.py            # Market prices
│   └── mcp/                    # MCP servers
│       ├── __init__.py         # load_mcp_tools(), get_mcp_tools()
│       └── time_server/        # Time MCP server
│           ├── server.py
│           └── timer_manager.py
└── .langgraph_api/             # LangGraph deployment state
```

---

## Key Files to Understand

### 1. **graph.py** - Agent Definition
```python
from flopsy.mcp import get_mcp_tools
from flopsy.tools import all_tools

mcp_tools = get_mcp_tools()
combined_tools = all_tools + mcp_tools

agent = create_deep_agent(
    name="voice_agent",
    model=model,
    tools=combined_tools,
    system_prompt=VOICE_AGENT_PROMPT,
)
```

**What it does**:
- Loads all regular tools (web, news, weather, finance, market)
- Loads all MCP tools (time-mcp tools)
- Creates LangGraph deep agent
- Binds tools to Claude model

### 2. **mcp/__init__.py** - MCP Tool Loading
```python
async def load_mcp_tools() -> List[Any]:
    """Load MCP tools from mcp.json via langchain-mcp-adapters"""

def get_mcp_tools() -> List[Any]:
    """Synchronous wrapper for synchronous contexts"""
```

**What it does**:
- Reads `mcp.json` configuration
- Creates `MultiServerMCPClient`
- Discovers and loads tools from all MCP servers
- Returns LangChain-compatible tools

### 3. **mcp.json** - MCP Server Configuration
```json
{
  "mcpServers": {
    "time-mcp": {
      "command": "uv",
      "args": ["--directory", "./flopsy/mcp/time_server", "run", "server.py", "--timezone=UTC"]
    }
  }
}
```

**What it does**:
- Defines all MCP servers
- Specifies how to start each server
- Configuration is auto-discovered by LangGraph

### 4. **tools/__init__.py** - Tool Exports
```python
from flopsy.tools.web import web_search, fetch_url
from flopsy.tools.news import news_search, ...
# ... all tools exported as groups
all_tools = web_tools + news_tools + weather_tools + ...
```

**What it does**:
- Exports individual tools
- Groups tools by category
- Exports `all_tools` list for agent

---

## Architecture Overview

### Tool Loading Pipeline

```
mcp.json
   ↓
graph.py imports get_mcp_tools()
   ↓
get_mcp_tools() reads mcp.json
   ↓
MultiServerMCPClient starts servers
   ↓
load_mcp_tools() retrieves tools
   ↓
Tools converted to LangChain format
   ↓
combined_tools = all_tools + mcp_tools
   ↓
agent = create_deep_agent(tools=combined_tools)
```

### Tool Categories

**Regular Tools** (in `flopsy/tools/`):
- Web: `web_search`, `fetch_url`
- News: `news_search`, `news_world`, `news_wiki`, `news_subreddit`
- Weather: `get_weather`
- Finance: `get_exchange_rate`

**MCP Tools** (in `flopsy/mcp/time_server/`):
- `time_current(timezone)` - Current time in any timezone
- `time_convert(source_tz, time_str, target_tz)` - Convert between timezones
- `time_timezone_list()` - All 400+ IANA timezones
- `time_word_clock(timezone)` - Time in English words
- `time_timezone_validate(timezone)` - Validate timezone string

---

## Code Conventions

### Python Style
- **Type hints**: Required for all functions
- **Naming**: snake_case for functions, PascalCase for classes
- **Imports**: Standard lib → third-party → local
- **Docstrings**: Google style with Args/Returns
- **Error handling**: Specific exceptions, return error dicts

**Example**:
```python
async def load_mcp_tools() -> List[Any]:
    """Load MCP tools from mcp.json configuration.
    
    Returns:
        List of LangChain-compatible tools from MCP servers
    """
    try:
        # Implementation
        return tools
    except Exception as e:
        print(f"Warning: Failed to load MCP tools: {e}")
        return []
```

### Tool Development
```python
@mcp.tool("tool_name")
def my_tool(param1: str, param2: int = 0, ctx: Context = None) -> dict:
    """Tool description with parameters.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)
        ctx: MCP context for logging
    
    Returns:
        Result dict or {"error": "message"} on failure
    """
    try:
        result = do_work(param1, param2)
        if ctx:
            ctx.info(f"Tool executed successfully")
        return result
    except Exception as e:
        if ctx:
            ctx.error(str(e))
        return {"error": str(e)}
```

---

## Common Tasks

### Add a New MCP Server

**1. Create directory**:
```bash
mkdir -p agent/flopsy/mcp/weather_server
```

**2. Implement server** (`agent/flopsy/mcp/weather_server/server.py`):
```python
from mcp.server.fastmcp import Context, FastMCP

class WeatherMCP:
    def __init__(self):
        self.mcp = FastMCP(name="Weather MCP")
        self.register_tools()
    
    def register_tools(self):
        @self.mcp.tool("get_weather")
        def get_weather(city: str, ctx: Context = None) -> dict:
            """Get weather for a city."""
            try:
                result = {"city": city, "temp": 72}
                if ctx:
                    ctx.info(f"Weather for {city}")
                return result
            except Exception as e:
                if ctx:
                    ctx.error(str(e))
                return {"error": str(e)}
    
    def run(self):
        self.mcp.run(transport="stdio")

if __name__ == "__main__":
    WeatherMCP().run()
```

**3. Register in mcp.json**:
```json
{
  "mcpServers": {
    "time-mcp": { ... },
    "weather-mcp": {
      "command": "uv",
      "args": ["--directory", "./flopsy/mcp/weather_server", "run", "server.py"]
    }
  }
}
```

**4. Restart agent** → Tools auto-load from mcp.json

### Add a New Regular Tool

**1. Create file** (`agent/flopsy/tools/search.py`):
```python
async def search_images(query: str) -> dict:
    """Search for images."""
    # Implementation
    return {"results": []}
```

**2. Export in tools/__init__.py**:
```python
from flopsy.tools.search import search_images
search_tools = [search_images]
all_tools = web_tools + search_tools + ...
```

**3. Tool available to agent** → Agent can call it

### Test Tool Execution

```bash
# Test via Python
cd agents
python -c "
from flopsy.tools import all_tools
web_tool = [t for t in all_tools if t.name == 'web_search'][0]
result = web_tool.invoke({'query': 'test'})
print(result)
"

# Test MCP tool
python -c "
from flopsy.mcp import get_mcp_tools
tools = get_mcp_tools()
time_tool = [t for t in tools if 'time_current' in t.name][0]
"
```

---

## Configuration

### Model Selection (in `config.py`)
```python
model = init_chat_model("claude-3-5-sonnet-20241022")  # Default
# Or: init_chat_model("gpt-4")  # OpenAI
```

### Environment Variables
```bash
# .env file in agent/
ANTHROPIC_API_KEY=sk-ant-...
LANGGRAPH_API_KEY=...
```

---

## Troubleshooting

### "Failed to load MCP tools"
```bash
# Check mcp.json exists and is valid
python -m json.tool mcp.json

# Check time server starts
cd agent/flopsy/mcp/time_server
uv run server.py
```

### MCP server command not found
```bash
# Ensure dependencies installed
uv sync

# Verify uv is available
which uv
```

### Agent not using tools
```bash
# Verify tools are loaded
python -c "from flopsy.graph import combined_tools; print(len(combined_tools))"

# Check tool names
python -c "from flopsy.graph import combined_tools; print([t.name for t in combined_tools])"
```

### LangGraph dev server won't start
```bash
# Kill any existing process
lsof -i :8123
kill -9 <PID>

# Start again
uv run langgraph dev
```

---

## DO's ✅

- **Load MCP tools via mcp.json** — LangGraph auto-discovers
- **Use get_mcp_tools()** — Handles sync/async context
- **Type hint all functions** — Required for tool schemas
- **Return error dicts** — Never raise exceptions to agent
- **Use ctx for logging** — Structured via MCP context
- **Test tools independently** — Before adding to agent
- **Document tool parameters** — Agent uses docstring as schema
- **Handle missing timezones** — time-mcp supports all 400+ IANA zones

## DON'T ❌

- **Don't hardcode tool lists** — Use imports from tools/__init__.py
- **Don't modify mcp.json** — Only update via `mcpServers` key
- **Don't catch broad exceptions** — Be specific about errors
- **Don't skip type hints** — LangChain needs them for schemas
- **Don't ignore MCP context** — Log important events via ctx
- **Don't block long operations** — Use async/await
- **Don't create tools in graph.py** — Keep in separate modules

---

## Health Checks

```bash
# Check MCP tools load
cd agents
python -c "from flopsy.mcp import get_mcp_tools; print('Tools:', len(get_mcp_tools()))"

# Check all tools
python -c "from flopsy.tools import all_tools; print('All tools:', len(all_tools))"

# Check graph loads
python -c "from flopsy.graph import agent; print('Agent:', agent.name)"

# Test time-mcp server
python -c "
import asyncio
from flopsy.mcp import load_mcp_tools
tools = asyncio.run(load_mcp_tools())
print('MCP tools:', [t.name for t in tools if 'time' in t.name])
"
```

---

## Resources

- **MCP Documentation**: `MCP_INTEGRATION.md`
- **MCP Quick Reference**: `MCP_QUICK_REF.md`
- **Main AGENTS.md**: `../AGENTS.md` (project-wide)
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **MCP Spec**: https://modelcontextprotocol.io/

---

## Questions?

- Check tool implementations in `flopsy/tools/`
- Review `flopsy/mcp/time_server/` as MCP example
- Look at existing tool docstrings for schema patterns
- Test tools independently before integration
