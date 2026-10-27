---
title: records — eval
description: How every run leaves a structured, permanent record — the eval/ folder layout by category, what each run captures, the append-only index, the link to full traces in Langfuse — so a question asked six months later is answered by a query, not by memory.
status: active
---

# Records — every run, kept, traced, queryable

An experiment nobody can read back in six months did not happen. "What did we try on retrieval,
what did it cost, why did we revert it" is answered by querying the records and the traces, never
from memory or a chat log. Every run leaves its record, including the reverted ones: a reverted
run is the memory that stops the next loop from trying the same edit.

## Layout

One `eval/` folder at the root of the target's repository (or the skill's own `eval/`):

```
eval/
  README.md                       what the suite measures, the category list, how to run it
  datasets/<name>/                cases, splits, labels; each version pinned by hash
  graders/<failure-mode>/         the grader (code or judge prompt) + its calibration report
  experiments/
    index.jsonl                   one line per run, append-only: the table you query
    <category>/
      <YYYY-MM-DD>-<slug>/
        README.md                 for a person: hypothesis, change, result, verdict, what next
        run.json                  for a machine: the record below
        cases.jsonl               one line per case: the per-case results
```

**Category** is the part of the system the hypothesis is about (retrieval, ranking, generation,
pricing, a judge's calibration, a skill's trigger…), from a closed list declared in
`eval/README.md`. One run, one category. A new category is added to the list first; a run never
invents one.

## What a run captures — `run.json`

| Group | Fields |
|---|---|
| identity | `id` (`<category>-<date>-<slug>`), `parent` (the run it follows), `category`, `failure_modes`, `started_at`, `finished_at`, `operator` |
| intent | `hypothesis`, `prediction` (metric · bucket · direction · size), `change` (one sentence + diff pointer), `preregistration` (bar, arms, stop rules, spend cap) |
| code | repository, branch, commit SHA, dirty flag, prompt versions (name + version or hash) |
| models | for the target and every judge: requested id **and** the id actually served, provider, temperature, seed |
| data | dataset name, version or hash, split, case count, sampling rule |
| graders | per failure mode: kind (code · golden · reference-free · judge), version, and for judges the calibration it relies on (TPR, TNR, date, test size) |
| environment | flags and settings that change behaviour; anything turned off to keep ground truth out |
| results | per failure mode: n judged, n excluded with reason, raw rate, corrected rate and interval; overall; per bucket; tail; flips versus parent |
| cost | tokens, money, wall time, per arm |
| traces | the trace platform's run name and URL; trace id per case in `cases.jsonl` |
| verdict | KEEP · REVERT · PASS · BELOW_BAR · REGRESSED · NOT_RUN, the reason, and the next step |

`cases.jsonl`, one line per case: case id, bucket, input reference, output (or its reference),
each grader's answer with the judge's reasoning, error if any, latency, cost, trace id.

`index.jsonl` copies from each `run.json` the fields people filter on: id, parent, category,
failure modes, date, commit, models, dataset hash, headline numbers, cost, verdict. It is
append-only; a correction is a new line that names the line it supersedes.

## Full tracing — Langfuse

The record holds the numbers and the pointers; the trace platform holds every step.

- **The suite is a dataset** (one per suite, a folder path in the name, e.g. `eval/retrieval-golden`).
  Each case is a dataset item: input, expected output when there is one, metadata (bucket, failure
  modes it covers, source trace when it came from production). Item changes version the dataset;
  the run records which version it used.
- **Each run is an experiment** (a dataset run) named with the run's `id`. Its metadata carries
  the commit, the models (requested and served), the prompt versions and the category, so the
  platform can be filtered the same way the index is.
- **Each case is one trace**, linked to its dataset item, with a span for every model call, tool
  call and retrieval inside it. Nothing is summarised away.
- **Each grader answer is a score** on that trace: name = the failure mode, value = 1/0, comment =
  the judge's reasoning. Run-level numbers (corrected rate, cost) are scores on the run.
- **Prompts live in the platform's prompt management**, referenced by name and version from the
  run, so "which words produced this" is one click.

## Production is a record too

- Every production request is traced: input and metadata (user or tenant, session, agent version,
  feature, flags), every model and tool call, retrieved documents, the final output, user feedback,
  evaluator scores.
- The agent version is on every trace, so any metric can be cross-tabulated by version; a drop
  that lines up with a deploy is a regression.
- A production trace that reveals a failure becomes a dataset item with `source_trace_id`, so the
  golden set grows from what real users hit.
- What the system does today is read from the traces of today, never assumed from the last
  experiment.

## Rules

- A run without `run.json`, its index line and its traces is NOT_RUN, whatever it printed.
- Records are versioned with the code (committed); raw traces stay in the trace platform and are
  referenced by id. Secrets, keys and personal data never enter a record.
- Labels can be revised (standards drift as reviewers learn); a revision is a new dataset version,
  and the runs that used the old version keep pointing at it.
- Before proposing an experiment, query `index.jsonl` (and the platform) for runs in the same
  category and failure mode: what was tried, what was reverted, what it cost.
