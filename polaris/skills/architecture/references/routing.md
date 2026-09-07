# Routing — which book generates the options, which one decides

Load this at a fork, when more than one extract has something to say. Two columns, because
they are two different jobs: **generating** the option set and **adjudicating** between the
options are not the same act, and the failure this table prevents is loading the generator and
treating its forces as a verdict.

**These assignments are not ours.** Each extract declares in its own `when_not` where it stops
and who owns the question, and the Ford siblings carry an explicit overlap table naming a
winner per row. This file transcribes those declarations. **Never reassign an adjudication a
book hands to another book** — if a row here looks wrong, the fix is in the extract's own
table, not here.

Paths are relative to `references/company-os-book-library/_extract/`. Shorthand:
**HP** = `ford-richards-hard-parts` · **EV** = `ford-parsons-evolutionary-architectures` ·
**DDIA** = `kleppmann-ddia` · **TT** = `skelton-pais-team-topologies`.

## Contents

- [The forks](#the-forks)
- [The standing rule between the two Ford books](#the-standing-rule-between-the-two-ford-books)
- [Where all four stop](#where-all-four-stop)
- [The one ambiguity, left visible](#the-one-ambiguity-left-visible)

## The forks

| Fork | Generates the options | **Adjudicates** | Whose declaration |
|---|---|---|---|
| **Granularity** — split or merge a service or module | EV `transactional-boundaries-set-the-granularity-floor` (the floor) · `start-with-a-few-large-services` (direction of travel) · `choose-the-partition-axis-deliberately` | **HP §C** — `granularity-equilibrium` (six disintegrators against four integrators), then `leftover-naming-test` on the remainder | EV overlap table: *"The Hard Parts. This book gives the floor and the direction of travel and stops. It has no disintegrator/integrator analysis."* |
| **Two designs weighed against each other** | EV supplies the forces: `three-forces-of-dynamic-coupling`, the connascence ladder, `prefer-static-to-dynamic-connascence` | **HP §J** — `three-step-tradeoff-process` · `mece-the-comparison-set` · `qualitative-not-quantitative` · `least-worst-not-best` | EV overlap table: *"This book's method is 'It depends!' stated eleven ways. It supplies the forces, not the adjudication."* Khononov's `when_not` routes here too |
| **Architecture quantum · static vs dynamic coupling** | **EV, and EV alone** — `architecture-quantum` · `the-database-is-inside-the-quantum` · `ui-coupling-collapses-the-quantum` · `static-quantum-diagram-for-legacy` | **EV** — same source | EV overlap table: *"Shared, this book is sufficient. Do not re-derive them from the sibling; note the overlap and use one."* Loading HP §B as well duplicates the definition and is the named failure |
| **Cross-service transactions, sagas, eventual consistency** | — | **HP §E** — `eventual-consistency-pattern-selection` · `saga-state-machine-required` · `compensating-transaction-is-not-a-rollback` · `dont-default-to-epic-saga` | EV defers **verbatim**, Ch 5: *"covered in the book Software Architecture: The Hard Parts and is beyond the scope of this book"* |
| **Data ownership · access versus update · database type** | EV names the seven concerns and immediately cites the sibling for all of them | **HP §D** — `writes-determine-ownership` · `joint-ownership-four-techniques` · `data-access-pattern-selection` · `database-type-selection` | EV overlap table, Ch 6 |
| **Reshaping a schema that is already in production** | **EV** — `expand-contract` · `expand-contract-three-cases` · `migrations-are-immutable` · `skip-undo-migrations` | **EV** — it keeps the refactoring half explicitly | EV overlap table: *"What it keeps for itself is the refactoring half — expand/contract, migrations, stored-procedure extraction"* |
| **Storage engine · index · partition · replication · isolation level** | HP §D frames who owns the data; it does not choose the mechanism | **DDIA** — `lsm-or-btree` · `row-or-column` · `index-count` · `partitioning-scheme` · `isolation-level-selection` · `replication-architecture` | Nobody else has mechanism. HP's `database-type-selection` chooses a *type*; DDIA chooses inside it |
| **Is this rule mechanically checkable, and does it warn or block** | HP `govern-structure-automatically-not-by-review` raises the question | **EV** — `objective-outcome-or-its-not-one` · `continuous-verification-or-its-not-one` · `cadence-by-criticality` · `cascading-fitness-function` · `principles-without-enforcement` | EV overlap table: *"This book, decisively, and the sibling does not claim it. This is the whole non-duplicative contribution"* |
| **Contract strictness — strict versus loose** | HP §F `contract-type-before-contract-format` sets up the choice | **EV** — `contract-strictness-by-change-frequency` · `need-to-know-contracts` · `postels-law-for-contracts` · `consumer-driven-contracts` | EV overlap table: *"Contracts: strict vs loose → This book"* |
| **Who owns the surface · is this unit overloaded · does the boundary go here** | — | **TT** — rules 1 (domain-capacity ceiling) · 4 (four-property fitness test) · 5 (friction signals a defect) · 7 (indefinite collaboration signals a wrong boundary) · 12 · 13 · 15 (single owner) | Both Ford books defer to TT **by name**; Khononov's `when_not` names TT rules 1/12/13/15 for boundary-drawing |

## The standing rule between the two Ford books

Same lead author, overlapping vocabulary, and the sibling defers to the other by name twice.
When both fire and no row above covers it:

> **At the coupling step, load HP. At the governance step, load EV. Where both fire, EV yields
> on the decision and keeps the enforcement.**

## Where all four stop

A fork that lands here is not resolved by loading more of these four. It halts.

| Question | None of the four decides it | Where it goes |
|---|---|---|
| Subdomain classification (core / supporting / generic), integration patterns between contexts (anticorruption layer, open-host, shared kernel), where a **domain** boundary falls | Zero hits across all four extracts, confirmed by the extract audit | The language-and-boundaries door — a different job, and it does not exist yet. **Halt and say so**; do not improvise it from a component-boundary rule |
| What to build, whether the advantage is worth having | All four take the business driver as an *input* | Strategy vertical |
| Which number a person or a role answers to | All four measure systems, never organisations | The role-contract door |
| A fitness function that passes green while the thing it guards degrades | EV has **no** theory of this: `false negative` appears zero times in it | Nobody. Two EV case studies are the raw material — `measure-the-instrument-before-trusting-it` is extrapolated from a case study, not stated as a principle. Treat it as thin |
| Vendor-specific tuning (Postgres knobs, a cloud store's own patterns) | Deliberately out — the maintained vendor skill owns it | The vendor skill; extract the pattern, never fork the text |

## The one ambiguity, left visible

**Contract strictness.** EV's overlap table awards contracts to EV. HP §F nonetheless carries
`deployment-cadence-overrides-strictness`, an override with no EV equivalent: when two sides
release on different cadences, the cadence overrides what the change-frequency rule chose.

Resolution used here, and it is a reading rather than a declaration: **EV decides the
strictness; HP §F supplies the override when the deployment cadences differ.** Recorded as a
reading because the extracts do not adjudicate it themselves — if a real case shows it wrong,
this is the row to fix, and the fix belongs in the extracts' own tables.
