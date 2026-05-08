import asyncio
import json
import os
from typing import Any, List


async def load_mcp_tools() -> List[Any]:
    try:
        mcp_config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "mcp.json"
        )

        if not os.path.exists(mcp_config_path):
            return []

        with open(mcp_config_path, "r") as f:
            mcp_config = json.load(f)

        servers_config = mcp_config.get("mcpServers", {})

        if not servers_config:
            return []

        from langchain_mcp_adapters import MultiServerMCPClient
        client = MultiServerMCPClient(servers_config)
        mcp_tools = await client.get_tools()

        return mcp_tools
    except Exception as e:
        print(f"Warning: Failed to load MCP tools: {e}")
        return []


def get_mcp_tools() -> List[Any]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return []
        return loop.run_until_complete(load_mcp_tools())
    except RuntimeError:
        return asyncio.run(load_mcp_tools())


__all__ = ["load_mcp_tools", "get_mcp_tools"]
