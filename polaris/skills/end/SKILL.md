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
distill decides later what is durable, so never skip this because the session felt routine.

**Check the repo owns a journal BEFORE you call `remember` — the binary resolving is not the test:**

```bash
test -d .wiki/journal || echo "NOT memory-wired — skip the remember line"
```

This matters more than it looks. `polmem` may be installed **globally** and work perfectly while
being wired to a different repository: run `remember` in a repo without its own `.wiki/journal/` and
the line does not fail — it silently lands in **someone else's** journal, carrying this session's
content out of this repository. Measured, not hypothetical: an `/end` run inside a scratch repo
wrote its handoff into an unrelated vault. `command -v polmem` passes in exactly that state, which
is why the wiring test is the repo's directory, never the binary.

```bash
polmem remember "session YYYY-MM-DD @<login>" "<shipped/verified, one clause> — next: <first step>"
```

The line is **written to this repo's committed journal** — shared history. Same privacy boundary as
the contract README: no secrets, credentials, customer data or personal information, ever. Failure
branches: no `.wiki/journal/` → skip the line, say once that the repo is not memory-wired, continue
the handoff (tell the repo owner; do **not** wire it yourself); `command not found: polmem` → run the
plugin installer once, then re-check the wiring above. Never run `polmem init` yourself.

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

## Step 4 — Prune the live pointer (the only step allowed to close a thread)

**Resolve it from the MAIN worktree**, exactly as `/update` Step 3 does — the handoff has to land
where the next session will actually open, not inside the worktree you happen to be in:

```bash
MAIN_WT="$(git worktree list --porcelain | head -1 | sed 's|^worktree ||')"  # main worktree is listed first
# → "$MAIN_WT/_polaris/state/current.md"  (or "$MAIN_WT/state/current.md" when the repo root IS _polaris)
```

**Reconcile** it: read it first, never blind-overwrite, same rules as `/update` Step 3 (threads keyed
by branch, nothing open lost, other panels' threads and `Next` lines untouched) — with one
difference. **`/end` is the only Team OS command with closing authority**, and it spends it against
ground truth rather than impression.

**A thread closes only when its work actually landed.** Ask git and the tracker; never infer death
from "nothing moved lately". Work parked on a live branch while its owner spent the week elsewhere
is the normal shape of parallel development — several panels, several worktrees, several branches
open for days — and dropping that thread is precisely the loss this file exists to prevent:

```bash
git worktree list                                        # a worktree still holds the branch → live, stop
git branch --merged origin/main | grep -qx "  <branch>"  # merged into the base?
gh pr list --head "<branch>" --state all --limit 1 --json number,state,mergedAt
```

Close the thread when its branch is **merged** (or its PR reports `MERGED`), and cite that evidence
in the session log you just wrote. Otherwise it stays: an open PR is not a closed thread, a green
real-test is not a merge, "the code is done" is not a merge, and a branch with no recent commits is
parked, not dead. The other exit is **promotion** — a thread that became an issue/plan leaves one
pointer line (`→ #123`), never a silent delete. A thread with no branch closes only against named
evidence in the log.

On a clean handoff the `Next` line is the first step for the next session; leave other panels' `Next`
lines alone. Closed threads leave the pointer — their story lives in the session log you just wrote,
not here.

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
