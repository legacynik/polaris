# Changelog — architecture

## 1.5.2 — 2026-10-25

- Public-package clean (C5): eval run notes and prompts carry neutral names (`acme/acme-api`, `<vault>`, "offerte") instead of the product repo, its owner login and machine paths. No behaviour change.

## 1.5.1 — 2026-10-25

- `check_context_backbone.py` treats `executed` as in force, like `accepted` (operating model §13
  step 1): one `IN_FORCE` set drives the landing checks (call sites, legacy review, one record per
  key), default-context eligibility and the legacy-authority scan. Before, promoting a record to
  `executed` exempted it from every check and a register of only executed records read as empty.
  `superseded` and `deprecated` stay out. RED recorded in `state/tdd/a1-executed-in-force.jsonl`.

## 1.5.0 — 2026-10-24

- Decision homes per the operating model §6 (step 6 and `references/record.md` §4): a DEC file
  with `call_sites`, `probe` and `probe_kills` plus one ledger line when the choice must be enacted
  or passes all three ADR tests — `kind: architecture` (an ADR) only in the latter case, else
  `kind: process`; anything else is a ledger entry in `decisions.md`.
- Lifecycle: the skill writes `proposed`; the founder sets `accepted`; `accepted` is not
  `executed` — only `plan close` writes it, when `check_decision_execution.py` reports the probe
  passing. New check `eval/checks.json` c9.
- The nine fixed field names stay Italian (`reversibilità` … `prossimo`, `modalità`): they are a
  contract that `eval/checks.json` and the tests grep, so renaming them is a separate change.
- Form: body 60 lines, five fixed sections; the former body (verbs, Step 0, census, domain
  handoff, the nine fixed fields, rationalizations, red flags, verification, where this goes)
  moved to `references/process.md`. `tests/test_arch_doctor_r1.py` now reads the nine-field table
  there; `tests/test_architecture_form.py` runs the suite gate on the skill (RED recorded before the rewrite).
- Description starts "◇ Polaris — " and names its hard dependency (python3).
- Chain: `invoked-by` gains `grill`.
- Scripts, references and existing evals unchanged; `check_absorption.py` 26/26.
- Carries the `## Where this goes` block that `scripts/skill_outputs_check.py` reads.
- `eval/split/train.json` drops `p01`, retired from `prompts.json` at 1.0.0 but left in the split;
  `_standard/eval_run.py` refused the set as FORMAT.
