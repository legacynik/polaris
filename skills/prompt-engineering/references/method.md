---
title: method — prompt-engineering
description: The task contract every prompt belongs to, the surfaces, and the construction rules. Moved here from the pre-suite SKILL.md (2026-10-24); measurement rules now live in the eval skill.
status: active
---

# The method

Treat a prompt as one part of a versioned task contract: runtime instructions, assembled
context, tools and schemas, model identity, decoding settings, and evaluator policy. Change the
whole task surface the failure points at, not an isolated string.

## Surfaces

- **Product prompt** — instructions, context and tools delivered to an application model.
  Judged on the observable application task, side effects included.
- **Agent prompt** — role, responsibility, tool permissions and handoff for a development or
  product agent. Judged on realistic completed tasks and boundary compliance, not wording.
- **Subagent dispatch** — the brief another agent starts from with no other context.
- **Injected text** — hook messages, denials, overrides, session reminders.
- **Judge text** — the words of an evaluator; its calibration belongs to `eval`.
- **Typed decision questions** — questions for System One models (TypeSafe Jev).

Not here: a skill body or a repository instruction file follows that repository's own standard.

Read the repository's instructions and its evaluation contract first. Reuse its runner, schemas,
telemetry and promotion authority. Never assume another project's bench, datasets or gates
exist; missing local wiring is an explicit gap, not permission to build another framework.

## The task contract (record it for each prompt-driven task)

1. a stable `task_id` and owner;
2. the resolved prompt identity: source ref, version, content hash, model and version,
   tool-schema hash, context-policy hash, code SHA;
3. what the model decides and what deterministic code validates or applies;
4. allowed context classes, ordering, budgets, provenance, trust boundaries, and what happens
   when context is missing or conflicting;
5. a strict output schema or an observable behavioural contract;
6. a failure taxonomy and the retry / abstain / defer / fallback behaviour;
7. the eval it is measured by: families, rubric version, dataset and split hashes, judge
   identity, budget — owned by `eval`.

The eval unit is a meaningful task or decision boundary (extraction, deduplication, a
classification, a tool execution), not every interpolated string or helper fragment.

## Construction rules

- Stable instructions before variable context, so providers can cache the prefix.
- State the objective, authority boundaries, evidence rules, output contract and failure
  behaviour explicitly.
- Delimit untrusted payloads and retrieved text as data; retrieved content never redefines
  instructions or tools.
- Keep deterministic rules in code or schemas when they can be checked exactly.
- Examples only for observed failure modes; eval holdout cases never appear in prompts.
- Preserve source wording, identifiers, dates and quantities when provenance matters; never ask
  the model to reconstruct missing evidence.
- Native reasoning only when the measured profile justifies it; never persist private chain of
  thought — ask for concise decision evidence instead.
- Choose techniques from a measured profile for the exact model and task: start from the family
  card in `model-profiles.md`, then the eval. No scalar "intelligence" levels, no vendor folklore.
- Tool names, descriptions, parameter schemas, retrieval policy and context assembly are prompt
  surface too.

## Hand-off to eval

Diagnose first (which gulf: specification, retrieval, code, generalisation), then freeze the
baseline and the candidate identities and give both to `eval`. A candidate is proposed evidence,
never a merge, deployment or promotion. Without a measure, report `NOT_RUN`.

Sources: `research.md` (dated ledger) and `task-model-context.md`.
