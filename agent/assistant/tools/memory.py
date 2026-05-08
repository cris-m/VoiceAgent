from typing import Annotated
from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore


@tool
def memory_store(
    key: str,
    value: str,
    namespace: str = "memories",
    config: RunnableConfig = None,
    store: Annotated[BaseStore, InjectedStore()] = None,
) -> str:
    """Store a memory with key and value.

    Args:
        key: Memory key identifier
        value: Memory content (string)
        namespace: Memory namespace/category (default: 'memories')
        config: Runtime config with user_id
        store: Injected store

    Returns:
        Success message
    """
    if not config or "configurable" not in config:
        return "Error: No user context"

    user_id = config["configurable"].get("user_id")
    if not user_id:
        return "Error: User ID required"

    ns = (namespace, user_id)
    store.put(
        ns,
        key,
        {
            "value": value,
            "stored_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return f"Memory stored: {key}"


@tool
def memory_retrieve(
    key: str,
    namespace: str = "memories",
    config: RunnableConfig = None,
    store: Annotated[BaseStore, InjectedStore()] = None,
) -> str:
    """Retrieve a memory by key.

    Args:
        key: Memory key to retrieve
        namespace: Memory namespace/category (default: 'memories')
        config: Runtime config
        store: Injected store

    Returns:
        Memory value or error message
    """
    if not config or "configurable" not in config:
        return "Error: No user context"

    user_id = config["configurable"].get("user_id")
    ns = (namespace, user_id)

    item = store.get(ns, key)
    if not item:
        return f"Memory '{key}' not found"

    return item.value.get("value", "")


@tool
def memory_search(
    query: str,
    namespace: str = "memories",
    limit: int = 10,
    config: RunnableConfig = None,
    store: Annotated[BaseStore, InjectedStore()] = None,
) -> str:
    """Search memories by keyword or filter.

    Args:
        query: Search query
        namespace: Memory namespace (default: 'memories')
        limit: Max results (default: 10)
        config: Runtime config
        store: Injected store

    Returns:
        Search results
    """
    if not config or "configurable" not in config:
        return "Error: No user context"

    user_id = config["configurable"].get("user_id")
    ns = (namespace, user_id)

    items = store.search(ns, query=query, limit=limit)

    if not items:
        return f"No memories match '{query}'"

    results = []
    for item in items:
        results.append(f"• {item.key}: {item.value.get('value', '')}")

    return "\n".join(results)


@tool
def memory_list(
    namespace: str = "memories",
    limit: int = 20,
    config: RunnableConfig = None,
    store: Annotated[BaseStore, InjectedStore()] = None,
) -> str:
    """List all memories in a namespace.

    Args:
        namespace: Memory namespace (default: 'memories')
        limit: Max results (default: 20)
        config: Runtime config
        store: Injected store

    Returns:
        List of memory keys and values
    """
    if not config or "configurable" not in config:
        return "Error: No user context"

    user_id = config["configurable"].get("user_id")
    ns = (namespace, user_id)

    items = store.search(ns, limit=limit)

    if not items:
        return f"No memories in {namespace}"

    results = []
    for item in items:
        results.append(f"• {item.key}: {item.value.get('value', '')}")

    return "\n".join(results)


@tool
def memory_delete(
    key: str,
    namespace: str = "memories",
    config: RunnableConfig = None,
    store: Annotated[BaseStore, InjectedStore()] = None,
) -> str:
    """Delete a memory.

    Args:
        key: Memory key to delete
        namespace: Memory namespace (default: 'memories')
        config: Runtime config
        store: Injected store

    Returns:
        Success or error message
    """
    if not config or "configurable" not in config:
        return "Error: No user context"

    user_id = config["configurable"].get("user_id")
    ns = (namespace, user_id)

    item = store.get(ns, key)
    if not item:
        return f"Memory '{key}' not found"

    store.delete(ns, key)
    return f"Memory deleted: {key}"


memory_tools = [
    memory_store,
    memory_retrieve,
    memory_search,
    memory_list,
    memory_delete,
]
