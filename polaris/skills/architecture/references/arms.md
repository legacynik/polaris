# The arms — which trigger loads which rules, and the `land` verb

Loaded by `decide`, `land` and every symptom that arrives without a verb. The table is the
router: find the row, load exactly its `loads`, emit its artifact, honour its halt.

The rows are **not** verbs. `feature`, `framework`, `migrate`, `db-expand`, `db-reshape`,
`db-tune` and `hotpath` are the triggers `decide` routes on once it has fired:
`/architecture decide "this query is fast until it is not"` is the interface, and this table is
how that ask finds its rules. Rule files are named by subject; [routing.md](routing.md) maps each
subject to its file and says which file adjudicates at a fork. Where a component or module
boundary — not a domain concept, not a service granularity call — is the question, load the
component-boundary rules [decision-rules/component-boundary.md](decision-rules/component-boundary.md) alongside the row's
own `loads`: the rows decide what to do once a boundary is being considered, the component rules
decide *when to build one at all*.

| Trigger | loads | emits | halts when |
|---|---|---|---|
| **existing system judged before a refactor** | [audit-arm.md](audit-arm.md) — scope mode first (`mono`: one named surface, deep · `full`: discovery sweep, then STOP for the pick), the four-cost lens, the finding contract and the addition test; it names the rules each step loads | the audit report — every finding priced in the four costs, ranked by blast radius, carrying the **simplification** it enables; a finding whose only remedy is an addition fails §5 and is a hypothesis | the instrument a signal needs does not exist here → `ASSUMED` plus the instrument to build, never a fabricated number |
| **architectural decision** | decomposition §J `least-worst-not-best` · `three-step-tradeoff-process` · `mece-the-comparison-set` · `qualitative-not-quantitative` · `model-the-hard-scenario` · `bottom-line-not-evidence` · `adr-with-alternatives-and-consequences` | the decision record ([record.md](record.md)) | the options are genuinely balanced → a trade-off statement in business language, and the choice is the repo owner's (decomposition `tradeoff-statement-to-the-business`) |
| **new feature touching architecture** | decomposition 18 · 20 · 27 · 9 · 97 · 102 `hypothesis-based-analysis` · governance `retrofit-at-the-stress-point` · `principles-without-enforcement` · `last-responsible-moment` | the decision record + the boundary the feature moves, named | the boundary is not yet under friction → `last-responsible-moment` says wait; say so rather than building it |
| **framework or library adoption** | governance `frameworks-push-libraries-pull` · `jit-anticorruption-layer` · `pull-model-for-dependencies` · `cots-hold-integration-points-to-your-maturity` · `detector-resume-driven-development` · `detector-vendor-king` · `licence-change-detection` · decomposition `proof-of-concept-unfamiliar-technique` · component-boundary 10 | the decision record + the anticorruption layer's trigger condition | nobody here has used the technique → a proof of concept priced on cost **and** environment before the record is final |
| **external repo folded in / migrated** | decomposition §A `business-driver-gate` · `decomposition-feasibility-gate` · `decomposition-approach-selection` · `service-based-stepping-stone` · governance `fidelity-fitness-function` · `fidelity-cutover-gate` · `strangler-fig-with-a-fitness-function` · `coarse-functional-tests-before-restructuring` · data-systems `derived-view-migration` | the decision record + the cutover gate, with the consumer inventory that must be closed first | the business driver reduces to "nothing else works" → unfundable, stop (`business-driver-gate`) |
| **DB schema expands** | governance `expand-contract` · `expand-contract-three-cases` · `migrations-are-immutable` · `skip-undo-migrations` · `schemas-tested-versioned-incremental` · data-systems `relationship-shape` · `schema-field-addition` · `index-count` · decomposition 30 · 32 · 45 · 65 | the decision record + the expand/contract sequence, each phase with its own gate | the new field must be mandatory → that breaks backward compatibility during the rollout; the expansion is not additive and needs its own decision |
| **data reshaped or moved** | data-systems `derived-view-migration` · `never-dual-write` · `audit-your-derived-data` · `log-compaction-for-bootstrap` · decomposition §D `writes-determine-ownership` · `never-reach-into-another-database` · `data-decomposition-balance` · `schema-migration-downtime-choice` · governance `no-shared-database-integration` · `migrate-method-from-database` | the decision record + the system of record, named, and the derived views that follow from it | the only available path is a dual write → say plainly that the expensive path was chosen, and what detects the divergence |
| **query or index tuned** | data-systems `row-or-column` · `lsm-or-btree` · `index-count` · `secondary-index-placement` · `partitioning-scheme` · `hot-key-handling` · `isolation-level-selection` · decomposition 38 · 39 · 41 · 43, then [the measurement loop](#the-measurement-loop--query-and-hot-path) | the decision record + the named query pattern that justifies the index | the measurement the rule needs does not exist → acquiring it is the first task, and the record says so instead of guessing (`ASSUMED` is not a substitute here) |
| **backend hot path optimised** | decomposition 22 · 23 · 40 `protocol-change-is-not-decoupling` · 64 · 70 · governance `mechanical-sympathy` · `derive-thresholds-from-production-not-estimates` · data-systems `hot-key-handling` · `exactly-once-mechanism`, then [the measurement loop](#the-measurement-loop--query-and-hot-path) | the decision record + the threshold, derived from production | the fix is "switch protocol" → that changes no coupling; reopen the real dependency |
| **architecture doc written or re-trued** | [doc-arm.md](doc-arm.md) — the document's contract and the per-repo section menu | repository-root `ARCHITECTURE.md` to that contract, plus the derived map where the repository declares a generator | an invariant cannot be shown true today → it goes to *Known limits* as a target; a sentence an ordinary feature PR would falsify (a count, a `file:line`, a version) → it leaves the document for a command in *Keeping this document true* |

Rules that decide **who owns** the surface — is this unit overloaded, does the boundary go
here — are ownership rules 1 · 4 · 5 · 7 · 12 · 13 · 15. Load them by number; decomposition and
governance both hand that question to them.

## The measurement loop — query and hot path

The two performance rows share one loop, and each turn of it is evidence the record cites:

1. **Measure** the baseline with the instrument production already trusts — query timing, the
   request trace, the profiler — on real data or a production-shaped copy. A number from a
   local toy dataset is `ASSUMED`.
2. **Identify** the one bottleneck the measure points at, by name (this query plan, this call,
   this lock). A fix aimed at a suspected bottleneck is a guess with a diff attached.
3. **Fix** that bottleneck and nothing else in the same change, so the next measure is
   attributable.
4. **Verify** with the same instrument and the same load. Keep the change only when the number
   moved past the noise of repeated runs; otherwise revert it — an unmeasured optimisation is
   complexity with no matching benefit.
5. **Guard** the gain with a check that goes red when it regresses (a timing budget in a test, a
   query-count assertion, an alert threshold derived from production). That check is the
   record's `enforcement`.

## The `land` verb — make an accepted Decision real

`/architecture land <Decision>` runs after adoption, never before it. Resolve every
`call_sites[]` entry against the component paths in `DOMAIN.md`, verify every prerequisite is
closed on its live authority or explicitly blocking, then execute the declared `closure_check`.
For `issue:` prerequisites, query the live tracker; local prose is not closure evidence and an
unavailable tracker is `BLOCK`. Missing call sites, unknown component/domain scope, a stale live
document or a failed closure check also emits `BLOCK` and no executable ContextPack. The landing
receipt records Decision ID, call sites, prerequisite verdicts, closure command, exit code, source
hashes and `modalità` — `piena`, or `ridotta` naming every input that was missing, same field and
rule as the decision record's.

Direct landing is serial: call sites are evidence, not worker lanes. Its receipt leaves
write-wave selection, deferral and merger-ownership fields empty unless multiple landing packets
were explicitly declared and [director.md](director.md) was loaded.

Approval alone is not landing. A Decision whose old call path still runs remains open even when
its prose says `accepted`. Before returning `PASS`, sweep the repository's status-bearing legacy
registers (for example `adr/`) for another `accepted` record governing the same call sites. A
narrative decisions log is history, never acceptance evidence. An undeclared or conflicting
legacy authority is `REPLAN`: migrate it or supersede it explicitly.

### Retiring the old path

When the Decision replaces a running mechanism, landing **is** the migration, and it closes in
this order:

1. **The replacement covers every critical use of the old path and runs in production** before
   any caller is moved. Moving callers onto something unproven trades one risk for two.
2. **Migrate caller by caller.** For each call site: find every touchpoint, switch it, verify the
   behaviour matches, delete the old reference. Pick the shape by what the callers can bear —
   route traffic gradually from old to new (strangler), keep the old interface over the new
   implementation (adapter), or switch per caller behind a flag — and name the shape in the
   receipt.
3. **The owner of the old path moves its callers.** Announcing a deprecation and leaving callers
   to migrate themselves leaves the old path running indefinitely; a compulsory deadline is
   justified only by a security or maintenance cost, and it ships with the migration tooling.
4. **Remove only after usage is proven zero** — by the census over the tree and, where the old
   path is called at runtime, by logs or metrics. Then delete the code, its tests, its
   configuration and its documentation in one change. The closure check is that zero, measured.
5. **A schema behind the old path follows the expand/contract rules** (governance
   `expand-contract`): additive first, the destructive drop in its own later deploy, after no
   code reads the old shape.

Code with live callers and no owner is the case this order exists for: give it an owner and a
migration, or a record that keeps it on purpose. It does not stay in between.
