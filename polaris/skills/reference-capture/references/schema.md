---
title: External reference dossier schema
description: Frontmatter contract and mandatory body spine consumed by reference-capture. Version 2 adds the extraction spine that makes a dossier reproducible instead of merely well-labelled.
status: active
schema_version: 2
---

# External reference dossier schema

## Why this document has two halves

The frontmatter half decides whether a dossier can be **found**. The body half decides whether it is
**worth finding**. Version 1 specified only the first, and the result was measurable: dossiers that
passed every gate, entered the catalog, and contained no command, no version, no reproducible step —
because nothing ever checked the content. A dossier can be perfectly labelled and still be useless.

The rule that ties both halves together, and the one to fall back on whenever this document is
ambiguous:

> **Can someone act on the source using only this dossier, without going back to the original?
> If no, it is incomplete — regardless of how good the metadata is.**

## Frontmatter

```yaml
---
title: Atono — product and architecture study
description: Verified feature and mechanism inventory relevant to Polaris document workflows.
catalog: true
schema_version: 2
source_url: https://example.com/source
source_type: article
source_version: commit-or-release-or-published-date
analyzed_at: 2026-09-09
last_verified_at: 2026-09-09
reference_depth: deep
reference_relevance: core
reference_status: verified
serves: [polaris]
domains: [search, memory]
aliases: [atono, document workflow]
capabilities: [source lineage, item context, version restore]
related:
  - "[[references/ai-ml/qmd]]"
license: proprietary
---
```

### Field rules

- `schema_version`: `2` opts the dossier into the body spine below and into `related` validation.
  Its **absence means version 1**, which is validated exactly as before. This is deliberate: a
  contract that invalidates every existing dossier the day it lands does not get adopted, it gets
  bypassed. Migration is per file, on the next time someone touches it.
- `source_type`: `video | repo | article | paper | changelog | thread | course`. It is not
  decoration — it selects which shape the **Contenuto completo** section takes, and it is what makes
  "show me every video tutorial about X" answerable.
- `reference_depth`: `note | study | deep` describes research effort, not importance.
- `reference_relevance`: `core | adjacent | watch` is relative to `serves`.
- `serves` must be evidenced by the request or the current repository contract/remote. Never infer
  it from unrelated memory or a prior project; unresolved ownership is `BLOCKED_OWNER`, not a guess.
- `reference_status`: `captured | verified | adopted | rejected | stale`.
- `domains`: stable internal domain IDs from the served repo's glossary. External vocabulary does
  not enter the glossary automatically; keep it in `aliases` until an architecture/domain decision
  maps or adopts it.
- `related`: required at `schema_version: 2` when `reference_depth` is `study` or `deep`, and every
  target must resolve to a file that exists. A dossier nobody can reach from anywhere is a file, not
  knowledge — and a dangling `[[link]]` is worse than no link, because it looks like a connection.
- `aliases` and `capabilities` carry the vocabulary people will actually query. Write them with the
  words **you** will use searching in six months, not the words the author used. The retrieval index
  ranks frontmatter only, so anything not here is unreachable by search.
- `source_url` owns dedup. Use the canonical upstream URL, not a search result or local clone path.
- `catalog: true` is explicit admission. Absence means ignored.
- `verified` and `adopted` require `source_version` and `last_verified_at`. `captured` may omit
  them, and cannot prove a decision.
- Internal `ARCHITECTURE.md`, domain/glossary docs and ADRs never use this schema: they are
  authority, not external evidence.

## Body spine — `schema_version: 2`

`reference_depth: note` keeps the four verdict headings alone, so a ten-line note stays valid. That
exemption exists for genuinely small findings; it is not a way to file a two-hour analysis as a note.

`study` and `deep` require the spine below, in this order. The order is not cosmetic: sections 1–4
are the **reading head** — enough to decide whether this source is worth your afternoon without
reading the rest. The detail follows, and the detail never compresses.

```md
## Executive summary
## Problemi che risolve
## Problemi che NON risolve
## Correlati
## Punti di partenza
## Contenuto completo
## Rischi e caveat
## Dati e numeri citati
## Risorse citate
## Alternative e scelte
## Mapping sul nostro sistema
## Actionable
## Why relevant
## Reusable mechanisms
## What not to copy
## Promotion status
```

### What each section owes the reader

**Executive summary** — what the source is, what you end up with if you adopt it, and the single
most important takeaway. This is the *only* synthetic section in the document. Everywhere else,
summarising is losing.

**Problemi che risolve** — the failure the source addresses, in its author's own framing, including
their war stories and any measured data about the problem. The author's motivation is usually the
best-argued part of any source; it is also the part that tells you whether you have that problem.

**Problemi che NON risolve** — where the source stops. What it declares out of scope, what it
promises and does not deliver, and what it simply never addresses. Mark each line `AUTORE` when the
author says it, `OUR NOTE` when we observe it. This section exists because adopting something and
discovering its ceiling afterwards is the expensive way to learn it, and because a source that
appears to have no limits has only been read charitably.

**Correlati** — links to other dossiers and to our internal authorities, **one line per link saying
why the link exists**. A bare list of wikilinks is not a graph; it is decoration. "Same problem,
opposite approach" or "supersedes the mechanism in X" is a graph.

**Punti di partenza** — every tool, account, dependency, version, skill level and cost the source
assumes or names, *including the implicit ones*. "Open this in your knowledge base" implies you have
one. Implicit prerequisites are where reproduction actually fails.

**Contenuto completo** — the heart, and the section version 1 had no equivalent for. Its shape
follows `source_type`; its rule never changes:

| `source_type` | Shape |
|---|---|
| `video`, `course` | numbered step-by-step, each step carrying `[HH:MM:SS]`, the command or action verbatim, what it needs, and how you know it worked. Sub-steps nested, never flattened |
| `repo` | reconciled mechanical inventory · real architecture (verified via code graph, not the README) · public API · what it explicitly does NOT do |
| `article`, `paper` | thesis and the evidence actually offered · method · what is measured versus what is asserted |
| `changelog` | delta against the previous dossier for this source, line by line |
| `thread` | the claim, the strongest counter-argument in the thread, and what was settled versus what stayed contested |

The rule, for every shape: **complete, not synthetic.** Every command, file name, flag, price,
percentage, version number and product name appears verbatim. Compression is allowed only for
sponsor reads, filler and repetition — and even then one line records that they existed, because a
reader who cannot tell what was skipped cannot trust what was kept.

For tutorials the bar is highest, and worth stating plainly: the value of a tutorial *is* the
detail. The exact flag, the order of the steps, the warning said in passing at minute fourteen. A
summary of a tutorial is not a summary, it is a loss — the reader will follow your dossier instead
of watching the video, so a step you dropped is a step they will never perform.

**Rischi e caveat** — every limitation, edge case, failure mode, security note and cost trap the
source mentions, plus the ones evident to us but unmentioned, marked `OUR NOTE`.

**Dati e numeri citati** — every metric, benchmark, percentage, price, latency and time claim, with
its context. These are what justify or kill a decision months later, and they are the first thing a
summary drops.

**Risorse citate** — every repo, product, link, doc, paper and person named, with the role each
plays. This is how one dossier becomes the entry point to the next.

**Alternative e scelte** — the decision points: "you could also…", "I tried X first and it failed",
"if you use Y instead". Failed attempts are the highest-value content in any source, because they
are the experiments you now do not have to run.

**Mapping sul nostro sistema** — honest comparison in both directions, marking `verified` versus
`assumed`. State what the source does **better** than what we have. A comparison that only finds
flaws in the external system is not analysis, it is reassurance, and it is how we end up rebuilding
something mature.

**Actionable** — concrete steps if we adopt, smallest first. Never an issue or an ADR by itself;
this section proposes, it does not commit.

**Why relevant · Reusable mechanisms · What not to copy · Promotion status** — the verdict, kept
from version 1 and moved to the end. These are our judgment *about* the source; they belong after
the source has been faithfully rendered, not instead of it.

### Empty sections

A required section with nothing to say is written with one line stating that, and why — for example
`Nessun dato quantitativo: la fonte non misura nulla, tutte le affermazioni sono argomentate.`
Silence and absence look identical to a reader; a declared absence is information.

## Fail-closed summary

Blocked, in both schema versions: missing required frontmatter field, unknown enum value, duplicate
normalized `source_url`, `verified`/`adopted` without `source_version` + `last_verified_at`.

Additionally blocked at `schema_version: 2`: a missing spine heading at `study`/`deep`, `related`
absent at `study`/`deep`, and a `related` target that does not resolve to an existing file.
