# The doc arm — what an ARCHITECTURE.md must carry

Load this only when the trigger is *write or re-true the architecture document*. It is not
loaded by any other arm.

Everything below was distilled from the **diff of four runs of the same dictated method**,
across four repositories of deliberately different shape: a layered service with machine-
enforced import contracts, an agent runtime with modules and delegation tiers, a product with
two disjoint databases, and this vault (a markdown corpus plus a script toolbelt). What all
four needed is the contract in §1 and §2. What only some needed is the menu in §3 — those are
sections, not requirements, and a repo that has no ports does not get a ports section.

The baseline this arm exists to beat, and the four invariants it produces that the naked run
did not, are recorded in [`bypass-test.md`](bypass-test.md).

## Contents

- [1. The frontmatter contract](#1-the-frontmatter-contract)
- [2. The nine sections all four needed](#2-the-nine-sections-all-four-needed)
- [3. The menu — sections some repos need](#3-the-menu--sections-some-repos-need)
- [4. Counts](#4-counts)
- [5. Halts](#5-halts)

## 1. The frontmatter contract

Every field mandatory. This is the half the document's future depends on: without it the
document cannot be checked, cannot be dated, and cannot be known to be stale.

| Field | Rule |
|---|---|
| `schema_version` | the live-document schema version, currently `1` |
| `document_type` | exactly `architecture` |
| `status` | exactly `active`; freshness is computed, never inferred from this field |
| `owner` | one role or address |
| `snapshot_scope` | the smallest explicit list of governed paths. What is outside it is unexamined, not implicitly current |
| `snapshot_ref` | `scope-sha256:<hash>` produced from path+content hashes over `snapshot_scope`; branch names, dates and manually typed SHAs are invalid |
| `review_trigger` | observable changes that make the document stale — port inventory, contract set, router list, data authority. Never a time interval |
| `related` | links to `CONTEXT.md`, `DOMAIN.md`, governing Decisions and the canonical plan |
| `modalità` | `piena`, or `ridotta` naming every input that was missing — the rule library, typed `decisions/`, a domain glossary, the graph verify leg. Same field, same rule as the decision record's (#78): a doc run degraded by a missing library is the single most exposed path this door has, and silence about it is a defect here too |

## 2. The nine sections all four needed

In this order. A document missing one is incomplete, not a draft.

| # | Section | What makes it pass |
|---|---|---|
| 1 | **Opening** | what the system is, in one paragraph · *read it before <the specific acts this document gates>* · that counts were read out of the code and not the spec · a pointer to the re-check section · and the tiebreak, stated: where this document and an older one disagree, the code wins |
| 2 | **Summary** | prose plus a two-column facts table. Every row a fact with a number or a name, never an adjective |
| 3 | **Bill of materials** | what it is built out of, with versions. Pins named as pins |
| 4 | **Where the code lives** | the directory census with counts per unit, and the dead paths named as dead — a document that quietly omits the old layout lets every stale doc that uses it keep looking current |
| 5 | **Entrypoints** | every way execution starts, including the unattended ones (CI, cron, hooks). The unattended entrypoints are the ones nobody remembers and the ones that break silently |
| 6 | **Data architecture** | the stores, the direction of flow, and which store is the system of record |
| 7 | **Enforcement and gates** | a table with a **blocks?** column. The value of this section is entirely in the rows that answer *no*: a gate that reports and does not block is a gate people believe in wrongly |
| 8 | **Decisions that govern this architecture** | the records, grouped by what they govern, plus the honest state of the record itself — how many are unratified, how many point at code that moved, which period is covered by which tier. All four runs found the decision record in worse shape than the code |
| 9 | **Where the code disagrees with the documents** | the findings, each with a tracker or an owner. **This is the section that makes the document worth reading**, it appeared in all four runs, and the naked baseline produced it unprompted — so its presence proves nothing about method; its per-finding tracker does |
| 10 | **What this is not** | the patterns a reader will otherwise assume, denied by name, so a refactor proposal shaped like one escalates instead of landing |
| 11 | **Keeping this document true** | last section. The runnable commands that re-check every count above, and the sentence binding the `review_trigger`: a PR that changes those things changes this file in the same PR |

Sections 1–11 with two optional (4 and 10 are cheap, 12 rows below are not) — the nine that
every one of the four runs needed are 1, 2, 4, 5, 7, 8, 9, 10, 11. Sections 3 and 6 were
needed by three of four; include them unless the repo genuinely has neither dependencies nor
a datastore.

## 3. The menu — sections some repos need

Add a row only when the repo has the thing. Each one appeared in at least one run and in at
least one it would have been noise.

| Section | Include when |
|---|---|
| **The layers, and the dependency rule as enforced** | a layer contract is machine-checked; quote the contracts verbatim and give the local command that runs them |
| **Ports / seams inventory** | an explicit port or interface layer exists. The table's useful columns are *called from* and *adapter* — that is what exposes a port declared and never wired |
| **Modules · delegation tiers · approvals** | the system runs agents or workers with per-unit capability sets. The finding this section produces is a tier with no ceiling |
| **The pipeline** | the product's value passes through one ordered transformation worth naming stage by stage |
| **Environments** | more than one, and they are not proven equal |
| **Deployment and operation** | it is deployed somewhere with a procedure, plus the recurring failure worth knowing before debugging |
| **Areas and parallel work** | more than one agent or person works the repo at once. Derive isolation from `git log` — how often a domain's commits touch nothing else — and regenerate rather than maintain it |
| **Adding a new `<unit>`** | the repo has a repeated extension shape (a new use case, a new module, a new data source). Numbered, and it names the file to copy |
| **Terms** | the repo's own words carry meaning outsiders will get wrong. Three of four needed it |
| **Diagrams index** | there is more than one diagram; then no diagram is added without a line here |

## 4. Counts

Every count in the document is produced by the census-then-verify shape in `SKILL.md`, and
carries one of two states:

- **closed** — the verify leg confirmed it, and §11 has the command that reproduces it;
- **`ASSUMED`** — the verify leg could not close it, and the reason is stated inline.

A count with neither state is the failure mode this arm exists to remove. Two of the four runs
found their own predecessor documents carrying counts that had been wrong for months, and in
one case the *golden* run itself shipped a directory count that a §11 command would have
caught — the commands are not ceremony, they are the only reason a number stays true.

Never re-state a count that another document owns. Point at that document instead; two copies
of a number is one number going stale.

## 5. Halts

- **A count the verify leg cannot close, where the decision depends on it.** Ship it
  `ASSUMED`, and name what instrument would close it.
- **A section in the menu whose subject is contested** — two readings of what the layers are,
  two candidates for the system of record. That is a decision, not a documentation task: run
  the matching arm, then come back.
- **`snapshot_ref` cannot be produced** from the declared scope or the repository has no checker.
  Stop: an unpinnable document is the artifact this arm was built to stop shipping. Generate the
  hash through the repository's document checker, never by hand.

## 6. Executable freshness

The artifact is incomplete without one repository-local command that recomputes every declared
scope hash and returns nonzero on drift. Polaris uses:

```bash
python3 -I scripts/check_context_backbone.py --check .
```

For a brownfield bootstrap, `--init <repo>` writes only the derived Decision manifest after the
triad and authority audit are already valid; rerunning it unchanged must return `NOOP` with the same
three seals. A work-item replay uses `--emit-context <repo> --work-item <declared-id>` and blocks
unless an applicable accepted Decision cites that ID as evidence.

The same PR that changes a governed source updates every affected live document and its Decision
manifest. A later reseal with no structural diff is repair evidence, not proof of same-change
document production.
