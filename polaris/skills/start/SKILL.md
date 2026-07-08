---
name: start
description: Start a session — loads repo-local context from _polaris/state/current.md, _polaris/sessions/, _polaris/state/goals.md, then adds cross-repo Polaris context (POLARIS.md dashboard, active deadlines). Use at the beginning of any session, when resuming after a break, or when the user types /start.
---

# start

Load all context needed to begin working. Two layers: repo-specific state + cross-repo portfolio view.

## When to use

- Beginning of any working session
- Resuming after a pause or multi-day break
- User types `/start` or asks "where were we?"

## Process

### 1. Get today's date
```bash
date +%Y-%m-%d
```

### 2. Load repo context
All paths are inside `_polaris/` in the current repo root. Skip silently if files don't exist.

Read in order:
1. `_polaris/state/current.md` — current priorities, open threads, status
2. `_polaris/sessions/{TODAY}.md` — if exists, we're resuming today's session
3. Most recent file in `_polaris/sessions/` — for continuity if no today file
4. `_polaris/state/goals.md` — annual/monthly goals

### 3. Check follow-ups
From `_polaris/state/current.md`: surface items with review date ≤ today, deadlines within 3 days.

### 4. Load cross-repo portfolio context
Read `~/Desktop/All Vibe Proj/_polaris/POLARIS.md`:
- Current phase and capacity allocation
- Top 3 active alerts
- Plan with nearest deadline

Skip silently if cross-repo `_polaris/` is unreachable.

### 5. Present briefing

```
{Day}, {Date}

[{repo-name}]
1. {top priority}
2. {second priority}
3. {third priority}
Alerts: {if any}

[Portfolio — Phase {X}]
Capacity: {one-line}
Alert: {most urgent}
Deadline: {nearest plan} ({N} days)

How can I help today?
```

Keep it tight. Details on request.

## Path standard (every repo)

```
repo/_polaris/
  sessions/{TODAY}.md     ← daily log
  state/current.md        ← priorities and status
  state/goals.md          ← goals
  decisions.md            ← repo-specific decisions
  weekly/                 ← weekly reports
```

## Notes

- If today's session file exists, acknowledge what was already covered
- If `_polaris/state/current.md` is missing, create it with blank template
- This skill reads only — writing happens in `update` and `end`
