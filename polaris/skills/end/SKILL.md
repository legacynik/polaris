---
name: end
description: Polaris skill — close a repository-first team session with a handoff, decision proposals, a plan tick and an optional pathspec-only commit. Trigger when stopping work, before a multi-day pause, or on "wrap up / end session / /end".
user-invocable: true
---

# /end — close without losing the handoff

Use the same root and contributor resolver as `/start`. Before writing anything, read the ground
truth:

```bash
git rev-parse --abbrev-ref HEAD   # confirm the branch (shared checkouts)
git status --short                 # what actually changed this session
```

## Step 1 — Write the handoff

Append to `team/<login>/sessions/YYYY-MM-DD-@<github-login>.md`:

```md
## HH:MM — session end
- Shipped / verified: <evidence-backed result>
- Still open: <one concrete thread>
- Next session: <first step>
```

## Step 2 — Tick the plan

Update the matching row in `team/<login>/weeks/$(date +%G-W%V).md` only when its state or proof
changed. Do not rewrite the plan.

## Step 3 — Surface durable decisions (propose, don't write)

If the session produced a genuinely durable choice (an architecture decision, a reversed approach, a
convention the team must follow), **propose** a `<root>/decisions.md` entry and wait for confirmation
before writing it:

```md
## YYYY-MM-DD — <decision title>
Chose <X> over <Y> because <evidence>. Affects <area>.
```

Do not log routine progress as a decision. If nothing durable happened, say so.

## Step 4 — Prune the live pointer

**Overwrite** (never append to) `<root>/state/current.md` after the handoff, keeping the same six
compact fields `/update` uses: updated, owner, outcome, status, blocker, next. This gitignored file
is a live pointer, not a second session log; on a clean handoff its `Next` is the first step for the
next session — do not retain completed threads.

## Step 5 — Offer a clean commit

If `git status --short` shows changes, propose a single **pathspec-only** commit scoped to what you
touched — never `git add -A`:

```bash
git add <root>/team/<login>/sessions/<file> <root>/team/<login>/weeks/<file>   # only the files you wrote
git commit -m "chore(polaris): session handoff <date> @<login>"
```

Never commit or push without an explicit request. After committing, if the branch is ahead of its
remote, remind the contributor there is unpushed work:

```bash
git status -sb | head -1   # e.g. "## main...origin/main [ahead 1]"
```

## Finish

Summarize the handoff in three bullets (shipped, open, next). This command never writes outside the
current repository and never mutates the tracker.
