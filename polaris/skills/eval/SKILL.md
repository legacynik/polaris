---
name: eval
description: ◇ Polaris — Measure prompts, agents and skills before calling them better. Build an eval suite from real failures, choose between a golden set, code checks and a judge, calibrate the judge, audit an existing eval, run a bounded keep-or-revert loop, prove a skill change test-first, gate a release or a CI on no regression, monitor production. Use when something must be measured, two versions compared, or a judge trusted. Requires python ≥ 3.9; a judge key only for paid runs.
version: 0.4.2
user-invocable: true
auto: true
status: active
lifecycle: eval/ versioned in the target — datasets, graders, and every run's record under eval/experiments/<category>/ plus an append-only index.jsonl, all committed; full traces in the trace platform, referenced by id; the verdict also pasted into the PR or the work's plan file
invokes: [prompt-engineering]
invoked-by: [human]
io: a target (prompt, agent, judge or skill) and the question to answer -> a preregistered eval, its report (per case, with cost) and one verdict KEEP | REVERT | PASS | BELOW_BAR | REGRESSED | NOT_RUN
---

# eval

## What it does

Measures before anything is called better: read the failures, name the failure modes, give each
the cheapest grader that sees it, trust a judge only once calibrated, decide on cases nobody tuned
on, and leave a record a stranger can query in six months. For skills one format (`eval/prompts.json`,
`eval/checks.json`, `eval/split/`) run by `_standard/eval_run.py`. New words come from
`prompt-engineering`; this skill decides whether they hold.

## When

| Mode | The ask | Read |
|---|---|---|
| setup · read | a target has no eval; what is failing behind many results | [suite.md](references/suite.md) |
| judge | golden set, code check or judge? write and calibrate one | [graders.md](references/graders.md) |
| audit | an eval exists: is it testing anything? report only | [audit.md](references/audit.md) |
| loop · skill-tdd · lift | improve against a metric; change a skill test-first; does this skill help at all | [loops.md](references/loops.md) |
| release · CI · production | no regression before publishing; a gate per change; live traffic | [ship.md](references/ship.md) |

Every mode: [records.md](references/records.md); agents, conversations, retrieval, tools: [systems.md](references/systems.md); commands: [runner.md](references/runner.md).

## Steps

1. **Query the record first**: `eval/experiments/index.jsonl`, the trace platform, today's production
   traces. Done when you can say what was tried, what was reverted, and what the system does now.
2. **Preregister**: question, bar, arms, decoys, stop rules, spend cap — written before any run.
3. **Error analysis**: each trace's first failure, grouped into failure modes. Done when 20 failing
   traces add no new mode and every mode has a prevalence and a verdict: *specification gap*
   (`prompt-engineering` fixes the words) or *generalisation failure* (it earns a grader).
4. **One grader per mode**, the cheapest that sees it: code check → golden comparison →
   reference-free check → binary judge → a person.
5. **Calibrate every judge** on train/dev/test labels: TPR and TNR on test above 0.9 (or the bar a
   miss's cost sets); the observed rate corrected, with an interval.
6. **Spend gate**: `--dry-run` ($0) proves the wiring; `--pilot 3` prices the run and unlocks it.
7. **Run the mode** from its reference; decide on `test` only. A test split used for tuning is spent.
8. **Record**: `run.json`, `cases.jsonl` and the index line under `eval/experiments/<category>/`,
   every case traced. Done when the verdict can be rebuilt from the record and the traces alone.

## Always

- A person names the failure modes; a model sorts notes and finds, counts and plots traces.
- Every grader answers PASS or FAIL for one mode; every number has its cases behind it (per case, per bucket, the tail).
- Agent, judge, prompt and dataset pinned by version or hash; requested and served model both kept.
- A judge or harness error is excluded and counted ("judged 47 of 50").
- Held-out cases stay out of every prompt and example; whoever edits a skill leaves its `eval/` untouched.

## Output

The record and one verdict: KEEP, REVERT, PASS, BELOW_BAR, REGRESSED, or NOT_RUN when nothing was
judged or nothing was recorded. A stub is never a pass.

## Where this goes

This skill produces: **validation** (the record and verdicts, at the host's `outputs.validation`).

## Not for

- Writing or changing the words of a prompt — `prompt-engineering`, then back here.
- Merge readiness of product code — `real-testing`. Unit tests of ordinary code — `tdd-dev`.
