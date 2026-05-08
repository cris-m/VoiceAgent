---
name: information-retrieval
description: Search and information retrieval for personal assistant. Handles web search, fact lookup, latest news, weather data, and contextual information gathering.
license: Apache-2.0
compatibility: Designed for VoiceAgent personal-assistant
metadata:
  author: agent
  version: "1.0"
  agent-affinity: ["voice_agent", "personal_assistant"]
---

# Information Retrieval Skill

## Purpose

Provide fast, accurate information retrieval across web search, news, weather, market data, and reference materials. Support fact-checking, staying updated on current events, and contextual lookups for decision-making.

## When to Use This Skill

Use when queries contain these keywords:
- **Web search**: "Look up", "Search for", "Find", "What is", "Tell me about", "How do I", "Definition of"
- **News**: "Latest news", "What's happening", "In the news", "Recent", "Breaking", "Current events"
- **Weather**: "Weather", "How's the weather", "Forecast", "Is it raining", "Temperature"
- **Market data**: "Stock price", "Currency", "Market", "Bitcoin", "Exchange rate"
- **Fact-checking**: "Is it true that", "Verify", "Fact check", "Confirm"
- **Location info**: "How far is", "Travel time", "Distance to", "Where is"

## Prerequisites

### Available Tools

| Tool | Purpose | Parameters |
|---|---|---|
| `web_search(query, count)` | Search web for information | query: str, count: int (default: 10) |
| `fetch_url(url)` | Fetch and summarize URL content | url: str |
| `news_search(query, region)` | Search news articles | query: str, region: str (default: 'world') |
| `news_africa(query)` | African news focus | query: str |
| `news_world(query)` | International news | query: str |
| `get_weather(location)` | Current weather and forecast | location: str (city/coordinates) |
| `get_exchange_rate(from_currency, to_currency)` | Currency conversion | from_currency: str, to_currency: str |
| `get_market_prices(commodity, region)` | Commodity/market data | commodity: str, region: str |

### Data Sources

- **Web Search**: Real-time indexing, multiple sources per query
- **News**: Global news feeds, regional filtering available
- **Weather**: Multi-day forecasts, alerts for severe weather
- **Currency**: Live exchange rates between major currencies
- **Update Frequency**: Real-time for web/news, hourly for weather and currency

---

## Step 1 -- Web Search Queries

### Basic Lookup Pattern

```python
# User: "What is the capital of Australia?"
web_search(
    query="capital of Australia",
    count=5
)
# Returns: [
#   {"title": "Canberra is the capital...", "url": "...", "snippet": "..."},
#   ...
# ]

# Summarize: "The capital of Australia is Canberra. It was chosen as a compromise between Sydney and Melbourne."

# User: "How do I fix a leaky kitchen sink?"
web_search(query="how to fix leaky kitchen sink", count=10)
# Top results likely from DIY sites, plumbing guides
```

### When to Use web_search vs fetch_url

- **web_search**: General questions, definitions, comparisons ("What are the differences between...")
- **fetch_url**: Need detailed info from specific source, want full article content
- **Combined**: Search first (to find relevant sources), then fetch URL if user asks "Tell me more"

### Search Strategy

```python
# User: "I'm thinking about adopting a dog - what should I know?"
web_search(
    query="dog adoption guide first time owner",
    count=10
)
# Collate: temperament, costs, training, healthcare into consolidated response

# User: "Compare Python and JavaScript for backend development"
web_search(query="Python vs JavaScript backend 2026", count=10)
# Extract: performance, frameworks, ecosystem, job market, learning curve
```

---

## Step 2 -- News & Current Events

### Search News by Topic

```python
# User: "What's the latest on AI regulations?"
news_search(
    query="AI regulations 2026",
    region="world"
)
# Returns: 5-10 most recent articles from credible sources

# User: "Any news from Africa today?"
news_africa(query="technology news")
# Focus African news with global implications

# User: "What's happening in the Middle East?"
news_world(query="Middle East", region="middle_east")
```

### News Summarization for Voice

```
User: "Give me a quick news update"

Strategy:
1. news_search(query="latest news", region="world") → get 5 top stories
2. news_search(query="tech news") → 2-3 tech stories
3. news_search(query="finance markets") → 1-2 market stories

Voice response format:
"Here's what's happening in the news today:

[Top story 1]: Brief summary in 1 sentence
[Top story 2]: Brief summary
Technology: [1-2 line update]
Markets: [1-line update]"
```

---

## Step 3 -- Weather Information

### Current Weather & Forecast

```python
# User: "What's the weather like?"
# Requires: establish user location (stored from profile or ask)
get_weather(location="New York")
# Returns: {
#   "current": {"temp": 72, "condition": "Sunny", "humidity": 60},
#   "forecast": [
#     {"date": "2026-04-16", "high": 75, "low": 60, "condition": "Partly cloudy"},
#     ...
#   ]
# }

# Voice response: "It's 72 degrees and sunny in New York right now. 
# Tomorrow will be partly cloudy with a high of 75."

# User: "Should I bring an umbrella?"
get_weather(location="New York")
# Check forecast: if rain predicted, suggest "Yes, rain is forecasted"
# If clear, suggest "No, clear skies expected"
```

### Weather-Aware Task Suggestions

```
Integrate with task-management skill:
- If rain forecasted: "Don't forget your umbrella for that 2pm outdoor meeting"
- If hot: "Stay hydrated during your jog today"
- If cold: "Bundle up for your morning run"
```

---

## Step 4 -- Currency Exchange

```python
# User: "How much is 100 USD in EUR?"
get_exchange_rate(base="USD", targets=["EUR"])
# Returns: {"base": "USD", "rates": {"EUR": 0.92}, "date": "2026-05-08"}

# Response: "100 US dollars is about 92 euros at today's mid-market rate."
```

---

## Step 5 -- Fact-Checking & Verification

### Verify Claims

```python
# User: "Is it true that drinking 8 glasses of water a day is necessary?"
web_search(query="8 glasses water myth fact check 2026", count=10)
# Look for sources: medical, scientific consensus
# Respond: "That's actually a myth. Most health experts recommend drinking 
# enough water so your urine is light colored, which varies by person and activity."

# User: "Confirm: COVID vaccines have microchips?"
web_search(query="COVID vaccine microchips fact check", count=5)
# Authoritative sources: CDC, WHO, Snopes
# Respond: "No, that's a widespread false claim. Vaccines contain no microchips."
```

### Citation in Voice

When fact-checking, cite source authority:
- "According to the Mayo Clinic..." (medical)
- "A 2025 study found..." (research)
- "Multiple credible sources confirm..." (consensus)

---

## Step 6 -- Context-Aware Information

### Enriching Conversations

```
Scenario: User mentions a place, person, or event in conversation

User: "I'm traveling to Japan next month"
Agent: Proactively gather:
- web_search("Japan travel tips 2026")
- get_weather(location="Tokyo")
- news_search("Japan current events 2026")
→ Store context for future questions about Japan during conversation
```

### Connected Information

Link information across skills:
- Search for: "weather" → integrate with task-management ("Don't forget umbrella for meeting")
- Search for: "news about company X" → link to calendar if user has meeting with them
- Search for: "price of X" → use time-management to alert when price hits threshold

---

## Step 7 -- Handling Search Results

### Result Quality & Relevance

```python
# User: "What's the best programming language?"
web_search(query="best programming language 2026", count=10)
# Recognize: this has subjective answers, not one "best"

# Aggregate response:
# "Depends on your goal! Python is popular for data science and AI,
# JavaScript for web development, Go for microservices, Rust for systems programming."

# User: "Who won the 2026 championship?"
web_search(query="2026 championship winner", count=5)
# Check: is 2026 in past (when answering) or future?
# If future: "It hasn't happened yet"
# If past: cite the winner
```

### Handling "No Results"

```python
# User: "Tell me about fictional character XYZ"
web_search(query="fictional character XYZ", count=10)
# If no results: "I can't find information about that character. 
# Can you tell me which book/movie they're from?"

# User: "What's the weather on Mars?"
get_weather(location="Mars")
# Returns error (Mars not in service)
# Respond: "I can't get weather data for Mars, but I can tell you 
# about Mars conditions from NASA data if you'd like"
```

---

## Common Pitfalls

### 1. Stale Information in Web Results

**Problem**: Web search returns outdated articles
**Solution**: Check article dates in results, prioritize recent sources, note when data is from ("As of April 2026...")

### 2. Misinformation in Search Results

**Problem**: Top results include false or misleading content
**Solution**: Cross-reference with multiple sources, cite authoritative sources (CDC, WHO, academic journals), flag if claims are disputed

### 3. Too Much Information

**Problem**: Web search returns 1000s of results, voice response becomes overwhelming
**Solution**: Limit to top 5-10 results, synthesize into 2-3 key points, offer to "Tell me more" if user wants details

### 4. Missing User Location for Weather

**Problem**: "What's the weather?" without knowing where user is
**Solution**: Establish location early: "You mentioned you're in New York - weather there is..."
Or ask: "Where are you located?"

### 5. Conflicting Information

**Problem**: Different sources say different things
**Solution**: 
- Acknowledge: "Sources are mixed on this"
- Cite both: "Some experts believe X, others argue Y"
- Defer to consensus: "Most credible sources agree..."

### 6. Outdated Market Data

**Problem**: Exchange rates, stock prices, commodity prices change constantly
**Solution**: Note timestamp ("As of 2pm today"), suggest checking live sources for trading decisions

### 7. Context Loss Between Searches

**Problem**: User asks follow-up question, agent forgets previous search context
**Solution**: Cache search results and context within conversation session, reuse if relevant

---

## Validation Checklist

Before responding with retrieved information:

- [ ] Used appropriate tool for query type (web_search vs news_search vs get_weather)?
- [ ] For general questions, used `web_search()` not `fetch_url()`?
- [ ] For news updates, used `news_search()` or `news_africa()` as appropriate?
- [ ] For weather, established user location or asked for it?
- [ ] For market data, noted timestamp of prices/rates?
- [ ] Synthesized multiple results into concise summary?
- [ ] Cited authoritative sources when fact-checking?
- [ ] Checked article/data dates to ensure freshness?
- [ ] Offered "Tell me more" option if response was condensed?
- [ ] Flagged conflicting information if sources disagree?

---

## Quick Reference: Tool Selection

| Query Type | Tool | When to Use |
|---|---|---|
| Definition, explanation, how-to | web_search | General knowledge |
| Specific article deep-dive | fetch_url | After search finds relevant source |
| Breaking news, current events | news_search | Latest updates |
| African news focus | news_africa | Regional interest |
| Weather & forecast | get_weather | Location-based conditions |
| Currency conversion | get_exchange_rate | Financial calculations |
| Commodity/market prices | get_market_prices | Agricultural/financial data |
