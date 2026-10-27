# Writing the architecture documents — map, area README, ADR, ledger line

Load this when `decide` is about to write a record, `init` meets a repository with no ADR set, or
`doc` is about to write `ARCHITECTURE.md` or an area's README. It owns two things: **which**
document a statement belongs in, and **how** each is written and kept current. There are four and
no others; the code carries the detail. What a record must prove before it is admitted (the six
requirements) stays in [record.md](record.md).

## Which document

| Statement | Document | Shape |
|---|---|---|
| affects the system's **structure, non-functional characteristics, dependencies, interfaces or construction techniques** — and passes the three ADR tests (hard to reverse · surprising without the context · a real trade-off) | **ADR** | one decision, one to two pages |
| a choice someone could re-argue, below that bar: a threshold, a method, a prompt, a heuristic, a number, a library inside one module | **ledger line** in `decisions.md` | a few lines |
| how one area works today: its flow step by step, where it breaks, what is off in production | the **area README**, `docs/<areas\|modules>/<area>/README.md` | read in ten minutes |
| the components, their boundaries and the main flows across areas | **`ARCHITECTURE.md`**, one per repository ([doc-arm.md](doc-arm.md)) | a short map |
| a name, a placement, a wording nobody would re-argue | the pull request or a comment beside the code | — |

A low-level choice is a ledger line **even when code carries it**: the commit enacts it, the line
says why. A DEC file `kind: process` remains the home of a non-architecture choice still to be
built that a command can check (operating model §6); an ADR is never a DEC file. The quick test for the ADR bar is the component diagram: if the
boxes, the arrows between them or the way they are built change, it may be an ADR; if only what
happens inside one box changes, it is a ledger line or a step in the area README.

## Rules for all of them

- **Conclusion first.** The title or first line says what was decided or how it works; the
  reasoning follows.
- **Numbers carry their source and date** — `31 false accepts in 400 matches (review, 2026-10-20)`.
  A number without both is marked `ASSUMED`.
- **One name per concept.** Pick the word once and use it everywhere; a second word for the same
  thing makes the reader look for a second thing.
- **Plain words.** Short sentences, active voice, the term the code uses.
- **A diagram for any flow** of three or more steps — a fenced Mermaid block or the generated
  map, never prose alone.

## ADR

**Where**: always `docs/adr/NNNN-kebab-title.md`, numbered in sequence, in every repository —
never a DEC file in the typed register. An ADR that needs enforcement may carry optional `probe:`
and `probe_kills:` frontmatter. **The set starts with ADR 0001, "Record architecture decisions"**: the meta-record that
states this format and the governance below. A repository with no ADR set gets it first, from
[adr-0001.md](adr-0001.md), before its first real decision becomes 0002.

**Budget**: one to two pages. A healthy set has a median around 100 lines; a 400-line record is a
smell `doctor` flags.

```markdown
# N. <Short title that names the decision>

Date: YYYY-MM-DD

## Status
Proposed | Accepted | Superseded. Supersedes ADR-NNNN / Superseded by ADR-NNNN (linked both ways).

## Context
The forces, as value-neutral facts, measured where possible: each number with source and date.
What undoing this would take.

## Decision
Full sentences, active voice: "We will …".

## Consequences
All of them, not only the good ones: what gets easier, what gets harder, what it now costs.
Check: <the test or gate that fails on a violation>. Reopen when: <the outside condition>.

## Rejected                       (optional — only alternatives that carry signal, each with its cost)
## Measurement                    (optional — when a number decided it: what, how, the result)
## Not decided                    (optional — what this record leaves open, so nobody reads more into it)
## How it would be proven wrong   (optional — the observation or measurement that would falsify it)
```

Title, Date, Status, Context, Decision and Consequences are required. The optional four earn
their place when they carry something; the last two catch over-reading and untestable claims in
review. The six admission requirements land here: undo cost and evidence in *Context* (or
*Measurement*), enforcement and the review trigger in *Consequences*, the options with their cost
in *Rejected* — the ones that carry no signal stay in the run's reply (`opzioni`, `costo per
opzione`). Rules, `governs`, and an optional `probe` / `probe_kills` go in the frontmatter.

Example:

```markdown
# 7. Pricing runs as its own service

Date: 2026-10-26

## Status
Proposed. Supersedes ADR-0003.

## Context
Quoting and invoicing both compute prices and disagreed on 12 of 300 invoices (reconciliation,
2026-09-30). The price tables sit in the quoting database, so invoicing reads another service's
tables. Undoing this means moving the tables back and re-pointing two callers.

## Decision
We will run a pricing service that owns the price tables and is the only code that computes a
price. Quoting and invoicing will call it over HTTP.

## Consequences
One place answers "what does this cost". Every quote now pays a network hop, and a pricing outage
blocks quoting. We run and page for one more service.
Check: an import contract fails if quoting or invoicing imports the price tables.
Reopen when: quote latency p95 exceeds 800 ms.

## Rejected
- A shared pricing library — two deploys per price change, and the tables stay shared.

## Not decided
Caching prices in the callers, and who may edit the tables.
```

## Keeping the set current

The set is kept **minimal and current, so every ADR describes the system as it is**.

| Change | Act |
|---|---|
| drift — a path, a name, a count, a status line, wording that reality has outrun | **amend in place**; an amendment never changes what was decided |
| a real reversal of what was decided | **supersede**: a new ADR, the old one `Superseded`, both linked |
| overlapping records, dead records, a record grown past two pages | **compact**: merge, drop the dead, renumber; git history is the archive, and each compacted record carries a provenance note naming the ADRs it absorbed |
| a dated "update" appended to a record | **never** — that is how one record becomes a diary of 13 sections |

**A diary ADR** — appended update sections, or far past two pages — is undone in three moves: what
the system does today goes into the owning area's README (`ARCHITECTURE.md` when it spans areas);
the record is compacted into one current decision (with its provenance note) or superseded by a
new ADR; each appended change below the bar becomes a ledger line. `scripts/adr_triage.py
<adr-dir>` gives the signals for every file in a folder, read-only ([doctor.md](doctor.md)). A
compacted ADR set states the decisions as they hold today; it never replaces the area README,
which carries the flow end to end and links the ADRs.

## The area README

`docs/<areas|modules>/<area>/README.md` — one file per area besides its plans: what the area
owns, how it works today step by step, and the links to its ADRs and ledger lines. **Updated**
when a plan closes and in any pull request that changes how the area works. **Budget**: read in
ten minutes, about 200 lines; past that, the area splits. **Today's state only**: history stays
in the ADRs, the ledger and git, never in dated sections. Where the README carries a generated
map between `area-map` markers, write outside them.

```markdown
# <Area>
## What it owns              — and what it does not
## Goals and non-goals
## The flow                  — one diagram of the whole flow
## Steps                     — per step:
### <Step>
In: <what enters>. Logic: <two or three lines>. Out: <what exits>. Files: <the main ones>.
Breaks when: <the failure>, proof: <test, eval or validation link>. Off in production: <flag, or none>.
## Decisions                 — one line each, linking the ADR or ledger line, never restated
## Open questions
```

Example of one step:

```markdown
### Classify rows
In: rows from the splitter, one per printed line. Logic: an LLM labels each row item, subtotal
or note; one request per document. Out: labelled rows to the catalogue writer. Files: `classify.py`.
Breaks when: a scanned page has no text layer; proof: eval/ingest-scanned (14/20, 2026-10-12).
Off in production: the OCR fallback (`INGEST_OCR=0`).
```

`ARCHITECTURE.md` at the root is the repository-wide map — components, boundaries and the main
flows across areas, each linking the area READMEs for step detail ([doc-arm.md](doc-arm.md)).

## Ledger line in `decisions.md`

**When**: below the ADR bar, a choice someone could re-argue. **Budget**: a few lines, newest on
top, append-only. Fields: chose · over · because · evidence · supersedes · impact.

```markdown
- 2026-10-26 · catalogue matcher · chose: accept at cosine ≥ 0.84 · over: 0.78 · because: false
  accepts cost a manual fix each · evidence: 31 false accepts in 400 matches at 0.78 (review,
  2026-10-20) · supersedes: 2026-08-02 matcher line · impact: matcher.py, judge prompt v3
```

A changed value is a new line that names the one it supersedes; the old line stays.

## Red flags

- An ADR over two pages, or with a section titled "Update", "Aggiornamento" or `2bis`.
- An ADR for a threshold, a prompt or a heuristic.
- An amendment that changes what was decided — that is a supersede.
- A repository with ADRs and no 0001 stating how the set is kept.
- An area README with dated sections, or a step without "breaks when".
- A fifth kind of architecture document next to these four.
- The same concept under two names across the documents.
- A number with no source or no date.
