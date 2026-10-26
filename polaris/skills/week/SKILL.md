---
name: week
description: ◇ Polaris — your own week, both ends. At the start, build your weekly focus from carryover and live tracker issues; after a finished Sunday→Saturday week, report it against that focus with merged-PR evidence. Both open with the decisions accepted and still not done. Use on "plan my week / what am I picking up / weekly report / what shipped / planned vs actual". Requires git, gh, python3.
version: 1.0.2
user-invocable: true
status: active
lifecycle: carryover + tracker → team/<login>/weeks/<ISO week>.md (never rewritten) → state/todos.md reconciled → after the week, team/<login>/reports/<Sunday>.md
invokes: []
invoked-by: human
io: login + mode (forward | `week report`) → this ISO week's focus file, or the finished week's report file, each headed by the NOT_DONE decisions
---

# week

## What it does

Your own week, both ends. **Forward** (default) writes the week's focus and reconciles
`state/todos.md`; **report** (`week report`) measures a finished week against it with `gh` and git
evidence. Both open with the decisions accepted and still not done. No tracker mutation, ever.

## When

- Start of a week, or "plan my week / what am I picking up" → forward.
- After a week ended, before a team review, or "weekly report / what shipped" → report.

## Steps

1. Resolve: `eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"`;
   `REPO` = `config.yml` `tracker.github_repo`, `LOGIN` = your profile's `github:`. Missing → stop,
   point to `docs/TEAM-ONBOARDING.md`. You write only under your own `team/$LOGIN/`.
2. Decided and not done, printed first, verbatim (minutes: every probe runs, 90 s cap each):
   ```bash
   SG="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py"
   D="$ROOT"; [ -f "$D/scripts/check_decision_execution.py" ] || D="$(python3 "$SG" vault --root "$ROOT")"
   if [ -f "$D/scripts/check_decision_execution.py" ]; then
     python3 "$D/scripts/check_decision_execution.py" --root "$D" --not-done --timeout 90
   else echo "NOT_DONE: skipped — no decision gate here or in a declared vault"; fi
   ```
3. **Forward.** `WEEK="$(python3 -c 'import datetime as d;t=d.date.today();t+=d.timedelta(days=(7-t.weekday())%7 if t.weekday()>4 else 0);print(t.strftime("%G-W%V"))')"`
   (a weekend rolls to next Monday's week). Ask this week's load (`light` 2–3 epics, `normal`
   4–5, `heavy` 7–8; profile `weekly_capacity` is the default). Read carryover (last week's file,
   your open assigned issues) and `gh issue list --repo "$REPO" --state open --json
   number,title,labels,updatedAt --limit 60`; rank severity › unblocks › scope fit › age; show the
   full slate and let the contributor choose. `gh` fails → report it and stop, never invent issues.
4. Write `WEEKLY="$ROOT/team/$LOGIN/weeks/$WEEK.md"` from
   `${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/templates/repo-contract/weekly-plan.md` (`## Outcome`, `## Not starting`,
   `## Evidence`); never overwrite an existing one silently. Red items wait for their named approver.
5. Reconcile `state/todos.md` — rows keep their `Added:` week, `Active` is never emptied:
   `printf '%s\n' "| #<n> — <outcome> | | <context> |" | python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/state_upsert.py" week "$ROOT/state/todos.md" --week "W${WEEK#*-W}"`,
   then `python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/todos_roll.py" "$ROOT/state/todos.md" --now "$(date +%F)"`.
6. **Report.** Resolve the last finished Sunday→Saturday window (`references/report.md`), show it
   and wait for "yes" before any query; a week not yet over is refused.
7. Gather read-only evidence: merged PRs and closed issues by `$LOGIN` in the window, commits via
   `gh api …/commits?author=`, local unpushed commits, session logs, `decisions.md` entries.
   Size every PR as `code +X/−Y · docs +A/−B`, `UNKNOWN` never `0` (`references/report.md`).
8. Write `team/$LOGIN/reports/<Sunday>.md` from the same templates folder's `weekly-report.md`; append a
   dated update instead of overwriting an earlier report.

## Output

The NOT_DONE list, then forward: the ranked slate, `weeks/<ISO week>.md` and the `state/todos.md`
diff; or report: `reports/<Sunday>.md` (TL;DR, planned versus actual, per-PR sizes, bottleneck, PM
action, next week). Facts carry a link; assumptions are labelled.

## Where this goes

This skill produces: **none (the week's files live under `team/<login>/`)**.

## Not for

- Resuming (`start`), a checkpoint (`end checkpoint`), or someone else's week — each authors their own.
- Creating issues, assignments, branches or PRs — this skill only reads the tracker.
