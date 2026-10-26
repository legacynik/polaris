# Changelog — eval

## 0.4.2 — 2026-10-27

- `runner.md`: `promote.py` judges a skill only when it is new or its description changed;
  `--evals` judges every one. A trigger case reads only the description and the catalog.

## 0.4.1 — 2026-10-26

- `runner.md`: `eval_run.py --repeat N` judges each item N times (odd) and scores the majority,
  every answer kept in `items.json`; `--compare` refuses only when more cases went from right on
  every baseline call to wrong on every call now than the reverse. `promote.py` passes
  `--repeat 3` to both arms: one haiku call against one refused unchanged skills at random.

## 0.4.0 — 2026-10-26

- `lift`: `eval_run.py --lift` runs each behavioural check that names a `task` with the skill's
  SKILL.md and without it, same judge; `lift.json` reports with, without and the lift; a negative
  lift exits 1. First live run, this skill on sonnet: c8 passed with the skill and failed without,
  c7 failed both (the arm sees SKILL.md only) — lift +0.50. Tests in
  `_standard/tests/test_eval_run.py` (RED recorded).
- The weekly skill loop (propose-only, small itemised edits, kept only if trigger accuracy and
  lift hold, rejected edits logged) in `references/loops.md`.
- Always: whoever edits a skill or prompt leaves its `eval/` untouched.
- `checks.json` c7 and c8 carry a `task`.

## 0.3.0 — 2026-10-26

- Rebuilt around the stages of an eval suite, one reference per stage: `suite.md` (traces, error
  analysis, golden set vs reference-free, splits, reading results), `graders.md` (choosing the
  grader, building and calibrating a judge, corrected rates, drift; absorbs `judges.md`),
  `audit.md` (checklist and tells), `loops.md` (one-change experiments, noise floor, stop rules,
  fix ladder, automated loops, skill-tdd), `ship.md` (release, CI, guardrails, production),
  `systems.md` (multi-turn, retrieval, tool calls, agents), `runner.md` (commands, backends;
  absorbs the runner part of `modes.md`, which is removed).
- New `records.md` and step 8: every run leaves `run.json`, `cases.jsonl` and an append-only
  `index.jsonl` line under `eval/experiments/<category>/`, every case traced in the trace platform
  (dataset, experiment run, scores per failure mode). A run without its record is NOT_RUN. Step 1
  queries the record and today's traces instead of recalling. The runner does not write the record
  yet (`runner.md`, "Not built yet").
- SKILL.md: an *Always* list; frontmatter `lifecycle` now keeps records committed. Cases p12, p13,
  n09 and checks c7, c8.

## 0.2.0 — 2026-10-26

- New judge backend `claude-code`: one headless `claude -p` per item (no tools, no MCP, no
  settings or hooks, in an empty dir), `--model` required so reports compare on one pinned model,
  no key and no priced pilot (subscription, $0 marginal). The founder picked it on 2026-10-26 as
  the judge of the promotion gate (`promote.py` with `EVAL_JUDGE_BACKEND=claude-code`), over a paid
  OpenRouter judge and over promoting without evals. Tests in
  `skills-suite/_standard/tests/test_eval_run.py` (RED recorded); measured live on `grill`'s test
  split: 5/5, 18 s, 26k tokens.

## 0.1.0 — 2026-10-24

- New skill (operating model §12): one door to set up, audit, read and drive evals, write and
  calibrate judges, prove skill changes test-first, and gate a release on no regression. Built
  on the principles of goal-directed keep-or-revert loops, skill optimisation, applied evals
  practice (error analysis first, binary calibrated judges, TPR/TNR) and preregistered evals
  (bars, arms, decoys, stop rules; a $0 stub dry run; a priced 3-item pilot gating spend;
  audits report only).
- Runner: `skills-suite/_standard/eval_run.py` over the one format
  (`eval/prompts.json`, `eval/checks.json`, `eval/split/`); judge backend is a setting
  (`harness`, `openrouter` with the GPT-family guard, `typesafe-jev`).
  Tests: `skills-suite/_standard/tests/test_eval_run.py` (RED recorded with `red_check.py`).
- Calls `prompt-engineering` for the candidate words; `prompt-engineering` hands back here.
