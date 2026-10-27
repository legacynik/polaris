---
name: problem-solver
description: "◇ Polaris — Unstick a problem by changing how it is looked at: name what repeats and the crux, propose three opposite ways of thinking about it, let the founder pick, then work the problem through that lens to an answer and the cheapest experiment that confirms it. Use after repeated failed attempts, a fix budget STOP, or on \"siamo in loop\", \"we're stuck\", \"options we haven't thought of\", \"ribalta questo piano\" / \"flip this plan\". Requires git."
version: 0.4.1
user-invocable: true
auto: true
status: active
lifecycle: one problem-solving note in the work's plan file (section 9) or the bead, when the experiment's result is known; approaches that yielded nothing stay in the note
invokes: [prototype]
invoked-by: [human, grill]
io: a problem that resisted several attempts, or a course of action to flip -> three opposite approaches with a recommendation and a question; after the founder's pick, the problem worked through that approach to an answer and the cheapest experiment that would confirm it
---

# problem-solver

## What it does

Changes how a stuck problem is looked at instead of trying the same fix again: three opposite
ways of thinking about it, the founder picks, then the work follows that one for real. Approaches
and optional tools: [methods.md](references/methods.md) — an open list, not a menu to recite.

## When

- Several attempts at the same thing failed, or a fix budget (`bugfix`, `implement-plan`) said STOP.
- "Siamo in loop", "non so come risolverlo", "we're stuck", "options we haven't thought of", or
  `grill` found every approach on the table weak.
- "Ribalta questo piano" / "flip this plan".

## Steps

1. **Stop.** Name what is being repeated: the attempts so far and the assumption they share.
2. **The crux**, in a sentence or two: what actually blocks. What would have to be true for this
   to be the real blocker? If the framing is the problem, restate it.
3. **Three approaches, not three fixes.** Ways of thinking about *this* problem — invert it, drop
   the constraint treated as fixed, dig to the first cause, find the loop that keeps it alive,
   borrow from a field with the same structure, work backwards from done, or one of your own.
   Choose three that pull in different directions and that the attempts so far did not use. For
   each: what it would look at, what it might surface, why it fits here. Recommend one, with why.
   Flipping a plan: one approach attacks the plan's central assumption.
4. **Stop and ask.** The first reply ends with the three and a question — which one, or the one
   fact that would change the recommendation. No solution yet. "You pick" → pick and go on.
5. **Work the chosen approach for real**, to an answer. Push it: what would have to be true, what
   would prove it wrong? End with the cheapest experiment that would confirm it and the result
   expected if it is right; run it through `prototype` when it needs code.
6. **Nothing there?** Say so plainly and offer the next approach; never dress up a weak answer.

## Output

First reply: the repetition, the crux, three approaches, the recommendation, one question. After
the pick: the work, the answer, the experiment and its expected result; once known, a note in the
plan file (section 9) or the bead, with the approaches that yielded nothing. **Next:** back to the
stuck skill (`bugfix`, `implement-plan`, `plan-area`); a recurring cause → `scripts/lesson_record.py`.

## Where this goes

This skill produces: **review** (the note, in the plan file or the bead it unblocks).

## Not for

- A defect with a reproduction and a known way forward (`bugfix`); a metric to push (`eval` loop).
- Product ideas to grow (`grill`); a choice between options already on the table (`architecture`).
