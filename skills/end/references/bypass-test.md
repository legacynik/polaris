---
title: bypass-test — end
description: The ways a session was closed without a usable handoff, a checkpoint was faked, stacked or lost, or a lesson was lost, and the check that now stops each.
status: active
---

# Bypass cases — end

## B1 — a refusal fell through to the commit

An `if [ -f "$GATE" ] && … || echo "no gate"` chain sent every refusal of `session_gate.py close`
— even `ID_COLLISION` — into the `||` branch with `$?` at 0, and `end` went on to commit. Step 7
is now `session_gate.py close … || exit 1`: a missing engine exits 0 with a note, a refusal stops.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" --selfcheck
```

## B2 — a decision lived only in the log

A `#decisione` clause that names no home is the decision the next session makes again. The close
gate refuses it (`DECISION_UNWRITTEN`); a bare `#407` does not count as a home.

## B3 — a lesson written where the vault refuses it, or never turned into a check

`lessons.md` is a retired pointer (`scripts/record_gate.py` refuses a lesson there). Step 4 writes
only through `lesson_record.py`, which matches first and appends an occurrence instead of a second
record. A recurring family or an incident opens one `kind:followup src:lesson` bead naming the
check; without `bd` the check is named in the summary, never dropped.

```bash
python3 scripts/record_gate.py --root .
python3 -m pytest -q scripts/test/test_lesson_record.py
```

## B4 — a lane closed on impression

The pruner closes a lane only when the tracker AND the repository agree (`PROVEN`); one `BLOCKED`
stops the whole run with exit 2 instead of silently skipping a lane.

```bash
python3 skills-suite/end/scripts/merge_truth.py --selfcheck
```

## B5 — a handoff reported but not landed

A missing weekly file made `git add -- existing missing` stage nothing and exit 128; a hook refusal
left the handoff staged for the next commit. `session_commit.sh --end` drops missing paths before
`add`, unstages on refusal and names any path still staged; `git status --short` is read back.

```bash
bash skills-suite/end/scripts/session_commit.sh --selfcheck
python3 -m pytest -q skills-suite/end/tests/test_session_commit_index.py
```

## B6 — `end` closes the plan

Closing plan files and promoting decisions belongs to `plan close`, run by `ship` after the merge
(operating model §3 phase 8). The body names no `done/` move and no epic squash.

## B7 — checkpoint: the cockpit stacks instead of updating

Measured: 14 stacked `## Open` sections and 6 lines for `main` in one repository. Step 3 writes the
lane through `state_upsert.py thread`, which rewrites the one matching key; `checkpoint.sh verify`
fails on a second `Updated:` line.

```bash
python3 skills-suite/end/scripts/state_upsert.py --selfcheck
bash skills-suite/end/scripts/checkpoint.sh --selfcheck
```

## B8 — checkpoint: a checkpoint reported but not committed

"Checkpointed" on a dirty tree was the failure. `verify` exits 1 when the log or a pointed-to
record is not committed, when the cockpit is stale or stacked, or when the scratch was not
harvested; an unreadable cockpit is named as unreadable (`tests/test_checkpoint_verify.py`).

## B9 — checkpoint: a refused commit leaves the handoff staged

A hook refusing the commit used to leave the session paths staged, so the next pathspec-less
commit carried them away. `session_commit.sh` now unstages them, and names any path it could not
unstage (`STILL STAGED`) instead of claiming the index was restored
(`tests/test_session_commit_index.py`).

## B10 — checkpoint: a lesson written where the vault refuses it

`lessons.md` is a retired pointer: `scripts/record_gate.py` refuses a lesson written there. Step 4
records through `lesson_record.py`, and the `- Lesson:` pointer names the record id it printed,
which `verify` checks in `records/`.

## B11 — checkpoint: another panel's work committed

`git add -A` and stashes swallowed other panels' files. `checkpoint.sh commit` takes exact paths
only and refuses a pre-staged shared ledger (`decisions.md`, `occurrences.jsonl`).

## B12 — a handoff for a closed lane, or none for an open one

A handoff file is written unless the lane is closed: `lane_phase.sh` printed `READY_FINALIZE`
and `In progress`, `Next session` and `Blocker` are all `none`. Every state the classifier cannot
read — not a checkout, no remote, no `git-power`, no verifiable PR — prints something other than
`READY_FINALIZE`, so an unknown lane always gets its handoff.

```bash
bash skills-suite/end/scripts/lane_phase.sh --selfcheck
```

## B13 — `end` writes a decision by hand

`end` lists decisions with their homes and writes none: each goes through `/architecture decide`,
and a hook on the founder's machine refuses a hand-written ADR, DEC, `decisions.md` or
`ARCHITECTURE.md`. A `#decisione` clause with no home is still refused by the close gate
(`DECISION_UNWRITTEN`, B2).
