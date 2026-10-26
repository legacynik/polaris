---
name: domain
description: ◇ Polaris — Name the domain and place its boundaries. Fires when a term is overloaded, when two words are used for one thing, when a subdomain must be typed core, supporting or generic, or when two contexts with different models must integrate or be mapped. Not for where a service boundary falls, nor for interface, schema or framework commitments.
version: 0.5.2
user-invocable: true
auto: true
job: settle one question of domain language or domain boundary — the canonical term with the aliases it kills, the subdomain type with its sourcing consequence, the integration pattern with what it costs, or the context map with one labelled row per pattern — and halt the moment the modelling stops resolving a decision or a line
when_not: deciding WHERE a boundary line falls or how granular a unit should be (fracture planes and quanta — `architecture`, through its ownership and decomposition rules); committing to an interface, a data contract, a schema, a framework or a hot path (`architecture`); choosing what the company should build at all (strategy); implementing an aggregate, value object, repository or event-sourced model (nobody — write the code)
lifecycle: one settled question per invocation — a `CONTEXT.md` row per canonised term, a `CONTEXT-MAP.md` row per integrating pair and pattern, or a repository-root `DOMAIN.md` update for stable domain/component IDs; an ADR only when the three-condition test passes, handed to `architecture`, which writes the record (operating model §6) · files are created lazily, never in advance of the first thing to write in them · every halt is written into the artifact it interrupted · every edge not closed against a caller ships marked `ASSUMED`
invokes: []
invoked-by: [human, architecture, grill]
io: "receives: a contested term, subdomain, integrating contexts, system to map, or proposed stable domain/component ID -> produces: the canonical term, sourcing consequence, integration pattern, context map, or current DOMAIN.md mapping; otherwise a halt naming who owns the question."
status: active
---

# domain

## What it does

Settles **one** question of domain language or boundary: the canonical term and the aliases it kills,
a subdomain's type and its sourcing consequence, the integration pattern between two contexts and its
cost, or the context map. Here a choice is wrong because it is **false**; in `architecture` because it
**costs**. Rules: `references/decision-rules/domain-strategy.md`, loading only the ids a step names.

## When

- A term is overloaded or vague, or two words name one thing; a subdomain must be typed.
- Two contexts with different models must integrate, or a system's contexts must be mapped.
- `grill` or `architecture` hands over a contested name; stable IDs are due in `DOMAIN.md`.

## Steps

1. **Step 0, the halt** — first and at every step: a term earns a place only when it changes a
   decision or moves a line; a session that resolves neither stops. Stop drilling when every finer
   child is the same type as its parent (rule 8).
2. **Read the repo's language first** — `CONTEXT.md`, `CONTEXT-MAP.md`, `DOMAIN.md`, or wherever it
   keeps its terms; its convention wins. Ask the agent memory (`ai-memory-retrieval`) for earlier
   sessions on the term; skip if absent.
3. **Three habits in session**: challenge a term that contradicts the glossary on the spot; propose
   the canonical term when a vague one is said; cross-check the glossary against the code.
4. **Name the boundary in play**: subdomains are discovered, contexts are designed (rule 11).
5. **Run the arm** — halts and detail in [process.md](references/process.md):

   | Question | Loads | Emits |
   |---|---|---|
   | a term is overloaded, vague, or doubled | rule 12 | a `CONTEXT.md` row |
   | how much engineering a subdomain deserves | rules 1–10 | core · supporting · generic, with its consequence |
   | two contexts must talk | rules 18 → 19–24 → 25 → 26–28 | pattern, direction, why this branch, cost |
   | map the contexts | rules 29–31 | `CONTEXT-MAP.md`, one row per pattern |
   | bind stable domains and components | settled terms + census | `DOMAIN.md`, then the map regenerated |

6. **Every edge is a claim**: one script pass, the graph closes the survivors, the rest ships `ASSUMED`.
7. **Ask only what changes the model**: one plain question, your recommendation, ≤ 3 options with a cost.
8. **An ADR only when all three hold** — hard to reverse, surprising without context, a real
   trade-off — and `architecture` writes it (operating model §6); else a dated line.

## Output

First line `modalità: piena` or `modalità: ridotta — missing: <tag>[, <tag>...]` (`rule-library` ·
`glossary` · `graph-verify`). Then one of: a `CONTEXT.md` row (`term: <Name>`, what it is here,
aliases to avoid, the boundary dialogue, flagged ambiguities); a `CONTEXT-MAP.md` row (pair,
pattern — never `customer–supplier` —, direction, why this branch, cost, `ASSUMED`); a subdomain
type with its consequence; a `DOMAIN.md` update; or a halt naming who owns the question. Files
are created lazily. **Next:** back to the caller (`grill`, `architecture`).

## Where this goes

This skill produces: **domain, diagram (the context map beside DOMAIN.md)** — the repo's convention wins.

## Not for

- Where a boundary line falls or how granular a unit is; an interface, schema, framework or hot
  path commitment (`architecture`).
- Tactical DDD — aggregates, value objects, repositories: write the code.
- Whether to build the thing at all (strategy).
