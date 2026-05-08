import logging
import os
import re
from typing import Literal

from langchain_core.tools import tool

from assistant.config import Configuration

logger = logging.getLogger(__name__)


def _search_duckduckgo(query: str, max_results: int, topic: str) -> dict:
    from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

    backend = "news" if topic == "news" else "text"
    wrapper = DuckDuckGoSearchAPIWrapper(max_results=max_results, backend=backend)
    raw = wrapper.results(query, max_results=max_results)

    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("link", ""),
            "content": r.get("snippet", ""),
            "score": None,
        }
        for r in raw
    ]
    return {"results": results, "source": "duckduckgo"}


def _strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"</?(p|br|div|h[1-6]|li|tr)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
        .replace("&quot;", '"')
    )
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

@tool
def web_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news"] = "general",
) -> dict:
    """Search the web for current information.

    Tries Tavily first (requires TAVILY_API_KEY). Falls back to DuckDuckGo
    automatically when the key is absent or Tavily is unavailable.

    Args:
        query: Search query — use targeted phrases for best results.
        max_results: Number of results to return (default: 5).
        topic: "general" for reports/data, "news" for current events.

    Returns:
        dict with "results" list (title, url, content) and "source" key.
    """
    config = Configuration.from_runnable_config()
    tavily_key = os.environ.get("TAVILY_API_KEY", "")

    if tavily_key:
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=tavily_key)
            result = client.search(query, max_results=max_results, topic=topic)
            result["source"] = "tavily"
            return result
        except Exception as e:
            logger.warning(f"Tavily search failed, falling back to DuckDuckGo: {type(e).__name__}: {e}")

    try:
        return _search_duckduckgo(query, max_results, topic)
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {type(e).__name__}: {e}")
        return {"error": f"All search backends failed: {type(e).__name__}: {e}", "results": []}


@tool
def fetch_url(
    url: str,
    timeout: int = 15,
    extract_content: bool = True,
    max_chars: int = 8000,
) -> dict:
    """Fetch the full content of a web page.

    Useful for reading complete text of a source found via web_search.
    Tries Tavily Extract first, then falls back to direct httpx fetch.

    Args:
        url: The full URL to fetch (must start with http:// or https://).
        timeout: Maximum seconds to wait (default: 15).
        extract_content: If True, return clean plain text. If False, raw HTML.
        max_chars: Truncate content to this many characters (default: 8000).

    Returns:
        dict with url, content, and status_code.
    """
    if not url.startswith(("http://", "https://")):
        return {"url": url, "content": "Invalid URL: must start with http:// or https://", "status_code": None}

    api_key = os.environ.get("TAVILY_API_KEY")
    if api_key:
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
            result = client.extract(urls=[url])
            if result and result.get("results"):
                page = result["results"][0]
                content = page.get("raw_content", "")
                return {"url": url, "content": content[:max_chars], "status_code": 200}
        except Exception as e:
            logger.warning(f"Tavily extract failed for {url}, falling back to httpx: {type(e).__name__}: {e}")

    # httpx fallback when Tavily isn't configured or its extract fails.
    try:
        import httpx

        connect_timeout = min(10, timeout)
        httpx_timeout = httpx.Timeout(timeout=float(timeout), connect=float(connect_timeout))
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; VoiceAgent/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(
            follow_redirects=True,
            timeout=httpx_timeout,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
        ) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            final_url = str(response.url)

            if not extract_content:
                return {"url": final_url, "content": response.text[:max_chars], "status_code": response.status_code}

            content = _strip_html(response.text)
            return {"url": final_url, "content": content[:max_chars], "status_code": response.status_code}

    except Exception as e:
        return {"url": url, "content": f"Fetch failed [{type(e).__name__}]: {e}", "status_code": None}
