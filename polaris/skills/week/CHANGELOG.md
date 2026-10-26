# Changelog — week

## 1.0.2 — 2026-10-25

- `end` absorbed `update`: `state_upsert.py week` and `todos_roll.py` resolve from `end/scripts/` (body, `references/forward.md`, bypass case, eval check).

## 1.0.1 — 2026-10-25

- Public-package clean (C5): CHANGELOG provenance names the public package repo, not its owner login.

## 1.0.0 — 2026-10-24

- New skill: absorbs `plan-week` (1.4.3, forward: the week's focus + `state/todos.md`
  reconciliation) and `report` (1.3.3, the finished Sunday→Saturday week, planned versus actual).
  Both folders are removed; their bodies live on as `references/forward.md` and
  `references/report.md`, their mechanisms unchanged (weekend roll-forward, `state_upsert.py week`
  keeping `Added:`, `todos_roll.py`, per-PR code/docs split, `UNKNOWN` never `0`, confirm before
  the first query). `CREDITS.md` moved from `plan-week`.
- Forward computes `WEEK` once (a weekend rolls to next Monday's week) and stamps `state/todos.md`
  with that week, not today's.
- New: both ends open with the decided-and-not-done list, printed from
  `scripts/check_decision_execution.py --not-done` (operating model §6), oldest first.
- In the 60-line form with `lifecycle`, `io`, `references/bypass-test.md`, `## Where this goes`,
  and `eval/` (12 trigger cases, 4 checks, train/test split). Plan unit B6a.

## Absorbed history — plan-week

### 1.4.3 — 2026-10-24

- Imported into polaris-os `skills-suite/` from the public package repo at 8fdfee9 (`polaris/skills/plan-week`).
- Version bump: patch (import), from 1.4.2. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
- 2026-10-24: removed — absorbed into `week` 1.0.0.

## Absorbed history — report

### 1.3.3 — 2026-10-24

- Imported into polaris-os `skills-suite/` from the public package repo at 8fdfee9 (`polaris/skills/report`).
- Version bump: patch (import), from 1.3.2. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
- 2026-10-24: removed — absorbed into `week` 1.0.0 (`week report`).
