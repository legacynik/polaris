# Changelog — domain

## 0.5.2 — 2026-10-25

- Public-package clean (C5): one eval prompt names "il mio socio" instead of a real person.

## 0.5.1 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 0.5.0.

## 0.5.0 — 2026-10-24

- Form: body 60 lines, five fixed sections. The former body (where the output goes, the halt,
  the three habits, which boundary is in play, the arms with their halts, the `CONTEXT.md` /
  `CONTEXT-MAP.md` / `DOMAIN.md` contracts, the two glossaries, the quick reference) moved
  verbatim to `references/process.md`.
- An ADR, when all three tests pass, is handed to `architecture`, which writes the record in the
  operating model §6 home; domain never writes a parallel record.
- Memory through the agent memory (`ai-memory-retrieval`), skipped if absent.
- Description starts "◇ Polaris — "; `invoked-by` gains `grill`.
- `tests/test_domain_form.py` runs the suite gate on the skill (RED recorded before the rewrite).
  Existing evals unchanged.
- Carries the `## Where this goes` block that `scripts/skill_outputs_check.py` reads.
