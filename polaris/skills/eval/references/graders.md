---
title: graders — eval
description: Choose the grader for each failure mode (code check, golden comparison, reference-free check, LLM judge, person), build a judge, calibrate it with TPR/TNR, correct its rate, watch its drift.
status: active
---

# Graders

A **grader** is whatever turns one output into PASS or FAIL for one failure mode. A **judge** is
the one kind of grader that is itself a model. Every judge is a grader; most graders should not be
judges.

## Choosing the grader — first row that fits wins

| The failure mode is… | Grader | Cost and trust |
|---|---|---|
| decidable by a rule: parses, matches a schema or regex, counts, executes, stays under a limit | **code check** | ms, $0, deterministic; trust it once it has been seen failing |
| a single right answer exists | **golden comparison**: exact match, normalised match, structural match (AST, JSON fields), numeric tolerance | cheap; needs labelled cases; penalises valid alternatives, so normalise first |
| a property of the output, no reference needed | **reference-free check** (code where possible: required fields present, forbidden terms absent, citations resolve) | cheap; runs on unlabeled production traffic |
| needs interpretation: faithfulness, tone, helpfulness, did it follow the instruction | **binary LLM judge**, one per mode, calibrated below | seconds and money per case; trusted only through TPR/TNR |
| contested, high-stakes or still being defined | **a person**, with a written rubric | slowest; the source of labels for everything above |

A score scale (1–5) without a rubric per point drifts and disagrees. A judge that grades three
things grades none: split it into three binary judges.

## Building a judge

The prompt has four parts:
1. **One narrow criterion**, worded from the failure-mode notes.
2. **PASS and FAIL definitions**, precise, with the boundary spelled out.
3. **Examples from `train` only**, ideally borderline ones, both labels. Leaving examples out is
   the most common reason a judge underperforms; one to eight are enough.
4. **Structured output**: `{"reasoning": "...", "answer": "PASS" | "FAIL"}`, reasoning first.

The words come from `prompt-engineering` (`references/write-judge.md` there). Pin the judge model's
exact version, prefer a family other than the one under test, temperature 0.

## Calibrating it

1. **Labels.** Hand-label cases from real traces, both PASS and FAIL. One principal expert is
   enough for a narrow domain; with several annotators, measure agreement per criterion (Cohen's
   kappa ≥ 0.6 before labelling more). A criterion stuck around 0.3–0.4 is two criteria under one
   name: split it. Raw agreement flatters: 85% agreement can be kappa 0.48.
2. **Splits.** train 10–20% · dev 40–45% · test 40–45%, 30–50 of each label in dev and test.
   Production may be 95% PASS; the split is balanced on purpose.
3. **Iterate on dev.** Run the whole dev set; compute **TPR** (true PASS judged PASS) and **TNR**
   (true FAIL judged FAIL); read every false PASS and false FAIL; sharpen the wording, swap the
   examples, move a missing edge case into train. Repeat until both exceed 0.9, or the bar the cost
   of a miss sets (missing a failure that costs money → push TNR).
4. **Measure test once**, after freezing the prompt. Suspiciously high numbers mean leakage: a test
   case is in the prompt.

Precision and recall hide which way the judge errs; agreement rises with the pass rate and
flatters the judge. TPR and TNR are the two ways a judge misestimates a pass rate.

## Using its numbers

On unlabeled traces the judge's raw pass rate is biased. Correct it:

```
true_rate ≈ (observed_pass_rate + TNR − 1) / (TPR + TNR − 1)      clipped to [0, 1]
```

Meaningless when TPR + TNR ≈ 1 (the judge is guessing). Give an interval: bootstrap the test set,
recompute TPR, TNR and the corrected rate each time, report the 2.5th–97.5th percentiles. Raising
TPR narrows the interval most.

## Biases and drift

- **Position**: shuffle candidate order in pairwise comparisons; run both orders when it matters.
- **Verbosity**: longer answers win unearned; include a short correct answer among the examples.
- **Self-preference**: a judge rates its own family higher; judge with another family.
- **Drift is silent**: provider models move behind unpinned aliases and the team's standard moves
  too. Re-run alignment on fresh labels every few weeks and on any model or criterion change.
  Never change a judge inside a campaign it is grading: freeze, finish, then recalibrate.
- **A judge that fails** (unparseable reply, timeout) is excluded and counted, never scored. A
  fabricated score on a judge error poisons the average silently.
