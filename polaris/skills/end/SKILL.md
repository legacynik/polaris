---
name: end
description: Polaris skill — close a repository-first team session with a handoff, decisions/lessons written to the ledgers, a plan tick and a pathspec-only commit. Trigger when stopping work, before a multi-day pause, or on "wrap up / end session / /end".
user-invocable: true
version: 1.3.0
---

# /end — close without losing the handoff

Use the same root and contributor resolver as `/start`. Before writing anything, read the ground
truth:

```bash
git rev-parse --abbrev-ref HEAD   # confirm the branch (shared checkouts)
git status --short                 # what actually changed this session
```


## One home (write-target for ALL session-state)

Every write in this skill — session log, handoff file, plan tick, `current.md`, `current-state.md`,
decisions/lessons appends — lands in the **MAIN worktree**, whichever worktree/branch this panel
sits in. One home = appends from every panel land in one file, in time order; per-worktree copies
diverge on N branches and lose data at merge. Provenance lives in the block header (`wt:`/`branch:`).

```bash
MAIN_WT="$(git worktree list --porcelain | head -1 | sed 's|^worktree ||')"
ROOT="$MAIN_WT/_polaris"; [ -f "$ROOT/config.yml" ] || ROOT="$MAIN_WT"
```

## State hygiene (every run — the skills are the writers AND the janitors)

Before writing, sweep the CURRENT repo's Polaris root for strays (multi-panel machines drift:
older sessions write with pre-patch instructions):

1. Session files in the LEGACY top-level `<root>/sessions/` (not `team/<login>/sessions/`):
   `git mv` (or mv, if untracked) each into `team/<login>/sessions/`, adding a `-legacy` suffix
   on filename collision. Note the move in one line of this run's checkpoint — never silently.
2. Non-canonical `current` variants in `<root>/state/` (anything beyond `current.md`,
   `current-state.md`, `goals.md`, `backlog*.md`): FLAG them in your output with their mtime and
   first heading; fold their still-live content into the cockpit only on explicit confirmation.
3. **Worktree sweep** — the founder works wt-first and `/end` is the only janitor he runs:

   ```bash
   bash "$SKILL_DIR/scripts/wt_sweep.sh"        # /end: apply
   ```

   Deterministic and safe by construction (`--selfcheck` proves it): a worktree that is
   **clean AND already merged** into the default branch is removed (content lives on main;
   branch deleted with `-d`, which refuses unmerged) · a **dirty** worktree is NEVER touched —
   reported as `sporco, NON tocco` (lesson 2026-08-03: other panels' uncommitted work) · a
   **clean but unmerged** worktree is a pause — reported with age, kept alive · `git worktree
   prune` always. Paste the script's summary line into the handoff so the removals are on
   record. If a paused worktree carries an Open thread, its path must already be in the
   `## Open` line (see Step 4) — the sweep report is how you notice when it isn't.
Skip silently when the repo is already clean. Never delete anything in steps 1–2.

## Step 1 — Write the handoff

Append to `team/<login>/sessions/YYYY-MM-DD-@<github-login>.md`:

**Stesso formato di `/update`** — è lo stesso file, letto dalla stessa persona tre settimane dopo:
due grammatiche nello stesso log costringono a leggere due volte e rendono il log non contabile.
`/end` cambia solo la parola dopo l'orario (`session end`) e chiude con `Next session`.

```md
## HH:MM — session end · <titolo: cosa lascia questa sessione> · wt: <worktree> · branch: <branch>
- Done: <risultato verificato, con la prova>
- In progress: <cosa resta a metà, e dove sta>
- Next session: <primo comando da eseguire>
- Blocker: <esatto, oppure none>
- Key context: <decisione e perché · scelta architetturale · scoperta che ribalta una conclusione ·
  errore e regola che ne segue · decisione superata e cosa la supera>
  — tag: #decisione #architettura #scoperta #errore #superata #incidente
- Files: <path · simbolo toccato · perché>
```

`Key context` e `Files` valgono qui più che altrove: la sessione finisce, e quello che non è scritto
adesso non esiste più. `Files` come `path · simbolo · perché` è ciò che permette a Serena e a questo
log di incontrarsi sullo stesso simbolo mesi dopo. SHA e numeri si leggono da `git log`, non si
ricordano.

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

### Step 1c — Cockpit append (dense session state, every contributor)

ALWAYS append the same dense block to the CURRENT repo's `<polaris-root>/state/current-state.md`
(gitignored per contract — `state/` is ephemeral; append-only, never pruned here). This is each
contributor's per-repo cockpit — every contributor runs parallel panels, not just the founder.

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

## Step 2 — Tick the plan

Update the matching row in `team/<login>/weeks/$(date +%G-W%V).md` only when its state or proof
changed. Do not rewrite the plan.

## Step 3 — Capture durable decisions and lessons (WRITE them — a proposal that dies with the session is data loss)

/end WRITES qualifying decisions and lessons directly — append-only, One home, attributed
`(@<login>)` — and lists what it wrote in the closing summary (git history protects; a proposal
that dies with the session protects nothing). Only the genuinely durable qualifies.

**A decision** qualifies only if it either **supersedes a past decision** (name which, and align it)
**or** sets an **architectural direction** whose impact runs from today out to 30 days–years on the
product/development. → `<root>/decisions.md`:

```md
## YYYY-MM-DD — <decision title> (@<login>)
Chose <X> over <Y> because <evidence>. Supersedes: <past decision, or —>. Impact: <area, horizon>.
```

**A lesson** = a real mistake — usually a loop or blocker you overcame — plus the one rule that
prevents its recurrence. → `<root>/lessons.md`.

**ADR — backstop audit (the ADR is born AT DECISION TIME, per the apex rule — not here).**
Sweep this session for qualifying decisions: each must ALREADY have its `docs/adr/NNNN-<slug>.md`.
One missing = a miss to repair NOW, and say so in the closing summary (the rule slipped once —
name it so it doesn't become a habit). Scaffold the missing ADR exactly as the apex rule
prescribes:

1. Resolve every referenced file/symbol with **Serena** (`find_symbol`) — exact paths from the
   tree, never inferred from prose (the 12-wrong-path lesson).
2. Put them in `code_refs:` frontmatter — **symbols (qualified names) are the primary key**
   (`ClassName.method`, module-level names); file paths only as context; **line numbers never**
   (they drift on every edit — false-positive machine). The ADR file's frontmatter IS the store:
   git-versioned, scanner-validated, CI-gated — no service, no separate index. Serena resolves
   symbols live for drift checks (`find_symbol` still exists? signature changed?
   `find_referencing_symbols` for impact).
3. The decisions.md entry gets `→ ADR: docs/adr/NNNN-<slug>.md` appended; the ADR body states
   decision, alternatives weighed, and consequences — content per domain-modeling.
4. Include the ADR file in the Step 5 commit pathspec.

If nothing durable happened, say so. Do not log routine progress as either.

## Step 4 — Prune the live pointer (the only step allowed to close a thread)

Path per the **One home** rule: `$ROOT/state/current.md` — the handoff lands where the next
session opens. **Reconcile** it: read it first, never blind-overwrite, same rules as `/update` Step 3 (threads keyed
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

## Step 5 — Land the handoff in git (same guard as `/update`, in code)

If `git status --short` shows changes, land what you wrote through **the same script `/update` uses**
— pathspec-only, and it commits ONLY from the default branch of the MAIN worktree. A handoff
committed on a feature branch is stranded: invisible to `/start` until that branch merges, which for
a paused worktree is days or never (observed loss). Off the default branch the script defers: the
files stay on disk as the single copy and the next main-tree session lands them — say so, do not
hand-commit around the guard. The Step 1 `polmem remember` line lands in `.wiki/journal/`: it is
committed shared history, so it belongs here or it never reaches the team.

```bash
cd "$MAIN_WT"
SC="${CLAUDE_PLUGIN_ROOT:-}/skills/update/scripts/session_commit.sh"          # plugin install
[ -x "$SC" ] || SC="$HOME/.agents/skills/update/scripts/session_commit.sh"    # skills-CLI install (npx)
"$SC" --end "$ROOT/team/$LOGIN/sessions/<file>" "$ROOT/team/$LOGIN/handoff/$(date +%F).md" \
            "$ROOT/team/$LOGIN/weeks/<file>" "$ROOT/decisions.md" "$ROOT/lessons.md" \
            ".wiki/journal/<file-from-step-1>"   # ONLY the files you wrote this session
```

`--end` is the mode that may commit `decisions.md` / `lessons.md` (they are this command's vetted
promotion); it still refuses `state/current.md` and `.env*`, and never pushes. On a **deferred** run
say plainly that the handoff is on disk and not yet committed — the dense copy in the cockpit is what
the next panel resumes from meanwhile. If a later `git checkout <default>` in that tree is refused
because of the deferred file, git is protecting the append: copy aside, switch, re-append, re-run. **Both resolver
candidates missing** (say which you tried): on the default branch only, `git add --` those exact
paths and `git commit -m "chore(polaris): session handoff $(date +%F) @$LOGIN"` — never `git add -A`;
on any other branch commit nothing and report the handoff as deferred on disk.

Never commit or push without an explicit request. After committing, if the branch is ahead of its
remote, remind the contributor there is unpushed work:

```bash
git status -sb | head -1   # e.g. "## main...origin/main [ahead 1]"
```

## Finish

Summarize the handoff in three bullets (shipped, open, next). This command never writes outside the
current repository and never mutates the tracker.
