---
title: audit — eval
description: Audit an existing eval without editing it — the checklist of what makes an eval test nothing, and the tells that point at each defect.
status: active
---

# Audit — is this eval testing anything?

Read, never edit. Report per suite, each finding naming the file and the case; fixes go to setup,
judge or loop mode afterwards. Done when every item below has a verdict: holds · broken (with the
case) · cannot tell (with what is missing).

## The checklist

1. **Grounded in failures.** Cases trace back to error analysis of real traces, not to a list
   someone imagined. Each failure mode has a prevalence.
2. **Can fail.** Every case has been seen failing on some version; a case green across every
   version, or an assertion a no-op output satisfies, tests nothing.
3. **Both polarities.** Should-not cases and decoys from adjacent behaviour exist; a suite of only
   positives rewards saying yes.
4. **Graders fit.** Code checks where a rule decides; one binary judge per mode, never a 1–5 scale
   without a rubric; no judge grading several things.
5. **Judges calibrated.** TPR and TNR on a held-out test split, both labels present; the reported
   rate corrected, with an interval. A raw judge pass rate is a finding.
6. **No leakage.** No test or golden case in a prompt, an example or train; no pipeline code reading
   expected outputs.
7. **Pinned.** Model versions of agent and judge, prompt hash, dataset hash in every report.
8. **Split discipline.** Tuning happened only on train/dev; the test split is not spent.
9. **Breakdown.** Results reported per case and per bucket, with the tail; not only an average.
10. **Errors honest.** Judge and harness errors counted and excluded, not scored.
11. **The ruler.** The metric measures the goal (a lexical overlap may undercount meaning; a parser
    may drop valid formats). Spot-check a sample by eye.
12. For skills: `eval_run.py --dry-run --skill <name>` lists the format defects.

## Tells

| You see | It usually means |
|---|---|
| 85% agreement between annotators that felt easy | chance agreement; compute kappa |
| one criterion stuck at kappa 0.3–0.4 | two criteria under one name |
| judge TPR/TNR suspiciously high | a test case is in the prompt |
| the same failure back after a fix | it was never added to the golden set |
| retrieval great on synthetic questions, users unhappy | synthetic questions copy the source's words |
| evaluator numbers flat while users leave | a failure mode no evaluator watches |
| a function call stopped working with no code change | an unpinned model alias moved |
| five small gains in a row that add up to nothing | tuning inside the noise floor |
| a great average with angry users | a bimodal result hidden by the mean |
| the reviewers stopped using the review tool | review friction too high; fix the interface first |
