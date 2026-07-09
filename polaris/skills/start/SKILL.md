---
name: start
description: Polaris skill — start a session — loads repo-local context from _polaris/state/current.md, _polaris/sessions/, _polaris/state/goals.md, then adds cross-repo Polaris context (POLARIS.md dashboard, active deadlines) when the vault is available. Use at the beginning of any session, when resuming after a break, or when the user types /start.
user-invocable: true
---

# start

Load all context needed to begin working. Two layers: repo-specific state + cross-repo portfolio view.

## Vault resolution (cross-repo layer — optional)

The repo layer (`_polaris/` in the current repo) ALWAYS works and needs nothing.
The cross-repo portfolio layer needs the Polaris vault:
- if env `POLARIS_VAULT` is set AND that directory exists → use it;
- if env `POLARIS_VAULT` is set but the path does NOT exist → print once
  "portfolio layer: POLARIS_VAULT set but path not found — skipping" and
  treat the portfolio layer as NOT available (same as the branch below);
- else if `~/Desktop/All Vibe Proj/_polaris` exists → use it (founder machine);
- else → the portfolio layer is NOT available: print one line
  "portfolio layer: not available on this machine" in the briefing/closing and
  skip every cross-repo step silently. This is normal on teammate machines, not an error.
`polmem` (CLI or bundle): use it only if `command -v polmem` succeeds OR
`scripts/polaris_memory_repo.py` exists in the repo; otherwise say
"polmem: not available" once and continue.

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
Per the vault-resolution rule above: if the portfolio layer is available, read
`$POLARIS_VAULT/POLARIS.md`:
- Current phase and capacity allocation
- Top 3 active alerts
- Plan with nearest deadline

Skip silently if the portfolio layer is not available.

### 4b. Load the Memory-OS map (inject how memory works)
If the portfolio layer is available, read the **🗺️ THE MAP** section (the fenced
diagram + the "three principles") from `$POLARIS_VAULT/MEMORY-OS.md` and hold it as
active context for the session — so you always know: memory lives per-repo in
`<repo>/.wiki`, Polaris reads them externally, recall is `recall(query, repo?)` /
`polmem recall`, and the update is a local hook + out-of-band runner (never in the
commit hot-path). Do NOT print the whole map in the briefing — just surface a
one-line pointer (see step 5). Read the full `MEMORY-OS.md` on demand if memory
questions arise.

Skip silently if the portfolio layer is not available or `MEMORY-OS.md` is unreachable.

### 4c. Memory health — READOUT ONLY (founder flip 2026-07-03, supersedes D1 gating)
Gate the invocation on actual availability — never invoke the bare `polmem`
word unless `command -v polmem` already succeeded:
- if `command -v polmem` succeeds → run exactly: `polmem health || true`
- else if the portfolio layer is available (per the vault-resolution rule
  above) → run `python3 "$POLARIS_VAULT/mcp/polmem" health || true` instead
- else if `scripts/polaris_memory_repo.py` exists in this repo → print
  "polmem CLI not on PATH — repo bundle present, MCP recall available" once
  and skip (do NOT shell out to `polmem` — it isn't on PATH, that's noise)
- else → print "polmem: not available" once and continue

When actually run, the exit code is the severity (0=green, 1=warn, 2=red),
NOT a failure — `|| true` keeps the harness from flagging a RED as an error
and from double-running fallbacks. Read the printed lines.
- Surface RED lines in the briefing's Alerts. That is ALL /start does.
- Do NOT drain, do NOT sync, do NOT launch anything at /start — session context is
  sacred. Sync is fully automatic elsewhere: git hooks (.md commit on main +
  post-merge → `polmem sync <repo>`) + launchd 6h backstop + `/end` (cross-repo).
  A `wiki-sync` RED here means those triggers are broken — report it as an alert,
  don't paper over it in-session.

### 5. Present briefing

The `Memory:` line is gated, not unconditional:
- memory layer NOT resolved (no `polmem` on PATH and no
  `scripts/polaris_memory_repo.py` in the repo) → omit the line entirely.
- memory layer resolved but the portfolio layer is NOT available (teammate
  machine, no vault) → `Memory: per-repo .wiki via recall (MCP)` — no map
  pointer, since there's no vault to point into.
- memory layer resolved AND the portfolio layer is available → `Memory:
  per-repo .wiki + \`polmem recall\` (map: $POLARIS_VAULT/MEMORY-OS.md)`.

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

Memory: {gated line per rule above, or omitted}

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
