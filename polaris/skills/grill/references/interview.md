# The interview — evidence, premise, questions

How steps 2–6 of `grill` run. The body of the skill says what; this file says how.

## Scope

Name one primary repository and one change; list other repositories as dependencies with their own
contracts. Resolve the repository root and its Polaris contract (`_polaris/` or `config.yml`). If
the contract is absent, continue from repository evidence and say once that durable Polaris
context is unavailable; never bootstrap it from here.

## The evidence pack — read only what can change the interview

1. The governing `AGENTS.md`, `CLAUDE.md` or equivalent.
2. Current state (`state/current.md` or the repository's equivalent) for open threads and blockers.
3. Accepted decisions with their supersession links, and the lessons in `records/`.
4. Any issue, request, design note or spec the founder named.
5. The implementation surface: manifests, lockfiles, entry points, tests, routes, services, jobs,
   auth boundaries, current code.
6. The data surface when relevant: schema, migrations, ORM models, generated types, constraints,
   indexes, tenancy, and the backend code that reads or writes them. Load `database-schema` for
   this; it never runs DDL, DML, migrations or type generation during a grill.
7. Earlier ideas: open beads `kind:idea` for the area, `plans/archive/` and `plans/done/` for the
   same subject.
8. The agent memory, through `ai-memory-retrieval` when installed: earlier sessions that discussed
   the idea. Skip it when absent and say so once. Memory is a lead; verify it on code.

Follow the repository's code-discovery rules: its code graph when present, text search for
strings, configuration and gaps in the graph.

## Keep evidence honest

A small working ledger with three labels:

- **Evidence** — observed now in code, tests, git, the tracker, the database or official docs.
- **Inference** — a reasoned conclusion that still needs confirmation.
- **Unknown** — a material branch neither the repository nor the founder has resolved.

Decisions, lessons, plans and session notes are leads; current-state claims are verified on code,
git, the tracker or the runtime. When decisions conflict, name the newest active one, what it
supersedes, and whether the code follows it. Never expose secrets, credentials, customer or
personal data in a question or in the plan file.

## Prior art

How other repositories and products solved the same problem, from primary sources: their code,
docs, release notes, issues. Name each source in the plan file with what it does better than what
we have. For an external SDK, framework or API, read the installed version from the lockfile and
query its official docs for that version (Context7 when available, the vendor's docs otherwise),
and record version and conclusion as Evidence. Never send proprietary code, secrets or customer
data to an external tool.

## Tear down the premise — before the first question and whenever an answer moves it

1. Is the request already satisfied? Does its stated cause hold? When a safe read-only command can
   show the behaviour, run it; record `file:line`, command and output in the ledger.
2. Compare the request with code, accepted decisions, docs and earlier statements. Record each
   contradiction with both sides and their evidence; never settle it by picking a document. If the
   request contradicts an accepted decision, the question offers the real choice: respect it, or
   reopen it through `architecture`.
3. One word with several meanings → list them with evidence and route the naming to `domain`.
4. A moved boundary, interface, schema or data contract, or dependency → `architecture` owns
   reversibility and whether a decision record is due. Do not write a decision here.

## Questions

One question per turn, resolving one decision. Each carries a real choice between named options
with one recommended as the default (so "yes" accepts it), the evidence or unknown behind it, and
what the answer unlocks. Never "do you confirm?".

Reply budget — the founder is not a developer: at most three short findings, only those that
change the decision, each naming its file; plain words instead of repository jargon; a specialist
skill named only with what it does; end on the single question.

Cover only material gaps: outcome and user, current behaviour, scope and exclusions, constraints,
data and dependency contracts, observable acceptance, rollout and rollback, decision conflicts.

## Assumptions and convergence

Every assumption in section 3 says how it will be tested: a command, a spike for `prototype`, a
measurement. Stop asking when material branches are resolved, acceptance is observable, exclusions
are explicit and every assumption has a test. Low-value questions are not asked.

## Gotchas

- The feature already exists → show the live result before asking what still needs changing.
- Code, docs and earlier statements disagree → name both sides; recency alone is not reconciliation.
- Convergence is not permission to build: the exit is the founder's yes on scope, then `plan-area`.
