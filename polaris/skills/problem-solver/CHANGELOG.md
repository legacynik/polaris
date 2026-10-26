# Changelog — problem-solver

## 0.3.0 — 2026-10-26

- Renamed from `unstick` to `problem-solver` (founder's choice). Remove the old install once:
  `npx skills remove -g unstick`.

## 0.2.0 — 2026-10-26

- Restating uses the problem worksheet (outcome, measure, deadline, off limits, decision maker
  and values, sources of insight), a flipped premise and a relaxed constraint.
- Step 3 builds a mutually exclusive, collectively exhaustive tree cut more than one way and
  prunes it by impact × ability to move; the crux is the big, movable branch.
- Converging: the one-day answer as a target, "what would you have to believe" per hypothesis,
  the knock-out test first with the expected result sketched per hypothesis.
- `methods.md` gains sizing heuristics and bias counter-measures, and a systems section: draw the
  loop, read behaviour over time, recognise the trap from its symptoms, act at a stronger lever
  than a number.

## 0.1.1 — 2026-10-26

- Eval only: check c3 no longer asks that the reply *end* with the experiments. A reply that
  proposed a time-boxed knock-out test with the expected result per hypothesis, then a closing
  summary, was graded as a fail: the ruler was wrong, not the skill.

## 0.1.0 — 2026-10-26

- New skill: break a loop when nobody knows how to solve the problem — stop and list the
  attempts, restate the problem, find the crux, at least ten hypotheses with inverted
  assumptions and the contradiction stated, prior art from fresh-context scouts with links, a
  systems check for loops, then the experiment that separates the top hypotheses, run through
  `prototype`. Methods in `references/methods.md`.
- Measured on sonnet with the claude-code judge: triggers 11/11 (6 positives, 5 decoys from
  bugfix, eval, grill, architecture, naming); lift +0.67 (c1 and c2 pass only with the skill; c3,
  the discriminating experiment, fails in both arms — the next thing to improve).
