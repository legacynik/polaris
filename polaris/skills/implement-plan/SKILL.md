---
name: implement-plan
description: "◇ Polaris — Build an accepted plan's Beads epic phase by phase: claim the next ready task, hand it to a fresh-context agent that records RED first, close each phase only through the feature gate. Use when a plan is accepted and its epic poured, or to resume a build after a crash. Requires bd (Beads) and plan-area's feature_gate.py."
version: 0.3.0
user-invocable: true
status: active
lifecycle: task and phase beads closed in the epic → implement stage closed → ship
invokes: [plan-area, tdd-dev, real-testing, review]
invoked-by: [human, cron]
io: epic id + its record file → closed phase beads and findings as beads, or a STOP line from the fix budget
---

# implement

## What it does

Runs phase 5 of the operating model on a poured epic: one task at a time from `bd ready`, each
task to a fresh-context agent, each phase closed by a gate (green tests) and only through `feature_gate.py`; `review` and
`real-testing` run once, on the PR. A crashed run resumes from `bd ready`.

## When

- The plan is `accepted` (`in-progress` once poured) and its epic exists, or a run died mid-phase.

## Steps

`G` = `python3 <skills>/plan-area/scripts/feature_gate.py <cmd> --record <plan> --repo <root>`.

1. **Refuse to start** unless `G check --stage plan` exits 0 and the epic (the plan's `Beads
   epic:` link) has `plan` and `critic` closed (only `G` closes them). Ask the agent memory
   for past runs in this area (`ai-memory-retrieval`; skip if absent).
2. **Pick** with `scripts/next_bead.py --mol <epic>` (reads `bd ready --mol`, never unscoped):
   a ready bead of the current phase, the lowest open one: a child task or an open blocker; any
   other ready bead is skipped (defence in depth). Empty: go to 5, unless it names
   a `held` bead. **Claim** with `G claim --step <bead>` (it reaps dead leases, then claims; so a
   held bead of a dead claimant comes back after its 5-min lease). Note `base <HEAD sha>` on the
   bead, and on the phase bead at its first task; heartbeat every 2 min.
3. **Dispatch** a fresh-context agent from your harness, on the strongest model it has, with
   `references/dispatch-brief.md` filled from the bead. It records RED with tdd-dev's
   `red_check.py record` before any fix, and runs the fix budget before each new attempt.
   No subagent tool: run the brief yourself.
4. **Close the task** only after you re-run `red_check.py verify` (exit 0) and
   `scripts/fix_budget.py --base <task base> --scope <task globs and RED log>`. Exit 1 is STOP:
   give the human its line and change nothing more. Then `bd close <task> -r <sha>`.
5. **Phase gate**, once the phase's tasks are closed:
   - `G close --step <phase>`: tests green (the plan's `tests:` command) and no open bead
     blocking the phase. No review and no real-test per phase: both run once, on the PR (`ship`).
     Non-zero: the phase stays open, fix what it names.
6. After the last phase: `G close --step <implement step>`; then hand the branch to `ship`.

## Output

Beads closed (tasks with their commit, phases and implement through `G`), findings with `gh-N` on the bead.
**Next:** `ship` after the last phase; or STOP with the budget's line or the gate's refusal.

## Where this goes

This skill produces: **tasks** — task, phase and finding beads in the epic; code on the branch.

## Not for

- A plan not accepted, an epic not poured; tiny work (`tdd-dev` → `ship`); a bug (`bugfix`).
- The AFK loop, except medium work whose plan the founder set to `accepted`; `risk:high` never.
- Getting past a gate: never `--force`, never `bd close --continue` (it claims the next step),
  never `bd dep add|remove` on a step, never a non-task step closed outside `G`.
- A wisp epic (a wisp step has no lease): steps are poured. A dead claimant's step is
  recovered by `G claim`'s lease reaper (`bd reclaim`), never by hand.
