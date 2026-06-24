---
name: update
description: Mid-session checkpoint — saves progress to repo-local _polaris/state/current.md and _polaris/sessions/, then appends to the cross-repo Polaris vault (_polaris/sessions/ and memo/log.md). No commit, no decision surfacing. Use before a temporary context switch, after a significant work block, or before launching a long task.
---

# update

Snapshot current progress. Saves at two levels: repo-local `_polaris/` + cross-repo vault. Append-only, no commit.

## When to use

- Before a temporary break (coming back later)
- After completing a significant chunk of work mid-session
- Before launching a long task (Hand run, deploy, build)
- User says "update", "checkpoint", "save", "aggiorna", "pol-update"

Use `end` instead for closing a session.

## Process

### 1. Synthesize progress (3 bullets max each)
From the current conversation:
- **Done**: what has been completed so far
- **In progress**: what is still open or mid-flight
- **Next**: what comes after (if clear from context)

### 2. Write to repo-local _polaris/

**`_polaris/state/current.md`** — update the checkpoint header (create if missing):
```markdown
<!-- checkpoint: {YYYY-MM-DD} {HH:MM} -->
{one-line summary of current status}
```
Do not rewrite the whole file. Update header only.

**`_polaris/sessions/{TODAY}.md`** — append (create with `# Session Log: {TODAY}` if missing):
```markdown
## checkpoint {HH:MM}

**Done**: …
**In progress**: …
**Next**: …
```

### 3. Write to cross-repo vault

**`~/Desktop/All Vibe Proj/_polaris/sessions/{TODAY}.md`** — append:
```markdown
## [{repo-name}] checkpoint {HH:MM}

**Done**: …
**In progress**: …
**Next**: …
```

**`~/Desktop/All Vibe Proj/_polaris/memo/log.md`** — append one line:
```
## [{TODAY} {HH:MM}] checkpoint | {repo-name} | {one-line summary}
```

### 3b. Layer-3: distill AND WRITE lessons (B loop)

Distill *today's so-far* scratch + flagged corrections into lessons **and WRITE them now**. Karpathy system-prompt-learning. Skip silently if there's no signal.

> **Why this WRITES (changed 2026-06-19):** `/update` is frequently the LAST action before the session is closed (the user often skips `/end`). If distillation is only "proposed" here and deferred to `/end`, the lessons are LOST on close. So `/update` MUST persist them, not propose. Writing to `lessons.md` is append-only and fork-free (the recurrence `--bump` may fork — if it fails, the write still stands).

1. **Read the signal.** Read today's scratch for the current contributor at `_polaris/sessions/scratch/<contributor>/` (`git config user.email` slug) + entries flagged `[CORRECTION]` (set by the Stop hook).
2. **Distill** each into an imperative lesson — **Why** + **How-to-apply**, generalized (the rule, not the incident).
3. **Classify** (§1 of `_polaris/plans/2026-06-18-decision-to-enforcement-loop.md`): **note** (rationale) / **context** (judgment/preference) / **gate** (damage + script-detectable).
4. **WRITE the lesson record now** — append a `## ` block to `_polaris/lessons.md` for EVERY distilled lesson (fields: `rule` = Why+How, `tier`, `recurrence: 0`, `source`, `last_triggered`). This is the persistence that survives session close. For `context`/`gate` tiers ALSO propose the higher-effort artifact (a `MEMORY.md`/`CLAUDE.md` line, or a preflight check) for the human to apply — but the lesson itself is already saved in `lessons.md`, never lost.
5. **Recurrence check + bump.** For each, run `python3 _polaris/scripts/lesson_recurrence.py --match "<lesson>"`; if it already exists, `--bump` it and surface the promotion proposal. If the script can't run (fork-starved), note it and continue — the write in step 4 already persisted the lesson.

No signal → say nothing.

### 4. Confirm
Show the checkpoint block that was written. Done.

## Path standard (every repo)

```
repo/_polaris/
  sessions/{TODAY}.md     ← append checkpoint here
  state/current.md        ← update header here
```

## What this skill does NOT do

- Offer a commit → use `end`
- Surface decisions → use `end`
- Read git diff
- Modify `decisions.md`
- Touch `activity.log` (owned by git hook)

(Note: as of 2026-06-19, step 3b DOES write lessons to `lessons.md` — `/update` may be the last action before close, so lessons must persist here, not wait for `end`. `end` additionally surfaces decisions + offers a commit.)
