# Changelog — tdd-dev

## 2.7.4 — 2026-10-25

- Public-package clean (C5): three runner-output fixtures renamed to English descriptions (`jest__no_tests_found`, `vitest__no_test_files`, `shell__npm_ci_in_docker`); the runner, exit and verdict segments are unchanged.

## 2.7.3 — 2026-10-25

- Follows the rename `implement` → `implement-plan` (references, `invoked-by`, eval tuples). Text only.
- Version bump: patch, from 2.7.2.

## 2.7.2 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 2.7.1.

## 2.7.1 — 2026-10-25

- `invoked-by` gains `implement`: each task's agent records its RED with `red_check.py` and the orchestrator re-runs `verify` before closing the task. No behaviour change.
- Version bump: patch, from 2.7.0.

## 2.7.0 — 2026-10-25

- Test-writing rules come first (founder, 2026-10-25: "tests always on behaviour, never on a name,
  a path or other unstable things"; "how to write the tests must be the first thing"). A new
  section `## How tests are written` opens the body, before `## What it does`: seven one-line
  rules — public seam only, never a name, path, file text, wording, config value, private
  structure or timing; one behaviour per test; deterministic, time and order passed in at the
  seam; an oracle derived without the code; subject-scenario-result names; unit tests design the
  unit while integration and `real-testing` catch regressions of the whole; no test without a
  named break.
- Step 1's admission refuses aloud a requested test of a name, path, text, wording or config
  value and replaces it with the behavioural test, the unit fed its own inputs (settings
  included). Step 2 points at the section instead of restating four rules.
  `references/test-admission.md` gains the matching row (file exists, doc holds a word, function
  has a name, config value equals 5 → refuse, run the unit with inputs the test supplies).
- `references/writing-tests.md` takes Steve Sanderson's "Writing Great Unit Tests" (paraphrased,
  credited in `CREDITS.md`): what unit tests are for, configuration is not a unit, one behaviour
  asserted once, no shared preconditions, subject-scenario-result names (§5 reconciled with the
  SKILL.md rule); the clock is passed in at the seam, never patched inside the module.
- To stay at 60 lines: the GREEN `record` is the comment line after the RED one (same command),
  the two "fix exists / green accepted" triggers are one bullet, Output points at the receipt
  template in `references/cycle.md` instead of repeating it. `red_check.py` and every script are
  unchanged.
- Evals, skill TDD: `checks.json` gains c9–c13 (refuse name/path/text/config tests for a
  behavioural one; config handed in, not read; determinism at the seam, not by patching; a
  whole-flow regression goes to integration or `real-testing`; one behaviour per test). c7 was
  itself a source-text grep (`grep -q 'writing-tests.md' SKILL.md`, plus "a removed file stays
  removed"): now a judged assertion. RED/GREEN recorded in `eval/red-2026-10-25/`: same five
  requests, fresh agent, blind judge — 2.6.0 fails c10, c11, c12 (6/10 checks), 2.7.0 passes
  10/10 (`eval_run.py --backend harness --transcript`).
- Version bump: minor, from 2.6.0.

## 2.6.0 — 2026-10-24

- The 60-line form: `SKILL.md` is What it does · When · Steps · Output · Not for (56-line body).
  The previous body moved unchanged to `references/cycle.md` (iron law, test admission, the seven
  steps, output contract, excuses, selfcheck); the six `red_check.py` commands stay in Steps.
- Description starts "◇ Polaris — " and names its dependencies (python ≥ 3.9, pytest for the
  break). Its two `[form: …]` lines leave `_standard/nonconforming.allow`.
- Form only: `red_check.py` and every script keep their interface, behaviour and messages
  (other repos and workers call them now). Deferred, declared: the scripts' Italian help and
  messages, and the Italian fixture file names under `tests/fixtures/`.
- Version bump: minor, from 2.5.0. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md` (DEC-polaris-operating-model-001).


## 2.5.0 — 2026-10-24

- Baseline: the version this skill carried when the per-skill CHANGELOG became a gate (`_standard/check_skill_changelog.py`). Earlier history is in git.
