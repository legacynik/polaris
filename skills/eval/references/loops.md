---
title: loops — eval
description: Improve a target against a metric in bounded keep-or-revert experiments — hypothesis, one change, the held-out gate, noise, stop rules, the fix ladder — and change a skill test-first.
status: active
---

# Loops

## The experiment

Every experiment is one hypothesis, one change, one verdict.

1. **Observe.** Pick one failure mode from error analysis; read at least 3 failing traces of it.
   One trace is an anecdote.
2. **Hypothesise.** One falsifiable claim: which step is responsible, what change should fix it,
   and the prediction — "if this is right, metric Z on bucket B moves by at least D". Two equally
   likely causes → two experiments, never one stitched change. Low confidence → a spike
   (`prototype`) before spending a run.
3. **One change.** One prompt field, one rule, one parameter. More than one logical change → split
   it. The change never touches the eval, its cases or its graders, and never reads ground truth.
   The words come from `prompt-engineering`.
4. **Run** baseline and candidate on the same cases, same graders, same pinned models, more than
   one seed when the target is stochastic, and cross-check on a second bucket the change was not
   aimed at.
5. **Decide** on the held-out split: **KEEP** only if the candidate beats the current version
   **and** the best version so far, loses no case the baseline passed, and the gain clears the
   noise floor; otherwise **REVERT**. Log it: hypothesis, change, numbers, verdict, parent.

## Noise and the bar

- Measure the noise floor first: run the baseline twice (or across seeds). A gain inside that band
  is not a gain.
- Set the KEEP threshold above the noise (in high-variance targets that can mean +10 points, not
  +2) and write it in the preregistration.
- A gain on the target bucket with a loss on the cross-check bucket is a trade, not a win: REVERT
  unless the preregistration accepted that trade.
- Every proxy metric can be gamed by the change it measures. Before KEEP, check a sample of the
  winning outputs by eye against the real goal.

## Stop rules

Stop and report the reason on any of: the budget or spend cap reached; the iteration cap; three
inconclusive experiments in a row; five experiments in a row under the bar (the problem is
structural, not wording: move up the ladder below); harness, judge or data drift; leakage found;
an infrastructure error (stop, fix, rerun — partial output is never interpreted).

## The fix ladder

Climb only when the rung below is exhausted:

1. **Specification**: clearer instruction, two or three examples (never CI cases), the missing tool
   or field.
2. **Structure**: split the task into steps, fix retrieval or context assembly, rewrite tool
   descriptions, add a verification call or a guardrail.
3. **Heavy**: fine-tuning, an automated prompt optimiser, human review in the loop.

When repeated prompt fixes keep failing on one mode, the cause is usually upstream of the prompt
(what was retrieved, how data was grouped, a wrong granularity). Measure per step (retrieval miss
vs ranking miss vs generation miss) and fix the step that owns the first failure.

## Automated loops

An optimiser that edits a document (prompt, skill) in a loop follows the same gate, mechanically:

- **Held-out selection split** the optimiser never sees; accept a candidate only if it beats the
  current and the best version there.
- **Small edits per step**, a fixed number; large rewrites lose what already worked.
- **Protected regions** the optimiser may not touch: the contract, the safety rules, the output
  shape.
- **A memory of tried edits**, kept outside the document, including the rejected ones, so the loop
  stops proposing what already failed.
- **A hard cost cap** per target and per cycle.
- **Propose-only for anything shipped**: the loop writes a proposal; a person or the repository's
  acceptance gate adopts it. A kept candidate is evidence, never a merge, deploy or promotion.

## lift — does this skill help at all

A skill earns its place by changing the outcome, not by triggering. Each behavioural check that
names a `task` runs twice — the agent with the skill's SKILL.md and without it — and the same
judge grades both against the check's assertion:

`eval_run.py --lift --skill <name> --backend claude-code --model sonnet` → `lift.json`:
`with` and `without` passes, `lift = (with − without) / n`. A negative lift fails (exit 1): the
skill makes the outcome worse. Zero means the skill only costs tokens: shorten it to what the
model does not already do, then measure again. A promotion needs lift ≥ 0, and a skill change is
kept only if its lift does not drop.

## The skill loop — weekly, propose-only

1. Pick the two skills with the most failures this week: lesson occurrences that name them,
   failed traces, checks that fell.
2. For each, propose small itemised edits (a line added, merged or removed — never a rewrite),
   words from `prompt-engineering`.
3. Keep an edit only if the held-out trigger split does not drop and the lift does not drop;
   log the rejected ones in the skill's CHANGELOG as "tried, reverted, why" so the next round
   does not retry them.
4. The kept edits go to a PR for a person; nothing ships from the loop itself.

## skill-tdd — a skill change, test-first

1. Write the case that shows the defect: a trigger case in `eval/prompts.json` (with its split) or
   an assertion in `eval/checks.json`.
2. **RED** on today's skill: run it and keep the report
   (`eval_run.py --skill <name> --backend harness`, or a priced backend after `--pilot 3`).
3. Change the skill (description or body; the words through `prompt-engineering`).
4. **GREEN**: the same run passes the new case, and `--compare <RED report>` shows no other flip.
5. Both reports go in the PR; bump the skill's version and its CHANGELOG.
