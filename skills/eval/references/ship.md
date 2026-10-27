---
title: ship — eval
description: Evals at the boundaries — the release gate against the published version, the golden set in CI, guardrails in the critical path, and monitoring production traffic.
status: active
---

# Release, CI and production

Four places an eval runs after it exists, from strictest to widest.

| | Release gate | CI | Guardrail | Production monitoring |
|---|---|---|---|---|
| Question | is the candidate at least as good as what is published? | did this change break a known case? | must this one output be stopped now? | how is the system doing on real traffic? |
| Cases | the frozen test split | the golden set | every output | a sample of live traces |
| Graders | all of the suite's | code checks and golden comparisons; calibrated judges if affordable | deterministic code only | reference-free checks and calibrated judges |
| Blocks | the release | the merge | the output (fallback, retry, simpler path) | nothing; it opens findings |

## Release — no regression against the published version

1. Check out the published version (its tag, or the public repository) and run it with the same
   backend, pinned models and split: that report is the baseline.
2. Run the candidate with `--compare <baseline report.json> --split test`.
3. REGRESSED (lower accuracy) or any flipped case blocks the release until explained; PASS also
   needs the preregistered bar (`--bar`). Check the tail: no bucket may drop past its own margin
   even when the average rises.
4. The verdict and both report paths go in the PR body.

## CI — the golden set on every change

- Runs on every prompt edit, model swap, new tool, dependency bump that reaches the model.
- 20–50 cases to start, 100–200 mature: core paths, past critical failures, edge cases. It is a
  smoke test: green proves no known case broke, not that quality is good.
- Pin exact versions of the agent's model and the judge's model; an unpinned alias moves under you
  and the CI reports your change for the provider's.
- Fail the build on a regression. A flaky case is fixed or removed the same day; a CI people
  re-run until green measures nothing.
- A diff on each commit proves no golden case appears in a prompt or an example.

## Guardrails — in the critical path

- Deterministic and fast: schema validation, regex, blocklist, parser (`ast.parse`, a SQL parser),
  limits. A judge is too slow for the critical path.
- On a hit: reject with a fallback, retry, or take a simpler path; log every hit.
- Measure its false-positive rate on known-good traffic before enabling it; above about 1% it reads
  as a broken product.

## Production monitoring

- A handful of evaluators (five to seven), one per known failure mode, mixed code and judge.
- Judges run asynchronously on a sample (1–5% of traffic), never in the request path.
- Report corrected rates with intervals ([graders.md](graders.md)), per failure mode, over time.
- Review a blended sample by hand on a fixed cadence: failure-driven, uncertainty-driven and a
  random slice ([suite.md](suite.md)). Flat evaluator numbers with falling user engagement mean a
  failure mode no evaluator watches: read random traces.
- Re-run judge alignment on fresh labels on a schedule (weekly is cheap once labels flow) and after
  every model change.
- After a deploy, verify on real traces that the new version is the one answering and that the
  evaluators still fire. "Deployed" is not "working".
