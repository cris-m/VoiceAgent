---
name: time-management
description: Real-time time and timezone management for personal assistant. Handles current time queries, timezone conversions, time comparisons across zones, schedule coordination, and time-aware reminders.
license: Apache-2.0
compatibility: Designed for VoiceAgent personal-assistant
metadata:
  author: agent
  version: "1.0"
  agent-affinity: ["voice_agent", "personal_assistant"]
---

# Time & Timezone Management Skill

## Purpose

Provide accurate, real-time time information across multiple timezones. Enable schedule coordination across regions, calculate time deltas, validate timezone names, and support time-aware task scheduling for a personal voice assistant.

## When to Use This Skill

Use when queries contain these keywords:
- **Current time**: "What time is it?", "what's the current time", "it's X o'clock"
- **Timezone conversion**: "What time is it in Tokyo?", "Convert 3pm EST to PST", "What's 2am UTC in London?"
- **Time comparisons**: "When is the call?", "How much time until...", "In how many hours..."
- **Schedule coordination**: "Find a time that works for...", "Schedule meeting across zones", "What time works for everyone?"
- **Time zones**: "List all timezones", "Is 'America/New_York' valid?", "IANA timezone"
- **Spoken time**: "What time is it in words?", "Tell me the time naturally"

## Prerequisites

### Available Tools

| Tool | Purpose | Parameters |
|---|---|---|
| `time_current(timezone)` | Get current time in any IANA timezone | timezone: str (e.g., 'America/New_York', 'Asia/Tokyo') |
| `time_convert(source_tz, time_str, target_tz)` | Convert time between timezones | source_tz, time_str (format: '14:30'), target_tz |
| `time_timezone_list()` | List all 400+ IANA timezones | None |
| `time_word_clock(timezone, precision)` | Express time in English words | timezone, precision: 'minute'/'5min'/'hour' (default: 'minute') |
| `time_timezone_validate(timezone)` | Validate timezone string | timezone: str |

### Timezone Database

- **Source**: IANA Time Zone Database
- **Coverage**: 400+ timezones (includes historical changes, DST rules)
- **Update frequency**: Automatic (via pytz)
- **Accuracy**: Account for DST, UTC offsets, historical changes

## Step 1 -- Current Time Queries

### Basic "What time is it?" Pattern

```python
# User: "What time is it in London?"
time_current("Europe/London")
# Returns: ISO datetime + day of week + formatted string

# User: "It's 3pm here. What time is it in Tokyo?"
time_current("Asia/Tokyo")
# Compare with user's local time automatically
```

### Spoken Time (Natural Language)

```python
# User: "Tell me the time in words"
time_word_clock("America/New_York", precision="minute")
# Returns: "It's a quarter past two in the afternoon" (2:15 PM)

# With less precision for announcements
time_word_clock("Europe/Paris", precision="hour")
# Returns: "It's two o'clock in the afternoon" (2:XX PM)
```

### When NOT to Use convert()

If user asks "What time is it in X?", use `time_current(X)` directly, NOT convert.
Convert is for "I have a specific time and need to know what it is in another zone."

---

## Step 2 -- Timezone Conversions

### Convert a Specific Time

```python
# User: "My meeting is at 2pm EST. What time is that in Pacific?"
time_convert("US/Eastern", "14:00", "US/Pacific")
# Returns: 11:00 AM Pacific

# User: "Schedule 9am Tokyo time - what's that for London?"
time_convert("Asia/Tokyo", "09:00", "Europe/London")
# Returns: 1:00 AM London (or 2:00 AM depending on DST)
```

### Format for time_convert()

| Parameter | Format | Examples |
|---|---|---|
| source_tz | IANA string | "US/Eastern", "Europe/London", "Asia/Tokyo" |
| time_str | "HH:MM" (24-hour) | "14:00", "09:30", "23:45" |
| target_tz | IANA string | "US/Pacific", "Australia/Sydney" |

**Important**: time_convert uses current date for DST calculations. If conversion spans DST boundaries, result includes DST offset for today.

---

## Step 3 -- Timezone Validation & Discovery

### Validate User Input

```python
# User: "Convert 2pm 'EST' to PST"
# First validate the timezone strings
time_timezone_validate("EST")  # Result: false (EST is not IANA)
time_timezone_validate("US/Eastern")  # Result: true

# Guide user: "I need 'US/Eastern' instead of 'EST'. Ready to convert?"
```

### Find Timezone for City

```python
# User: "What's the timezone for Sydney?"
# Not directly in tools, but respond:
# "Sydney is in 'Australia/Sydney' (UTC+10/+11 with DST)"

# Suggest: time_current("Australia/Sydney")
```

### List Available Timezones

```python
# User: "What timezones do you know?"
timezones = time_timezone_list()
# Returns: ["Africa/Abidjan", "Africa/Accra", ..., "UTC", "Etc/Zulu"] (400+ total)

# In voice response, never list all. Instead:
# "I can convert to any IANA timezone - over 400 options. Name a city or region?"
```

---

## Step 4 -- Schedule Coordination

### Find overlapping work hours across timezones

```
Scenario: User is in New York, needs to schedule with team in London and Tokyo

**Pattern**:
1. Get current time in each zone
2. Ask for work hour preferences (e.g., "9am-6pm local")
3. Find overlapping window
4. Confirm time in all zones
```

**Example Response**:
```
User: "Schedule a meeting with London at 10am their time. What time is that for me and Tokyo?"

Step 1: time_current("Europe/London") → 10:00 AM London
Step 2: time_convert("Europe/London", "10:00", "America/New_York") → 5:00 AM NY
Step 3: time_convert("Europe/London", "10:00", "Asia/Tokyo") → 7:00 PM Tokyo

Response: "That's 5am here (very early!), and 7pm in Tokyo (after work). 
Should we find a better time? 
How about 2pm London time? That would be 9am here and 11pm Tokyo."
```

---

## Step 5 -- Time-Aware Context

### Calculate Time Deltas

```python
# User: "When is the standup?"
# (Assume metadata says: next_standup_time = "14:30")
current_time = time_current("America/New_York")  # e.g., 14:15
# Delta: 15 minutes away

Response: "Your standup is in 15 minutes at 2:30pm"
```

### Relative Time Expressions

- "In 5 minutes" = current time + 5 min
- "At 3pm" = 3:00 PM today (or tomorrow if already past)
- "Tonight" = between now and midnight
- "Tomorrow morning" = next day 6am-12pm
- "Next week" = 7-14 days from now

---

## Step 6 -- DST & Edge Cases

### Daylight Saving Time

```python
# DST transitions happen on specific dates by timezone
# time_convert() automatically handles DST for the current date

# Example: US transitions first Sunday in March
# Mar 8, 2:00 AM → 3:00 AM EST (spring forward)

# If user asks: "Convert 2:30am EST on March 8"
time_convert("US/Eastern", "02:30", "US/Pacific")
# Result: 11:30 PM Pacific (previous day)
# Because that time doesn't exist (EST skips to 3am)
```

### Historical Timezone Changes

- Some timezones have changed UTC offset (rare but real)
- pytz handles these automatically
- Example: India Standard Time (IST) changed in 1950s

If user queries historical dates, time_current() uses today's rules. For exact historical data, note limitation: "I calculate based on current DST rules."

---

## Step 7 -- Voice-Specific Patterns

### Announce Time Naturally

```python
# For voice output, never say "14:00"
word_clock = time_word_clock("America/New_York")
# "It's two o'clock in the afternoon"
# NOT: "It's 14:00" or "It's 14 hundred hours"

# Include day for future times:
# "It's Friday at 3:15 in the afternoon in London"
# (day is in returned string automatically)
```

### Disambiguation

```
User: "What time is it in New York?"
Agent: "It's 2:15 PM in New York."

User: "And London?"
Agent: "It's 7:15 PM in London - 5 hours ahead."

User: "What about Sydney?"
Agent: "Sydney is 16 hours ahead of New York, so it's 6:15 AM tomorrow morning there."
```

---

## Common Pitfalls

### 1. Confusing timezone abbreviations with IANA names

**Problem**: User says "EST" or "PST" → these are NOT valid IANA timezones
**Solution**: 
- EST = "US/Eastern" (Eastern Standard Time, winter)
- PST = "US/Pacific" (Pacific Standard Time, winter)
- For current time, always use IANA names: `time_current("US/Eastern")`
- Validate first: `time_timezone_validate(user_input)`

### 2. Forgetting DST exists

**Problem**: Converting 2:30 AM on DST transition day fails
**Solution**: time_convert() handles it automatically. If time doesn't exist, it returns the next valid time.

### 3. Saying times wrong for voice

**Problem**: Speaking "14:00" aloud → user hears "fourteen hundred"
**Solution**: Use time_word_clock() → "two o'clock in the afternoon"

### 4. Not asking for clarification on ambiguous zones

**Problem**: User says "What's 3pm in 'EST'?" → EST is ambiguous (can mean Eastern or others)
**Solution**: Ask "Do you mean US/Eastern?" before converting

### 5. Assuming user's timezone

**Problem**: Converting without knowing user's home timezone
**Solution**: Establish timezone early: "Where are you?" or use configurable default

### 6. Incorrect time_convert() format

**Problem**: Passing "3:00 PM" instead of "15:00" or "3pm" instead of "03:00"
**Solution**: Convert input to 24-hour "HH:MM" format before calling

---

## Validation Checklist

Before responding with time information:

- [ ] For "What time is it in X?", used `time_current()`, not `convert()`?
- [ ] Timezone name is valid IANA format (not abbreviated)?
- [ ] Validated timezone with `time_timezone_validate()` if uncertain?
- [ ] Time format for convert is "HH:MM" (24-hour)?
- [ ] Using natural language in voice output (not "14:00", but "two pm")?
- [ ] Included day of week for clarity when needed?
- [ ] Noted any DST considerations if relevant?
- [ ] Avoided timezone abbreviations (EST, PST) in tool calls?
- [ ] Checked if user meant "today" or "tomorrow" for ambiguous times?

---

## Quick Reference: Common Timezones

| Region | IANA Timezone | UTC Offset (Standard) |
|---|---|---|
| New York | US/Eastern | UTC-5 (EST) |
| Los Angeles | US/Pacific | UTC-8 (PST) |
| London | Europe/London | UTC+0 (GMT) |
| Paris | Europe/Paris | UTC+1 (CET) |
| Dubai | Asia/Dubai | UTC+4 |
| Tokyo | Asia/Tokyo | UTC+9 |
| Sydney | Australia/Sydney | UTC+10 (standard) |
| UTC | UTC | UTC+0 |

