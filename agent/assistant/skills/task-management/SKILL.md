---
name: task-management
description: Personal task and todo management for voice assistant. Handles task creation, status tracking, priority management, deadlines, and recurring task patterns.
license: Apache-2.0
compatibility: Designed for VoiceAgent personal-assistant
metadata:
  author: agent
  version: "1.0"
  agent-affinity: ["voice_agent", "personal_assistant"]
---

# Task & Todo Management Skill

## Purpose

Enable voice-driven task management with natural language creation, deadline tracking, priority levels, and status updates. Integrate with time-management skill for scheduling and reminders.

## When to Use This Skill

Use when queries contain these keywords:
- **Task creation**: "Create a task", "Add to my todo", "Remember to...", "I need to..."
- **Status updates**: "Mark complete", "Done with that", "Check off..."
- **Priority management**: "High priority", "Urgent", "Low priority", "Mark as important"
- **Deadline setting**: "Due tomorrow", "By Friday", "Due date", "When is it due?"
- **Task queries**: "What do I need to do?", "Show my tasks", "List todos", "What's pending?"
- **Recurring tasks**: "Every day", "Weekly", "Monthly", "Repeat this task"
- **Task modification**: "Rename task", "Change priority", "Move deadline", "Remove task"

## Prerequisites

### Available Tools

| Tool | Purpose | Parameters |
|---|---|---|
| `task_create(title, description, priority, due_date)` | Create new task | title: str, description: str (optional), priority: 'low'\|'medium'\|'high', due_date: ISO string (optional) |
| `task_list(status)` | List tasks by status | status: 'pending'\|'completed'\|'all' (default: 'pending') |
| `task_update(task_id, status, priority, due_date)` | Update task fields | task_id: str, status: 'pending'\|'completed', priority, due_date |
| `task_delete(task_id)` | Delete task | task_id: str |
| `task_recurring(task_id, frequency)` | Set recurrence pattern | task_id: str, frequency: 'daily'\|'weekly'\|'monthly' |
| `task_get_upcoming(days)` | Tasks due within N days | days: int (1-365) |

### Task Database

- **Storage**: PostgreSQL with task metadata persistence
- **Fields**: id, title, description, status (pending/completed), priority (low/medium/high), created_at, due_date, recurrence_pattern, tags
- **Timezone**: Tasks use user's local timezone for deadline interpretation
- **Sync**: Changes persist and sync across sessions

## Step 1 -- Task Creation

### Basic "Create Task" Pattern

```python
# User: "Create a task to buy groceries"
task_create(
    title="Buy groceries",
    description="",
    priority="medium",
    due_date=None
)
# Returns: {"task_id": "task_123", "title": "Buy groceries", "status": "pending"}

# User: "Add high priority meeting with Sarah tomorrow at 2pm"
task_create(
    title="Meeting with Sarah",
    description="Tomorrow at 2pm",
    priority="high",
    due_date="2026-04-16T14:00:00"
)
```

### Natural Language Deadline Parsing

- "Tomorrow" = current_date + 1 day
- "Next Friday" = next Friday from today
- "In 3 days" = current_date + 3 days
- "By end of week" = Friday of current week
- "This month" = before last day of current month
- "Next quarter" = before start of next quarter

Extract deadline using time-management skill, then pass ISO string to task_create.

---

## Step 2 -- Task Status & Completion

### Mark Tasks Complete

```python
# User: "Mark the groceries task as done"
task_list(status="pending")
# → Find task with title matching "groceries"
task_id = "task_123"

task_update(
    task_id=task_id,
    status="completed",
    priority=None,
    due_date=None
)
# Returns: {"task_id": "task_123", "status": "completed", "completed_at": "2026-04-15T10:30:00"}

# User: "Check off all my morning tasks"
tasks = task_list(status="pending")
# Filter tasks tagged with #morning or due before 12:00 PM
for task in filtered_tasks:
    task_update(task_id=task["id"], status="completed")
```

### List and Query Tasks

```python
# User: "What do I need to do today?"
all_tasks = task_list(status="all")
today_tasks = [t for t in all_tasks if t["due_date"] and date(t["due_date"]) == today]

# User: "Show high priority tasks"
all_tasks = task_list(status="all")
high_priority = [t for t in all_tasks if t["priority"] == "high" and t["status"] == "pending"]
```

---

## Step 3 -- Priority Management

### Set and Update Priority

```python
# User: "That meeting is urgent - make it high priority"
task_update(
    task_id="task_123",
    status=None,
    priority="high",
    due_date=None
)

# User: "Lower the priority on that grocery task"
# Change "medium" → "low" or "high" → "medium"
task_update(task_id="task_456", priority="low")
```

### Priority Levels

- **High**: Time-sensitive, business-critical, or explicitly marked urgent
- **Medium**: Standard tasks, default for new tasks unless specified
- **Low**: Nice-to-have, can defer if needed

Voice announcements should emphasize high-priority items: "You have 2 high-priority tasks due today."

---

## Step 4 -- Recurring Tasks

### Create Repeating Tasks

```python
# User: "I have a weekly standup every Monday at 10am"
task_create(
    title="Weekly standup",
    description="Team standup meeting",
    priority="medium",
    due_date="2026-04-21T10:00:00"  # Next Monday
)
task_id = response["task_id"]

task_recurring(
    task_id=task_id,
    frequency="weekly"
)
# Returns: {"task_id": task_id, "recurrence": "weekly", "next_due": "2026-04-21"}

# User: "Daily reminder to drink water"
task_create(
    title="Drink water",
    priority="low",
    due_date="2026-04-15T09:00:00"  # Today
)
task_recurring(task_id=response["task_id"], frequency="daily")
```

### Handling Recurring Task Completion

When user marks a recurring task complete, system should:
1. Mark current instance as completed
2. Create next instance based on frequency (e.g., next Monday for weekly)
3. Never delete recurring tasks, only archive them

```python
# User: "Done with standup"
# System internally:
task_update(task_id="task_123", status="completed")
# Auto-create: same task, due_date = "2026-04-28T10:00:00" (next week)
```

---

## Step 5 -- Deadline Management with Time Skill

### Integrate Deadlines with Time-Management Skill

```
Scenario: User asks "When do I need to finish the report?"

Step 1: Find task
task_list(status="pending")
report_task = [t for t in tasks if "report" in t["title"]][0]

Step 2: Get current time in user's timezone
time_current(user_timezone)

Step 3: Compare
deadline = parse_iso(report_task["due_date"])
time_until = deadline - current_time

Response: "The report is due in 2 days, Thursday at 5pm."
```

### Upcoming Tasks Alert

```python
# User: "What's coming up?"
upcoming = task_get_upcoming(days=7)
# Returns tasks due in next 7 days, sorted by date

# Format for voice:
# "You have 3 tasks due in the next week:
#  - Finish report (due tomorrow by 5pm)
#  - Team meeting (due Thursday at 10am)
#  - Review documents (due Friday)"
```

---

## Step 6 -- Voice-Specific Patterns

### Natural Task Announcements

```python
# WRONG: "You have task_456 with priority 'high' status 'pending' due 2026-04-16T14:00:00"
# RIGHT: "You have a meeting with Sarah tomorrow at 2pm - it's marked high priority"

# WRONG: "5 tasks pending, 2 completed"
# RIGHT: "You have 5 things to do, and you've completed 2 today"

# WRONG: "Recurrence pattern: weekly"
# RIGHT: "This repeats every week"
```

### Task Status Summary for Daily Check-in

```
User: "Give me a quick summary of my tasks"

Response structure:
1. High-priority items due soon (< 2 days)
2. Regular tasks due today/tomorrow
3. Completed count for encouragement
4. Reminders about recurring tasks

Example:
"You've got one urgent thing: the client presentation is due this afternoon at 3. 
You also have 4 regular tasks to do, and you've knocked out 8 things so far this week. 
Oh, and your weekly standup is tomorrow morning at 10."
```

---

## Step 7 -- Task Integration & Reminders

### Task-Triggered Actions

```python
# When task is created with priority="high" and due_date within 24h:
# → Auto-create reminder via time-management skill
# → Mention in next daily-summary

# When task marked completed:
# → Record completion time (for productivity tracking)
# → If recurring, create next instance
# → Include in daily summary "you've completed X tasks today"
```

### Task Linking

Tasks can reference other skills:
- Link to calendar events: "This task is connected to your 2pm meeting"
- Link to information: "You wanted to research this - here's what I found"
- Link to time zones: "Your 10am call with Tokyo team is due in 6 hours"

---

## Common Pitfalls

### 1. Ambiguous Deadline Language

**Problem**: User says "Due Friday" but Friday is vague (this Friday? next Friday?)
**Solution**: 
- If Friday already passed this week, assume next Friday
- If today is Friday, assume next Friday
- Confirm: "I put it due next Friday - does that work?"

### 2. Forgetting to Create the Recurring Instance

**Problem**: User creates recurring task but system doesn't generate next occurrence
**Solution**: Always call task_recurring AFTER successful task_create, never delete recurring tasks

### 3. Not Integrating with Time Management

**Problem**: Deadlines stored as uninterpreted strings, can't compare to current time
**Solution**: Always convert user's deadline language to ISO string using time_current + time conversion

### 4. Missing Timezone Handling

**Problem**: "10am" is ambiguous across timezones
**Solution**: 
- Establish user's home timezone early
- For tasks: store due_date in user's local timezone
- When comparing: convert current_time to user's timezone using time_current(user_tz)

### 5. Task Priority Inflation

**Problem**: User marks everything "high priority"
**Solution**: 
- Guide subtly: "I mostly mark things high priority when they're truly urgent or have external deadlines"
- Offer to adjust: "Would you like me to mark this as high priority?"

### 6. Not Handling Task Deletion Safely

**Problem**: Deleting recurring tasks loses the pattern
**Solution**:
- Never delete recurring tasks, only archive them (set a deleted_at flag)
- Confirm before deletion: "This will delete the task - not just mark it complete"

---

## Validation Checklist

Before responding with task information:

- [ ] For "Create task", called `task_create()` with title and priority?
- [ ] For "Mark complete", called `task_update(status="completed")` not just noted it?
- [ ] For recurring tasks, called `task_recurring()` after creation?
- [ ] Deadlines interpreted using time-management skill (not just text)?
- [ ] User timezone established for all deadline comparisons?
- [ ] Confirmed ambiguous deadlines ("Due Friday" → "Next Friday at 5pm?)?
- [ ] Never deleted a recurring task, only archived it?
- [ ] Voice response uses natural language, not data format?
- [ ] Integrated upcoming tasks with time skill for relative time ("due tomorrow", "in 3 days")?

---

## Quick Reference: Priority Levels

| Priority | When to Use | Voice Phrase | Default Response |
|---|---|---|---|
| High | Time-sensitive, externally-driven, urgent | "This is urgent" | Show first in lists |
| Medium | Standard work, normal deadline | "This is standard" | Default level, most tasks |
| Low | Nice-to-have, deferrable, exploratory | "This can wait" | Show last, deprioritize |

---

## Integration with Daily Summary

Task-management feeds into daily-summary skill:
- Highlight: High-priority tasks due today/tomorrow
- Celebrate: Count of completed tasks
- Remind: Recurring tasks coming up
- Warn: Overdue tasks (if any)
