import urllib.parse
from typing import Literal

import httpx
from langchain_core.tools import tool

_HEADERS = {
    "User-Agent": "VoiceAgent/1.0",
    "Accept": "application/json",
}
_TIMEOUT = 15


def _get(url: str) -> dict:
    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            r = client.get(url, headers=_HEADERS)
            r.raise_for_status()
            return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _reddit_posts(subreddit: str, sort: str, limit: int) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    res = _get(url)
    if not res["ok"]:
        return []
    children = res["data"].get("data", {}).get("children", [])
    return [
        {
            "title": p["data"]["title"],
            "score": p["data"]["score"],
            "comments": p["data"]["num_comments"],
            "date": p["data"].get("created_utc"),
            "url": (
                p["data"]["url"]
                if p["data"]["url"].startswith("http")
                else f"https://reddit.com{p['data']['permalink']}"
            ),
            "subreddit": p["data"]["subreddit"],
        }
        for p in children
        if p.get("data")
    ]


@tool
def news_search(
    query: str,
    limit: int = 15,
) -> dict:
    """Search for news articles about any topic across Reddit's worldnews and news subreddits.

    Args:
        query: Search query, e.g. "AI regulation EU" or "earthquake japan 2026".
        limit: Results per subreddit (default: 15).

    Returns:
        dict with "results" list (title, score, date, url, subreddit) sorted by score.
    """
    subreddits = ["worldnews", "news"]
    all_posts: list[dict] = []

    for sub in subreddits:
        encoded = urllib.parse.quote(query)
        url = (
            f"https://www.reddit.com/r/{sub}/search.json"
            f"?q={encoded}&restrict_sr=1&limit={limit}&sort=relevance&t=month"
        )
        res = _get(url)
        if not res["ok"]:
            continue
        children = res["data"].get("data", {}).get("children", [])
        for p in children:
            d = p.get("data", {})
            all_posts.append({
                "title": d.get("title", ""),
                "score": d.get("score", 0),
                "comments": d.get("num_comments", 0),
                "date": d.get("created_utc"),
                "url": (
                    d["url"]
                    if d.get("url", "").startswith("http")
                    else f"https://reddit.com{d.get('permalink', '')}"
                ),
                "subreddit": d.get("subreddit", sub),
            })

    all_posts.sort(key=lambda x: x["score"], reverse=True)
    return {
        "query": query,
        "count": len(all_posts),
        "results": all_posts[:limit],
    }




@tool
def news_world(
    limit: int = 20,
    sort: Literal["hot", "new", "top"] = "hot",
) -> dict:
    """Get latest world news headlines from Reddit worldnews.

    Args:
        limit: Number of posts to return (default: 20)
        sort: "hot" (trending), "new" (most recent), or "top" (most upvoted)

    Returns:
        dict with "posts" list.
    """
    posts = _reddit_posts("worldnews", sort, limit)
    return {
        "source": "reddit/r/worldnews",
        "sort": sort,
        "count": len(posts),
        "posts": posts,
    }


@tool
def news_wiki(limit: int = 10) -> dict:
    """Get recent news articles published on WikiNews.

    WikiNews articles are encyclopaedic, neutral, and fact-checked by editors —
    useful for verified recent events.

    Args:
        limit: Number of recent articles to return (default: 10)

    Returns:
        dict with "articles" list (title, date, url).
    """
    url = (
        "https://en.wikinews.org/w/api.php"
        f"?action=query&list=recentchanges&rcnamespace=0"
        f"&rclimit={limit}&rcprop=title|timestamp&format=json&origin=*"
    )
    res = _get(url)
    if not res["ok"]:
        return {"error": res["error"], "articles": []}

    changes = res["data"].get("query", {}).get("recentchanges", [])
    articles = [
        {
            "title": c["title"],
            "date": c["timestamp"],
            "url": "https://en.wikinews.org/wiki/" + urllib.parse.quote(c["title"].replace(" ", "_")),
        }
        for c in changes
    ]
    return {"source": "WikiNews", "count": len(articles), "articles": articles}


@tool
def news_subreddit(
    subreddit: str,
    limit: int = 15,
    sort: Literal["hot", "new", "top"] = "hot",
) -> dict:
    """Get posts from any specific subreddit.

    Args:
        subreddit: Subreddit name without r/ prefix, e.g. "technology", "science", "movies".
        limit: Number of posts (default: 15)
        sort: "hot", "new", or "top"

    Returns:
        dict with "posts" list.
    """
    posts = _reddit_posts(subreddit, sort, limit)
    return {
        "source": f"reddit/r/{subreddit}",
        "sort": sort,
        "count": len(posts),
        "posts": posts,
    }


@tool
def get_hacker_news_posts(
    limit: int = 20,
    story_type: Literal["top", "new", "best"] = "top",
) -> dict:
    """Get top tech and AI news from Hacker News.

    Hacker News is a curated tech/startup/AI news aggregator with high-quality posts
    and discussion. Useful for tracking AI advances, crypto/tech trends, and startup news.

    Args:
        limit: Number of stories to return (default: 20; max 30)
        story_type: "top" (most upvoted), "new" (newest), or "best" (editor picks)

    Returns:
        dict with "stories" list (title, score, comments, url, timestamp).
    """
    limit = min(limit, 30)

    endpoint_map = {
        "top": "topstories",
        "new": "newstories",
        "best": "beststories",
    }
    endpoint = endpoint_map.get(story_type, "topstories")

    ids_url = f"https://hacker-news.firebaseio.com/v0/{endpoint}.json"
    ids_res = _get(ids_url)
    if not ids_res["ok"]:
        return {"error": f"Failed to fetch story IDs: {ids_res['error']}", "stories": []}

    story_ids = ids_res["data"][:limit]

    stories = []
    for story_id in story_ids:
        story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        story_res = _get(story_url)
        if not story_res["ok"]:
            continue

        story = story_res["data"]
        if story.get("type") != "story":
            continue

        stories.append({
            "title": story.get("title", ""),
            "score": story.get("score", 0),
            "comments": story.get("descendants", 0),
            "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
            "timestamp": story.get("time"),
            "author": story.get("by"),
        })

    return {
        "source": "Hacker News",
        "story_type": story_type,
        "count": len(stories),
        "stories": stories,
    }
