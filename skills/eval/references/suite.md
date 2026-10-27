---
title: suite — eval
description: Build an eval suite from real failures — traces, error analysis, failure modes, the dataset (golden set or reference-free), splits, leakage — and read results at scale.
status: active
---

# Building the suite

A suite is three things: **cases** (inputs, with expected outputs where one exists), **graders**
(one per failure mode, [graders.md](graders.md)) and **splits** (what you may tune on, what you
decide on). It is built from what the target actually gets wrong, in this order.

## 1. Collect traces

- **Real first.** Logs, traces, transcripts, tickets, the cases a person already complained about.
  Aim for about 100; fewer is fine to start, more brings diminishing returns on one static set.
- **Synthetic only to fill a gap the real ones leave**, and built from dimensions, never "generate
  50 prompts" in one call (they come out as paraphrases of one capability):
  1. name 3 axes along which requests vary (feature × user type × scenario; for a skill: surface ×
     arrival × intent);
  2. write about 20 tuples by hand, one value per axis; let a model extend them to 100+;
  3. turn each tuple into a natural request in a **separate** call; discard anything awkward.
- **Sampling live traffic for review**: half failure-driven (thumbs-down, guardrail hits), a third
  uncertainty-driven (graders disagree, the model contradicts itself), a fifth **random**. The
  random slice is the only unbiased picture; without it every review looks worse than reality.

## 2. Error analysis

1. **Open coding.** Read each trace end to end as its user would. Write one short lowercase note on
   the **first** thing that went wrong: what happened, no diagnosis, no fix. The earliest violated
   step owns the failure; what went wrong downstream of a bad input is not its own failure.
2. **Axial coding.** Group the notes into failure modes. Split two similar notes when they need
   different fixes. A model may propose groupings; a person accepts them.
3. **Labels.** One binary column per mode, 1/0 per trace. Prevalence = count / traces read.
4. **Saturation.** Stop when 20 failing traces in a row add no new mode; two serious rounds
   usually get there.
5. **Specification or generalisation.** For each mode ask: did the prompt (or the tool set) clearly
   ask for the right behaviour? No → it is a specification gap: fix the words through
   `prompt-engineering`, no grader. Yes, and it still fails → a generalisation failure: it earns a
   grader. Roughly half of early failures disappear with a one-line spec fix.

Re-run error analysis on **fresh** traces after a fix ships, after a model change, after the user
base grows or shifts. The value is in what the system does now.

## 3. The dataset: golden set or reference-free

| | Golden set (reference-based) | Reference-free |
|---|---|---|
| What a case carries | input **and** the expected output (an exact value, a canonical structure, a reference answer) | input only; the grader checks a property of the output |
| Use when | there is genuinely one right answer: extraction, classification, a computed value, a canonical query | many outputs are acceptable: tone, faithfulness, completeness, safety |
| Where it runs | CI, release gates, loops — labelled cases | the same, plus production traffic, which has no labels |
| Weak spot | penalises valid alternatives; costs labels | sees only the properties you thought to encode |

For each important failure mode, the strongest pair is both: a golden check in CI and a
reference-free check on live traffic. Add **executability** to either when it applies: run the
query, parse the JSON, simulate the tool call.

**Golden set contents**: core features, every past critical failure, edge cases, one case per
distinct path through the system. Start with 20–50; grow to 100–200 only by adding confirmed
failure modes, never by bulk generation. A failure that comes back after a fix is a failure that
was never added to the golden set.

**Ground truth stays outside the system under test.** The pipeline, its config and its prompts
never read an expected-output field, not even to "calibrate"; a diff on each change checks it.

## 4. Splits

| Purpose | Splits | Rules |
|---|---|---|
| deciding on a change (loop, release) | `train` · `test` | tune on train, decide on test; a test split used for tuning is spent |
| building a judge | `train` 10–20% · `dev` 40–45% · `test` 40–45% | few-shot examples only from train; iterate on dev; measure test once, after freezing; 30–50 PASS and 30–50 FAIL in each of dev and test |
| a selection split for a loop | `select` held out from the optimiser | the optimiser never sees it; a candidate is accepted only on it ([loops.md](loops.md)) |

Version the suite with the target. Pin the dataset by hash in every report.

## Reading results at scale (mode `read`)

Numbers point at traces; they are not findings.

1. Break every aggregate down: per case, per bucket, per failure mode. An average hides a bimodal
   result (half the cases near perfect, half unusable); report the tail and the worst bucket.
2. Read the traces behind the worst cells. Put each failure in one bucket: harness or environment,
   missing retrieval, bad context assembly, underspecified prompt, model generalisation, grader
   error.
3. Check the ruler before the target: a metric that undercounts (lexical overlap blind to
   synonyms, a parser that drops a format) produces failures that are not there. Confirm a
   surprising failure with a second, independent measure before acting on it.
4. Cluster when traces are too many to read: cluster the **outputs**, not the inputs, when input
   clusters only rediscover known categories; a bimodal histogram (latency, turns, length) is two
   populations or two failure modes — split and read each.
5. Use a model to find, count, search and plot traces. The explanation of *why* comes from a person
   reading them; a model asked why will produce a plausible story.

Expect to drop most first hypotheses. A cluster is a prompt to go read, never a conclusion.
