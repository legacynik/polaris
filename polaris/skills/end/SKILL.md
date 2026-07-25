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



## Write-target rule (single physical path — NEVER per-worktree, NEVER per-branch)

ALL session-state writes in this skill — session log, weekly-plan tick, `state/current.md`,
`state/current-state.md` — go to the **MAIN worktree's** files, regardless of which worktree or
branch this panel sits in:

```bash
MAIN_WT="$(git worktree list --porcelain | head -1 | sed 's|^worktree ||')"
ROOT="$MAIN_WT/_polaris"; [ -f "$ROOT/config.yml" ] || ROOT="$MAIN_WT"
```

Why (founder rule, 2026-07-25): parallel worktrees each writing their own copy of the same daily
file = N divergent copies on N branches = overwrites and data loss at merge time. One physical
path means appends from every panel land in ONE file, in mtime order. Session-state never rides a
feature branch. Tag entries with `· wt: <name> · branch: <branch>` so provenance survives without
fragmentation.

## State hygiene (every run — the skills are the writers AND the janitors)

Before writing, sweep the CURRENT repo's Polaris root for strays (multi-panel machines drift:
older sessions write with pre-patch instructions):

1. Session files in the LEGACY top-level `<root>/sessions/` (not `team/<login>/sessions/`):
   `git mv` (or mv, if untracked) each into `team/<login>/sessions/`, adding a `-legacy` suffix
   on filename collision. Note the move in one line of this run's checkpoint — never silently.
2. Non-canonical `current` variants in `<root>/state/` (anything beyond `current.md`,
   `current-state.md`, `goals.md`, `backlog*.md`): FLAG them in your output with their mtime and
   first heading; fold their still-live content into the cockpit only on explicit confirmation.
Skip silently when the repo is already clean. Never delete anything in this step.

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

This matters more than it looks. `polmem` may be installed **globally** yet wired to a different
repository: run `remember` in a repo without its own `.wiki/journal/` and it does not fail — it
silently lands in **someone else's** journal, carrying this session out of this repo (observed).
`command -v polmem` passes in exactly that state, which is why the wiring test is the repo's
directory, never the binary.

```bash
polmem remember "session YYYY-MM-DD @<login>" "<shipped/verified, one clause> — next: <first step>"
```

The line is **written to this repo's committed journal** — shared history. Same privacy boundary as
the contract README: no secrets, credentials, customer data or personal information, ever. Failure
branches: no `.wiki/journal/` → skip the line, say once that the repo is not memory-wired, continue
the handoff (tell the repo owner; do **not** wire it yourself); `command not found: polmem` → run the
plugin installer once, then re-check the wiring above. Never run `polmem init` yourself.

### Step 1b — Structured handoff → `$ROOT/team/<login>/handoff/YYYY-MM-DD.md`

The contract's `handoff/` directory is for handoffs RICHER than a checkpoint — write it on every
/end (main worktree, append if the file exists):

```md
# Handoff YYYY-MM-DD HH:MM — @<login>
Repo: <repo> · wt: <worktree name or main> · branch: <branch> · commits: <shas this session>
## Shipped (verified)
## Open threads (with exact state)
## Next session: first command to run
## Risks / do-not-touch
```

This file is committed shared history (Step 5 includes it). The cockpit block stays the dense
personal view; THIS is the structured one a teammate (or you in 3 days) resumes from.

## Step 2 — Tick the plan

Update the matching row in `team/<login>/weeks/$(date +%G-W%V).md` only when its state or proof
changed. Do not rewrite the plan.

## Step 3 — Capture durable decisions and lessons (WRITE them — a proposal that dies with the session is data loss)

Founder rule 2026-07-25: /end WRITES qualifying decisions and lessons directly — append-only, in
the MAIN worktree, attributed `(@<login>)` — and lists what it wrote in the closing summary so the
founder can amend/revert (git history protects; a never-confirmed proposal protects nothing).
Write only if genuinely durable — never routine progress.

**A decision** qualifies only if it either **supersedes a past decision** (name which, and align it)
**or** sets an **architectural direction** whose impact runs from today out to 30 days–years on the
product/development. → `<root>/decisions.md`:

```md
## YYYY-MM-DD — <decision title> (@<login>)
Chose <X> over <Y> because <evidence>. Supersedes: <past decision, or —>. Impact: <area, horizon>.
```

**A lesson** = a real mistake — usually a loop or blocker you overcame — plus the one rule that
prevents its recurrence. → `<root>/lessons.md`.

If nothing durable happened, say so. Do not log routine progress as either.

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

**The thread line is the handoff that survives.** A session log committed on a branch is
INVISIBLE to `/start` until that branch merges — for a paused worktree that can be days. So the
thread line in `current.md` must carry the resume-essence on its own, written as if it is the only
survivor (it is): `- \`branch\` — <done in 1 clause; next concrete step; blocker or none> ·
wt: <worktree path if not main> · since YYYY-MM-DD`. Pausing WITHOUT a PR is normal: keep the
worktree alive, record its path in the line, and the next session reopens that same worktree from
`/start` — never feel forced to PR early just to make work visible.

**Branch discipline (superpowers:finishing-a-development-branch).** If this session produced
commits on a feature branch, invoke `superpowers:finishing-a-development-branch` before the
handoff. It does NOT force closure — its menu includes "keep as-is", which IS the pause path:
the discipline it adds is that tests get verified and the branch's fate is an EXPLICIT recorded
choice (merge / PR / keep / discard), never silent limbo. One adaptation: if tests are RED on
work-in-progress, do not treat that as a blocker — skip the menu, park the branch in the handoff
(thread line + cockpit) and note the red state. Session end ≠ branch end.

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
        "_polaris/team/$LOGIN/handoff/$(date +%F).md" \
        "_polaris/decisions.md" "_polaris/lessons.md" \
        ".wiki/journal/<file-from-step-1>"   # only files you wrote this session — incl. handoff + any Step 3 append
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

## Cockpit append (dense session state — EVERY contributor; multi-panel is the norm)

ALWAYS append the same dense block to the CURRENT repo's `<polaris-root>/state/current-state.md`
(gitignored per contract — `state/` is ephemeral; append-only, never pruned here). This is each
contributor's per-repo cockpit: Gio/JP run parallel panels too.

Additionally, if `$HOME/Desktop/All Vibe Proj/_polaris` exists (the founder vault) and is not the
current root, ALSO append the FULL handoff
to `<vault>/state/current-state.md` (gitignored, append-only — the everything-file: next steps, tasks, resume instructions, nothing compressed away). No vault → the per-repo cockpit is the only copy.

```markdown
## Session end: {YYYY-MM-DD HH:MM} · {repo} · {branch}{ · wt: <path>}
### Topics
### Decisions
### Files modified
### Open threads
### Next actions
### Commits (history)     ← `git log --oneline <base>..HEAD` del branch: gli sha SONO il log
### Resume instructions   ← come riprendere ESATTAMENTE: worktree, branch, comando, primo passo
```

This block is IN ADDITION to the thread line in `current.md` (thin index) and the committed
session log (team history). The cockpit file is where "tutto" lives.
