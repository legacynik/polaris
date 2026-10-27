# Changelog — status

## 1.5.3 — 2026-10-25

- `end` absorbed `update`: a checkpoint or the close → `end`.

## 1.5.2 — 2026-10-25

- Public-package clean (C5): CHANGELOG provenance names the public package repo, not its owner login.

## 1.5.1 — 2026-10-25

- Follows the rename `implement` → `implement-plan` (references, `invoked-by`, eval tuples). Text only.
- Version bump: patch, from 1.5.0.

## 1.5.0 — 2026-10-24

- Rewritten to the 60-line form with `lifecycle`, `io`, `status: active`, a ◇ description under
  500 characters; the full procedure lives in `references/procedure.md`.
- New: prints decided-and-not-done from `scripts/check_decision_execution.py --not-done`, oldest
  first, as the **DECIDED, NOT DONE** section (operating model §6). The per-repo investigation
  names no model ("a fresh-context agent … on the fastest model your harness offers"); history
  comes from the agent memory (ai-memory), never as proof of state.
- New: `references/bypass-test.md`, `eval/` (10 trigger cases, 3 checks, split). Plan unit B6a.

## 1.4.0 — 2026-10-24

- Imported into polaris-os `skills-suite/` from the public package repo at 8fdfee9 (`polaris/skills/polaris-status`).
- Renamed from `polaris-status` to `status` (plain names, "Polaris" in the description); directory, `name:`, chain fields, body references, scripts and tests follow.
- Version bump: minor (rename), from 1.3.4. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
