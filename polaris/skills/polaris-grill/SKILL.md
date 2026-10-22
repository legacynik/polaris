---
name: polaris-grill
description: Polaris skill — clarify product or technical intent. Use for "grill this idea", "clarify this feature", "challenge this spec", or ambiguous requirements before planning. Not for status, session resume, implementation, or autonomous issue creation.
user-invocable: true
version: 1.1.1
---

# /polaris-grill — clarify before building

Turn an ambiguous request into a decision-complete, repo-grounded handoff.
Answer discoverable facts yourself; ask one material question at a time.

This is a read-only interview. Do not implement. It does not create issues, branches, pull requests
or assignments, and it does not append decisions, lessons, journal entries, or session state.

## 1. Fix the scope

Name one primary repository and change; list others as dependencies with separate contracts.

Resolve the repository root, then its single committed Polaris contract at `_polaris/`. If the
contract is absent, continue from repository evidence and report that durable Polaris context is
unavailable; do not create or bootstrap it.

## 2. Build a bounded evidence pack

Read only what can change the interview:

1. The repository's governing `AGENTS.md`, `CLAUDE.md`, or equivalent instructions.
2. `_polaris/state/current.md` for open threads and blockers.
3. Applicable accepted decisions, supersession links, and lessons at the repository's declared paths.
4. Any issue, request, design note, or canonical spec path explicitly named by the user.
5. The implementation surface: manifests, lockfiles, entry points, tests, API routes, services,
   jobs, auth boundaries, and current code.
6. The data surface when relevant: schema files, migrations, ORM models, generated types,
   constraints, indexes, tenancy rules, and the backend code that reads or writes them.
7. The repository's own notes for this change: search its decision log and lessons at the
   declared paths for the change intent and main constraint. If it keeps none, say so once and
   continue with committed contract files and live evidence.

Follow the repository's code-discovery rules. Prefer its configured code graph or code-intelligence
surface when present; use text search for strings, configuration, or gaps in the graph. Verify a
graph or index is fresh when the repository contract requires freshness checks.

### Database and backend discovery

If an installed `database-schema` skill exists, load it as the specialized schema-inspection
contract. Its instructions cannot override this skill's read-only boundary. Otherwise apply its
core rule directly: read the real schema before reasoning about database behavior and never guess a
table, column, type, relationship, enum, nullable field, or index.

Prefer committed schema, migrations, ORM models, and generated types. Use live database metadata
only when read-only access is already configured and authorized; never run DDL, DML, migrations, or
type generation during the grill. Compare schema intent with the backend paths that actually query
it, including validation, authorization, tenancy, transaction, retry, and error behavior.

## 3. Keep evidence honest

Maintain a small working ledger with three labels:

- **Evidence** — directly observed in current code, tests, Git, tracker, database, or authoritative
  external documentation.
- **Inference** — a reasoned conclusion that still needs confirmation.
- **Unknown** — a material branch that neither the repository nor the user has resolved.

Memory is context, never proof of current state. Treat decisions, lessons, plans,
and session notes as leads. Verify current-state claims against code, Git, the tracker, the database,
or another authoritative runtime. When decisions conflict, identify the newest active decision,
what it supersedes, and whether current code follows it.

Never expose secrets, credentials, private keys, customer data, personal data, or raw environment
values in the interview or handoff.

## 4. Use Context7 only for a real dependency question

For an external SDK, framework, library, database engine, or API question:
1. Identify the dependency and installed version from manifests and lockfiles.
2. Query Context7 for official, version-aware documentation about that behavior.
3. Record version and conclusion as Evidence.
4. If unavailable, use official docs through the available research surface and disclose the fallback.

Do not query Context7 for repository behavior the code can answer. Never send proprietary code,
secrets, customer data, private decisions, or private prompts to Context7 or another external tool.

## 5. Tear down the premise before asking

Before the first question and whenever an answer changes the premise:

1. Check whether the request is already satisfied and whether its stated cause holds. Search the
   evidence pack, code, backend/data contracts, and prior art; follow memory leads to live evidence.
   When a safe read-only command can demonstrate the behavior, RUN it, not just read its source.
   Record `file:line`, command and raw output in the evidence pack; the turn obeys the reply budget.
   If execution is unavailable, name the missing access and keep the claim Unknown.
2. Compare the request, code, applicable accepted decisions, docs, and earlier statements in this
   session. Record each contradiction with both claims and their evidence.
   Separate intended rules from observed behavior; never silently pick a document to settle a conflict.
   If the request contradicts an accepted decision, the question offers the real choice: respect it
   (and meet the need another way) or reopen it through `architecture` and Decision admission.
3. Check key terms against their uses in code and docs. If one word has multiple meanings, list
   them in plain Italian with evidence and route the naming question to `domain`.
   The handoff records `domain: <term, meanings, evidence, open choice>`.
4. If the request moves a boundary, interface, schema/data contract, or dependency, route that
   commitment to `architecture`, which owns reversibility and Decision admission.
   The handoff records `architecture: <changed boundary, consumers, evidence, open choice>`.
   These doors compose with the interview; do not copy their procedures or write an ADR by reflex.

Before each question, auto-answer from these sources and versioned dependency docs when relevant.
Ask only for intent, authority, risk tolerance, or tradeoffs that evidence cannot settle.

## 6. Run the grill

Ask one question at a time. Each question resolves exactly one material decision; never bundle
multiple gates into one question. Each question must include:

- a real choice between named options (A or B), one marked as recommended and default so "sì"
  accepts it; never a bare "Confermi?" or "È questo che vuoi?";
- the short Evidence basis or the Unknown it resolves;
- the decision that the answer unlocks.

**Reply budget** — the founder is not a developer; the turn is a conversation, the evidence pack is not:

- at most 3 short findings, only those that change the decision (premise already met, cause wrong,
  a contradiction); each says what it means for him, not which script does what;
- each finding names its file (two for a contradiction, one per side); line numbers, commands and
  raw output stay in the evidence pack; no script lists;
- translate repo jargon (lane, recall, manifest, STALE, seal, retrieval) into a plain phrase;
- name a specialist skill only with what it does ("lo fissiamo col passaggio sui termini, `domain`");
- no labels, emoji, headings, or formulas such as "un sì vale A": say "ti consiglio A";
- end with the single question. Never batch even independent questions; wait for the answer.

Cover only material gaps: outcome/user, current behavior, scope/exclusions, constraints,
backend/data and dependency contracts, observable acceptance, rollout/rollback, and decision conflicts.

Challenge vague terms such as "fast", "scalable", "safe", "compatible", or "done" until they map
to an observable threshold or an explicitly accepted tradeoff.

## 7. Stop at decision completeness

Converge when material branches are resolved, acceptance is testable, exclusions explicit,
dependencies version-grounded, and risks classified. Stop low-value questions.

### Offer verification before the final handoff

Once questions converge, draft the handoff internally. ALWAYS offer the `critic` skill in a fresh
context before emitting it: one plain-Italian line with a recommendation, then wait for consent.
For example: "Consiglio un controllo con la skill `critic` in un contesto fresco, per cercare
premesse sbagliate, contraddizioni, soluzioni esistenti ignorate e termini o confini irrisolti: lo facciamo?"
Never start it automatically. Only an explicit yes authorizes a fresh-context run, never a fork of
the current context. Give it the draft and bounded evidence pack to attack those four failure areas.
Fold surviving findings into the handoff or list them as open questions before emitting it.
If declined, emit the handoff and record `critic: offered, declined`. If accepted but unavailable,
state the limitation and ask whether to emit without it; never claim the check ran.

Produce this handoff after the offer is resolved:

```markdown
# Polaris Grill — <change>

## Problem and outcome
## Evidence / Inference / Unknown
## AS-IS
## Locked decisions and conflicts
## Scope / out of scope
## Backend, data, and dependency contracts
## Acceptance and real-test path
## Rollout / rollback / observability
## Decision and lesson proposals
## Open questions
## Specialist routes and critic status
## Execution boundary
## Recommended next workflow
```

Decision and lesson entries are proposals only; route confirmation through the existing lifecycle.
Include pending `domain` / `architecture` handoff lines; unsettled routes remain explicit open questions.

Under **Execution boundary**, state: `Do not implement; do not create issues, branches, pull
requests or assignments from this handoff.` Keep each interview turn under 1,200 characters and the
default final handoff under 5,000 characters unless the user explicitly asks for deeper detail.

## 8. Route the handoff without inventing process

- If the implementation fits a single context window, hand the brief to the repository's existing
  execution workflow.
- If it spans multiple contexts, name the repository's existing canonical spec path and recommend
  that the execution workflow update it after the read-only grill; do not modify it here. Then
  decompose the handoff into independently testable, context-sized work items.
- Never invent a second spec directory, task tracker, memory layer, or orchestration framework.
- Require a fresh context to review the completed implementation against the handoff, repository
  rules, tests, schema, backend contracts, and current code before declaring it done.

Finish with the recommended next workflow and the evidence still required. Stop there.

## Gotchas

- A requested feature already exists → show the live result before asking what still needs changing.
- Code, docs and prior statements disagree → name both sides; recency alone is not reconciliation.
- One word hides several concepts → list the meanings and route to `domain`, not an invented glossary.
- A boundary changes → route to `architecture`; no automatic Decision or ADR.
- Convergence feels like permission to delegate → offer `critic`, then wait for an explicit yes.

## Verification

- [ ] Premises were checked live where safe; findings cite evidence and contradictions name both sides.
- [ ] Each turn asks one material question with a recommendation, acceptable default and consequence.
- [ ] Handoff separates Evidence / Inference / Unknown, preserves specialist routes and critic status.
- [ ] No implementation, tracker mutation, document write, or unapproved critic run occurred.
