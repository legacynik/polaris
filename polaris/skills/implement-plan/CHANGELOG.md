# Changelog — implement-plan

## 0.3.0 — 2026-10-26

- Step 5: a phase closes through `G close` on green tests alone; no per-phase `real-testing`
  or `review`. Founder: real-testing and review on every Beads phase were rigid and made small
  phases drift; both now run once, at the GitHub boundary, on the PR (`ship`). Operating model §10 updated.

## 0.2.0 — 2026-10-25

- Renamed `implement` → `implement-plan`: the billing-plane plugin's `implement` command shadowed the skill — Claude Code registered neither the skill nor `/implement` (tested: the same SKILL.md registers under another name). Folder, `name:`, eval, the dispatch-brief path and suite-ci follow. The feature gate's `implement` STEP keeps its name.
- Version bump: minor, from 0.1.3.

## 0.1.3 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 0.1.2.

## 0.1.2 — 2026-10-25

- `invokes` and the gate path follow the rename `plan` → `plan-area`. No behaviour change.
- Version bump: patch, from 0.1.1.

## 0.1.1 — 2026-10-25

- `invokes` declares the chain the steps already run: `plan` (`feature_gate.py` claims and closes every step), `tdd-dev` (`red_check.py` RED per task), `real-testing` (per-phase mode) and `review` (on the phase's last commit). Each of them lists `implement` in `invoked-by`. No behaviour change.
- Version bump: patch, from 0.1.0.

## 0.1.0 — 2026-10-24

- New skill: phase 5 of the operating model (`docs/modules/polaris-harness/specs/2026-10-24-operating-model.md`
  §3, §10, §11). Works an accepted plan's Beads epic: reads `bd ready --mol`, claims through the
  plan skill's `feature_gate.py claim` (lease reaper first; bd 1.3.1 refuses `--claim` with
  `--mol`), one fresh-context agent per task with `references/dispatch-brief.md`, RED recorded
  with tdd-dev's `red_check.py`; tasks close with `bd close`, every other step only through the gate.
- Phase gate: tests, `real-testing` per-phase mode, `review` on the phase's last commit. Both file
  their misses as beads `discovered-from` + `blocks` on the phase (children of the epic, never of
  the phase: bd keeps one edge per pair); implement makes sure each carries `gh-N` on the bead
  itself. The phase closes only through the plan skill's `feature_gate.py close`. Only the current
  phase is worked: a parent's blockers do not reach its children in bd (fixed in `pour` by plan
  0.2.1, #615; kept here as defence in depth).
- `scripts/next_bead.py`: the current phase's next ready bead (child task or open blocker),
  the later-phase beads bd lists as ready (skipped), and the current phase's held beads (a dead
  claimant's comes back on the next `feature_gate.py claim`), in plan order. Tests: `tests/test_next_bead.py`
  (RED recorded). Findings filed by review/real-testing are adopted into the epic
  (`bd update --parent <epic> --external-ref gh-N`): without a parent the gate's own blocker check
  and `bd ready --mol` do not see them (measured; bd still refuses the close).
- `scripts/fix_budget.py`: the fix loop's circuit breaker (gstack `/qa` weights: +15 per revert,
  +20 per file outside the task scope, STOP above 20), read from git since the task base, so a
  resumed run gets the same score. Tests: `tests/test_fix_budget.py` (RED recorded with `red_check.py`).
- Crash safety per the Beads adoption tests §3: poured steps with a lease; a dead claimant's step
  comes back on the next `feature_gate.py claim` (reaper), never by hand. AFK: medium work with an accepted plan only, `risk:high` never.
- Prior art credited in `references/prior-art.md`: parallel-issue-flow, superpowers
  executing-plans / subagent-driven-development / dispatching-parallel-agents, Osmani
  incremental-implementation, gstack `/qa`.
