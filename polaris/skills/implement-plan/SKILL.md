---
name: implement-plan
description: "◇ Polaris — Build an accepted plan's Beads epic phase by phase: claim the next ready task, hand it to a fresh-context agent that records RED first, close each phase only through the feature gate. Use when a plan is accepted and its epic poured, or to resume a build after a crash. Requires bd (Beads) and plan-area's feature_gate.py."
version: 0.4.0
user-invocable: true
status: active
lifecycle: task and phase beads closed in the epic → implement stage closed → ship
invokes: [plan-area, tdd-dev, real-testing, review]
invoked-by: [human, cron]
io: epic id + its record file → closed phase beads and findings as beads, or a STOP line from the fix budget
---

# implement

## What it does

Runs phase 5 of the operating model on a poured epic: each ready task to a fresh-context agent,
each phase closed only through `feature_gate.py` on green tests; `review` and `real-testing` run
once, on the PR. Beads and `git log` are the ledger: after a crash or a compaction trust them
over memory; a task whose bead is closed with a commit is never dispatched again.

## When

- The plan is `accepted` (`in-progress` once poured) and its epic exists, or a run died mid-phase.

## Steps

`G` = `python3 <skills>/plan-area/scripts/feature_gate.py <cmd> --record <plan> --repo <root>`.

1. **Refuse to start** unless `G check --stage plan` exits 0 and the epic has `plan` and `critic`
   closed. **Preflight**: plan vs spec (or area README, the authority) vs code; rule on each
   conflict before the first dispatch (`references/preflight.md`).
2. **Pick** with `scripts/next_bead.py --mol <epic>` (never an unscoped `bd ready`); empty: go to 5,
   unless it names a `held` bead. **Claim** with `G claim --step <bead>`; `bd note` the bead
   `base <HEAD sha>`; heartbeat every 2 min. Tiny same-shape tasks ready in the phase go out as
   one batch: claim each.
3. **Dispatch** with `references/dispatch-brief.md`, choosing the model for the task: the
   cheapest that can do it (a mechanical 1–2 file change with the code in the plan is cheap;
   integration is standard; design judgment gets the strongest). The agent may ask before coding,
   records RED first, never spawns its own agents. No subagent tool: run the brief yourself.
4. **Close the task** after re-running `red_check.py verify` (exit 0) and
   `scripts/fix_budget.py --base <task base> --scope <task globs and RED log>`, and, for a batch,
   seeing every file of the brief in the diff. Then `bd close <task> -r <sha>`.
5. **Phase gate**: `G close --step <phase>` (tests green, nothing blocking); non-zero: fix what it names.
6. After the last phase: `G close --step <implement step>`; hand the branch to `ship`.

**Rulings, not stalls.** A conflict, an ambiguity, a plan defect, an agent's question the plan
cannot answer: decide it, `bd note` the bead or epic `Ruling: <what> — <why> — <cost if wrong>`,
keep going (`references/rulings.md`). Stop and ask only for: an irreversible or destructive
operation; a security-sensitive action; a side effect outside the worktree (merge, push to a
shared branch, publish, a shared database); a plan so broken every path is a guess. The fix
budget's exit 1 and a `G` refusal also stop: they are evidence, not ambiguity — give the human
their line and change nothing more. Between tasks, at most one short line; never "continue?".

## Output

Beads closed (tasks with their commit, phases and implement through `G`), rulings and findings
noted on their beads, findings with `gh-N`.
**Next:** `ship` after the last phase; or STOP with the budget's line, the gate's refusal or one
of the four stops above.

## Where this goes

This skill produces: **tasks** — task, phase and finding beads in the epic; code on the branch.

## Not for

- A plan not accepted, an epic not poured; tiny work (`tdd-dev` → `ship`); a bug (`bugfix`).
- The AFK loop, except medium work whose plan the founder set to `accepted`; `risk:high` never.
- Getting past a gate: never `--force`, never `bd close --continue`, never `bd dep add|remove`
  on a step, never a non-task step closed outside `G`; a dead claimant's step comes back
  through `G claim`'s lease reaper, never by hand. A wisp epic: steps are poured.
