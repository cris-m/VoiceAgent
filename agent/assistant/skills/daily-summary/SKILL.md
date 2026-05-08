---
name: daily-summary
description: Daily briefing and recap for personal assistant. Aggregates tasks, events, news, weather, and productivity metrics into natural voice summary.
license: Apache-2.0
compatibility: Designed for VoiceAgent personal-assistant
metadata:
  author: agent
  version: "1.0"
  agent-affinity: ["voice_agent", "personal_assistant"]
---

# Daily Summary & Briefing Skill

## Purpose

Deliver a natural, time-aware daily briefing that includes tasks to complete, calendar events, news updates, weather, and accomplishments. Provide structure without overwhelming the user—prioritize actionable items and positive reinforcement.

## When to Use This Skill

Use when queries contain these keywords:
- **Daily briefing**: "Good morning", "Daily summary", "What's on my agenda", "Give me a briefing"
- **Day recap**: "How was my day?", "What did I accomplish?", "Day summary", "Recap"
- **Quick check-in**: "What's coming up?", "Anything important today?", "Quick update"
- **Productivity stats**: "How many tasks done?", "How productive was I?", "Did I accomplish..."
- **Evening briefing**: "Good night", "Evening summary", "Tomorrow preview"
- **Weekly summary**: "Week in review", "What happened this week?", "Weekly recap"

## Prerequisites

### Integration with Other Skills

Daily-summary aggregates data from:
- **task-management**: Pending tasks, completed count, high-priority items due
- **time-management**: Current time, timezone, relative time (today, tomorrow, this week)
- **information-retrieval**: Latest news, weather, market updates
- **calendar** (optional): Scheduled events, meetings, block time

### Available Tools (Aggregators)

| Tool | Purpose | Parameters |
|---|---|---|
| `task_list(status)` | Get all tasks by status | status: 'pending'\|'completed' |
| `task_get_upcoming(days)` | Tasks due in N days | days: int (1-365) |
| `time_current(timezone)` | Current time for context | timezone: str |
| `news_search(query, region)` | News for briefing | query: varies by brief |
| `get_weather(location)` | Weather for day | location: str |
| `get_market_prices(commodity, region)` | Market data (optional) | commodity: str, region: str |

### Briefing Data

- **Scope**: Last 24h recap, next 24h agenda, weekly trends
- **Priorities**: High-priority tasks first, time-sensitive items next
- **Tone**: Conversational, encouraging, action-oriented
- **Length**: ~2-3 minutes of speaking time (keeps attention)

---

## Step 1 -- Morning Briefing Structure

### Welcome & Time Context

```python
# User: "Good morning" or "Morning briefing"

Step 1: Get current time and greet appropriately
time_current(user_timezone)
# If 6-9am: "Good morning!"
# If 9am-12pm: "Morning! Great to see you"
# If after 12pm: "Looks like it's already afternoon!"

Example opener:
"Good morning! It's Tuesday, April 15th at 8:30 AM. 
Let me catch you up on what's coming your way today."
```

### Agenda Preview

```python
# Step 2: Get today's tasks and upcoming events
pending_tasks = task_list(status="pending")
today_tasks = task_get_upcoming(days=1)  # Due today/tomorrow

# Step 3: Prioritize
high_priority = [t for t in today_tasks if t["priority"] == "high"]
normal_priority = [t for t in today_tasks if t["priority"] == "medium"]

# Step 4: Announce
if high_priority:
    print(f"You have {len(high_priority)} high-priority thing{'s' if len(high_priority) > 1 else ''}")
    for task in high_priority[:3]:  # Max 3 to keep brief
        print(f"  - {task['title']} (due {relative_time(task['due_date'])})")

if normal_priority:
    print(f"And {len(normal_priority)} regular task{'s' if len(normal_priority) > 1 else ''}")
    # Summarize without listing all
```

### Weather & Context

```python
# Step 5: Get weather
weather = get_weather(user_location)

# Integrate with tasks:
if "rain" in weather["condition"].lower():
    print(f"It's {weather['condition']}, so don't forget your umbrella 
            if you're heading out.")
else:
    print(f"Weather looks {weather['condition'].lower()} at {weather['temp']}°F.")
```

### Motivational Close

```
"You've got this! Here's what you need to tackle:
[3-5 most important items]

Good luck today!"
```

---

## Step 2 -- Evening / Day Recap

### Accomplishment Celebration

```python
# User: "Recap my day" (said in evening)

Step 1: Get completed tasks
completed_today = [t for t in task_list(status="completed") 
                   if t["completed_at"] is today]

# Celebrate completion count
if completed_today:
    print(f"Great job today! You completed {len(completed_today)} task{'s' if len(completed_today) > 1 else ''}:")
    # Highlight high-priority completions
    important = [t for t in completed_today if t["priority"] == "high"]
    if important:
        print(f"  Important wins: {', '.join(t['title'] for t in important)}")
else:
    print("Today was a lighter day - that's okay too!")
```

### Remaining Items

```python
# Step 2: What's left undone?
pending = task_list(status="pending")
urgent = [t for t in pending if t["due_date"] and date(t["due_date"]) <= today]

if urgent:
    print(f"You have {len(urgent)} task{'s' if len(urgent) > 1 else ''} still pending from today:")
    for task in urgent[:3]:
        print(f"  - {task['title']}")
    print("Want to knock a few more out before bed?")
```

### Tomorrow's Outlook

```python
# Step 3: What's coming tomorrow?
tomorrow_tasks = task_get_upcoming(days=2)  # Due tomorrow
tomorrow_high = [t for t in tomorrow_tasks if t["priority"] == "high"]

if tomorrow_tasks:
    print(f"Tomorrow you have {len(tomorrow_tasks)} task{'s' if len(tomorrow_tasks) > 1 else ''} scheduled.")
    if tomorrow_high:
        print(f"  {len(tomorrow_high)} are high priority")
        for t in tomorrow_high[:2]:
            print(f"    - {t['title']}")
```

---

## Step 3 -- Weekly Summary

### Week-in-Review

```python
# User: "Weekly summary" or "Week in review"

Step 1: Calculate metrics for last 7 days
last_7_days = datetime.now() - timedelta(days=7)
completed_week = [t for t in task_list(status="completed")
                  if t["completed_at"] >= last_7_days]
pending_week = task_get_upcoming(days=7)

# Step 2: Highlight trends
print(f"This week, you completed {len(completed_week)} task{'s' if len(completed_week) > 1 else ''}.")

if len(completed_week) > 10:
    print("That's excellent productivity!")
elif len(completed_week) > 5:
    print("Good steady progress.")
else:
    print("It was a lighter week.")

# Step 3: Theme or pattern?
# Group by category/tag
print(f"\nThis coming week ({next_week_start.strftime('%A')} onward):")
if pending_week:
    print(f"You have {len(pending_week)} tasks to work on")
    high_p = [t for t in pending_week if t["priority"] == "high"]
    if high_p:
        print(f"  {len(high_p)} are high priority")
```

---

## Step 4 -- News & Information in Briefing

### Relevant News Snippets

```python
# Optional: Include 1-2 news items if user asks for full briefing

# User: "Full briefing - include news"
news_items = news_search(query="technology business", region="world")
top_news = news_items[:2]  # Only top 2

print("Quick news update:")
for item in top_news:
    print(f"  - {item['title']} ({item['source']})")

# Don't include multiple news items unless specifically requested
# Keep focus on user's personal agenda
```

### Weather-Aware Tips

```
If rainy forecast tomorrow:
"By the way, rain is expected tomorrow, 
so plan indoor activities or bring an umbrella for your afternoon meeting."

If very hot:
"It's going to be hot tomorrow - stay hydrated and consider that outdoor jog for early morning."

If cold snap:
"Temperatures dropping tonight - bundle up for your commute tomorrow."
```

---

## Step 5 -- Adaptive Briefing Length

### Conciseness by Context

```python
# Morning (user probably in a hurry):
# Duration: 60-90 seconds
# Include: Top 3 tasks, weather, one motivational line

# Evening (more relaxed):
# Duration: 2-3 minutes
# Include: Day recap, tomorrow preview, weekly trend

# Full briefing (user explicitly asks):
# Duration: 4-5 minutes
# Include: Everything above + news, market data, detailed insights
```

### Dynamic Summarization

```
IF many high-priority tasks:
  Emphasize urgency: "You've got a busy day ahead!"
  
IF few tasks:
  Emphasize flexibility: "Pretty light agenda - good chance to catch up on other things"
  
IF mostly completed:
  Celebrate: "You're on a roll!"
  
IF many overdue/pending:
  Reframe: "Let's focus on what you can control today"
```

---

## Step 6 -- Special Briefing Types

### Pre-Meeting Briefing

```
User: "Brief me before my 2pm call with the client"

Step 1: Find that calendar event
calendar_event = find_event_at("14:00")  # 2pm

Step 2: Gather context
- client_name = calendar_event["participant"]
- web_search(f"recent news about {client_name}")
- Check related tasks: recent emails, documents

Step 3: Brief
"In 15 minutes you have a call with Acme Corp. 
Recent context: [2-3 bullet points from news/tasks]
You have these related tasks: [list]
Good luck!"
```

### Travel Day Briefing

```
User: "I'm traveling to Tokyo today"

Step 1: Establish timezone
flight_tz = "Asia/Tokyo"
home_tz = "US/Eastern"

Step 2: Get context
get_weather(location="Tokyo")
news_search("Tokyo travel updates")

Step 3: Brief
"Safe travels! Here's what you need to know:

Destination: Tokyo
Local time on arrival: [time conversion]
Weather: [Tokyo forecast]
Tasks while traveling: [travel-specific only]

Have a great trip!"
```

---

## Step 7 -- Periodic Briefings

### Scheduled Daily Briefing

For users with voice wake-word or scheduled check-ins:

```python
# Automatically triggered at 8:00 AM
trigger_time = parse_time("08:00", user_timezone)

def auto_briefing():
    current = time_current(user_timezone)
    if current == trigger_time:
        return morning_briefing()
```

### Weekly Review Trigger

```python
# Every Friday afternoon
trigger_time = parse_time("17:00", user_timezone) on Friday

def auto_weekly_review():
    if is_friday_5pm(current_time, user_timezone):
        return weekly_summary()
```

---

## Common Pitfalls

### 1. Overwhelming Information Overload

**Problem**: Daily summary becomes 10-minute monologue with every detail
**Solution**: 
- Max 5-7 items per briefing
- Only high-priority or time-sensitive items
- Offer: "Want more details on anything?"

### 2. Stale Task Data

**Problem**: Task-list hasn't been updated, summary references old tasks
**Solution**: Always call task_list() fresh in each briefing, never cache

### 3. Wrong Time Context

**Problem**: "Good morning" briefing said in evening, or timezone mismatch
**Solution**: Call time_current(user_timezone) before generating greeting

### 4. Ignoring Completed Tasks' Psychological Value

**Problem**: Summary only focuses on what's left, ignores accomplishments
**Solution**: Always celebrate completions in recap, even if just "You finished that important task"

### 5. Too Much News/Market Data

**Problem**: User doesn't care about commodity prices or world news, wants personal briefing
**Solution**: Only include external information if:
  - User explicitly requested it
  - It's highly relevant to their tasks/events
  - Keep to 1-2 items max

### 6. Not Personalizing Tone

**Problem**: Generic briefing tone doesn't match user personality
**Solution**: 
- Track user preferences: brief vs detailed, formal vs casual
- Remember user context: vacation coming up? Project deadline? Health goal?

### 7. Time Zone Failures

**Problem**: "Your meeting is in 5 hours" but user is traveling
**Solution**: Establish timezone per briefing, use time_current(user_tz) consistently

---

## Validation Checklist

Before sending daily summary:

- [ ] Called `time_current()` to get greeting-appropriate time?
- [ ] Fetched fresh task list with `task_list()`, not cached data?
- [ ] Prioritized high-priority items to top of list?
- [ ] Included completion celebration for recap, not just pending items?
- [ ] Weather integrated naturally, not tacked on ("Don't forget umbrella")?
- [ ] Summary length appropriate for context (morning: brief, evening: relaxed)?
- [ ] Used natural language, not data format ("You've completed 5 things" not "5x completed=true")?
- [ ] All times expressed in user's timezone and relative (today, tomorrow, in 3 days)?
- [ ] Offered next steps: "Want to tackle the first task?" or "Anything else you need?"
- [ ] No external news/market data unless user requested or highly relevant?

---

## Quick Reference: Briefing Templates

| Briefing Type | Best Time | Duration | Key Sections |
|---|---|---|---|
| Morning | 6-9 AM | 60-90s | Greeting, top 3 tasks, weather, motivational close |
| Daytime | 9 AM-5 PM | 30-60s | "Quick update:" what's next? Any new high-priority? |
| Evening | 5-9 PM | 2-3 min | Day recap, completed count, tomorrow preview, well-done |
| Weekly | Friday 5 PM | 3-4 min | Week accomplishments, pending next week, trend |
| Full (requested) | Anytime | 4-5 min | All sections, news, market data, detailed outlook |

---

## Integration Points

Daily-summary connects all skills:
- **time-management**: Current time, relative time expressions, meeting context
- **task-management**: Pending/completed tasks, priorities, deadlines
- **information-retrieval**: News updates, weather, market context, research summaries
- **voice-specific output**: Natural language, appropriate pacing, emotional tone

Best practices:
- Call daily-summary explicitly after task/calendar changes
- Use as check-in hub: "Here's what's changed since last briefing"
- Celebrate wins: completion count, streak tracking, goal progress
