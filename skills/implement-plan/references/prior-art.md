---
title: implement — prior art absorbed, and the Beads facts it rests on
status: active
---

# Prior art

`implement-plan` takes mechanisms from these, as references, not code. Each one does something better
than we do; the column says what we kept.

| Source | What it does better | What implement kept |
|---|---|---|
| `parallel-issue-flow` (`~/.agents/skills/parallel-issue-flow`) | a GitHub issue as the input contract, one worktree per issue, deterministic ports, a per-commit review gate and a self-heal loop across repos | the per-commit review gate becomes the per-phase `review` audit; the issue contract becomes the claimed bead + plan §5–6 |
| superpowers `subagent-driven-development` | a fresh implementer per task plus a spec-and-quality review per task, rulings ledgered instead of stalls | a fresh-context agent per task with a brief, never history (`dispatch-brief.md`); rulings noted on the bead instead of stalls, the four stops (`rulings.md`); a preflight conflict scan (`preflight.md`); a model tier per task, batching of tiny same-shape tasks, no agent spawning agents, the ledger trusted over memory after compaction. Not taken: the per-task review (founder: review runs once, on the PR) and a separate progress file (Beads + `git log` are the ledger) |
| superpowers `executing-plans` | runs the plan inline when no subagent tool exists, one final review | the fallback: with no subagent tool, run the brief yourself, the gates do not change |
| superpowers `dispatching-parallel-agents` | one agent per independent problem domain, concurrently | not taken yet: claims are sequential (one claimant per epic); the bd claim race is proven safe for more (adoption tests §2.3) when the cap rises |
| Osmani `incremental-implementation` (agent-skills build) | thin vertical slices: implement → test → verify → commit, each leaving the system working | one task = one slice = one commit, closed only when its test went RED then GREEN |
| gstack `/qa` self-regulation ("WTF-likelihood") | a fix loop that scores its own risk (+15 per revert, +20 for unrelated files) and stops above 20 to ask | `scripts/fix_budget.py`, the same weights, read from git since the task base (noted on the task bead at claim) so a resumed run gets the same score |

# Beads facts (bd 1.3.1, measured)

From `docs/modules/polaris-harness/validation/2026-10-24-beads-adoption-tests.md` (§3 overrides
the operating model where they differ) and this skill's own E2E:

- **Claim:** `bd ready --mol <epic> --claim` is refused ("--claim cannot be combined with --mol",
  exit 1). The claim is `feature_gate.py claim --step <task> --record <plan>`: it runs the lease
  reaper on this epic's in-progress beads (`bd reclaim --older-than 0s --id …`), then
  `bd update <task> --claim`, atomic (1 winner out of 100) with a 5-minute lease.
- **Unscoped `bd ready --json`** costs ~38 KB for 10 rows on a mirrored db: always scope.
- **Leases:** only poured steps carry one; a wisp step of a dead claimant stays stuck until
  `--force`. The TTL is fixed at 5 min in code; `bd heartbeat <id>` keeps it alive; `bd reclaim`
  (run by the next `feature_gate.py claim`) returns a dead claimant's step to `open`, and the
  dead claimant's next heartbeat fails, so it learns to stop.
- **`bd close --continue`** claims the next step automatically: implement closes without it.
- **Holes the gate must cover:** `bd close --force` and `bd dep remove` both unblock a phase; bd
  has no judge hook, so "close only through `feature_gate.py`" is a convention. The gate's
  `edges` check refuses a missing edge; an extra `blocks` edge (a finding) is allowed.
- **Squash and burn drop `discovered-from` edges:** the `gh-N` external ref goes on the finding
  itself.
- **A parent's blockers do not reach its children:** on plan 0.2.0 every task of every phase was
  listed by `bd ready --mol` while `critic` was still open (measured here). Since plan 0.2.1
  (#615) `pour` gives each task `blocked-by` its phase's predecessor; `scripts/next_bead.py`
  still works only the current phase (lowest open phase bead: its children and open blockers),
  so a hand-added task or a future formula cannot reorder the build.
- **A blocker outside the epic is invisible to the gate's own check:** a finding with `blocks` on
  a step but no parent is not in `bd mol show`, so `feature_gate.py close` skips straight to the
  stage check; only bd's own blocked-close refusal stops it. `bd update <bead> --parent <epic>`
  makes the gate answer "blocked by open step(s)" and puts the bead in `bd ready --mol`.
- **One edge per pair:** `bd create --parent <phase> --deps discovered-from:<phase>` fails
  ("dependency … already exists with type parent-child"). A finding is a child of the epic,
  `discovered-from` the phase, and `blocks` it.
