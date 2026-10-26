---
name: start
description: ◇ Polaris — resume the current objective from the latest local handoff, read-only and local, and open the session that end checkpoints and closes; first use also provisions your own team path. Use at session start or on "start / resume / where were we". Not a status view. Requires git, python3; gh only on first use.
version: 1.15.4
user-invocable: true
status: active
lifecycle: profile + weekly focus + cockpit + newest session log → one resume brief; opens the session that end checkpoints and closes
invokes: []
invoked-by: human, hook
io: a checkout with a Polaris contract → the resume brief (Resume, Remember, Pack, Signals) and an open session
---

# start

## What it does

Restores the smallest local context needed to continue: branch, this week's outcome, the latest
handoff, one blocker, the next action. It reads local files only — no fetch, no PR scan, no health
check (that is `status`) — and never writes the cockpit. It opens the session `end` checkpoints and closes.

## When

- A session begins, or "start / resume / where were we".
- First use in a repository: it also provisions your own `team/<login>/` path.

## Steps

1. `git rev-parse --abbrev-ref HEAD`; not a git checkout → stop.
2. `eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"` sets
   `MAIN_WT ROOT LOGIN CURRENT RADAR`; non-zero → print its message and stop, never guess a path.
3. First use (`$ROOT/team/$LOGIN/profile.yml` absent): provision only your own path and the team
   settings — commands in `references/first-use.md`. Then, every run, the identity gate:
   `grep -q "^github: $LOGIN$" "$ROOT/team/$LOGIN/profile.yml" || { echo "STOP: profile github: does not match $LOGIN"; exit 1; }`
4. Read only the resume set, in order (`references/resume-set.md`): the profile (`language:`,
   `voice:` → `references/voice.md`); `team/$LOGIN/weeks/$(date +%G-W%V).md`; `$CURRENT`'s
   `## Active Priorities` and your `## Open` line; your newest `team/$LOGIN/sessions/` file;
   `state/goals.md` (older than 30 days → ask once if it is current); the last 5 `decisions.md`
   entries; the radar `[ "$RADAR" = none ] || python3 "$RADAR"`.
5. Open the session:
   `python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" open --root "$ROOT" --login "$LOGIN"`.
   `opened`/`resumed` are normal; `blocked — <CODE>` is reported, not fatal; silence = no engine.
6. Signals:
   `python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/brief_signals.py" --root "$ROOT" --current "$CURRENT" --login "$LOGIN" --main-wt "$MAIN_WT"`
   — each line describes itself; where each goes in the brief: `references/resume-set.md`.
7. The local branch differs from this week's file's branch → stop with the exact mismatch.

The context pack (polcontext) is optional: without it the `PACK:` lines are simply absent. Memory
is not read here — it is history, not state; for "what did we decide about X", ask the agent memory
(`ai-memory-retrieval`), skipped if absent. After a compaction the SessionStart hook puts the pack
back; to do it by hand, `session_gate.py reinsert --root "$ROOT"` (`references/compaction.md`).

## Output

The brief only, plain markdown, never in a code fence, in the profile's `language:` (default
English), empty lines omitted: `{Weekday} {date} — <repo> on <branch>`, then **Resume** (Outcome ·
Checkpoint · Blocker · Next action), **Remember** (the `QUEUE*` lines verbatim), **Pack** (the
`SESSION:` line and the resolver lines verbatim), **Signals** (the other lines verbatim). Focus and
handoff disagree → name it in Blocker. No handoff → derive the next action from the week's file and
say no checkpoint exists. Implementation waits for an explicit request.

## Where this goes

This skill produces: **none (the brief is an answer; the session receipt is the engine's)**.

## Not for

- A repository or portfolio view, open PRs, health → `status`.
- Saving progress or closing the session → `end` (`/end checkpoint` keeps it open); the week → `week`.
- Running again after a compaction: the hook reinserts the pack, nothing is re-read.
