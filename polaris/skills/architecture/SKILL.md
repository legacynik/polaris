---
name: architecture
description: ◇ Decide one architectural commitment and emit its record — most often arriving as a move already picked and offered for a sanity check: "I was going to X, sound?", "lo adottiamo?", "procedo?", "basically free, right?". Fires when the change moves a boundary, an interface or a data contract — including when the interface does not exist yet and several genuinely different shapes should be compared before committing to one ("sto partendo da zero su X, che struttura gli do?"); when a feature needs a dependency that is not there yet, or is the Nth patch on the same thing; when a library or framework would tie you in; when a repo or its stray consumers must be folded in or migrated; when a column must be added under readers that deploy separately; when data must be reshaped, moved, or kept in step across two stores; when a query is fast until it is not; when a hot path is slow or repays the same cost every turn; when the written description of the system is stale, missing, or still names services that were deleted; when a part of the system must be judged before it is refactored — you cannot tell what a folder is for, you are afraid to touch something because you do not know what it breaks, or the question is whether this repo has architecture problems at all. Gates on reversibility before anything else — whether every caller can still change in one commit — because that answer inverts every rule after it. Not for reading or mapping a codebase with no change in view, not for a measurement wanted as a number and nothing else, not for restoring behaviour that is simply wrong, not for how-to or installation documentation, not for choosing what to build, not for the domain's own vocabulary and subdomain boundaries.
version: 0.9.2
user-invocable: true
auto: true
job: emit one decision record whose options are MECE, whose every option names what it COSTS, whose pick is the least worst, and which carries its enforcement hook and its closure check — or, before a target has been chosen, one audit report whose every finding names the simplification it enables — or, before a module exists at all, N genuinely different interface designs compared and one recommended — or halt naming the measurement that is missing and who owns getting it
when_not: mapping or reading a codebase without changing it (navigation — `code-graph`); choosing what the company should build (strategy); the domain's own vocabulary, subdomain classification and integration patterns between contexts (that is the language-and-boundaries door, and it is not this one); vendor-specific tuning where a maintained vendor skill already carries the rules
lifecycle: one typed Decision under `decisions/` per adopted commitment; `kind: architecture` is the ADR case, never a parallel `adr/` authority · a doc-arm run writes the repository-root `ARCHITECTURE.md` · a land run binds an accepted Decision to call sites, prerequisites and its executable closure check · an audit-arm run emits the report and hands each actionable finding to the arm named in its `decisione` field, which is where a record gets written · a `design` run emits a comparison and a recommendation, never a decision record — if the recommendation is then adopted, that adoption is a separate invocation of `decide` and gets its own record · every halt is written into the record it interrupted, never dropped · unmeasurable claims carry `ASSUMED` and are drained by the next run against the same `review_trigger`
invokes: [domain, critic]
invoked-by: [human]
io: "receives: a decision, accepted Decision, feature, framework, repo to fold in, schema change, hot path, system to judge, architecture document, or module that does not exist yet -> produces: the reversibility verdict and fixed-field record; a landing receipt binding Decision to call sites, prerequisites and closure check; a current ARCHITECTURE.md; an audit report; N compared interface designs; or a halt naming what is missing."
status: active
---

# architecture

## Where this goes (host repository decides)

A skill decides **how** to produce a document, never **where** it lives. Before writing any spec,
plan, audit, review, validation receipt or diagram, read the host repository's output map and use
it; a document that lands where the repository does not look was never written.

```bash
sed -n '/^outputs:/,/^[^ ]/p' _polaris/config.yml 2>/dev/null || sed -n '/^outputs:/,/^[^ ]/p' config.yml
```

This skill produces: **decision, diagram (archify architecture map beside ARCHITECTURE.md)**. Kinds: `spec` `plan` `audit` `review` `validation` `diagram` `decision` `archive` — each maps to a
documentation area `docs/modules/<area>/…` whose README is a generated map. Never invent a third
location; if the repository declares no map, say once where you wrote and why.

Emit **one** commitment, with what it costs. Not a survey of the options, not a map of the
code: the code you did not change is `code-graph`'s job, and this door only opens when
something is being committed to.

The rules are not here. They are in the audited book library, and every step below names the
exact file and rule ids it loads. **Load only what the step names — never a rule the row does not
name, however adjacent** (breach observed in the 2026-08-18 form-constancy run 2) — a step
that loads more is a step whose answer stopped being reproducible.

## Runtime route — take the shortest closed path

1. For `init`, `check` or `emit-context`, after resolving the repository snapshot the **first access
   to the checker must be the exact quick-reference command**. Reading, grepping, hashing or asking
   help from the checker before that command invalidates the run. A zero exit with every promised
   receipt field closes the run; do not run a second audit or inspect implementation to re-prove it.
2. A single decision loads Step 0, then only its router row. A single landing loads only the
   Decision, `DOMAIN.md`, the declared call sites/prerequisites and the closure command. The
   checker-first rule above does not apply to `land`: resolving and hashing those declared inputs
   before the closure command is valid.
3. Resolve resume before Step 0, arm routing or any book load. Load
   [`references/director.md`](references/director.md) only for multiple evidence lanes, multiple
   landing packets, a missing result, background work or resume. A matching sealed receipt carries
   its commitment; do not re-decide it. Never load the director for a direct command or one serial
   decision.
4. `BLOCK` and `REPLAN` are not `PASS`. A chosen target whose prerequisite probe or closure check
   is still open remains `REPLAN` or `BLOCK` in the top-level verdict.


All extract paths are relative to `references/company-os-book-library/_extract/`, and always
`DECISION-RULES.md` — never the chapter files, which are study material. Resolve that root in
order: this skill's own directory, then the repository root. **The library does not travel with
an install** — outside the repository that holds it both resolutions fail, and that is the common
case on a product repo, not an edge one.

A run that cannot load a row's rules still emits **every fixed field**: Step 0 and the census carry
the common path on their own. What it may not do is shape the record from this file's headings while
presenting it as rule-derived — that is the field failure on record (#78). Declare the loss in
`modalità` instead. An unnamed degradation is a defect, not a fallback.

## Step 0 — reversibility, before any advice

**Can every caller still change in one commit?** Answer before reading a single rule, because
the answer inverts what comes after: the same question about the same interface has two
correct and opposite answers depending on it.

`OWNED` requires **all three**. Any one failing makes it `PUBLISHED`:

| # | Condition | How it is checked |
|---|---|---|
| a | the caller set is **closed** — enumerable today, no consumer you cannot name | census script over the tree, then the graph on the survivors (below) |
| b | every caller sits in a repo you can push | list the repos the callers live in |
| c | landing them together needs no other party's release, deploy window or approval | name the parties; zero others = pass |

It is **not** "internal versus external" and **not** a count. A module inside one repo with
forty consumers fails (c) and is `PUBLISHED`. A published library with one known consumer
fails (a) — the consumers you cannot name are the whole problem — and is `PUBLISHED`.

What the verdict switches:

| | `OWNED` | `PUBLISHED` |
|---|---|---|
| Optimise for | **depth** — behaviour per unit of interface | **commitment** — what you can no longer take back |
| A smaller surface | wins: fewer methods, fewer parameters | loses: an options object that can grow beats positional parameters |
| Build the seam | at **two** adapters, never one — one adapter is a hypothetical seam | at **zero** adapters — adding it later is a breaking change |
| Wrong because | it **costs** — coupling, a seam nobody earned | it **cannot be taken back** — every observable behaviour is already a contract |

**Halt** if the answer is genuinely contested: that contest is the decision, and it is the
founder's. Record both readings and what each would cost, and stop.

`OWNED` loads [`references/interface-and-seam.md`](references/interface-and-seam.md) — depth,
the deletion test, the two-adapter rule at its valid distance. `PUBLISHED` loads
[`references/contract-and-commitment.md`](references/contract-and-commitment.md) — Hyrum's Law
as the operating premise, additive-only evolution, the full idempotency contract. No module yet
to judge? Step 0 does not apply — that is the `design` verb, below.

## Census, then verify — how any count in the output is produced

Every step that inventories code runs this shape, and the output of a step that skipped it is
not evidence:

1. **One script pass** finds the candidates — one traversal, never N graph calls for a
   counting question.
2. **The graph closes the question** on the survivors that carry the decision.
3. The verify leg's mechanism depends on how invocation happens here: a symbol graph where
   calls are symbols, name-grep across config surfaces where invocation is textual.
4. **Whatever the verify leg cannot close is marked `ASSUMED`** in the output, with the reason.
5. **Name the graph you actually reached, or declare that you reached none.** The verify leg is
   the third repo-local assumption this door makes, beside the rule library and typed
   `decisions/`, and it fails the same silent way: a census whose survivors were closed by
   grep alone reads exactly like one closed by a symbol graph. A run with no graph is still a
   valid run — every unclosed survivor ships `ASSUMED` — but it is a `ridotta` run, and
   `modalità` names which leg was missing. Counts closed by grep on a codebase with structural
   typing, dynamic dispatch or textual invocation come out low and read as certain.

Structural typing, dynamic dispatch and textual invocation all defeat import scanning. A count
produced by scanning imports, in a codebase with any of the three, comes out low and reads as
certain.

## Domain handoff — names before commitments

Before a Decision introduces or reuses a contested domain, component or context name, invoke
`domain`. It must either return the canonical term/map row or halt with the unresolved ambiguity.
Only then may this door place that stable ID in `governs`. `architecture` owns what the commitment
costs and where it lands; `domain` owns whether the name and boundary are true. Neither absorbs the
other.

## The arms — one row per trigger

Eleven rows: the plan's eight triggers, the doc arm (founder decision Q1, 2026-08-17 grill:
"primo campo = il doc layer stesso" — the doc layer is the skill's first proving field, so
writing/re-truing `ARCHITECTURE.md` is an arm, not a separate skill), and the audit arm, which
is listed first because it is the only one that runs **before** a target has been chosen:
evaluating comes before evolving, and the refactor it points at must **simplify**.

**One door, twelve verbs — never twelve skills.** The table is the router, and the verb can be
named directly: `/architecture audit <target>` · `decide` · `doc` · `feature` · `framework` ·
`migrate` · `db-expand` · `db-reshape` · `db-tune` · `hotpath` · `design` · `land`. A named verb
wins over inference; the description routes the asks that arrive without one.

Find the row, load exactly its `loads`, emit its artifact, honour its halt. Which extract
*generates* the options and which one *adjudicates* is in
[`references/routing.md`](references/routing.md) — read it at the fork, and never reassign an
adjudication it hands to a book. Where a component or module boundary — not a domain concept,
not a service granularity call — is the question at hand, load
[`references/martin-boundary-rules.md`](references/martin-boundary-rules.md) alongside the
row's own `loads`: none of the ten rows below decide *when to build a boundary at all*, only
what to do once one is being considered.

| Trigger | loads | emits | halts when |
|---|---|---|---|
| **existing system judged before a refactor** | [`references/audit-arm.md`](references/audit-arm.md) — the scope mode first (`mono`: one named surface, deep · `full`: discovery sweep over every surface, then STOP for the pick), the four-cost lens, the finding contract and the addition test; it names which of `ford-richards-hard-parts` §J 86 · 87 · 90 · 91 · 92 · 102 and 2 · 3 · 5 · 19 · 20, `ford-parsons-evolutionary-architectures` `Code-level governance — 7 rules` · `Detectors — 11 rules` · `where-to-start` · `four-reasons-not-to-build-an-evolutionary-architecture` · `static-quantum-diagram-for-legacy` · `coarse-functional-tests-before-restructuring`, and `khononov-learning-ddd` 17 each step loads | the audit report (fields in the leaf) — every finding priced in the four costs, ranked by blast radius, and carrying the **simplification** it enables; a finding whose only remedy is an addition fails the leaf's §5 and is a hypothesis, not a result | the instrument a signal needs does not exist here → `ASSUMED` plus the instrument to build, never a fabricated number |
| **architectural decision** | `ford-richards-hard-parts` §J `least-worst-not-best` · `three-step-tradeoff-process` · `mece-the-comparison-set` · `qualitative-not-quantitative` · `model-the-hard-scenario` · `bottom-line-not-evidence` · `adr-with-alternatives-and-consequences` | the decision record (fields below) | the options are genuinely balanced → a trade-off statement in business language, and the choice is the founder's (§J `tradeoff-statement-to-the-business`) |
| **new feature touching architecture** | `ford-richards-hard-parts` 18 · 20 · 27 · 9 · 97 (`hypothesis-based-analysis`) · `ford-parsons-evolutionary-architectures` `retrofit-at-the-stress-point` · `principles-without-enforcement` · `last-responsible-moment` | the decision record + the boundary the feature moves, named | the boundary is not yet under friction → `last-responsible-moment` says wait, and say so rather than building it |
| **framework or library adoption** | `ford-parsons-evolutionary-architectures` `frameworks-push-libraries-pull` · `jit-anticorruption-layer` · `pull-model-for-dependencies` · `cots-hold-integration-points-to-your-maturity` · `detector-resume-driven-development` · `detector-vendor-king` · `licence-change-detection` · `ford-richards-hard-parts` `proof-of-concept-unfamiliar-technique` | the decision record + the anticorruption layer's trigger condition | nobody has used the technique → a PoC priced on cost **and** environment before the record is final |
| **external repo folded in / migrated** | `ford-richards-hard-parts` §A `business-driver-gate` · `decomposition-feasibility-gate` · `decomposition-approach-selection` · `service-based-stepping-stone` · `ford-parsons-evolutionary-architectures` `fidelity-fitness-function` · `fidelity-cutover-gate` · `strangler-fig-with-a-fitness-function` · `coarse-functional-tests-before-restructuring` · `kleppmann-ddia` `derived-view-migration` | the decision record + the cutover gate, with the consumer inventory that must be closed first | the business driver reduces to "nothing else works" → unfundable, stop (`business-driver-gate`) |
| **DB schema expands** | `ford-parsons-evolutionary-architectures` `expand-contract` · `expand-contract-three-cases` · `migrations-are-immutable` · `skip-undo-migrations` · `schemas-tested-versioned-incremental` · `kleppmann-ddia` `relationship-shape` · `schema-field-addition` · `index-count` · `ford-richards-hard-parts` 30 · 32 · 45 · 65 | the decision record + the expand/contract sequence, each phase with its own gate | the new field must be mandatory → that breaks backward compatibility during the rollout; the expansion is not additive and needs its own decision |
| **data reshaped or moved** | `kleppmann-ddia` `derived-view-migration` · `never-dual-write` · `audit-your-derived-data` · `log-compaction-for-bootstrap` · `ford-richards-hard-parts` §D `writes-determine-ownership` · `never-reach-into-another-database` · `data-decomposition-balance` · `schema-migration-downtime-choice` · `ford-parsons-evolutionary-architectures` `no-shared-database-integration` · `migrate-method-from-database` | the decision record + the system of record, named, and the derived views that follow from it | the only available path is a dual write → say plainly that the expensive path was chosen, and what detects the divergence |
| **query or index tuned** | `kleppmann-ddia` `row-or-column` · `lsm-or-btree` · `index-count` · `secondary-index-placement` · `partitioning-scheme` · `hot-key-handling` · `isolation-level-selection` · `ford-richards-hard-parts` 38 · 39 · 41 · 43 | the decision record + the named query pattern that justifies the index | the measurement the rule needs does not exist → acquiring it is the first task, and the record says so instead of guessing (`ASSUMED` is not a substitute here) |
| **backend hot path optimised** | `ford-richards-hard-parts` 22 · 23 · 40 (`protocol-change-is-not-decoupling`) · 64 · 70 · `ford-parsons-evolutionary-architectures` `mechanical-sympathy` · `derive-thresholds-from-production-not-estimates` · `kleppmann-ddia` `hot-key-handling` · `exactly-once-mechanism` | the decision record + the threshold, derived from production | the fix is "switch protocol" → that changes no coupling at all; reopen the real dependency |
| **architecture doc written or re-trued** | [`references/doc-arm.md`](references/doc-arm.md) — the emitted artifact's contract and the per-repo section menu | repository-root `ARCHITECTURE.md` to that contract, **and the archify map regenerated beside it** — `scripts/arch_diagram.py` derives every box, region, edge and `esiste / solo spec` tag from `DOMAIN.md`, `ARCHITECTURE.md` and the Decision register, so nothing on that map is typed by hand | a count cannot be closed by the verify leg → it ships marked `ASSUMED`, never as a bare number |

Rules that decide **who owns** the surface — is this unit overloaded, does the boundary go
here — are `skelton-pais-team-topologies` rules 1 · 4 · 5 · 7 · 12 · 13 · 15. Both Ford books
defer to it by name; do not reconstruct it from their summaries.

## The `land` verb — make an accepted Decision real

`/architecture land <Decision>` runs after adoption, never before it. Resolve every
`call_sites[]` entry against the component paths in `DOMAIN.md`, verify every prerequisite is
closed on its live authority or explicitly blocking, then execute the declared `closure_check`.
For `issue:` prerequisites, query the live tracker; local prose is not closure evidence and an
unavailable tracker adapter is `BLOCK`. Missing call sites, unknown component/domain scope, a stale
live document or a failed closure check also emits `BLOCK` and no executable ContextPack. The
landing receipt records Decision ID, call sites, prerequisite verdicts, closure command, exit code,
source hashes and `modalità` — `piena`, or `ridotta` naming every input that was missing, same
field and rule as the decision record's.
Direct landing is serial: call sites are evidence, not worker lanes. Its receipt leaves write-wave
selection, deferral and merger-ownership fields empty unless multiple landing packets were
explicitly declared and the director was loaded.

Approval alone is not landing. A Decision whose old call path still runs remains open even when
its prose says `accepted`. Before returning `PASS`, sweep the repository's status-bearing legacy
authority registers (currently `adr/`) for another `accepted` record governing the same call sites.
`decisions.md` is a hash-audited history/projection: never infer acceptance from its prose. An
undeclared or conflicting legacy authority is `REPLAN`; migrate or explicitly supersede and seal it.

## The `design` verb — before a caller exists

The eleventh row is not in the table above because it isn't a decision about something that
already exists — there is no interface yet, so Step 0 has nothing to judge. `design` fires when
a module, service, or interface is being built from scratch and the ask is which shape to give
it, including the symptom-phrased form: "sto partendo da zero su X, che struttura gli do?".

Loads [`references/design-verb.md`](references/design-verb.md): frame the problem space, spawn
3+ sub-agents with genuinely divergent constraints (minimize the interface · maximise
flexibility · optimise the common case · take inspiration from a named precedent), present each
design, compare on depth/locality/seam placement per
[`references/interface-and-seam.md`](references/interface-and-seam.md), then recommend one.

Emits a comparison and a recommendation — **never** a decision record. If the recommendation is
then adopted, that adoption is its own `decide` invocation once real callers exist to judge
`OWNED` vs `PUBLISHED` against.

## What every arm emits

Fixed fields. A record missing one is incomplete output, not a draft. The field NAMES are
deliberately Italian — typed Decisions may keep the narrative fields in Italian, and
`eval/checks.json` greps these exact strings; renaming them is a contract change, not a
translation:

| Field | Means |
|---|---|
| `reversibilità` | `OWNED` or `PUBLISHED`, with which of the three conditions decided it |
| `opzioni` | MECE — mutually exclusive, collectively exhaustive. Two options that overlap are one option written twice |
| `costo per opzione` | what each one **costs**, not what it buys. An option with no cost stated is a defective option |
| `scelta` | the least worst combination of trade-offs. Never "the best design" — there isn't one |
| `enforcement` | what mechanically notices a violation, and where. Always red plus a comment, never blocking, outside CI's own gates and the AFK pipeline |
| `verifica di chiusura` | the predicate, declared **before** the work, mechanically checkable, executed by something that is not the founder |
| `modalità` | `piena`, or `ridotta` naming every input that was missing — the rule library, typed `decisions/`, a domain glossary, the graph verify leg — and where the record was written instead. A degraded run that does not say so is a defect. **First line is a structured, machine-checkable summary**: `modalità: piena` or `modalità: ridotta — missing: <tag>[, <tag>...]`, tags from `rule-library` · `decisions` · `glossary` · `graph-verify`; prose explaining each one follows below it. A free-form paragraph alone, without the tagged first line, does not satisfy this field — that ambiguity (what markup, which line, is this the field or a mention of it) is exactly what let a bare declaration through undetected (#78, critic F5/F6/F7) |
| `ASSUMED` | every claim the verify leg could not close, each with its reason |

Every adopted commitment becomes one typed Decision under `decisions/`. `kind: architecture`
preserves the ADR classification without creating another authority.

**Where `decisions/` does not exist, the repository's own declared convention wins.** Write the record
where that repository already keeps its durable choices — `docs/adr/` plus a projection is a real
case — name that location in `modalità`, and never backfill existing records into a shape this
repository did not ask for. Introducing `decisions/` where another authority already runs is a
migration with its own reversibility question, never a side effect of writing one record.

**One decision does not qualify as done because it was signed.** A record that supersedes a
running mechanism is done when every existing call site has moved, and the closure check is
what proves it — an approved record whose hot path still runs the old way is the most
expensive failure this door exists to stop.

## When NOT to use it

- **Reading or mapping a codebase with no change in view.** That is navigation: `code-graph`
  decides when the graph beats direct reading. The audit arm is not the exception it looks
  like — it opens only when a refactor is the point of asking, and its output is findings that
  each name a simplification and route to an arm. A walkthrough, an orientation, or a number
  wanted as a number is `code-graph`'s, and the description is kept narrow so it stays there.
- **Deciding what to build.** Diagnosis, crux, what gets starved: the strategy vertical. None
  of the 345 rules in here decides that, and all three sources say so in their own `when_not`.
- **The domain's vocabulary, subdomain classification, integration patterns between
  contexts.** A different trade — a choice there is wrong because it is **false**, here
  because it **costs**. Two correctness criteria, two doors. If the question is "do these two
  concepts belong in the same model?", stop and say so.
- **Vendor-specific tuning.** Vendor skills are maintained by the vendor: extract the
  pattern, never fork the text.
- **A patch on a production symptom whose root is not architectural.** That is the `bugfix`
  door. If the root *is* architectural, both lanes start.

## Quick reference

| command | when | blocks? |
|---|---|---|
| `python3 scripts/detect.py <import-root> --json` | the audit arm's mechanical leg, always first | no — produces candidates, never recommendations |
| `python3 scripts/<census>.py` (one pass) | any count in the output | no — produces candidates |
| graph lookup on the survivors | close the question on the candidates that decide | no — whatever does not close becomes `ASSUMED` |
| `lint-imports` / the repo's layer contract | the record's enforcement hook | yes, where already installed |
| `python3 scripts/check_absorption.py` | verifies `references/absorption-checklist.md`'s 26 rows each have a real anchor | yes — exit 1 names the missing item |
| `python3 scripts/shingle_check.py` | verifies zero 12-word runs shared between `martin-boundary-rules.md` and the Martin skill's chapter files | yes — exit 1 on the first match, with line number |
| `python3 scripts/arch_diagram.py --from DOMAIN.md --out docs/modules/<area>/diagrams/<name>.architecture.json [--check-delivery]` | the doc arm, whenever `DOMAIN.md`, `ARCHITECTURE.md` or a Decision's status changes | no — but CI regenerates, diffs it and, with `--check-delivery`, refuses an HTML rendered from older bytes, so a map edited by hand is red |
| `node <archify>/bin/archify.mjs deliver architecture <json> <html> --quality showcase --json` | turn that JSON into the delivered map — always after the generator, never instead of it | yes — showcase acceptance is 9/9 artifact checks, 0 composition errors, 0 warnings, and CI then checks the HTML shows every string the JSON asserts |
| `python3 -I scripts/check_context_backbone.py --init <repo>` | run directly; its receipt includes `verdict: READY` plus `kind: PROMOTED|NOOP`, and unchanged input returns the same three seals | yes — audit, scope and freshness must be `READY` before the manifest write |
| `python3 -I scripts/check_context_backbone.py --check .` | run directly; validates the three live docs plus scoped Decision landing contract | yes — stale/unknown/conflicting sources block |
| `python3 -I scripts/check_context_backbone.py --reseal .` | merger-only after governed sources integrate; deterministically regenerates live-document/Decision seals and the manifest | yes — rolls back every derived write if final validation fails |
| `python3 -I scripts/check_context_backbone.py --emit-context <repo> --work-item <declared-id>` | run directly; alias of the production resolver `scripts/contextpack.py` — one implementation, one seal, held by a parity test, so neither entry point is the second authority; seals a real work item already cited by an applicable accepted Decision | yes — undeclared work items return `WORK_ITEM_UNVERIFIED` |

Bypass-test: [`references/bypass-test.md`](references/bypass-test.md).
