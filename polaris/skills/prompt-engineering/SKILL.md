---
name: prompt-engineering
description: ◇ Polaris — Write or change the words a model reads — system prompts, subagent dispatches, judge text, hook and deny messages, questions for typed decision models. Use when a prompt must be written, fixed or tightened; hand the candidate to `eval` to measure it, never done without that measure. Not for SKILL.md or AGENTS.md bodies. Requires nothing beyond the repository.
version: 1.0.1
user-invocable: true
auto: true
status: active
lifecycle: the prompt lands in the file that runs it (code, config, hook); its measure comes from eval and goes into the PR — this skill keeps no artifact of its own
invokes: []
invoked-by: [eval, human]
io: a prompt surface and the failure it shows -> a candidate prompt with frozen identities (source ref, content hash, model id) and the eval verdict that backs it, or NOT_RUN
---

# prompt-engineering

## What it does

Changes the words a model reads, and only those. A prompt is one part of a task contract —
instructions, context, tools and schemas, model, decoding, evaluator — so the change goes where
the failure points. It never calls a change done without a measure from `eval`.

## When

- A prompt must be written: a subagent dispatch, a product system prompt, a judge's text, a hook
  or deny message, a question for a typed decision model.
- A prompt misbehaves (hallucinates, ignores a rule, drifts) and the cause is in the words.
- `eval`'s improvement loop asks for the candidate of one hypothesis.

## Steps

1. Ask the agent memory (`ai-memory-retrieval`, skipped if absent) for past changes to this
   prompt and what they measured. Read the repository's instructions and eval contract.
2. Name the surface and open its reference, ending on its checklist with every box answered:
   `references/write-subagent.md`, `write-product-system-prompt.md`, `write-judge.md`,
   `write-injected-text.md`, `write-system-one.md`. The task contract and construction rules:
   `references/method.md`; model-family notes: `references/model-profiles.md`.
3. Diagnose before editing. Is the first failure in the words (specification), in missing
   context (retrieval), in a rule code could check, or in the model's generalisation? Only the
   first is a prompt change; name which it is.
4. Write the smallest change that could falsify one hypothesis: objective and authority first,
   untrusted input delimited as data, a closed output contract, failure behaviour stated,
   examples only for observed failures and never from held-out cases, stable text before
   variable context.
5. Freeze identities — source ref, content hash, model id and version, tool-schema hash — and hand
   baseline and candidate to `eval`. Never edit a judge in the same campaign as what it grades.
6. Report the verdict `eval` returned; without one the result is `NOT_RUN`.

## Output

The candidate prompt in the file that runs it, its frozen identities, the hypothesis it tests,
and `eval`'s verdict or `NOT_RUN`. Never a merge, deploy or promotion decision.

## Where this goes

This skill produces: **none** (the prompt lives in the file that runs it; the measure is `eval`'s).

## Not for

- Measuring, comparing models, calibrating a judge, running a loop — `eval`.
- A SKILL.md, AGENTS.md or CLAUDE.md body — the repository's skill and instruction standards.
- Plain code or config edits that happen to touch a prompt file.
