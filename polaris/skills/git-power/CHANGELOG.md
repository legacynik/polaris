# Changelog — git-power

## 0.7.3 — 2026-10-26

- `cantiere` `BLOCKED_DIRTY` names the checkpoint of `/end`, no longer `/update` (absorbed, #637).

## 0.7.2 — 2026-10-25

- `invoked-by` drops `update`, absorbed into `end` (which already invokes git-power).

## 0.7.1 — 2026-10-25

- Public-package clean (C5): recorded transcripts carry `~/` instead of the machine path; the bypass-test shell comments are in English.

## 0.7.0 — 2026-10-24

- Rewritten to the 60-line form (What it does · When · Steps · Output ·
  Not for); the finalize invariant, the guarded operations, `census --tsv/--apply` and the proof
  moved to `references/phases.md`. `scripts/` and the behaviour evals (`eval/behavior/`) unchanged.
- Description: "◇ Polaris — " prefix and its deps (git, gh, python 3); the trigger rate in
  `references/ratchet-state.json` was measured on the previous description.
- Version bump: minor, from 0.6.0. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md`.

## 0.6.0 — 2026-10-24

- Baseline: the version this skill carried when the per-skill CHANGELOG became a gate (`_standard/check_skill_changelog.py`). Earlier history is in git.
