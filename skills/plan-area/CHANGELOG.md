# Changelog — plan-area

## 0.5.0 — 2026-10-27

- A plan records decisions, not a transcript of the code: a code step is a signature, a file and
  the spec's values; a test step is a test name and its assertions. `check_plan_files.py` gains
  the `transcript` rule (code lines outnumber prose, mermaid not counted). Test:
  `test_plan_mostly_code_is_a_transcript` (RED recorded).
- `## Review Focus` (template, between §6 and §7): up to five inputs the spec implies and no
  phase tests, each pinned by a test in the owning phase.
- The owner's words are carried verbatim or with a pointer; agent additions are marked
  `proposal (agent):`. Approving the idea is not approving the plan: the owner approves the file.
- Spec by example: every contract and DoD behaviour carries a real input → expected output that
  can become its acceptance test (eval c11).
- Three thinking tools, one line each: riskiest assumption proven or killed in the earliest phase;
  a pre-mortem feeding the Review Focus; for Large work, what reacts after release and with what
  delay, named in the risks (founder, 2026-10-27).
- Builder check before `critic`: `references/builder-check.md` (fresh-context builder lists what
  it would still have to ask; answered · minor · the owner's).
- Body rewritten from a numbered procedure to goal, done-criterion, traps and questions to ask
  oneself (founder, 2026-10-27: heavy structure dulls the model); still 60 lines. Examples per
  behaviour moved to `references/plan-file.md`. Description unchanged.
- Version bump: minor, from 0.4.1.
## 0.4.1 — 2026-10-27

- Close absorbs the proven content into the area README (`<area>/README.md`); `plan_close.py --merged` checks that file, not `<area>/<area>.md`. Test: `test_close_promotes_a_passing_dec_moves_the_file_and_burns` (RED recorded). Founder 2026-10-27: no separate `<area>.md` main document.

## 0.4.0 — 2026-10-26

- `feature_gate.py` phase stage: tests green and nothing open blocking it — the real-test
  receipt, `--base` and the review approval are gone (`--receipt`/`--base` still accepted,
  ignored). Test: `test_a_phase_closes_on_green_tests_alone` (RED recorded). Founder:
  real-testing and review on every Beads phase were rigid and made small phases drift; both now run once, at the GitHub boundary, on the PR (`ship`). Operating model §10 updated.

## 0.3.4 — 2026-10-25

- Public-package clean (C5): two eval prompts say "ordini" instead of the product's own word.

## 0.3.3 — 2026-10-25

- Follows the rename `implement` → `implement-plan` (references, `invoked-by`, eval tuples). Text only.
- Version bump: patch, from 0.3.2.

## 0.3.2 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 0.3.1.

## 0.3.1 — 2026-10-25

- The plan opens with a short `## Executive` for a person: outcome, decision, risk, which sections
  to read for the review (founder, 2026-10-25). Template only, no new check.
- Version bump: patch, from 0.3.0.

## 0.3.0 — 2026-10-25

- Renamed `plan` → `plan-area`: Claude Code ships a built-in `/plan` (plan mode), so `/plan`
  never reached this skill. Folder, `name:`, eval `skill`, the `.beads/formulas/` link, suite-ci
  paths and every caller's `invokes` follow. The gate's `plan` STEP keeps its name (formula
  step id, `feature_gate.py` stage); only the skill moved.
- Version bump: minor, from 0.2.3 (the invocation name changed).

## 0.2.3 — 2026-10-25

- `invoked-by` gains `implement`: it claims and closes every step of the epic through `feature_gate.py`. No behaviour change.
- Version bump: patch, from 0.2.2.

## 0.2.2 — 2026-10-25

- `invoked-by` gains `ship`: its step 10 runs `plan_close.py` after the merge (B5). No behaviour change.
- Version bump: patch, from 0.2.1.

## 0.2.1 — 2026-10-25

- `pour` blocks each task on its phase's predecessor (critic for phase 1, phase N-1 for phase N),
  and `edges` checks those edges: bd does not pass a parent's blockers to its children, so
  `bd ready --mol` listed every phase's tasks right after pour (B2, measured on bd 1.3.1).

## 0.2.0 — 2026-10-25

- The `phase` stage reads the formats real-testing and review actually write (b4b): `--receipt`
  plus `--base <phase's first commit>`, validated with `verdict.py validate --base B --head HEAD`
  and refused on `verdetto: NOT-MERGEABLE`; the review approval for HEAD's tree is judged by
  review's own `gate_hook.py` (no JSON parsed here). `--audit` is gone: an open finding is a bead
  with `blocks:<phase>`, refused by the stage when `--step` is given and by every `close`.
- `references/beads.md`: findings are children of the epic (bd 1.3.1 allows one dependency per
  pair), tasks close with plain `bd close`, `bd ready --mol --claim` is refused — measured by B2.

## 0.1.1 — 2026-10-25

- One plan-file skeleton: `references/plan-file.md` now points to `grill/references/plan-file.md`
  (B3), which carries the shapes this skill and `feature_gate.py` read (`tests:`, `## 6.` bullets,
  `### Phase N:` under `## 7.`, `Beads epic:` under `## 8.`); the Rules section stays here.
- Chain: `invoked-by` gains `grill`.

## 0.1.0 — 2026-10-24

- New skill (operating model §3 phases 3, 4, 6, 8; §5 the plan file). One plan file per piece of
  medium or large work, area resolved first, one open plan per area (a second idea is a bead
  `kind:idea`), every claim `assumed` or `proven: <pointer>`.
- Absorbs `ambitious-goal` (outcome and falsifiable DoD, one question at a time, no invented
  baselines → `references/plan-file.md` Rules) and gstack /spec's mandatory code-reading and
  issue dedupe (step 3).
- `scripts/feature_gate.py`: the feature workflow's gate, mirroring bugfix's `fix_gate.py` (stage
  dict, exit 0 only with the stage's artifact): `plan` · `critic` · `phase` · `implement` · `ship`.
  Stages are the steps of `formulas/feature.formula.toml`, POURED (wisps take no lease); a step
  closes only through `close`, which diffs the live `blocks` edges against the formula and the
  plan's phase chain (a `bd dep remove` is refused); `claim` reaps expired leases of the molecule
  first; every bd read is scoped by `--mol`.
- `scripts/plan_close.py` (phase 8, called by `ship` after merge): canonical doc must name the plan;
  DECs in Links promoted to `executed` only on `check_decision_execution.py`'s own
  `EXECUTED_IN_FACT` verdict, then re-judged; epic burned at merge; at abandon a digest bead
  (bd's squash writes nothing for a poured molecule) and the file to `archive/`.
- Evidence: Beads adoption tests 2026-10-24 §3 (`docs/modules/polaris-harness/validation/`).
  Tests: `tests/` (RED recorded with `red_check.py`).
