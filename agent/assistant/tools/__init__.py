from assistant.tools.web import web_search, fetch_url
from assistant.tools.news import news_search, news_world, news_wiki, news_subreddit
from assistant.tools.weather import get_weather
from assistant.tools.finance import get_exchange_rate
from assistant.tools.memory import memory_store, memory_retrieve, memory_search, memory_list, memory_delete, memory_tools

web_tools = [web_search, fetch_url]
news_tools = [news_search, news_world, news_wiki, news_subreddit]
weather_tools = [get_weather]
finance_tools = [get_exchange_rate]
all_tools = web_tools + news_tools + weather_tools + finance_tools + memory_tools

__all__ = ["all_tools"]
