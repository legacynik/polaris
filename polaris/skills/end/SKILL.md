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

Then feed the repository memory with the same handoff, one machine-readable line — the offline
distill decides later what is durable, so never skip this because the session felt routine:

```bash
polmem remember "session YYYY-MM-DD @<login>: <shipped/verified, one clause> — next: <first step>"
```

This line is **written to the repo's committed journal** — shared history. Same privacy boundary as
the contract README: no secrets, credentials, customer data or personal information, ever. Failure
branches are the same as `/start` Step 4: `command not found: polmem` → run the plugin installer
once; `not memory-wired` → skip this line, say so once, continue the handoff. Never run
`polmem init` yourself.

## Step 2 — Tick the plan

Update the matching row in `team/<login>/weeks/$(date +%G-W%V).md` only when its state or proof
changed. Do not rewrite the plan.

## Step 3 — Surface durable decisions (propose, don't write)

If the session produced a genuinely durable choice (an architecture decision, a reversed approach, a
convention the team must follow), **propose** a `<root>/decisions.md` entry and wait for confirmation
before writing it:

```md
## YYYY-MM-DD — <decision title> (@<login>)
Chose <X> over <Y> because <evidence>. Affects <area>.
```

The same gate applies to durable lessons — a real mistake plus the rule that prevents its
recurrence: **propose** an entry in `<root>/lessons.md` and wait for confirmation before writing it.
Do not log routine progress as a decision or a lesson. If nothing durable happened, say so.

## Step 4 — Prune the live pointer

**Reconcile** `<root>/state/current.md` after the handoff, with `/update` Step 3's exact
semantics (read first; open-items ledger; nothing open ever lost; closed items leave only with
named evidence; promotion leaves a pointer; other owners' items untouched). On a clean handoff the
`Next` line is the first step for the next session. Completed threads leave the ledger — their
story lives in the session log you just wrote, not here.

## Step 5 — Offer a clean commit

If `git status --short` shows changes, propose a single **pathspec-only** commit scoped to what you
touched — never `git add -A`. The Step 1 `polmem remember` line lands in `.wiki/journal/`: it is
committed shared history, so it belongs in this commit or it never reaches the team:

```bash
git add "_polaris/team/$LOGIN/sessions/<file>" "_polaris/team/$LOGIN/weeks/<file>" \
        ".wiki/journal/<file-from-step-1>"   # only the files you wrote — INCLUDING the journal line
git commit -m "chore(polaris): session handoff $(date +%F) @$LOGIN"
```

Never commit or push without an explicit request. After committing, if the branch is ahead of its
remote, remind the contributor there is unpushed work:

```bash
git status -sb | head -1   # e.g. "## main...origin/main [ahead 1]"
```

## Finish

Summarize the handoff in three bullets (shipped, open, next). This command never writes outside the
current repository and never mutates the tracker.
