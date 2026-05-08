---
name: memory
description: Personal memory and context management for voice assistant. Stores preferences, notes, personal information, and maintains conversation context across sessions.
license: Apache-2.0
compatibility: Designed for VoiceAgent personal-assistant
metadata:
  author: agent
  version: "1.0"
  agent-affinity: ["voice_agent", "personal_assistant"]
---

# Memory Management Skill

## Purpose

Maintain a persistent, contextual memory of user preferences, personal information, notes, and conversation history. Enable the assistant to remember important details about the user, provide personalized responses, and maintain continuity across multiple sessions.

## When to Use This Skill

Use when queries contain these keywords:
- **Remember/recall**: "Remember that...", "What did I tell you about", "Do you remember", "I mentioned earlier"
- **Note-taking**: "Make a note", "Write that down", "Save this", "I want to remember"
- **Preferences**: "I prefer", "My favorite", "I like", "I don't like", "I always"
- **Personal info**: "My name is", "I live in", "I work at", "My phone is", "Call me"
- **Context reference**: "Like before", "Similar to last time", "As I said", "You know I..."
- **Forgetting/updating**: "Forget that", "Update my", "That's changed", "I'm no longer"

## Prerequisites

### Available Tools

| Tool | Purpose | Parameters |
|---|---|---|
| `memory_store(key, value, namespace)` | Store memory entry | key: str, value: str, namespace: str (default: "memories") |
| `memory_retrieve(key, namespace)` | Retrieve specific memory | key: str, namespace: str (default: "memories") → returns value or error |
| `memory_search(query, namespace, limit)` | Search memories by keyword | query: str, namespace: str (default: "memories"), limit: int (default: 10) |
| `memory_list(namespace, limit)` | List all memories in namespace | namespace: str (default: "memories"), limit: int (default: 20) |
| `memory_delete(key, namespace)` | Delete memory entry | key: str, namespace: str (default: "memories") |

### Memory Storage

- **Scope**: User-isolated namespace (automatically scoped by `user_id` from runtime config)
- **Persistence**: PostgreSQL database (persistent across sessions)
- **Lifecycle**: Retained across sessions until explicitly deleted
- **Privacy**: User data never shared across accounts (enforced via user_id isolation)
- **Capacity**: Unlimited entries per user
- **Namespaces**: Organize memories by type (default: "memories", can use custom like "tasks", "preferences", "notes")

---

## Step 1 -- Storing Personal Information

### Basic Information Storage

```python
# User: "My name is Sarah"
memory_store(
    key="user_name",
    value="Sarah",
    namespace="personal"
)
# Response: "Got it, Sarah. I'll remember that."

# User: "I live in Kinshasa"
memory_store(
    key="user_location",
    value="Kinshasa",
    namespace="personal"
)
# Response: "I'll remember you're in Kinshasa."

# User: "I work as a software engineer"
memory_store(
    key="user_occupation",
    value="software engineer",
    namespace="personal"
)
```

### Structured Personal Data

```python
# User: "My timezone is America/New_York"
memory_store(
    key="user_timezone",
    value="America/New_York",
    namespace="personal"
)

# User: "My phone number is +243-123-456"
memory_store(
    key="user_phone",
    value="+243-123-456",
    namespace="personal"
)

# User: "My birthday is March 15, 1990"
memory_store(
    key="user_birthday",
    value="1990-03-15",
    namespace="personal"
)
```

---

## Step 2 -- Storing Preferences

### User Preferences

```python
# User: "I prefer email over phone calls"
memory_store(
    key="communication_preference",
    value="email",
    namespace="preferences"
)
# Response: "I'll remember you prefer email communication."

# User: "My favorite color is blue"
memory_store(
    key="favorite_color",
    value="blue",
    namespace="preferences"
)

# User: "I don't like spicy food"
memory_store(
    key="food_preference_spicy",
    value="dislike",
    namespace="preferences"
)

# User: "I always wake up at 6am"
memory_store(
    key="wake_time",
    value="06:00",
    namespace="preferences"
)
```

### Contextual Preferences

```python
# User: "I work from home on Tuesdays and Thursdays"
memory_store(
    key="work_location_pattern",
    value="Remote: Tuesday, Thursday | Office: Monday, Wednesday, Friday",
    namespace="preferences"
)

# User: "I prefer mornings for important calls"
memory_store(
    key="meeting_time_preference",
    value="morning",
    namespace="preferences"
)
```

---

## Step 3 -- Note-Taking & Quick Notes

### Simple Notes

```python
# User: "Make a note: call the plumber about the kitchen sink"
memory_store(
    key="note_plumber_call",
    value="Call plumber about kitchen sink",
    namespace="notes"
)
# Response: "Noted."

# User: "Write down: Sarah's email is sarah@company.com"
memory_store(
    key="contact_sarah_email",
    value="sarah@company.com",
    namespace="notes"
)
```

### Timestamped Notes

```python
# User: "Save this: the project deadline moved to April 20"
memory_store(
    key="note_project_deadline",
    value="Project deadline moved to April 20 (updated on 2026-04-15)",
    namespace="notes"
)
```

---

## Step 4 -- Retrieving Memories

### Recall Personal Information

```python
# User: "What's my timezone?"
tz = memory_retrieve(key="user_timezone", namespace="personal")
# Returns: "America/New_York"
Response: "Your timezone is America/New_York."

# User: "What's my name?"
name = memory_retrieve(key="user_name", namespace="personal")
# Returns: "Sarah"
Response: "Your name is Sarah."
```

### Recall Preferences

```python
# User: "Do you remember my favorite color?"
fav_color = memory_retrieve(key="favorite_color", namespace="preferences")
# Returns: "blue"
Response: "Your favorite color is blue."

# User: "What time do I usually wake up?"
wake = memory_retrieve(key="wake_time", namespace="preferences")
# Returns: "06:00"
Response: "You usually wake up at 6 in the morning."
```

### Search Across Memories

```python
# User: "Do you have any notes about the plumber?"
results = memory_search(query="plumber", namespace="notes", limit=10)
# Returns: "• note_plumber_call: Call plumber about kitchen sink"
Response: "I found a note: call the plumber about the kitchen sink."

# User: "What do you remember about my preferences?"
prefs = memory_list(namespace="preferences", limit=20)
# Returns: "• communication_preference: email\n• favorite_color: blue\n..."
Response: "I remember you prefer email communication, your favorite color is blue, and you like mornings for meetings."
```

---

## Step 5 -- Context & Continuity

### Reference Previous Conversations

```
Scenario: User mentions something in one session, references it later

Session 1:
  User: "I just got promoted to Senior Engineer"
  Agent: memory_store("user_role", "Senior Engineer", namespace="personal")

Session 2 (next day):
  User: "Congratulate me on my new role"
  Agent: memory_retrieve("user_role", namespace="personal") → "Senior Engineer"
         → "Congratulations on becoming a Senior Engineer! That's a big achievement."
```

### Contextual Personalization

```python
# When the user asks: "What's the weather?"
user_location = memory_retrieve("user_location", namespace="personal")
timezone = memory_retrieve("user_timezone", namespace="personal")

# Instead of asking "Where are you?", use stored location
weather = get_weather(location=user_location)
Response: "It's sunny and 25 degrees in Kinshasa right now."
```

### Cross-Skill Context

```
User: "Good morning"

Agent uses memory:
1. memory_retrieve("user_name", namespace="personal") → "Sarah"
2. memory_retrieve("user_timezone", namespace="personal") → "America/New_York"
3. time_current(timezone) → 8:30 AM
4. memory_list(namespace="preferences", limit=5) → "morning person" preference

Response: "Good morning, Sarah! It's 8:30 here on the East Coast. 
You usually have important things first thing in the morning—what would you like to focus on today?"
```

---

## Step 6 -- Updating & Maintaining Memories

### Update Information

```python
# User: "My timezone changed, I'm now in Africa/Kinshasa"
memory_store(
    key="user_timezone",
    value="Africa/Kinshasa",
    namespace="personal"
)
# Response: "Got it, I've updated your timezone to Kinshasa."

# User: "Actually, I prefer phone calls over email"
memory_store(
    key="communication_preference",
    value="phone",
    namespace="preferences"
)
# Response: "Updated. I'll remember you prefer phone calls."
```

### Delete Memories

```python
# User: "Forget that note about the plumber"
memory_delete(key="note_plumber_call", namespace="notes")
# Response: "✓ Memory deleted: note_plumber_call"

# User: "You don't need to remember my old address anymore"
memory_delete(key="user_address_old", namespace="personal")
# Response: "✓ Memory deleted: user_address_old"
```

### Clear Categories

```python
# User: "Clear all my notes"
notes = memory_list(namespace="notes", limit=100)
# Parse results and delete each note via:
memory_delete(key="note_key", namespace="notes")
# Response: "I've cleared all your notes."
```

---

## Step 7 -- Privacy & Data Management

### User Data Isolation

```python
# Memory store enforces user_id isolation at runtime
# User A's memories are never accessible to User B
# Each memory_store call is automatically scoped to (namespace, user_id)
# This isolation is enforced in the tools layer, not by explicit parameters
```

### Data Sensitivity

```python
# When storing sensitive information:
# - Passwords: DON'T store directly. Ask user not to provide.
# - API keys: DON'T store. User should keep secure.
# - Financial info: Store only what user explicitly requests (account last 4 digits, not full numbers)
# - Health info: Store only if user volunteers and requests persistence

# User: "Remember my bank account number is 1234567890"
# Agent: "I don't recommend storing full account numbers. Would you like to save just the last 4 digits instead?"
```

### Transparency

```
When storing sensitive info:
- Confirm: "I'll save that, but remember only you can access this."
- Remind: "This is saved securely in your personal memory."
- Option: "Want to delete this later? Just ask."
```

---

## Common Pitfalls

### 1. Forgetting to Store What the User Mentions

**Problem**: User says "I prefer tea over coffee" and agent doesn't store it
**Solution**: Proactively identify preference-laden statements and store them with memory_store()

### 2. Not Personalizing Enough

**Problem**: Agent responds generically when context is available
**Solution**: Always check memory_context() before responding; use user's name, location, timezone, preferences

### 3. Storing Incorrect Keys

**Problem**: Storing "favorite_color" instead with inconsistent key naming
**Solution**: 
- Use snake_case for keys (e.g., user_name, favorite_color)
- Follow pattern: {what_it_is}_{detail} (e.g., user_timezone, communication_preference, note_deadline)
- Use descriptive names that explain the memory's purpose
- Keep keys consistent across sessions (same key = same meaning)

### 4. Using Wrong Namespace

**Problem**: Storing personal info in "notes" namespace or preferences in "personal"
**Solution**: 
- "personal" namespace: User identity (name, location, contact)
- "preferences" namespace: Likes, dislikes, communication style, patterns
- "notes" namespace: Quick notes, reminders, saved info
- "memories" namespace: Default for general-purpose storage
- Use custom namespaces for domain-specific grouping (e.g., "health_goals", "project_info")

### 5. Overwriting Without Confirmation

**Problem**: "My name is John" followed by "Actually, it's Juan" — agent overwrites without asking
**Solution**: For updates, if the old value exists, confirm: "Should I change this from X to Y?"

### 6. Storing Too Much Detail

**Problem**: Storing entire email threads or long documents instead of summaries
**Solution**: 
- Summarize: "You met with John on April 10 about Q2 planning"
- Keep values concise (under 500 characters is ideal)
- For long content, store the key insight, not the raw data

### 7. Not Respecting Privacy Preferences

**Problem**: Storing personal data the user didn't explicitly ask to save
**Solution**: Only store when user explicitly says "Remember..." or "Save..." or "Note that..."

### 8. Memory Conflicts Across Sessions

**Problem**: User changed preference but agent still uses old memory
**Solution**: Offer refresh: "I remember you used to prefer X, but things change. Should I update that?"

### 9. Ignoring Namespace Organization

**Problem**: Everything stored in default "memories" namespace, hard to find relevant info
**Solution**: Use namespaces to organize (personal info separate from notes, separate from preferences)

---

## Validation Checklist

Before responding with memory operations:

- [ ] Identified when user wants to store information (explicit "remember", "note", "save")?
- [ ] Used appropriate namespace (personal, preferences, notes, or custom domain-specific)?
- [ ] Consistent key naming (snake_case, descriptive)?
- [ ] For retrieval, checked memory_retrieve() before answering personalized questions?
- [ ] For updates, confirmed with user before overwriting existing memory?
- [ ] For sensitive info, asked permission and noted privacy implications?
- [ ] Used memory_retrieve() to personalize responses across skills?
- [ ] Never stored sensitive data (passwords, API keys, full account numbers) without warning?
- [ ] Kept values concise and summarized (not raw data dumps)?
- [ ] Clear, conversational confirmation of stored/retrieved information?
- [ ] Offered to delete or update outdated memories when relevant?
- [ ] Organized memories by namespace (don't put everything in default "memories")?

---

## Quick Reference: Memory Namespaces

| Namespace | Use For | Example Keys |
|---|---|---|
| **personal** | User identity, location, timezone, contact info | user_name, user_timezone, user_location, user_email |
| **preferences** | Likes, dislikes, communication style, schedules | communication_preference, favorite_color, food_preference, wake_time |
| **notes** | Quick notes, reminders, saved info, to-dos | note_plumber_call, contact_sarah_email, project_deadline |
| **memories** | Default namespace for general-purpose storage | Any memory that doesn't fit other namespaces |
| **custom** | Domain-specific storage (health, projects, habits) | health_goals, project_constraints, reading_list |

---

## Integration with Other Skills

Memory enhances all skills:
- **Time-management**: Use `memory_retrieve("user_timezone", namespace="personal")` to respect timezone without asking
- **Task-management**: Recall user's priorities via `memory_search("priority", namespace="notes")` or `memory_list(namespace="preferences")`
- **Information-retrieval**: Personalize search results based on `memory_retrieve("interests", namespace="preferences")`
- **Daily-summary**: Use `memory_list(namespace="preferences")` to tailor briefing content
- **Voice-mode**: Use `memory_retrieve("user_name", namespace="personal")` for natural personalization

Best practices:
- Start conversations by retrieving user name and timezone for personalization
- Offer to save important details when user mentions them proactively
- Update memories when things change (user: "I moved" → store new location)
- Delete outdated memories to keep context clean
- Use memory_search() to find related memories before responding
- Proactively suggest memory storage: "Should I remember this for next time?"
