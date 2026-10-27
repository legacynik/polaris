# Changelog — problem-solver

## 0.4.1 — 2026-10-27

- `invoked-by` adds `grill`: when every approach is weak, earlier attempts keep failing or the founder asks to flip the plan, grill hands off here and resumes with what it learned. No behaviour change.
- Version bump: patch, from 0.4.0.

## 0.4.0 — 2026-10-27

- Founder feedback: the skill took one path and went. It now proposes **three problem-solving
  approaches** (ways of thinking — invert it, drop the fixed constraint, the system loop, another
  field, work backwards…), opposite to each other and not the obvious ones, each with what it
  would look at, what it might surface and why it fits; recommends one and **stops for the
  founder's pick** ("you pick" lets it choose). Only then it works the problem through that
  approach to an answer and the cheapest experiment that would confirm it, with the expected
  result; an approach that yields nothing is said so, and the next one offered. "Flip this plan":
  one approach attacks the plan's central assumption.
- Lighter body (54 → 48 lines): six moves phrased as questions, no mandatory count, worksheet,
  tree, scouts or systems step. `methods.md` becomes an open list of fourteen approaches (each with when it fits, the move
  and the question it forces — inversion, dropping the fixed constraint, decomposing to the crux,
  the first cause, the system, another field, perspective shifts, attribute combinations, working
  backwards, the contradiction, the blind side, attacking the central assumption…) plus optional
  tools: the worksheet, the crux tree with two more cuts when the first feels obvious, "what would
  you have to believe?", the knock-out test, heuristics before big models, prior art, bias
  counters, and the system lens (the loop with stocks, flows and delays, the eight traps each with
  its way out, the leverage ladder with "if a fix doesn't hold, climb a rung");
  `bypass-test.md` rewritten to the new failure modes.
- Description adds "options we haven't thought of" (the `grill` handoff) and "ribalta questo piano"
  / "flip this plan"; trigger cases p07, p08 added.
- Eval rulers changed: old c2 (at least ten hypotheses before ranking) asserted a template count
  the founder rejected; old c3 (one or two time-boxed experiments) asserted the take-and-go shape.
  Both replaced: c2 three approaches, not fixes; c3 recommendation + question, nothing solved; c4
  flip a plan; c5 after a pick, the work follows the chosen lens to an experiment; c6 "you pick".
  c1 (attempts and their shared assumption) kept.

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
