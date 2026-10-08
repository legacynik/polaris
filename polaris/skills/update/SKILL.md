---
name: update
description: Polaris skill — record a short repository-first checkpoint during an active session. Trigger after meaningful progress, a blocker, a context switch, or on "checkpoint / save progress / /update".
user-invocable: true
model: sonnet
version: 3.4.0
invokes: [git-power]
---

# /update — checkpoint

## Overview

One session takes many checkpoints. Each one **appends** an entry to the session log and
**updates in place** what the previous checkpoint left in the cockpit. Two files, two opposite
rules, and the whole system rests on the difference:

| file | rule |
|---|---|
| `team/<login>/sessions/<date>.md` | append, always — the ledger, it grows |
| `state/current.md` (the cockpit) | overwrite — your lane's line is rewritten, never duplicated |

Founder, 2026-09-03: *«Non è che dentro current fa un'altra riga, ma va semplicemente ad
aggiornare l'update precedente. Invece all'interno della session mette sempre un'altra riga.»*

## When to Use

- After meaningful progress, a blocker, or a context switch
- On "fai un checkpoint", "save progress", `/update`

**When NOT to use:** resuming (`/start`), closing the session (`/end`), the weekly report
(`/report`), or recovering an earlier checkpoint — that is a read, not a write.

## Process

### 1. Prepare

```bash
"${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/checkpoint.sh" prepare
```

It resolves root, login, branch, session-log path and `CURRENT` — the MAIN worktree's cockpit,
never this panel's. `ARCHIVE_DIRTY` refuses a pre-existing staged or unstaged shared ledger;
resolve ownership before editing it. If prepare fails, read the message and stop. Never guess a path.

### 2. Append the entry to the session log

```md
## HH:MM — <title: what happened> · wt: <worktree> · branch: <branch>
- Done: <verified, with the proof>
- In progress: <what is half-done, so the next panel knows where it stands>
- Next: <one concrete step>
- Blocker: <exact, or none>
- Key context: <the decision and why · the finding that overturns a conclusion · the mistake and
  the rule that follows · the decision superseded and by what>
  — tags: #decisione #architettura #scoperta #errore #superata #incidente
- Files: <path · symbol touched · why>
```

The title carries the entry: `#1010 closed end-to-end: prod deployed`, not "checkpoint".
SHAs and counts come from `git log`, never from memory. A founder correction is the most valuable
line of the session and you are its only witness: write what you believed, what was true, what
proves it, the rule that stays. An empty `Key context` beats an invented one.

Keep it short. For a reusable mistake, add `#lezione` in `Key context` and
`- Lesson: <exact title>`; for a decision already made, add `#decisione` and
`- Decision: <exact title>`. These pointers name committed headings in this checkpoint's
`lessons.md` and `decisions.md`. Do not mark an open bug as a lesson or invent approval for a
decision. No qualifying record means no pointer.

### 3. Harvest the scratch delta

```bash
SID="${CLAUDE_SESSION_ID}"                     # this session's id; empty on a harness that has none
POLARIS_SID="$SID" "$CHECKPOINT" harvest-slice   # this session's scratch, the whole delta
POLARIS_SID="$SID" "$CHECKPOINT" harvest-done    # move the watermark in that file, always
```

The scratch is one file per session and per day. The script reads and stamps the files named for
this session's id and no others; with no id it takes the only one touched today, and when several
panels wrote today it reads nothing, stamps nothing and prints the candidates. Then pass the id
of your own session and re-run: never pick a file by date or size. Pass the same `POLARIS_SID`
to `verify`.

What you find becomes `Key context`.

Before committing, put each pointed-to lesson or decision in the matching append-only archive,
newest first. A lesson states the actual mistake and its repeat-prevention rule; a decision states
the choice and evidence. An architectural decision also gets its ADR under the repo's declared
decision house. Write qualifying records at this checkpoint; `/end` may never run.
Audit the work since the previous checkpoint before deciding there are no records; do not infer
"none" merely from missing tags in the draft log.

### 4. Update your lane in the cockpit

Read `## Open` in `$CURRENT`. Then decide:

- **A line is your lane** — same work, even under another branch name, even written by another
  panel or on another day → keep its first backtick key and replace that line.
- **No line is your lane** → choose a new stable key and add one line.

```md
- `<lane-key>` (<repo>) — branch `<branch>`; <state in one line> · since <first YYYY-MM-DD>
```

Set `LANE_LINE` to that exact line, then use the existing atomic writer:

```bash
: "${LANE_LINE:?set the one-line state for the existing or new lane}"
UP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/state_upsert.py"
printf '%s\n' "$LANE_LINE" | python3 "$UP" thread "$CURRENT" --owner "$LOGIN" --now "$(date +%F)"
```

It rewrites the one matching key or adds one new key, and maintains one `Updated:` line. Leave
other lanes byte-identical. Never close a thread by judgment or write `## Recent Context` here;
`/end` owns those. If nothing material changed, do not write at all.

### 4b. Remove what the tracker already closed

```bash
"$CHECKPOINT" reconcile
```

A panel that checkpoints and never reaches `/end` used to leave the cockpit false: a lane whose
pull request merged yesterday still under `## Open`, an issue already closed still second in
`## Active Priorities`. `reconcile` runs the prover `/end` closes with. A lane or a priority
leaves only when EVERY issue or PR it cites is proven done by the tracker and by this checkout;
the verdict is appended to today's session log, so run it after step 2. One unreadable answer
removes nothing, and the command always exits 0. Abandoned work (closed as not planned, a PR
closed unmerged) is a judgment and waits for `/end`. The tracker is asked once per window for
the whole repo (three hours by default), so most checkpoints print one line and cost nothing.

You decide nothing here and you do not help it: a line that cites no number, or that states a
fact no tracker holds (a version in production, a deploy to decide), stays until `/end`. If such a
line is false and you can prove it, say so in `Key context` and flag the line; do not delete it.

### 5. Weekly todo, if the item exists

If the checkpoint advanced a row in `## Active` of `state/todos.md`, edit **that row's text** and
keep its `Added` stamp: the stamp says how long the item has waited. Never add a row here —
`plan-week` reconciles the section.

### 6. Plan tick, if a weekly plan exists

One dated line under the outcome advanced in `team/<login>/weeks/<week>.md`. No file, no step.

### 7. Land and verify

```bash
python3 "$GP" commit-check --repo "$PWD"      # git-power, when installed
CHECKPOINT_PATHS=("$SESSION_LOG")
[ -f "$HANDOFF" ] && CHECKPOINT_PATHS+=("$HANDOFF")
# Append only exact owned paths written now: weekly/todos/lessons/decisions.
"$CHECKPOINT" commit "${CHECKPOINT_PATHS[@]}"
POLARIS_SID="${CLAUDE_SESSION_ID}" "$CHECKPOINT" verify "<title of the entry just written>"
```

Before `commit`, append any archive, plan, or todo file this checkpoint changed to
`CHECKPOINT_PATHS` — `state/todos.md` too when `reconcile` moved a row to `## Completed`; never include a merely dirty path owned by another panel. `verify` fails if
the log or a pointed-to archive is not committed, the cockpit is stale/stacked, or scratch was
not harvested. If this repo requires a remote push for lessons, follow its branch/PR policy and
report local-only until pushed. A foreign or unknown dirty path blocks: assign it, never stash
or commit for another panel.

Il log atterra sul branch corrente, sempre. Le due eccezioni che fermano l'intero commit sono
HEAD detached e policy `no-direct-default`; un path ignorato o annidato è invece nominato e
rifiutato singolarmente.

Then tick the session the `/start` of this checkout opened — one append-only event, so the
restartable boundary knows this checkpoint happened even if `/end` never runs:

```bash
SG="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py"
if [ -f "$SG" ]; then
  python3 "$SG" note --root "$ROOT" --note "<title of the entry just written>"
fi
```

Silence is the answer when no session is open and when the repo carries no engine. It never
fails a checkpoint: what is durable is the log you just committed, not this event.

### 8. Output

One line: `Checkpointed: <what>`. No summary, no next-action list — they are in the entry.

## Lessons and decisions

Use the append-only archives for qualifying records, not for routine progress. Never promote a
lesson or decision only in prose or only at `/end`; never write it to the apex (`CLAUDE.md`,
`rules/*.md`) — that goes through `pol-apex-curate`.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's a new session, I'll add a new `## Open` block" | Measured: 14 stacked `Open` sections and 6 lines for `main` in one repo. Sessions are many, the cockpit is one. Rewrite your line. |
| "The branch name changed, so it's a new lane" | The lane is the work, not the string. Same work, same line. |
| "That line was written by another panel" | If it is your work, it is your line. Panels share lanes; only lines of *other* work are not yours. |
| "I'll shorten the cockpit while I'm here" | A line that looks old may be the only copy of a handoff. `reconcile` removes what is proven closed; everything else waits for `/end`. |
| "That lane is obviously done, I'll delete it" | Obvious is how one panel's cleanup removed another panel's live thread. If the tracker cannot prove it, it stays. |
| "I remember the SHA" | Both versions of an A/B test wrote the same wrong SHA from memory. `git log`. |
| "Nothing to put in Key context, I'll write something" | Noise is counted like signal. Leave it empty. |
| "`verify` is a formality" | The rule was in prose for weeks and got skipped anyway. The gate is the rule. |

## Red Flags

- A second `## Open` heading or a second `Updated:` line in the cockpit
- Two lines in `## Open` describing the same work
- A `state/current.md` inside a worktree
- `git add -A`, a stash, or a commit for another panel's paths
- A checkpoint entry with no title, no `Files`, or a number not read from git
- Closing, pruning, or summarising by hand from `/update` — only `reconcile` removes, and only on proof

## Verification

- [ ] Session log has one new titled entry with `Files`
- [ ] `## Open` has exactly one line for this lane, `Updated:` is one line, dated today
- [ ] Every other cockpit line is byte-identical, except what `reconcile` reported as removed
- [ ] `checkpoint.sh verify "<title>"` exits 0
- [ ] Every `Lesson:` / `Decision:` pointer names a committed archive heading
- [ ] `git status --short` is empty in this worktree and in the main one

## Never

Create issues, branches, PRs or deployments · declare complete without linked proof · touch another
panel's lane · write a cockpit inside a worktree · `git add -A`.
