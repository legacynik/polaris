---
name: problem-solver
description: "◇ Polaris — Break a loop when nobody knows how to solve the problem: stop, restate it, find the crux, generate many hypotheses and invert the assumptions, search how other repos and products solved it, then pick the cheapest experiment that tells the hypotheses apart. Use after repeated failed attempts at the same thing, when a fix budget says STOP, or on \"non so come risolverlo\", \"siamo in loop\", \"we're stuck\". Requires git."
version: 0.3.0
user-invocable: true
auto: true
status: active
lifecycle: one problem-solving note in the work's plan file (section 9) or the bead, when the experiment's result is known; the hypotheses that failed stay in the note
invokes: [prototype]
invoked-by: [human]
io: a problem that resisted several attempts -> a restated problem, its crux, a ranked hypothesis table with the assumption each one flips, prior art with links, and one or two discriminating experiments run through prototype
---

# problem-solver

## What it does

Gets a stuck problem moving by changing how it is looked at, not by trying the same fix again.
It widens first — many hypotheses, flipped assumptions, how others solved it — then narrows to
the one cheap experiment that tells the best hypotheses apart. Methods: [methods.md](references/methods.md).

## When

- Three attempts at the same thing failed, or a fix budget (`bugfix`, `implement-plan`) said STOP.
- "Non so come risolverlo", "siamo in loop", "nothing works", a problem with no visible next step.

## Steps

1. **Stop the loop.** List every attempt so far: what was tried, what it showed. Done when the
   list exists and names the assumption each attempt shared.
2. **Restate the problem** in the problem worksheet ([methods.md](references/methods.md)): outcome,
   measure, deadline, what is off limits, who decides. Flip one premise and relax one constraint.
   Done when the statement is outcome-focused and measurable and one wider framing is noted.
3. **Break it down and find the crux**: a tree of the problem that is mutually exclusive and
   collectively exhaustive, cut by two or three different frames; score each branch on impact
   and on whether we can move it. Done when one movable, high-impact branch is named the crux.
4. **Diverge, at least ten hypotheses** before judging any: flip each shared assumption, state the
   contradiction (improving X worsens Y) and how to separate it, solve a smaller or related
   problem, work backwards from "solved", borrow from another domain, and add three on purpose
   absurd. Done when there are ten and none is evaluated yet.
5. **Prior art, in parallel**: fresh-context scouts, one lens each — GitHub repos and issues with
   the same symptom, products that solved it, papers, a neighbouring domain. Primary sources
   only, each with a link. Done when every lens returned or said it found nothing.
6. **Is it a loop in the system?** Look for a feedback loop, a delay or a limit that keeps
   recreating the problem; a fix at the leverage point beats a fix at the symptom.
7. **Converge**: write the one-day answer (situation · complication · resolution) as a target to
   attack; for the top hypotheses ask what you would have to believe for each to hold; pick the
   knock-out test — the one result that would make other work unnecessary — and sketch the chart
   it should produce under each hypothesis before running it. Time-box it.
8. **Run them** through `prototype`, one question per spike. Record the result, including the
   hypotheses it killed; a recurring cause becomes a lesson through `scripts/lesson_record.py`.

## Output

The problem-solving note: the attempts, the chosen restatement, the crux, the hypothesis table
(hypothesis · assumption flipped · evidence · test · cost), the prior art with links, the
experiments and their result. **Next:** the winning hypothesis goes back to the skill that was
stuck (`bugfix`, `implement-plan`, `plan-area`); none survived → back to step 2 with what was learned.

## Where this goes

This skill produces: **review** (the note, in the plan file or the bead it unblocks).

## Not for

- A defect with a reproduction and a known way forward (`bugfix`); a metric to push (`eval` loop).
- Product ideas to grow (`grill`); a decision between known options (`architecture`).
