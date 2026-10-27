# Changelog — database-schema

## 1.1.2 — 2026-10-25

- Public-package clean (C5): one eval prompt says "lista ordini" instead of the product's own word.

## 1.1.1 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 1.1.0.

## 1.1.0 — 2026-10-24

- Form: body 48 lines, five fixed sections. The measurement, every `schema_scan.py` exit code and
  refusal, gotchas, rationalizations, red flags and the verification checklist moved verbatim to
  `references/process.md`.
- Description starts "◇ Polaris — " and names its dependencies (python3 and git; psql for live
  checks).
- Added `eval/` (9 trigger cases, 4 checks, split) and `tests/test_database_schema_form.py` (the suite gate on the
  skill, RED recorded before the rewrite).
- Chain: `invoked-by` gains `grill`.
- Carries the `## Where this goes` block that `scripts/skill_outputs_check.py` reads.
