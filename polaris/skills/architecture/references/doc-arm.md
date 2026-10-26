# The doc arm — what an ARCHITECTURE.md must carry

Load this only when the trigger is *write or re-true the architecture document*. It is not
loaded by any other arm.

The document is **a map of a country, not an atlas of its states**. It tells a newcomer — human
or agent — where the thing that does X lives, what the thing they are looking at does, which way
the dependencies point, and what is deliberately absent. It specifies only what is unlikely to
change often, so an ordinary feature PR does not touch it and does not make it stale. It is
honest about where the code departs from the shape it describes, and it is not an audit.

## Contents

- [1. The frontmatter contract](#1-the-frontmatter-contract)
- [2. The sections](#2-the-sections)
- [3. What stays out, and where it goes instead](#3-what-stays-out-and-where-it-goes-instead)
- [4. The menu — content some repos need](#4-the-menu--content-some-repos-need)
- [5. Halts](#5-halts)
- [6. Executable freshness](#6-executable-freshness)

## 1. The frontmatter contract

Every field mandatory. Without it the document cannot be checked and cannot be known to be stale.
The frontmatter uses the notation the repository's other live documents already use (JSON or YAML);
never introduce a second one.

| Field | Rule |
|---|---|
| `schema_version` | the live-document schema version, currently `1` |
| `document_type` | exactly `architecture` |
| `status` | exactly `active`; freshness is computed, never inferred from this field |
| `owner` | one role or address |
| `workspace`, `repo` | the same identity pair `CONTEXT.md` and `DOMAIN.md` carry; the checker refuses a triad whose pairs differ |
| `snapshot_scope` | the repository-relative paths the document cites, written from the repository root (`backend/app/main.py`, never a bare `main.py`). Each must exist: a cited path that is gone makes the document `STALE`. Symbols (functions, env vars) are not checked — a rename is invisible, which is what `review_trigger` is for |
| `review_trigger` | observable structural changes that make the document stale — a module added or removed, a boundary moved, a store changing its system of record, a gate starting or stopping to block. Never a time interval, never "any change under `src/`" |
| `related` | links to `CONTEXT.md`, `DOMAIN.md` and the Decision register |
| `modalità` | the same structured first line `process.md` uses — `piena`, or `ridotta — missing: <tag>[, <tag>…]` — with the prose reason after it |

## 2. The sections

In this order, with unnumbered headings — refer to a section by its name, never by a number. Omit a section only when the repo genuinely has nothing for it, and say so in one
line rather than leaving a gap a reader will read as an oversight.

| # | Section | What makes it pass |
|---|---|---|
| 1 | **Opening** | what the system is, in one paragraph · *read it before <the acts this document gates>* · the tiebreak, stated: where this document and the code disagree, the code wins · a pointer to *Keeping this document true* |
| 2 | **Bird's eye view** | the problem the system solves, its inputs and outputs, and the one flow a newcomer must hold in their head. The derived map, if there is one, is linked here, never redrawn by hand |
| 3 | **Design principles** | the few principles the system is built on — three to six, one short paragraph each, each naming a choice it explains (e.g. the dependency rule and which way it points; "a function never knows who calls it, everything goes through the engine"). Anything the rest of the document leaves unexplained should be inferable from these. A principle the code does not keep today is not listed here: it goes to *Known limits* as a target |
| 4 | **Code map** | one short paragraph per **coarse** module, headed by its path in backticks: what it does and where the thing that does X lives. Name the important files, modules and types; do not link them and never give line numbers — symbol search finds them. Describe the composition **as it is**, spaghetti included. Say which way the dependencies point and whether the layout names the domain or only the framework. Two callouts, used only when true: **Architecture Invariant:** — a rule the code keeps today, often an absence ("nothing in `domain/` imports the web layer"), followed by what enforces it (the test or gate by name) or `not enforced` · **API Boundary:** — where callers outside the module start and the rules change. When `DOMAIN.md` declares classified domains, one bold-led line per domain (`- **<Term>** — <sentence>`, the term exactly as `DOMAIN.md` names it) is what a map generator reads as the box's gloss; code areas that are not domains get headings, never bold-led lines |
| 5 | **Cross-cutting concerns** | only the ones the repo has, one short paragraph each: error handling (and whether failures can be silent), observability, testing and gates — a table with a **blocks?** column, one row per **kind** of gate (the merge gate, the pre-commit hook, the scheduled eval), never one per job or per check, because the job list changes with ordinary PRs —, security and access, configuration and secrets, external and LLM access |
| 6 | **Data and environments** | the stores, the direction of flow, which store is the system of record; the environments, and whether they are proven equal. Short |
| 7 | **Known limits** | where the code today departs from the architecture this document describes — a claimed boundary that is crossed, an invariant that is a target and not yet true, a module that is a bag. Few, one line each, each linked to where it is measured or tracked. This is honesty about the map, not an audit: the full census of findings lives in dated audit reports |
| 8 | **Keeping this document true** | last section. The `review_trigger` restated as a PR rule — a PR that makes one of them true updates this file in the same PR — plus the commands that measure the things this document deliberately does not count (sizes, cycles, coverage), printed as commands, never with their output |

## 3. What stays out, and where it goes instead

The test for every sentence: **would an ordinary feature PR make it false?** If yes, it does not
belong in this document.

| Out of the document | Goes to |
|---|---|
| counts, sizes, line counts, `file:line` references, per-directory censuses | a command in *Keeping this document true*; an audit report when a dated number is needed |
| dependency and tool versions | the lockfile or manifest, named by path |
| per-endpoint, per-table, per-flag lists | the code, the schema, the OpenAPI document |
| findings with owners and trackers | the audit arm's report and the tracker; *Known limits* keeps only the few that change how a reader should read the map |
| the list of Decisions and their state | the Decision register (`decisions/`); the code map names only the few that shape a boundary |
| roadmap, planned modules | the board and the plans; a module that does not exist yet is not on the map |

Counts are not banned from the skill: `audit` and `decide` emit dated artifacts and still close
every number through the census-then-verify shape in `process.md`. They are banned from the one
document that is meant to stay true between reviews.

## 4. The menu — content some repos need

Add it inside *Code map*, *Cross-cutting concerns* or *Data and environments* only when the repo has the thing.

| Content | Include when |
|---|---|
| **The layers, and the dependency rule as enforced** | a layer contract is machine-checked; name the contract and the command that runs it |
| **Ports / seams** | an explicit port or interface layer exists; say where each is called from and which adapter serves it — that is what exposes a port declared and never wired |
| **Modules · delegation tiers · approvals** | the system runs agents or workers with per-unit capability sets |
| **The pipeline** | the product's value passes through one ordered transformation worth naming stage by stage |
| **Deployment and operation** | it is deployed somewhere with a procedure, plus the recurring failure worth knowing before debugging |
| **Adding a new `<unit>`** | the repo has a repeated extension shape; numbered, naming the file to copy |
| **Terms** | the repo's own words carry meaning outsiders will get wrong — or point at `DOMAIN.md` if it owns them |

## 5. Halts

- **An invariant you cannot show true today.** Do not state it as an invariant. It goes to *Known limits* as
  a target, with what would make it true.
- **A subject that is contested** — two readings of the layers, two candidates for the system of
  record. That is a decision, not a documentation task: run the matching arm, then come back.
- **A cited path does not resolve.** Fix or drop the name; never cite a path that is not there.
- **The map cannot be derived** — `DOMAIN.md` has no classified domains, so a generator has
  nothing to draw. Do not draw one by hand: write one line in the bird's eye view saying no map
  exists yet and why, and offer `domain` to classify the domains.

## 6. Executable freshness

Nothing is stored to be kept in sync: no hash, no seal to re-stamp. One command checks, at read
time, that every path in `snapshot_scope` exists, and returns nonzero on a gone path:

```bash
BACKBONE=$(python3 scripts/arch_doctor.py --which check_context_backbone.py --root <repo>)
python3 -I "$BACKBONE" --check <repo>
```

When `--which` exits nonzero the checker is not installed here: resolve every `snapshot_scope`
path by hand and record the result in `modalità`.

**The map beside the document.** When the repository's output map declares `outputs.diagram`
and a map generator, regenerate the map from `DOMAIN.md`, `ARCHITECTURE.md` and the Decision
register after the document changes, and link it from *Bird's eye view*. Every box, region, edge
and existence tag comes from those sources; a map typed by hand is a second, unchecked copy of
the document. Where no generator is declared, write no map.

Editing the contents of a cited file never makes the document stale; that is the point. Its known
blind spot: a boundary that moves inside a file that stays where it is. That is what the
`review_trigger` sentence in *Keeping this document true* is for.

For a brownfield bootstrap, `--init <repo>` writes nothing: it answers `READY` once the triad and the
authority audit are valid.
