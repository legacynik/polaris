---
name: update
description: Polaris skill — record a short repository-first checkpoint during an active session. Trigger after meaningful progress, a blocker, a context switch, or on "checkpoint / save progress / /update".
user-invocable: true
---

# /update — leave the work legible

Use the same resolver as `/start` (including the root-is-`_polaris` vault case): the Polaris root is `_polaris/`, and the contributor is their own
GitHub login (`gh api user --jq .login`) with the matching `team/<login>/profile.yml`. If your
profile is missing, run `/start` first — it provisions your own path. If the root itself is missing,
stop and point to `docs/TEAM-ONBOARDING.md`.

## What a good checkpoint contains

Three facts, no narration: **Done** (verified, not "worked on"), **Next** (one concrete step),
**Blocker** (exact, or none). No transcript, no tool dumps, no essay. If you cannot name a verified
result yet, say "in progress" — do not inflate.

## Step 1 — Append to the session log

Append to `team/<login>/sessions/YYYY-MM-DD-@<github-login>.md` (create it if today's file does not
exist):

```md
## HH:MM — checkpoint
- Done: <verified progress, with proof if any>
- Next: <one concrete next step>
- Blocker: <none, or exact blocker>
```

Keep the whole entry **≤10 lines**. This session log is shared history and is committed with the code.

## Step 2 — Tick the plan cell (only if state changed)

If the current weekly-plan item (`team/<login>/weeks/$(date +%G-W%V).md`) changed state, update only
its `Status`, `Proof` or `Blocker` cell. Do not rewrite the plan and do not create a new plan.

## Step 3 — Reconcile `state/current.md` (the convergence point) — add and flag, never close

**Resolve it from the MAIN worktree, always** — never from the checkout you happen to be sitting in:

```bash
MAIN_WT="$(git worktree list --porcelain | head -1 | sed 's|^worktree ||')"  # main worktree is listed first
# → "$MAIN_WT/_polaris/state/current.md"  (or "$MAIN_WT/state/current.md" when the repo root IS _polaris)
```

It is gitignored, so it never travels with a branch: written inside a worktree, the next session
(which opens the main checkout) never sees it — a handoff nobody will ever read, a measured loss (orphaned per-worktree handoffs).
One file in the main worktree keeps many parallel panels legible from one place.

Because every panel converges here, **the branch is a thread's identity**: one panel, one worktree,
one branch. Tag each thread with its branch and `/end` can ask git whether the work actually landed
instead of guessing — and no panel has to know which of the others is alive.

**Reconcile, never blind-overwrite and never blind-append**: read the existing file first, then
apply your changes to your own thread. **`/update` has no closing authority** — only `/end` may
remove a thread; `/update` adds one, updates its own thread's context, or flags one stale. Two
invariants, in priority order:

1. **Nothing open is ever lost, and `/update` never closes anything — even its own thread.** Many
   panels write this one file, sometimes within the same hour. The only reliable way for that to
   never eat someone's thread is for no delete path to exist here at all.
2. **Only open truth lives here.** No narrative of shipped work (→ session log), no decisions taken
   (→ decisions.md), no history. Size is an OUTPUT of that discipline, never a constraint: 10
   genuinely live threads = 10 threads in the file, each with 1–3 lines of context (a thread
   stripped of its why/where is half-lost). Never trim a live thread to make the file smaller.

```md
# Current — live threads
Updated: YYYY-MM-DD HH:MM by @login — <one line on what this session moved>

## Open
- `feat/123-short-name` — <1–3 lines: where it stands, what unblocks it> · since YYYY-MM-DD
- `fix/456-other-panel` — <another panel's thread — not yours to remove>

## Next
- `feat/123-short-name`: <one concrete first step>
- `fix/456-other-panel`: <their next step — never overwrite it with yours>
```

A thread idle >14 days gets flagged `stale?` — it stays until `/end` closes or promotes it, never
auto-dropped. `stale?` is a question, not a verdict: parked work on a live branch is still work.

If a `state/current.md` also exists in the **non-main** worktree you are in, it predates this rule:
say so once and offer to fold its live threads into the main file. Do not delete it silently — it
may be the only copy of a handoff.
If the file holds another owner's fresher checkpoint line, you may be on another panel's checkout —
confirm before touching it.

## Step 4 — Land the checkpoint in git (your branch, pathspec-only)

A checkpoint left uncommitted is an orphaned handoff — the exact failure Polaris exists to prevent.
Land it on your **current branch**: a checkpoint describes *this branch's* work, so it belongs here;
`/end` is what promotes durable history to main. Delegate the commit to the script so hygiene is
enforced in code, never left to prose:

```bash
LOGIN="$(git config --local --get polaris.login || gh api user --jq .login)"
ROOT="_polaris"; [ -f "_polaris/config.yml" ] || ROOT="."   # normal product repo → _polaris/ ; vault (repo root IS _polaris) → .
"$CLAUDE_PLUGIN_ROOT/scripts/session_commit.sh" \
  "$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md"    # the session log Step 1 wrote (under the resolved Polaris root)
  # add the weekly plan "$ROOT/team/$LOGIN/weeks/$(date +%G-W%V).md" as a 2nd arg ONLY if Step 2 ticked it
```

The paths MUST be under the resolved Polaris root (`_polaris/` in a normal repo, `.` in the vault): the
session log lives at `$ROOT/team/$LOGIN/sessions/`, and a bare `team/$LOGIN/...` would miss it — the
commit would find nothing and skip, leaving the checkpoint orphaned (the exact bug this step prevents).

The script is pathspec-only (never `git add -A`, so parallel panels sharing one tree can never drag
each other's uncommitted work), refuses to commit `state/current.md`, `decisions.md`/`lessons.md`
(those are `/end`'s vetted promotion) or any `.env*`, reports the branch it landed on, and skips
silently on an empty checkpoint. It never checks out another branch and never pushes.


## Cockpit append (dense session state — EVERY contributor; multi-panel is the norm)

ALWAYS append the same dense block to the CURRENT repo's `<polaris-root>/state/current-state.md`
(gitignored per contract — `state/` is ephemeral; append-only, never pruned here). This is each
contributor's per-repo cockpit: Gio/JP run parallel panels too.

Additionally, if `$HOME/Desktop/All Vibe Proj/_polaris` exists (the founder vault) and is not the
current root, ALSO append a dense block to
`<vault>/state/current-state.md` (gitignored, append-only, NEVER pruned by /update — the dense
cockpit file). No vault on this machine → the per-repo cockpit above is the only (and sufficient) copy.

```markdown
## Update: {YYYY-MM-DD HH:MM} · {repo} · {branch}{ · wt: <path> se non-main}
- {cosa fatto, 1-3 bullet DENSI — non comprimere}
- Files: {file toccati con stato}
- Commits: {`git log --oneline` degli sha di QUESTA sessione su questo branch, o "nessuno"}
- Next: {passo concreto}
```

## Boundaries

- Do not write a founder vault, global memo, private workspace or automatic lesson.
- Do not create or assign issues, branches, pull requests or deployments.
- Do not claim completion without a linked proof.

Finish by showing the session checkpoint and the `Next` line from `state/current.md`.
