---
name: polaris-grill
description: Polaris skill — run a bounded, repo-grounded product and technical interview that resolves fuzzy intent against live code, backend and database contracts, durable decisions, lessons, repository memory, and version-aware Context7 docs, then produce a decision-complete handoff. Use for "grill this idea", "clarify this feature", "challenge this spec", architecture discovery, or before planning implementation. Do not use for status, session resume, implementation, or autonomous issue creation.
user-invocable: true
---

# /polaris-grill — clarify before building

Turn an ambiguous product or technical request into a decision-complete handoff grounded in the
target repository. Ask one question at a time. Answer anything discoverable from code, data
contracts, repository memory, or current documentation before asking the user.

This is a read-only interview. Do not implement. It does not create issues, branches, pull requests
or assignments, and it does not append decisions, lessons, journal entries, or session state.

## 1. Fix the scope

Name one primary product repository and the change being clarified. For cross-repository work, keep
one primary repository and list the others as explicit dependencies. Do not mix multiple product
contracts or founder-vault state into one interview.

Resolve the repository root, then its single committed Polaris contract at `_polaris/`. If the
contract is absent, continue from repository evidence and report that durable Polaris context is
unavailable; do not create or bootstrap it.

## 2. Build a bounded evidence pack

Read only what can change the interview:

1. The repository's governing `AGENTS.md`, `CLAUDE.md`, or equivalent instructions.
2. `_polaris/state/current.md` for open threads and blockers.
3. The newest relevant sections of `_polaris/decisions.md` and `_polaris/lessons.md`.
4. Any issue, request, design note, or canonical spec path explicitly named by the user.
5. The implementation surface: manifests, lockfiles, entry points, tests, API routes, services,
   jobs, auth boundaries, and current code.
6. The data surface when relevant: schema files, migrations, ORM models, generated types,
   constraints, indexes, tenancy rules, and the backend code that reads or writes them.
7. A targeted memory query from the product repository:

```bash
polmem recall "<change intent and main constraint>" --top 5
```

If `polmem` is missing or the repository is not memory-wired, state the degraded memory coverage
once and continue with committed contract files and live evidence. Never run `polmem init`.

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

Memory is context, never proof of current state. Treat `polmem recall`, decisions, lessons, plans,
and session notes as leads. Verify current-state claims against code, Git, the tracker, the database,
or another authoritative runtime. When decisions conflict, identify the newest active decision,
what it supersedes, and whether current code follows it.

Never expose secrets, credentials, private keys, customer data, personal data, or raw environment
values in the interview or handoff.

## 4. Use Context7 only for a real dependency question

Use Context7 when the answer depends on an external SDK, framework, library, database engine, or
API:

1. Identify the actual dependency and installed version from manifests and lockfiles.
2. Query Context7 for official, version-aware documentation about the specific behavior in question.
3. Record the relevant version and documentation conclusion as Evidence.
4. If Context7 is unavailable, use official documentation through the available research surface and
   disclose the fallback.

Do not query Context7 for repository behavior the code can answer. Never send proprietary code,
secrets, customer data, private decisions, or private prompts to Context7 or another external tool.

## 5. Auto-answer before asking

For every potential interview question, run this loop first:

1. Search the evidence pack and current code.
2. Check active decisions and relevant lessons, including supersession links.
3. Check targeted `polmem recall` results as leads, then verify them.
4. Inspect backend and database contracts when the answer depends on data flow.
5. Check version-aware Context7 or official docs when the answer depends on an external contract.

If those sources resolve the question, record the answer as Evidence or Inference and do not ask the
user. Ask only for product intent, authority, risk tolerance, or tradeoffs that evidence cannot
determine.

## 6. Run the grill

Ask one question at a time. Each question resolves exactly one material decision; never bundle
multiple gates into one question. Each question must include:

- the recommended answer or default;
- the short Evidence basis or the Unknown it resolves;
- the decision that the answer unlocks.

Cover these gates only when material:

1. **Outcome and user** — who benefits, what changes, and which measurable result matters.
2. **AS-IS** — current behavior, data flow, ownership, and the observed failure or opportunity.
3. **Scope** — smallest useful slice, explicit out-of-scope, and compatibility boundary.
4. **Constraints** — invariants, latency, cost, security, privacy, tenancy, and operational limits.
5. **Backend and data** — API/service flow, schema facts, migrations, transactions, authorization,
   retention, volume, and failure semantics.
6. **Dependencies** — integrations, installed versions, contracts, failure modes, and fallbacks.
7. **Acceptance** — observable examples, regression boundaries, and a real-test path.
8. **Delivery** — rollout, migration, observability, rollback, and ownership after release.
9. **Decisions** — conflicts with durable decisions, reversibility, and what remains unknown.

Challenge vague terms such as "fast", "scalable", "safe", "compatible", or "done" until they map
to an observable threshold or an explicitly accepted tradeoff.

## 7. Stop at decision completeness

End the interview when all material branches are resolved, acceptance is testable, out-of-scope is
explicit, dependencies are version-grounded, and remaining risks are classified. Do not continue
asking low-value questions merely to make the document longer.

Produce this handoff:

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
## Execution boundary
## Recommended next workflow
```

Decision and lesson entries are proposals only. Quote the proposed entry and route confirmation
through the repository's existing Polaris lifecycle; do not write it from this skill.

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
