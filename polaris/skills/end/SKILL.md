---
name: end
description: ◇ Polaris — save the session, as a checkpoint or as the close. Every call appends a session-log entry, rewrites your lane line in the cockpit, records lessons, lists decisions with their homes and commits pathspec-only; the close also prunes the cockpit against git and the tracker and leaves a handoff only while the lane has open work. Use on "checkpoint / save progress / salva", after a blocker, or on "wrap up / end session". Requires git, python3; gh to prune; bd for follow-ups.
version: 1.26.0
user-invocable: true
status: active
lifecycle: session work → every call, one session-log entry + your lane line rewritten in the cockpit → at the close, the cockpit pruned against proof and a handoff file only while the lane has open work → committed on the current branch, raked to the default branch by a docs PR the same day, read by the next start
invokes: [git-power]
invoked-by: human
io: the session's changes + mode (checkpoint, or close by default) → one session-log entry, one cockpit lane line, lesson records and follow-up beads, the decisions listed with their homes, a pathspec-only commit; at the close also the pruned cockpit, handoff/<date>.md unless the lane is closed, a three-bullet summary
---

# end

## What it does

Saves the session so the next one resumes from files alone: every call logs an entry and rewrites
your lane line; the close also prunes the cockpit against proof and hands off only open work.

## When

- **Checkpoint**, the session stays open: "checkpoint / save progress / salva", `/end checkpoint`, or after progress, a blocker or a context switch.
- **Close**, the default for a bare `/end`: stopping work, before a pause, "wrap up / end session".

## Steps

1. Every call: `git rev-parse --abbrev-ref HEAD && git status --short`; `eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"`;
   `S="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills"` (a missing script is one degradation line). Checkpoint:
   `"$S/end/scripts/checkpoint.sh" prepare` (non-zero → stop, never guess a path). Close: sweep strays,
   classify the lane, `bash "$S/end/scripts/lane_phase.sh" "$PWD"` (`references/close.md`).
2. Append `## HH:MM — <title> · wt: <wt> · branch: <branch>` (close: `session end · <title>`) with six
   fields — Done (proof) · In progress · Next (close: Next session) · Blocker · Key context · Files
   (`path · symbol · why`); empty is `none`, SHAs from `git log`. Then `checkpoint.sh harvest-slice`
   and `harvest-done` with `POLARIS_SID` = your session id (`references/checkpoint.md`).
3. Your lane, one line, rewritten in place (same work = same key; nothing changed → write nothing):
   `printf '%s\n' "- \`<lane-key>\` (<repo>) — branch \`<branch>\`; <state> · since <date>" | python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/state_upsert.py" thread "$CURRENT" --owner "$LOGIN" --now "$(date +%F)"`.
4. Lessons only via `python3 "$ROOT/scripts/lesson_record.py" add --title "<mistake → rule>" --family …
   --area … --body-file …` (else the declared vault's); `- Lesson: <printed id>`. `OCCURRENCE`, a family
   with another lesson, or an incident → `bd create "<check to build>" -t task -l kind:followup,src:lesson,area:<area>`.
5. Decisions: `end` writes none. List each important one with its home (DEC id, `decisions.md` title,
   `issue:<repo>#<n>`); no home → `/architecture decide` now — hand-written ADR/DEC/`decisions.md` is refused.
6. Checkpoint stops here: `"$S/end/scripts/checkpoint.sh" commit <exact paths written now>`, `verify "<title>"`
   (same `POLARIS_SID`, exit 0), `python3 "$S/start/scripts/session_gate.py" note --root "$ROOT" --note "<title>"`.
7. Close only. Gate, a refusal stops `end`: `python3 "$S/start/scripts/session_gate.py" close --root "$ROOT"
   --handoff "$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md" || exit 1`.
8. Prune: `python3 "$S/end/scripts/prune_threads.py" "$CURRENT" --owner "$LOGIN" --now "$(date +%F)"`, then
   `--apply --log … --todos …`; PROVEN and DEAD leave, one BLOCKED stops (exit 2), resolve every
   `STALE=`. Then `state_priorities.py set` (≤ 7 lines) and one `recent_context.py` line.
9. Handoff `team/$LOGIN/handoff/$(date +%F).md` (census, open PRs without a reason) only while the lane
   is open. Closed = `lane_phase.sh` printed `READY_FINALIZE` and In progress, Next session and Blocker
   are `none` → no handoff file. Any other answer (KEEP, no remote, refused) writes it.
10. Land: `"$S/end/scripts/session_commit.sh" --end <log> <handoff if written> <week file> <records written>`;
    exit 2 names a declared exception — say it. `git status --short`: no Polaris path. Never `--no-verify`.
    Rake: `python3 "$S/end/scripts/session_rake.py" apply --merge`, then `sync`; exit 1 → say why (`references/close.md`, Step 5b).
11. Only on `READY_FINALIZE`: `python3 "$S/git-power/scripts/cantiere.py" phase finalize --repo "$PWD" --confirm "$PWD"`.

## Output

Checkpoint: one line, `Checkpointed: <what>`. Close: three bullets — shipped, open, next — then what was
written (lessons, beads, each decision with its home, the handoff or `no handoff — lane closed`), refusals verbatim.

**Next:** checkpoint → keep working; open work → `start` next session; closed lane → STOP — nothing to do.

## Where this goes

This skill produces: **none (the session log, cockpit and handoff live under `team/` and `state/`; decisions are written by `architecture`)**.

## Not for

- Resuming (`start`), a status view (`status`), the week (`week`).
- Writing a decision record (`architecture`); closing a plan file or a Beads epic (`plan close`, from `ship`).
- Pushing or merging anything but its own `chore/sessions-<login>-<date>` rake PR; deleting branches; the tracker.
