# Changelog — architecture

## 1.6.1 — 2026-10-27

- `invoked-by` names `apex-curate`: its new `adrs` mode runs `scripts/adr_triage.py` and writes
  superseding ADRs through `/architecture decide`. No rule moved; architecture still owns them.

## 1.6.0 — 2026-10-27

- The skill writes its documents well (founder, 2026-10-26: a product repo held 97 ADRs, 16,739
  lines, median 123, one grown 13 appended update sections into a diary, thresholds and prompts
  recorded as ADRs). New `references/writing.md` owns which of four documents a statement belongs
  in — `ARCHITECTURE.md` (the map), the area README (how one area works today), the ADR, the
  `decisions.md` ledger line; no fifth — and how each is written and kept, with a template, a
  budget and an invented example each, plus rules for all of them.
- ADRs always live in `docs/adr/NNNN-kebab-title.md`, in every repository, never as DEC files
  (founder, 2026-10-27); an ADR that needs enforcement may carry optional `probe:` / `probe_kills:`.
  DEC files stay for non-architecture choices that must be enacted (`kind: process`). `config.yml`
  gains `outputs.adr`, and `outputs.decision` no longer says an ADR is `kind: architecture`.
- ADR format: `docs/adr/NNNN-kebab-title.md`,
  `# N. <short title>` · Date · Status (Supersedes / Superseded by, both ways) · Context ·
  Decision ("We will…") · Consequences (all) · optional Rejected, Measurement, Not decided, How it
  would be proven wrong; one to two pages. New `references/adr-0001.md`: the meta-ADR "Record
  architecture decisions" that `init` (or the first `decide`) writes into a repo with no ADR set.
- The ADR bar: a decision affecting structure, non-functional characteristics, dependencies,
  interfaces or construction techniques, AND the three ADR tests; a threshold, method, prompt,
  heuristic or number is a ledger line even when code carries it. `record.md` §2 drops "threshold"
  from detail; §4 points to the one ADR format instead of carrying a second template.
- Governance replaces "never edited": amend in place for drift (never what was decided),
  supersede a reversal, compact overlapping or dead records with a provenance note; a dated update
  section is never appended. Decomposition rule 98 (the ADR rule) aligned: it said "keep it open
  to add issues found later", the habit that grew the diary.
- `doc` writes the area README `docs/<areas|modules>/<area>/README.md` (outside the generated
  `area-map` markers) when an area is named, else `ARCHITECTURE.md`; its *Bird's eye view* now
  carries the main flows end to end, linking the area READMEs (`doc-arm.md`, `arms.md`, `process.md`).
- `doctor <adr-dir>`: new read-only `scripts/adr_triage.py` (lines, median, appended sections,
  `kind`, `status`, `governed`; flags `appended` and `long`) and six calls in `doctor.md` — keep ·
  amend · supersede · compact with · demote to ledger · move to the area README. Behavioural test
  `tests/test_adr_triage.py`: RED with the script absent, GREEN, break observed.
- `docs/decision-records.md` (suite) aligned: the bar, the format, ADR 0001, the governance.
- Eval: six lift cases c10–c15 (c1–c9 unchanged). Sonnet, n=6, two runs each, on the same cases:
  before (1.5.3) `lift-baseline-v153-run{1,2}.json`: with 0/6 and 1/6, without 0/6 and 1/6, lift
  +0.00 both; after `lift-after-v160-run{1,2}.json`: with 6/6 and 5/6, without 0/6 and 1/6, lift
  +1.00 and +0.67; after the ADR-home change (`lift-after-v160-run3-adr-home.json`): with 5/6,
  without 0/6, lift +0.83. c13's ruler fixed before the final runs: it demanded the six ADRs linked by
  title, which a run without tools cannot know; a placeholder list now counts.
- Body kept at 60 lines: census and naming merged into one step; the graph-verify degraded line
  lives in `process.md` as before.

## 1.5.3 — 2026-10-26

- Two eval cases name a generic memory CLI instead of the private one, which does not ship.

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
