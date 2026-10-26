---
title: end — the close procedure, in full
description: The pre-form end body (1.23.5), kept as the detailed reference behind end/SKILL.md, with lessons moved to lesson_record.py and the follow-up bead of operating model §7.
status: active
---


# end — the close procedure, in full

Use the same root and contributor resolver as `start`. Before writing anything, read the ground
truth:

```bash
git rev-parse --abbrev-ref HEAD   # confirm the branch (shared checkouts)
git status --short                 # what actually changed this session
```


## One home (write-target for ALL session-state)

The log lives and is committed where the panel runs; the cockpit lives in the main worktree. The
session log, handoff file, plan tick and appends to decisions/lessons sit under `$ROOT`, which is
the contract of THIS worktree, and they land on the branch where the session actually happened.
Only `$CURRENT` — the cockpit, gitignored — keeps a single home in the main worktree, because a
per-worktree copy is a copy that no merge ever brings back. Provenance lives in the block header
(`wt:`/`branch:`).

```bash
eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"
```

One resolver, shared with `start`: `MAIN_WT`, `ROOT` (this worktree), `LOGIN`, `CURRENT` (the main worktree's cockpit) and `RADAR`. It exits
non-zero rather than guessing — not a git checkout, no contract, no resolvable login all stop here
instead of writing to an invented path. Three copies of this rule used to live in the package.


`$CURRENT` is THE cockpit of this repo — one per repo, whatever path the resolver hands back. Write
`$CURRENT`, never a cwd-relative `state/current.md`: inside a worktree that path is gitignored and
never comes back. There is no second cockpit to keep in step, and nothing here writes one.

## State hygiene (every run — the skills are the writers AND the janitors)

Before writing, sweep the CURRENT repo's Polaris root for strays (multi-panel machines drift:
older sessions write with pre-patch instructions):

1. Session files in the LEGACY top-level `<root>/sessions/` (not `team/<login>/sessions/`):
   `git mv` (or mv, if untracked) each into `team/<login>/sessions/`, adding a `-legacy` suffix
   on filename collision. Note the move in one line of this run's checkpoint — never silently.
2. Cockpits stranded in OTHER worktrees (`<worktree>/_polaris/state/current.md`): report them and
   name the one command that brings them home without merging or overwriting —
   `python3 "$ROOT/scripts/state_home.py" migrate`, which refuses loudly on an occupied
   destination and collects into `team/<login>/handoff/strays/<worktree>-<date>.md`. Never move
   them silently.
3. Non-canonical `current` variants in `<root>/state/` (anything beyond `current.md`, `todos.md`,
   `goals.md`, `backlog*.md`): FLAG them in your output with their mtime and first heading; fold
   their still-live content into the cockpit only on explicit confirmation. A repo that still
   carries an older dense cockpit beside `current.md` is exactly this case, not an exception.
4. **Branch state** — classify only the current lane before writing the handoff:

   ```bash
   # classify before the handoff
   LP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/lane_phase.sh"
   [ -f "$LP" ] || LP="$HOME/.agents/skills/end/scripts/lane_phase.sh"
   bash "$LP" "$PWD"
   ```

   `KEEP` means the worktree stays in the handoff. `READY_FINALIZE` means it may close only after
   the handoff commit. Unknown or unverifiable PR state is never cleanup permission. The script
   holds the two guards this question needs: a repo with **no remote** was never pushed, so it says
   so and stops (asking anyway answered «push presente ma nessuna PR verificabile», a refusal that
   reads like a broken branch), and a machine without `git-power` degrades in one line.
Skip silently when the repo is already clean. Never delete anything in steps 1–3.

## Step 1 — Write the handoff

Append to `team/<login>/sessions/YYYY-MM-DD-@<github-login>.md`:

**Same format as a checkpoint** (`references/checkpoint.md`) — it is the same file, read by the same person three weeks later:
two grammars in one log force a double read and make the log impossible to count. `end` changes
only the word after the time (`session end`) and closes with `Next session`.

```md
## HH:MM — session end · <title: what this session leaves behind> · wt: <worktree> · branch: <branch>
- Done: <verified result, with the proof>
- In progress: <what is left half-done, and where it sits>
- Next session: <first command to run>
- Blocker: <exact, or none>
- Key context: <decision and why · architectural choice · discovery that overturns a conclusion ·
  error and the rule that follows from it · superseded decision and what supersedes it>
  — tag: #decisione #architettura #scoperta #errore #superata #incidente
- Files: <path · symbol touched · why>
```

`Key context` and `Files` matter more here than anywhere else: the session ends, and what is not
written now no longer exists. `Files` as `path · symbol · why` is what lets the code-graph and this
log meet on the same symbol months later. SHAs and numbers are read from `git log`, not
remembered.

### The six fields are the five elements of the boundary — none is optional

The six lines are not a preferred format: they are the **five elements** that make the session
resumable, and the next session opens from here. A field with no content is written `none`,
explicitly; a field that is **absent** is a broken boundary, and `end` does not close.

| element | field |
|---|---|
| scope and decisions | `Key context` |
| task state and next task | `In progress` + `Next session` |
| changed files and working-tree state | `Files` |
| verification commands run and their outcome | `Done` |
| open questions, risks and approvals | `Blocker` |

**Fail-closed on a decision made and not written.** A `Key context` clause tagged `#decisione` or
`#superata` must **name the home that carries it**, in one of these three forms:

- the record id — `DEC-…` or `ADR-…` — and the record must exist under `decisions/`;
- the title of the `decisions.md` entry (Step 3), which the clause repeats in full;
- the issue in **qualified** form: `issue:<repo>#<number>`, for example `issue:acme-api#407`.
  The bare number (`#407`, «see PR #424») does **not** count: it is the most common thing to end up
  in a `Key context` line, and taking it for a home used to absolve every unwritten decision.

A retraction is a decision like any other — a withdrawn number is written **next to the number**,
not only here. If the clause names nothing, write it first (Step 3) and only then close: a
decision that lives only in this log is the decision the next session makes again, or overturns
without knowing it existed.

Where the repo carries the backbone gate, the same thing is an executable check and not a
reminder — otherwise the six lines above remain a checklist:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" close \
  --root "$ROOT" --handoff "$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md" || exit 1
```

It closes **the session that `start` opened in this checkout**: the sid is not passed and not
invented — it is checkout + day + login, recomputed here. The engine is the repo's own, if it
carries one, otherwise the declared vault's (`git config polaris.vault`), the same lookup the brief
pack does.

It closes **the open session**, not today's sid: at midnight the derivation changes while the
session is still open, and a panel may never have run `start`. `SESSION: none open — nothing to
close` exits 0 and `end` proceeds: the durable thing is the handoff commit, and a receipt already
written is never rewritten.

**The `|| exit 1` applies to refusals only.** This block used to be an `if [ -f "$GATE" ]` on a
host-only path, and with an `&&` … `||` chain EVERY refusal — even `ID_COLLISION` — fell into the
`||` branch printing «no gate» with `$?` at `0`: the skill went on to the Step 5 commit in
exactly the cases the gate exists to stop. Now a missing engine exits 0 printing the note, and the
`|| exit 1` catches only real refusals.

Seven refusals, all before the receipt — but only **with an open session**: without one the engine
does not run and only the two that the log earns by itself remain, which the door checks first
(`HANDOFF_MISSING`, `HANDOFF_UNREADABLE`, exit 1). The other five — unwritten decision, id already
spent, someone else's tree — have no session to run against: they still hold as a rule, and what
they uncover goes into an issue, not into a refusal that does not exist.
The seven: `HANDOFF_MISSING` if the log is not passed to it and
`HANDOFF_UNREADABLE` if the path is not readable (the five elements are read, not invented),
`HANDOFF_INCOMPLETE` names the missing element, `DECISION_UNWRITTEN` the clause that does not name
its home, `ID_COLLISION` a Decision id already spent elsewhere, `TREE_NOT_OURS` a dirty path that
no `Files` line declares and `TREE_UNREADABLE` a tree that `git` cannot read (one committer per
tree), `SESSION_UNKNOWN` a sid that has no `start.json`.
Lessons come out as `LESSON_PROPOSAL` lines on stderr: they are **proposals**, and Step 3 decides
which ones qualify and records them through `lesson_record.py`. The gate writes no lesson on its own.

### Step 1b — Structured handoff → `$ROOT/team/<login>/handoff/YYYY-MM-DD.md`, only while the lane is open

The contract's `handoff/` directory is for handoffs RICHER than a checkpoint, and a handoff exists to
hand over open work (founder, 2026-10-25: «if the lane is closed, end leaves no handoff; if there is
still work, it also leaves the handoff»). The lane is **closed** only when both hold:

- `lane_phase.sh` printed `READY_FINALIZE` (its PR is merged), and
- the session-end entry's `In progress`, `Next session` and `Blocker` are all `none`.

Then no handoff file is written, the output says `no handoff — lane closed`, and Step 5 simply
omits the path. Every other answer — `KEEP`, `no remote`, a refusal, `git-power not installed`, or
any open field — writes it: an unknown lane is never a closed one. `start` resumes from the session
log, not from this file, so a closed lane loses nothing. When the lane is open, write it (main
worktree, append if the file exists):

```md
# Handoff YYYY-MM-DD HH:MM — @<login>
Repo: <repo> · wt: <worktree name or main> · branch: <branch> · commits: <shas this session>
## Shipped (verified)
## Open threads (with exact state)
## Next session: first command to run
## Risks / do-not-touch
```

This file is committed shared history (Step 5 includes it). The cockpit carries the thin index and
the capped summary; THIS is the structured one a teammate (or you in 3 days) resumes from.

### Step 1c — `## Recent Context` (the session summary, capped at five)

The repo has ONE cockpit, `$CURRENT`, and inside it ONE place for session summaries. `end` is the
only writer of that section — a checkpoint never touches it — and it is a ring: five entries, newest
first. There is no second per-repo cockpit to append to: a dense file that
only grows is the surface that died at 188 KB while everyone kept reading `current.md`.

```bash
RC="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/recent_context.py"
python3 "$RC" "$CURRENT" --entry "### $(date +%F) — <what this session leaves behind, one line>"
```

Three surfaces, three jobs: `Updated:` carries date and owner, THIS section carries the summary,
the session log carries the full handoff. Exit 2 means the cockpit has no `## Recent Context`
section — add the heading the contract declares (`skills/start/templates/repo-contract/state/current.md`), never
let the entry land at EOF.

Additionally, if this repo DECLARES a vault and it is not the current root, put the SAME one-line
entry in the vault's own ring, so work done here is visible from there without growing a second
everything-file anywhere:

```bash
VAULT="$(python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" \
  vault --root "$ROOT")"                                 # declared per repo, never guessed
[ -n "$VAULT" ] && [ "$VAULT" != "$ROOT" ] || VAULT=""
```

```bash
RC="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/recent_context.py"
[ -n "$VAULT" ] && python3 "$RC" "$VAULT/state/current.md" \
  --entry "### $(date +%F) — <repo>: <what this session leaves behind> · branch <branch>"
```

No declaration, or a declared path that is not there → no copy, and this repo's cockpit is the only
record. A literal path used to live here, which meant every install looked for a directory that
exists on one machine and the public package carried a home directory. Set it once per repo:
`git config polaris.vault <path>`, the same mechanism `polaris.login` already uses — **one key**,
the one `start`, `init` and the doctor already read. `polaris.vault-root` was a second spelling
of the same fact and is still read for one cycle, with a deprecation note on stderr naming the
key that replaces it.

Three surfaces carry a session and no fourth exists: the thread line in `current.md` (thin index),
the `## Recent Context` entry (summary, capped), the committed session log (full handoff). The
richer per-session document is `handoff/YYYY-MM-DD.md` from Step 1b, which is committed history.

## Step 2 — Tick the plan

Update the matching row in `team/<login>/weeks/$(date +%G-W%V).md` only when its state or proof
changed. Do not rewrite the plan.

## Step 3 — Decisions listed with their homes, lessons written (a proposal that dies with the session is data loss)

`end` WRITES the lessons that qualify and LISTS the session's decisions, each with its home, in the
closing summary. Only the genuinely durable qualifies. Operating model §6–§7 decide the home.

**A decision** qualifies only if it either **supersedes a past decision** (name which, and align it)
**or** sets a direction whose impact runs from today out to months. **`end` never writes one.** Each
goes through `/architecture decide`, which measures it and writes the record where operating model
§6 puts it — a `decisions.md` entry when nothing needs building, a DEC file with `probe` and
`probe_kills` plus one ledger line when it must be enacted or passes all three ADR tests — and a hook
on the founder's machine refuses a hand-written ADR, DEC, `decisions.md` or `ARCHITECTURE.md`. A
decision already recorded is listed with its home (DEC id, `decisions.md` title, or
`issue:<repo>#<n>`); one with no home goes to `/architecture decide` before the Step 1 gate runs, or
the gate refuses it as `DECISION_UNWRITTEN`. The paths it wrote land in the Step 5 commit.

**A lesson** = a real mistake — usually a loop or blocker you overcame — plus the one rule that
prevents its recurrence. It is written ONLY by `scripts/lesson_record.py` (the repo's, else the
declared vault's: `python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" vault --root "$ROOT"`).
`lessons.md` is a retired pointer and `scripts/record_gate.py` refuses a lesson written there.

```bash
L="$ROOT/scripts/lesson_record.py"
[ -f "$L" ] || L="$(python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" vault --root "$ROOT")/scripts/lesson_record.py"
python3 "$L" match "<lesson title>"                      # read-only: is it already known?
python3 "$L" add --title "<mistake → rule>" --family <family from records/families.md> \
                 --area <area> --body-file <file with the story and the rule>
```

`add` prints `RECORD records/lessons/<id>.md` (a new lesson) or `OCCURRENCE <id> (family <f>)` (a
known lesson recurred: one line appended to `records/occurrences.jsonl`). `LESSON_REFUSED` (exit 2)
names what the schema refused — fix it, never write the file by hand. The `LESSON_PROPOSAL` lines
`session_gate.py close` prints on stderr are candidates: this step decides which qualify.

**Lessons become checks (operating model §7).** When `add` printed `OCCURRENCE` — the same family
recurs — or the lesson cost an incident (prod down, data lost, a revert, hours of rework), open one
bead naming the check that would have caught it:

```bash
bd create "<the check to build: what it refuses, where it runs>" -t task \
  -l kind:followup,src:lesson,area:<area> --description "lesson <record id>; family <family>"
```

No `bd` on this machine → say so in the closing summary with the check's text; never drop it.

**ADR — backstop audit (the ADR is born AT DECISION TIME, not here).** Sweep this session for
qualifying decisions: each must ALREADY have its record in the house the repository declares — the
`decision:` row of the `outputs:` map in its contract (`_polaris/config.yml`, else `./config.yml`
when the repository root is itself the contract root). One missing = a miss to repair NOW, named in
the closing summary, and repaired through `/architecture decide`, never by hand; include the file
it writes in the Step 5 commit.

If nothing durable happened, say so. Do not log routine progress as either.

## Step 4 — Prune the live pointer (the only step allowed to close a thread)

Path per the **One home** rule: `$CURRENT` — the handoff lands where the next
session opens. **Reconcile** it: read it first, never blind-overwrite, same rules as the checkpoint lane step (threads keyed
by branch, nothing open lost, other panels' threads and `Next` lines untouched) — with one
difference. **`end` is the only Team OS command with closing authority**, and it spends it against
ground truth rather than impression.

Pruning is **automatic and proven**, no longer by hand. The pruner asks two sources and requires
them to agree: the **tracker** (`gh pr view N` says `MERGED`, or `gh issue view N` says `CLOSED`
for `COMPLETED`) and the **repo** (the head of that PR, or its merge commit, is an ancestor of the
default branch HERE). First look, read-only:

```bash
# read-only: no line leaves `## Open`, only the verdicts are looked at
PT="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/prune_threads.py"
[ -f "$PT" ] || PT="$HOME/.agents/skills/end/scripts/prune_threads.py"
python3 "$PT" "$CURRENT" --owner "$LOGIN" --now "$(date +%F)"
```

A thread closes only when **every** citation it carries is settled: a lane reading «closes #77,
then #79» with #79 still open stays. Five verdicts. `PROVEN` really landed. `DEAD` is abandoned
work — a PR closed without merge, an issue closed as not planned — and closes the lane too, logged
as `DEAD`, never as completed; a `DEAD` citation next to an `OPEN` one keeps the lane (measured
2026-09-30: 15 of 38 lanes in a product cockpit were dead and `end` closed none). `AMBIGUOUS` is
merged where this checkout cannot see it, **or** a branch carrying commits past the merged head:
that lane is alive again. `OPEN` is a PR still open. `BLOCKED` is a tracker that does not answer
(no `gh`, an error, a rate limit, an empty answer): **one `BLOCKED` stops the whole run** and exits
`2`, because a prune that removes four lanes and silently skips one is the old silent no-op,
inverted. Then apply:

```bash
PT="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/prune_threads.py"
[ -f "$PT" ] || PT="$HOME/.agents/skills/end/scripts/prune_threads.py"
python3 "$PT" "$CURRENT" --apply --owner "$LOGIN" --now "$(date +%F)" \
  --log "$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md" \
  --todos "$ROOT/state/todos.md"
```

Every `PROVEN` leaves `## Open`, its `state/todos.md` row moves from `## Active` to `##
Completed` with today's date, `Updated:` shrinks to **date and owner**, and the thread **with its
verdict** is appended to the session log: the thread does not vanish, it moves, and the log stays
append-only. `Active` is never zeroed and `Added:` is not re-stamped: the other rows come back
byte-identical. `state/todos.md` is **not mandatory** in the contract: if it is missing, the step
works anyway and says so (`"todo": "skipped"`). Closing means removing the **whole lane** — the
line and what sits under it, indented children and fence block included: an orphan line under
`## Open` is work the next session has to reconcile.

The run also prints `STALE=` for every lane that cites nothing and is older than 14 days: no
verdict can close it, so **each one is resolved in this `end`** — open an issue for it (then it has
a citation), or close it by hand below with the reason in the session log. Reading `0 PROVEN` and
moving on is how a cockpit reached 38 lanes. The manual close takes the lane id, or `#N` for the
one lane citing #N; a missing `state/todos.md` is skipped, as the contract allows:

```bash
CL="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/state_close.py"
python3 "$CL" close "$CURRENT" --key "<branch>" --todos "$ROOT/state/todos.md" \
  --owner "$LOGIN" --now "$(date +%F)"
```

A key that does not name exactly one thread exits `2` and touches nothing — better a rerun than the
wrong lane deleted.

**Closing means REMOVING, not annotating.** A thread proven landed comes **out** of the file; a
`~~struck~~` line that stays is still tokens the next session reads and reconciles; the open
threads that remain must reflect reality. Same pass:
collapse the state line to **one** `Updated:` — date and login, nothing else: the clause on what
changed belongs to `## Recent Context`, and the full story to the session log. Target after pruning: under 2,000 tokens; `checkpoint.sh verify`
fails on a second `Updated:` line and warns above the size.

### The worksite census goes into the handoff

```bash
CT="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/git-power/scripts/cantiere.py"
[ -f "$CT" ] || CT="$HOME/.agents/skills/git-power/scripts/cantiere.py"
if [ ! -f "$CT" ]; then
  echo "NOTE: git-power not installed — handoff without the worksite census"
else
  OUT="$(python3 "$CT" census --tsv --repo "$MAIN_WT" 2>&1)"; CENSUS_RC=$?
  if [ "$CENSUS_RC" = "2" ]; then   # only "unknown flag": exit 1 means "something to act on"
    echo "NOTE: git-power predates the TSV contract — census in prose"
    python3 "$CT" census --repo "$MAIN_WT"
  else
    printf '%s\n' "$OUT"
  fi
fi
```

TSV rows `VERDICT\tbranch\tpath\tnote`, exit 0 clean / 1 something to act on / 2 error (the
`cantiere.py` contract). Copy into the handoff, verbatim, under a `**Cantiere**` line, every row
whose verdict is not MAIN — CLOSABLE is what can be closed, DIRTY is what has uncommitted work or
non-empty ignored files. These are the two things whoever resumes must know without re-reading the
graph. `end` **closes nothing** — it lists, and closing remains an explicit act.

`git-power` does not travel in this package, and the **three** sites that call it resolve it the
same way: `$CLAUDE_PLUGIN_ROOT` → `$HOME/.agents` chain, `[ -f ]`, and a declared degradation line.
Without that guard a half-run `end` broke with a raw Python error on a machine without
`git-power`. The fallback fires **only on exit 2**, which means «unknown flag»: exit 1 means
«something to act on» and is a valid result, not an error to repeat in prose. An older copy of the
contract rejects `--tsv` and the fallback prints the same thing as Italian prose, one item per
line with the verdict in square brackets. In both cases the same rule holds: **read the verdicts
the command prints**, not the ones this line remembers. The vocabulary belongs to the tool, and
this prose ages faster than it does.

### The panel's open PRs — one line of reason each

Whoever opens a PR carries it to merge. A PR left open at session end is not neutral: it conflicts
with the next lane, and several PRs open together on the same manifest make you pay the bill all
at once. So `end` **lists** them and says which ones already carry their reason in the cockpit:

```bash
CK="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/checkpoint.sh"
[ -f "$CK" ] || CK="$HOME/.agents/skills/end/scripts/checkpoint.sh"
bash "$CK" open-prs
```

`OPEN_PR=#N <branch> — reason: MISSING` (the script's output line) is the line that concerns you:
write **one line** in `$CURRENT` saying why that PR stays open — an act of the repo owner, a
credential you do not have, a CI run still to be read — and cite it with its `#N`, which is the key
the next round uses to find it again. `reason: PRESENT` means the cockpit already names it and there is nothing to write. `OPEN_PRS=unknown` is `gh` not
having answered: list them by hand and carry on anyway.

**This step never refuses** (repo owner decision, 2026-09-06): it is a reminder, not a wall. A gate
that blocks session close is a gate that gets bypassed, and a badly closed session loses the
handoff, not just the PR list. The command exits `0` in every branch, open PRs without a reason
included.

**`state/goals.md` is NOT touched here.** Goals change by explicit decision, never by session
inertia. If it is empty or untouched for more than 30 days, say so in the closing summary and ask
once — do not write it.

**The thread line is the handoff that survives.** A session log committed on a branch is
INVISIBLE to `start` until that branch merges — for a paused worktree that can be days. So the
thread line in `current.md` must carry the resume-essence on its own, written as if it is the only
survivor (it is): `- \`branch\` — <done in 1 clause; next concrete step; blocker or none> ·
wt: <worktree path if not main> · since YYYY-MM-DD`. Pausing WITHOUT a PR is normal: keep the
worktree alive, record its path in the line, and the next session reopens that same worktree from
`start` — never feel forced to PR early just to make work visible.

**Branch discipline (`git-power`).** Live GitHub state decides branch fate: an OPEN PR stays in
the handoff; a paused branch without a merged PR stays alive; only `READY_FINALIZE` may close after
the handoff has landed. Session end is not automatically branch end.

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

## Step 4b — Reconcile `## Active Priorities` (the only writer of the order)

The cockpit is the one view the repo owner reads, and `start` reads only it — so the order of the
work lives here and **this step is its only writer**. Every `end`, after Step 4, rebuild the
ordered list from four inputs: `state/goals.md` (where we are going), the `## Active` rows of
`state/todos.md`, the `## Open` threads that survived Step 4, and what this session changed.
Rules: each line is `#<issue or lane> — <outcome in one line>`; the first line is the next thing
to do. An item leaves **only** when Step 4 closed it as `PROVEN` — an `OPEN` or `AMBIGUOUS` lane
stays in the order, and if Step 4 stopped on `BLOCKED`, do not rewrite the order this session.
Keep it to **7** lines by folding the tail into one last line (`… — also: #A, #B, #C`), never by
dropping a live item in silence. If the order did not change, write it anyway —
the stamp records that it was reviewed today, and `start` names an order older than 7 days.

The heredoc is QUOTED (`<<'ORDER'`) on purpose: lane ids carry backticks, and inside double
quotes the shell would run them and write a corrupted order with exit 0.

Never edit the section by hand or by string surgery: on 2026-09-13 an unanchored `s.index` matched
a backtick mention of the heading and fused it into a sentence, and the order stayed wrong for ten
days. The script finds the real heading, writes atomically under the cockpit lock, and adds the
section before `## Open` when it is missing:

```bash
PR="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/state_priorities.py"
[ -f "$PR" ] || PR="$HOME/.agents/skills/end/scripts/state_priorities.py"
[ -f "$PR" ] || { echo "STOP: state_priorities.py not resolved — never hand-edit the order"; exit 1; }
python3 "$PR" set "$CURRENT" <<'ORDER'
#N — first
#M — second
ORDER
```

## Step 5 — Land the handoff in git (same guard as a checkpoint, in code)

Land what you wrote through **the same script a checkpoint uses** — pathspec-only, never `git add -A`,
and never a push. The session log is committed on the current branch, always, with two declared
exceptions — a detached HEAD, and the `no-direct-default` policy on the default branch.
A repo with no commit at all is not an exception: the first handoff lands like any other.

An `end` that postpones instead of committing is an `end` that did not do its work (repo owner
decision, 2026-09-04). Third declared outcome, always exit 2: a path that git refuses (ignored, or
inside a nested repo) is named with its reason and the other paths land anyway — a handoff does
not die because one file sits in an ignored directory.
On the exceptions the script exits 2 with a line saying which one: the files stay where you wrote
them, are not copied elsewhere, and you say so plainly instead of reporting success.
```bash
cd "$(git rev-parse --show-toplevel)"   # the panel's own worktree, never another one
SC="${CLAUDE_PLUGIN_ROOT:-}/skills/end/scripts/session_commit.sh"          # plugin install
[ -x "$SC" ] || SC="$HOME/.agents/skills/end/scripts/session_commit.sh"    # skills-CLI install (npx)
"$SC" --end "$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md" \
            "$ROOT/team/$LOGIN/handoff/$(date +%F).md" \
            "$ROOT/team/$LOGIN/weeks/$(date +%G-W%V).md" \
            "$ROOT/decisions.md" <each DEC file /architecture decide wrote> \
            <each records/ path lesson_record.py wrote>
```

On a closed lane the handoff path does not exist (Step 1b) and is dropped before the `add`, like
any absent path.

`--end` is the mode that may commit `decisions.md` and the lesson records (`records/lessons/<id>.md`,
`records/occurrences.jsonl`; they are this command's vetted promotion); it still refuses `state/current.md` and `.env*`, and never pushes. On one of the three
declared exceptions (exit 2) say plainly which one it was and that the handoff is still in the
working tree, uncommitted — never report a clean close. **Both resolver candidates missing**
(say which you tried): `git add --` those exact paths and
`git commit -m "chore(polaris): session handoff $(date +%F) @$LOGIN"` — never `git add -A`.

All the paths are named: those that do not exist are **discarded before** the `add`, because
`git add -- existing missing` stages NOTHING and exits 128 — a weekly plan never opened made the
whole handoff land nowhere. And if a hook rejects the commit the script exits 1, reports the hook's
line and cleans the index of the Polaris paths only: leaving them staged means the next commit,
without a pathspec, carries the handoff away. Never `--no-verify`.

Then read the ground truth back, because a skill that reports success on a dirty tree is the failure
this step exists to close:

```bash
git status --short   # 0 lines on the Polaris paths, or say exactly which one is left and why
```

Never commit or push without an explicit request. After committing, if the branch is ahead of its
remote, remind the contributor there is unpushed work:

```bash
git status -sb | head -1   # e.g. "## main...origin/main [ahead 1]"
```

## Finish

After the handoff commit, close only the current lane when it is already remote-merged:

```bash
LP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/lane_phase.sh"
[ -f "$LP" ] || LP="$HOME/.agents/skills/end/scripts/lane_phase.sh"
bash "$LP" "$PWD"
# only after READY_FINALIZE — and only where the lane phase could actually be read:
GP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/git-power/scripts/cantiere.py"
[ -f "$GP" ] || GP="$HOME/.agents/skills/git-power/scripts/cantiere.py"
[ -f "$GP" ] && python3 "$GP" phase finalize --repo "$PWD" --confirm "$PWD"
```

`finalize` preserves dirty/divergent main and removes only the current clean merged feature
worktree plus its exact branch ref.

Summarize the handoff in three bullets (shipped, open, next). This command never writes outside the
current repository and never mutates the tracker.
