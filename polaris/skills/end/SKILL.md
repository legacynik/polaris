---
name: end
description: Polaris skill — close a repository-first team session with a concise handoff and an optional commit proposal. Use when stopping work or before a multi-day pause.
user-invocable: true
---

# /end — close without losing the handoff

Use the same root and contributor resolver as `/start`. Read `git status --short` and the current
weekly-plan item before writing anything.

## Write the handoff

Append to `sessions/YYYY-MM-DD-@<github-login>.md`:

```md
## HH:MM — session end
- Shipped / verified: <evidence-backed result>
- Still open: <one concrete thread>
- Next session: <first step>
```

Update the matching plan row only when its state or proof changed. If a decision is genuinely
durable, **propose** a `decisions.md` entry and wait for confirmation before writing it.

## Prune the live pointer

Overwrite (never append to) `<root>/state/current.md` after the handoff. Keep exactly the same
six compact fields used by `/update`: updated time, owner, outcome, status, blocker and next.
This gitignored file is a live pointer, not a second session log. On a clean handoff its `Next`
field is the first step for the next session; do not retain completed threads.

## Finish

Summarize the handoff in three bullets. If the checkout has changes, propose a commit message;
never commit or push without an explicit request. This command never writes outside the current
repository.
