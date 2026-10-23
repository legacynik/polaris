# Routing — which rule file generates the options, which one decides

Load this at a fork, when more than one rule file has something to say. Two columns, because
they are two different jobs: **generating** the option set and **adjudicating** between the
options are not the same act. The failure this table prevents is loading the generator and
treating its forces as a verdict.

## The rule files

Each file lives in this skill's own `references/decision-rules/` folder, so it resolves on any
repository. Prose names a file by its subject; a Decision's `rules` key cites it as
`<subject>:<rule-id>`, and each id must be a rule heading of that file.

| Subject (file) | Decides |
|---|---|
| **decomposition** (`decomposition.md`) | whether and how to break a system apart, granularity, data ownership, distributed transactions, contracts, coordination, reuse, the trade-off method (groups `§A`–`§J`) |
| **governance** (`governance.md`) | fitness functions, enforcement, quanta and coupling forces, schema evolution, incremental change, migration, detectors |
| **data-systems** (`data-systems.md`) | storage engine, index, partitioning, replication, encoding, isolation, consensus, batch and stream, derived data |
| **ownership** (`ownership.md`) | who owns a surface, capacity ceilings, where a unit boundary goes |
| **domain-strategy** (`domain-strategy.md`) | the model-fit signals this door reads (rules 16, 17); everything else in it belongs to `domain` |
| **component-boundary** (`component-boundary.md`, cited by number: `component-boundary:12`) | when to build a component boundary inside one codebase, its form, its dependency direction |

## The forks

| Fork | Generates the options | **Adjudicates** |
|---|---|---|
| **Granularity** — split or merge a service or module | governance `transactional-boundaries-set-the-granularity-floor` (the floor) · `start-with-a-few-large-services` (direction of travel) · `choose-the-partition-axis-deliberately` | **decomposition §C** — `granularity-equilibrium` (six disintegrators against four integrators), then `leftover-naming-test` on the remainder |
| **Two designs weighed against each other** | governance supplies the forces: `three-forces-of-dynamic-coupling`, `connascence-strength-ladder`, `prefer-static-to-dynamic-connascence` | **decomposition §J** — `three-step-tradeoff-process` · `mece-the-comparison-set` · `qualitative-not-quantitative` · `least-worst-not-best` |
| **Architecture quantum · static vs dynamic coupling** | **governance alone** — `architecture-quantum` · `the-database-is-inside-the-quantum` · `ui-coupling-collapses-the-quantum` · `static-quantum-diagram-for-legacy` | **governance**. Loading decomposition §B as well defines the quantum twice; use one |
| **Cross-service transactions, sagas, eventual consistency** | — | **decomposition §E** — `eventual-consistency-pattern-selection` · `saga-state-machine-required` · `compensating-transaction-is-not-a-rollback` · `dont-default-to-epic-saga` |
| **Data ownership · access versus update · database type** | governance names the concerns | **decomposition §D** — `writes-determine-ownership` · `joint-ownership-four-techniques` · `data-access-pattern-selection` · `database-type-selection` |
| **Reshaping a schema already in production** | **governance** — `expand-contract` · `expand-contract-three-cases` · `migrations-are-immutable` · `skip-undo-migrations` | **governance** |
| **Storage engine · index · partition · replication · isolation level** | decomposition §D frames who owns the data; it does not choose the mechanism | **data-systems** — `lsm-or-btree` · `row-or-column` · `index-count` · `partitioning-scheme` · `isolation-level-selection` · `replication-architecture`. Decomposition `database-type-selection` chooses a *type*; data-systems chooses inside it |
| **Is this rule mechanically checkable, and does it warn or block** | decomposition `govern-structure-automatically-not-by-review` raises the question | **governance** — `objective-outcome-or-its-not-one` · `continuous-verification-or-its-not-one` · `cadence-by-criticality` · `cascading-fitness-function` · `principles-without-enforcement` |
| **Contract strictness — strict versus loose** | decomposition §F `contract-type-before-contract-format` sets up the choice | **governance** — `contract-strictness-by-change-frequency` · `need-to-know-contracts` · `postels-law-for-contracts` · `consumer-driven-contracts`; decomposition `deployment-cadence-overrides-strictness` overrides it when the two sides release on different cadences |
| **Who owns the surface · is this unit overloaded · does the boundary go here** | — | **ownership** — rules 1 (capacity ceiling) · 4 (four-property fitness test) · 5 (friction signals a defect) · 7 (indefinite collaboration signals a wrong boundary) · 12 · 13 · 15 (single owner) |
| **When to build a component boundary at all, and in which form** | — | **component-boundary** — 1 (inflection point) · 2 (partial boundaries) · 3 (physical forms) · 5 (dependency direction) |

## The standing rule between decomposition and governance

When both fire and no row above covers it: **at the coupling step, load decomposition; at the
governance step, load governance. Where both fire, governance yields on the decision and keeps
the enforcement.**

## Where every rule file stops

A fork that lands here is not resolved by loading more rule files. It halts or hands off.

| Question | Where it goes |
|---|---|
| Subdomain classification (core / supporting / generic), integration patterns between contexts, where a **domain** boundary falls | the `domain` door. Hand the question over; a component-boundary rule does not answer it |
| What to build, whether the advantage is worth having | strategy — outside this skill. Every rule file takes the business driver as an *input* |
| Which number a person or a role answers to | people and roles — outside this skill. These rules measure systems, never organisations |
| A fitness function that passes green while the thing it guards degrades | governance `measure-the-instrument-before-trusting-it` is the only rule on it, and it is thin: treat its answer as a hypothesis to test |
| Vendor-specific tuning (one database's knobs, one cloud store's patterns) | the vendor's own maintained guidance; take the pattern, keep the vendor text out of this skill |
