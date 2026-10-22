# The audit arm — judge it before you refactor it

Load this only when the trigger is *how is this part of the system doing, before we change it*.
It is not loaded by any other arm.

The arm exists because the other nine start after the target is chosen. This one chooses the
target, and it is the only arm whose output is a **verdict on code nobody has committed to
changing yet** — which is why the bar below is stricter than everywhere else in this door.

**The bar, and it is not negotiable.** The purpose of evaluating is to *simplify*. A finding
whose remedy makes the system bigger — a new layer, a new service, a new abstraction, a new
config surface — is a **defect of the audit**, not a result of it, until it clears both the
reversibility gate in `SKILL.md` and §5 below. Refactor-to-simplify is the whole point; an
audit that grows the system has answered a question nobody asked.

## Contents

- [0. Scope before you scan](#0-scope-before-you-scan)
- [1. The four costs — the lens every finding is priced in](#1-the-four-costs--the-lens-every-finding-is-priced-in)
- [2. Where to start](#2-where-to-start)
- [3. The sweep — what is measured, and what it costs when it cannot be](#3-the-sweep--what-is-measured-and-what-it-costs-when-it-cannot-be)
- [4. The two phases, and the report](#4-the-two-phases-and-the-report)
- [5. The addition test](#5-the-addition-test)
- [6. Halts](#6-halts)
- [7. Composing the rules that pull against each other](#7-composing-the-rules-that-pull-against-each-other)

## 0. Scope before you scan

A flat full-repo sweep is the wrong first move: deepening a module pays off on *future*
changes to it, so attention goes where change actually lands.

1. **The user named a direction** — a package, a subsystem, a pain point. Take it, skip the
   rest of this section. A named direction always wins.
2. **Otherwise, let the hot spots pull.** Walk back a good stretch of `git log --oneline
   --name-only` and let the files that keep coming up take attention first. Scattered history
   with no hot spot → widen the net, and say that you did.
3. **Read the repository-root `ARCHITECTURE.md` first when it exists.** Its last commit is the
   last state anyone audited; **everything that moved since is the first place to look, and the
   drift itself is usually finding number one.** Its `review_trigger` list tells you which
   changes were supposed to force an update — one that fired without an update is a finding
   about the document as much as about the code. When the file is **absent**, say so and
   recommend the **doc arm** before or alongside the audit: auditing a system nobody has
   described means re-deriving the description inside every future audit.
4. Read the domain glossary (`CONTEXT.md`) and the Decisions or ADRs covering the area before
   forming a single candidate. `git log` says where the heat is; the records say what was already
   settled.

**Vocabulary, and it is a hard rule.** The system is described in **its own domain language**
— the words in `CONTEXT.md`. The design vocabulary (module, seam, depth, adapter, leverage,
locality) is scaffolding for the conversation and **never becomes an artifact**: name a finding
in the domain's words, because "component", "service", "API" or "boundary" each smuggle in a
solution shape before the candidate has been picked.

## 1. The four costs — the lens every finding is priced in

A structure is not good or bad in the abstract —
it is expensive or cheap at four separate jobs, and a finding that does not name which one it
inflates is an aesthetic complaint.

| Cost | The question it answers | Why it is its own column |
|---|---|---|
| **sviluppo** | can someone add to this without coordinating with everyone who touches it? | a layout that suits one author suits nobody at four; this cost only appears when a second person arrives |
| **deploy** | how many units must ship together for one change to be live? | the number is the count of things that must move in lockstep, never the count of files |
| **esercizio** | what does it cost to run, and does it fail where you can see it? | **the cheapest of the four to buy out of** — hardware is cheaper than a restructuring, so a finding priced *only* here is the weakest refactor case in the set |
| **manutenzione** | split in two: **spelunking**, what it costs to find where a change goes; and **rischio**, the chance the change breaks something nobody looked at | the dominant cost, because it is paid on every change forever, and the split decides the remedy |

Two rules fall straight out of it, and they do most of the arm's work:

- **Escalation order: manutenzione > sviluppo > deploy > esercizio.** Two findings competing
  for the same refactor budget are ranked by the highest column each inflates, never by how
  offensive the code looks.
- **The spelunking/rischio split names the remedy.** Spelunking is cured by a seam a reader
  can name — the split. Rischio is cured *before* the split, by coarse functional tests around
  the behaviour (`coarse-functional-tests-before-restructuring`); a restructuring proposed with
  no such test is a finding that inflates rischio while claiming to reduce it.

## 2. Where to start

Governance `where-to-start` gives two defensible first targets
and they are chosen by **what you need to prove**, not by what is worst: *low-hanging fruit*
when the approach itself is still doubted, *highest value first* when it is already committed
and the question is whether the techniques survive contact with this ecosystem. Either way the
same rule applies — gather the metric before **and** after, or the refactor has no evidence it
worked.

Its own stop condition outranks the audit: if deployment is intractable, that is the finding,
and every structural finding under it is academic until it moves.

Before any of that, governance `four-reasons-not-to-build-an-evolutionary-architecture` is a
live exit.
A big ball of mud where rework costs more than rewrite, a system deliberately sacrificial, a
dominant conflicting characteristic — each is a legitimate reason for the audit to conclude
**do nothing structural**, and saying so is a result, not a failure to find one.

## 3. The sweep — what is measured, and what it costs when it cannot be

Every row runs the census-then-verify shape from `SKILL.md`: one script pass finds the
candidates, the graph closes the question on the survivors. **Every row also has a
precondition, and most of them are a tool that may not exist in this repo** — that is the
arm's most frequent halt, and the honest output is `ASSUMED` plus the instrument to build,
never a number that looks measured.

**Run the mechanical leg first, always.** `scripts/detect.py` is the script pass: one AST
traversal, stdlib only, no LLM and no API key, so it is cheap enough to re-run and stable
enough to diff between audits.

```bash
python3 scripts/detect.py <import-root> --json     # <import-root>, not the package — see below
```

It emits four rules and nothing else: `cycle` (Tarjan SCC over the import graph),
`package-size` (statements per package, outliers past mean + 2σ — statements, because
decomposition 19 rejects file count as a size metric), `instability` (Ce, Ca and
`I` for the modules pinned at 0 or 1), and `abstractness`, **which usually refuses**: with too
few explicit `ABC`/`Protocol` declarations, `A` collapses to ~0 and `D = |A+I−1|` merely
restates `I`, so it reports `ASSUMED` with the instrument instead of a number. That refusal is
the script's most important behaviour, not an edge case.

- **Point it at the import root**, the directory on `sys.path` — not at the package inside it.
  Give it the package and every intra-repo edge resolves to nothing and the graph comes back
  empty of cycles, which reads exactly like a clean codebase.
- **Ignores from day one**: `<root>/.architecture/detect.json` with `ignoreRules` and
  `ignorePaths`, plus an inline `arch-detect: ignore [rule ...]` comment in a module's first 20
  lines. A waived rule is a decision someone took; a detector with no waiver mechanism gets
  switched off wholesale the first time it is wrong.
- **Deferred rules, named rather than implied**: import-direction and layer-access contracts
  (needs a declared contract file), LCOM, cyclomatic complexity thresholds, per-module churn
  from `git log`, and the static quantum diagram. The arm computes these by hand when a finding
  turns on them, and the reference says so instead of pretending the script covers them.
- The script produces **candidates, never recommendations**, and it says so on stderr. What it
  finds still has to be priced, verified on the graph, and passed through §5.

### The named tells

Short list, each mapped to what settles it. A tell is a hypothesis (`102`), never a finding.

| Tell | Settled by |
|---|---|
| a `services/`- or `utils/`-shaped package that is a layer name holding many unrelated domains | `detect.py package-size`, then the `leftover-naming-test` on the proposed residue |
| a cycle that runs out through the API or transport layer and back | `detect.py cycle` — a cycle of N is one deployable unit of N, whatever the tree says |
| an adapter, port or interface with exactly one implementation | judgment: the two-adapter rule in `SKILL.md`, and it is only a defect under `OWNED` |
| ports that mirror the database tables one-for-one | judgment: domain-strategy 17 plus the model-fit read — the seam was cut on storage, not on behaviour |
| a module pinned at `I = 1.0` that everything else avoids | `detect.py instability`, then `abstractness` to tell **stable** from **rigid** — and it usually cannot, which is the honest answer |
| a config flag or parameter no live caller ever sets | judgment: census the call sites, then close on the graph |

| Signal | Rule | Reads as |
|---|---|---|
| `D = \|A + I − 1\|` from abstractness and instability | `distance-from-main-sequence`, with `read-instability-and-abstractness-together` | the zone, not the number. Low `I` is **stable** if mostly abstract and **rigid** if mostly concrete, and the two have opposite remedies. **Do not migrate a component in the zone of pain — repair it in place first** |
| import direction, layer access | `directionality-of-imports` · `layer-access-rules-as-code` | a rule that lives in a guideline instead of a check is a rule already being broken; the finding is the missing check, not the violation |
| dependency cycles between components | `archunit-governable-relationships` (1) | the auto-import affordance creates these silently; a cycle of N is one deployable unit of N, whatever the directory tree says |
| cyclomatic complexity | `cc-threshold` | a gate, and its stop matters more than its number: if the whole codebase fails the threshold, **do not lower the threshold** |
| cohesion of a class two units both want | `lcom-before-splitting-a-shared-class` | high LCOM → it was never one class, split it. Low LCOM and no appetite for sharing or replicating → **the boundary is in the wrong place**, move the boundary |
| component size | decomposition 19 `size-by-statements-not-classes` | statements and exposed operations. **File count is not a size metric** — and its stop is the anti-overengineering guard in rule form: a large outlier with **no clear sub-domains is left alone**. Splitting on size alone is not licensed |
| what a split would leave behind | decomposition 20 `leftover-naming-test` | if the remainder cannot be given a self-descriptive name, the split is wrong. The same test read forward: a top-level listing that names frameworks and layers instead of what the system *does* is a finding about the layout, not about the frameworks |
| call frequency between units | domain-strategy 17 `chatty-contexts-signal-a-wrong-model` | a **model defect**, never a performance problem. Caching, batching or co-locating hide the signal; the endpoint of ignoring it is a distributed monolith |
| how it is actually wired, operations included | `static-quantum-diagram-for-legacy` | what a change will break — the source tree alone does not show it |

The eleven governance detectors are read over the same evidence and answer a different question — *why
is it like this* — and two of them, `detector-resume-driven-development` and
`detector-vendor-king`, are the ones that explain a finding the metrics cannot.

The adjudication is decomposition §J: `86 least-worst-not-best`,
`87 three-step-tradeoff-process`, `90 mece-the-comparison-set`, `91 find-the-narrow-context`,
`92 model-the-hard-scenario`, `102 hypothesis-based-analysis`. **`91` is what stops the sweep
turning into a survey**: narrow the context before comparing, or every finding gets the same
generic answer. **`102` is what stops it turning into a wish list**: state the hypothesis, then
go find the evidence that would falsify it, rather than collecting evidence for a conclusion
already picked. Where the remedy is a decomposition, `2 decomposition-feasibility-gate`,
`3 decomposition-approach-selection` and `5 build-services-from-components` decide whether it
is even fundable — and `5` refuses the question outright until the components are named.

## 4. The two phases, and the report

**Phase 1 emits the candidate set and stops.** It does not design solutions, does not propose
interfaces, does not pick the seam. It ends on the question — *which of these do you want to
explore?* — and waits. The stop is the point: a run that designs the remedy for eight
candidates has spent seven candidates' worth of thinking on work nobody chose, and it anchors
the founder on whichever one was written up most fluently.

**Phase 2 takes the picked candidate into the decision ceremony of this same door** — the
`architectural decision` arm, with its reversibility gate, its MECE options, its cost per
option and its closure check. The audit hands over; it does not decide.

Each candidate in phase 1 is a card with a fixed shape — `Files` · `Problem` · `Solution` in
plain language · `Benefits` · `Before / After` · **recommendation strength**, one of
`Strong` · `Worth exploring` · `Speculative`. The badge is not decoration: it is the companion
to `gravità`, and it is what lets a founder skip nine cards and read one. End with the single
candidate you would take first, and why.

**Conflicts with a standing record.** Surface a candidate that contradicts a standing Decision **only when the friction
is real enough to justify reopening it**, and mark it as what it is — *contradicts DEC-…,
worth reopening because…*. Leave out the refactors a standing record already forbids: listing
them re-presents things already decided as findings.

The report below is the durable artifact of both phases. Fixed fields, exactly like a decision
record: a report missing one is incomplete output, not a draft. The field names are Italian,
for the same reason the decision record's are: `eval/checks.json` greps them.

**Scope mode, chosen before anything is read.** A disciplined perimeter finds the deep findings
and misses real candidates outside it; a sweep finds those and verifies nothing. The mode decides
which one this run is:

**Budget gate, before discovery:** `mono` is the default. `full` is `BLOCK` when the current
work item or request already identifies at least three unlanded architecture findings; do not
recount them or open another backlog. One allowed `full` run may promote at most three findings;
the remainder stays unpromoted evidence.

- **`mono`** — the caller named a surface. Exactly the current behaviour: one perimeter, deep,
  everything outside declared unexamined. The default whenever the request points somewhere.
- **`full`** — the caller asked for the whole system, or named nothing on a repo with more
  than one deployable/surface. Step zero is a **discovery sweep**: enumerate the surfaces
  (backend, each frontend, workers, ops/deploy, migrations, tests-as-mass) with one cheap
  roaming pass each — file counts, obvious tells, no verify leg, everything `ASSUMED` — then
  emit the surface list ranked by signal and STOP for the pick. The deep pass runs per picked
  surface as `mono`. Never N blind deep runs; the sweep is discovery, not audit, and its
  findings do not enter the report unverified.

**Header, once:**

| Field | Means |
|---|---|
| `scope` | `mono` or `full`, and — under `full` — the surface list the sweep produced, each with its one-line signal |
| `perimetro` | the directories read, and the commit SHA they were read at. What is outside is **unexamined**, not fine — say which |
| `strumentazione` | which signals in §3 could actually be measured here and which could not, listed before any finding, so the reader knows what the silence covers |
| `modalità` | `piena`, or `ridotta` naming every input that was missing — the rule library, typed `decisions/`, a domain glossary, the graph verify leg — same field, same rule, as the decision record's: a degraded audit that does not say so is a defect, not a draft. Same structured first line as the decision record's: `modalità: piena` or `modalità: ridotta — missing: <tag>[, <tag>...]` (`rule-library` · `decisions` · `glossary` · `graph-verify`), prose below it |

**Per finding, repeated:**

| Field | Means |
|---|---|
| `reperto` | what it is, one sentence, no adjective that is not a measurement |
| `evidenza` | the census number **and** the leg that closed it. A number from one script pass with no verify leg is `ASSUMED`, not evidence |
| `costo` | which of the four columns in §1 it inflates — and for `manutenzione`, whether spelunking or rischio, because that picks the remedy |
| `gravità` | **blast radius**: how many units a change here forces to move. Not a severity word — a count, or `ASSUMED`. Its companion is the strength badge from §4: `Strong` · `Worth exploring` · `Speculative`, which says how sure you are, where `gravità` says how much it costs |
| `semplificazione` | **what this lets you DELETE or SPLIT.** The field that makes the finding worth having. If it can only be filled with something to add, §5 applies |
| `decisione` | which arm of this door it hands to, named, or `nessuna` — a finding that routes nowhere is a note, and it should say so rather than posing as work |
| `ASSUMED` | every claim the verify leg could not close, with its reason |

A finding whose `semplificazione` and `decisione` are both empty does not go in the report. It
goes in one line at the end, under *noted, not actionable* — that list is short on purpose.

## 5. The addition test

Applied to **every** recommendation before it is written down:

> Does this DELETE code, or SPLIT one thing into two along a seam a reader can name — or does
> it ADD a layer, an indirection, a service, a flag?

Deletion and splitting pass. An addition passes only when **all three** hold, and the report
states all three:

1. the reversibility verdict in `SKILL.md` was taken first, and the addition survives it;
2. the addition removes a **named, priced** cost from §1 that is larger than the cost it adds
   — stated as both numbers, not as a direction;
3. the thing it replaces is deleted in the same change. An addition that leaves the old path
   running is two paths, and two paths is the most expensive finding in this file.

Fails any one → it is not a recommendation, it is a hypothesis, and `102 hypothesis-based-analysis`
says what to do with it: name the evidence that would settle it, and stop.

## 6. Halts

- **The instrument a signal needs does not exist here.** Most of §3 presumes a metrics tool
  bound to the platform. Ship `ASSUMED` naming both what could not be measured and the
  instrument that would close it. **Never a fabricated number** — a plausible metric is worse
  than a stated gap, because a gap gets filled and a wrong number gets cited.
- **The target is contested** — two readings of where the seam is, two candidates for what the
  package is *for*. That is a decision, not an audit: run the matching arm and come back.
- **The finding's root is behavioural, not structural.** That is the `bugfix` door. If it is
  both, both lanes start, and the report says which.
- **Nothing found that can be deleted or split.** A valid verdict, delivered as one. Padding an
  audit with additions to make it look productive is the exact failure this arm was added to
  prevent.

## 7. Composing the rules that pull against each other

Five places where the loaded rules give **opposite answers depending on which one an audit
happens to reach first**. Each is composed here, once, so the answer does not depend on reading
order. A finding that lands on one of these says which composition it used.

**A. Independent deploy stacks vs the largest valid monolith.** Governance
`just-enough-governance-three-stacks` presumes decoupled services; domain-strategy 16 says keep
the largest monolith that is still valid. For a modular monolith they pull opposite ways.
**Composition:** the single-stack tax only counts when a business driver names it
(decomposition §A `business-driver-gate`), and per-context dependency tiers enforced inside one repo buy most of
the three-stack benefit without separate deploys — a partial boundary, which is cheap and
reversible.

**B. Deferring a decision vs enforcing structure now — the dangerous one.** Governance
`last-responsible-moment` reads as a licence to postpone the import contract, and that reading is exactly how a
`services → api` drift happens: nobody ever decided it, everybody deferred it.
**State it at full strength: you defer the CONTENT of a choice, never the DIRECTION of its
dependencies.** The mechanical rules are what *keeps* the other decisions deferrable — the
database stays "a detail" only for as long as the domain does not import it. An audit finding
that cites LRM to postpone a direction rule has inverted the rule.

**C. The thresholds in the rule files are themselves estimates.** `D > 0.1`, `CC < 5`, a
shared-code percentage — the same rules that say `derive-thresholds-from-production-not-estimates`
hand you fixed numbers. **Composition:** fixed thresholds are **seeds for the first pass only**, replaced
by the repo's own population distribution the moment one exists. Prefer the population-based
forms (one standard deviation, a z-score) over the absolute ones, because those are already
derived rather than borrowed. `detect.py`'s size rule is written this way on purpose: mean + 2σ
over *this* repo, never a fixed statement count.

**D. "Generic subdomain → buy" against a capability the business competes on.** Not a
contradiction: the classification fork has two axes, and something generic on the capability
axis can still be a declared competitive advantage, which makes it core rather than bought.
**Run the advantage test before writing "buy"**, and hand the classification itself to `domain`. It is the inoculation against outsourcing the thing you actually compete on.

**E. Weeks of evidence vs act at the first friction.** Decomposition `business-driver-gate`
wants a driver proven before code moves; component-boundary 1 (the inflection point) says build
the boundary at the first real friction. Unresolved, this produces paralysis or impulsiveness,
and paralysis is the common failure: identified root causes get parked indefinitely.
**Composition: two bars for two classes of move.** The business-driver gate governs
**decompositions** — expensive, slow, hard to reverse. The inflection point governs
**incremental boundaries** — partial boundaries, a moved import, a deleted shim, all cheap and
reversible. **Every finding must say which class its remedy belongs to**, because that is what
selects its bar.

**One scale caveat, carried rather than hidden.** The capacity-ceiling ownership rules were
measured on human teams. Applied to agent units, **keep the ordering and drop the human head
counts**; the unit's attention budget is declared per run and recorded with the finding.
