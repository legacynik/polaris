---
name: reference-capture
description: ◇ Use after analyzing an external repository, competitor, article, paper, release or changelog that the founder wants to keep — writes or updates one canonical Markdown dossier with retrieval metadata, rejects duplicate source ownership, and rebuilds the navigable cross-repo reference catalog. Not a research engine — use autoresearch, best-practice-research or a researcher to gather evidence first.
version: 0.1.3
user-invocable: true
auto: false
lifecycle: "canonical dossier remains with its owning repo; generated references/CATALOG.md is rebuilt after capture and may be replaced at any time; adopted/rejected/stale status is drained by the next refresh or linked audit/ADR"
invokes: []
invoked-by: []
io: "receives verified research output or a small founder-selected finding plus canonical repo owner -> writes/updates exactly one catalog:true Markdown dossier and rebuilds a cross-repo CATALOG.md, or blocks with the missing/duplicate evidence named"
status: active
---

# reference-capture

## Overview

Research depth may vary; retrieval shape must not. This skill is the write-side boundary after
research: one source or deliberately grouped subject gets one canonical dossier, complete metadata,
and one generated catalog entry. It does not research the source, create wiki page trees, decide an
architecture, or open implementation issues.

Existing jobs remain separate:

| Job | Owns |
|---|---|
| `autoresearch` | persistent validator-gated research loop |
| `best-practice-research` | current official/upstream evidence, read-only handoff |
| `wiki-research` / `wiki-ingest` | general Obsidian distillation and multi-page knowledge graph |
| `polaris-memory` | recall of prior decisions and lessons |
| `reference-capture` | one canonical external-reference dossier + derived cross-repo catalog |

## Integration with architecture and domain context

This skill never catalogs a repo's own `ARCHITECTURE.md`, domain glossary or ADR as an external
reference. Those are internal authority produced by the architecture/domain workflow and grounded
on current code plus durable decisions. The join is narrow:

```text
code@SHA -> ARCHITECTURE.md + domain glossary + ADRs
external research -> reference dossier -> domains/capabilities
Initiative -> selects applicable domains and reference dossiers
ContextPack -> code graph + internal authority + optional external evidence slice
implementation -> doc-impact check -> internal docs refresh -> projections rebuild
```

`domains` stores IDs emitted by the served repo's domain-glossary contract. Until that contract is
stable, values are provisional routing metadata: they must not create, rename or merge domain
terms. External terms stay in `aliases`; only the domain workflow may adopt them into the glossary.

## Workflow

1. **Choose the canonical owner.** Reusable across products lives in `_polaris/references/`.
   Product-specific evidence stays in that product repo's `references/` or `docs/research/`.
   Never copy the same dossier into two repos. `serves` must come from the user's stated target or
   current-repo evidence (remote/repo contract), never from unrelated conversation history. If the
   owner cannot be proved, stop with `BLOCKED_OWNER`; do not invent a project just to satisfy schema.
2. **Deduplicate by source.** Search the aggregate index, then run `reference_catalog.py --lookup`
   against every configured repo root. It checks both admitted dossiers (`source_url`) and legacy
   reference notes (`source`): update the single owner, create only on `NONE`, and stop on
   `COLLISION`. The catalog build independently blocks duplicate opted-in ownership.
3. **Write or update one Markdown file** using [references/schema.md](references/schema.md).
   Small findings use `depth: note`; ordinary analyses use `study`; exhaustive competitor/repo
   work uses `deep`. Metadata completeness does not shrink with body length.
4. **Classify without a fake score.** `reference_relevance: core|adjacent|watch` is meaningful
   only with `serves`. `domains` links the dossier to the owning repo's domain glossary;
   `capabilities` says what mechanism can be learned. `reference_status` records lifecycle
   separately from relevance. Prefixed keys avoid overwriting each repo's existing generic
   `status`/`relevance` vocabulary.
5. **Rebuild the catalog** from the declared roots. The list lives in the commit
   ([`../../references/CATALOG.roots`](../../references/CATALOG.roots)), not in whoever's shell
   ran the build, and that file states the rule for adding one. Entries resolve against the
   **main checkout**, so the same commit produces the same catalog from any worktree:

   ```bash
   python3 scripts/reference_catalog.py --output "$(git rev-parse --show-toplevel)/references/CATALOG.md"
   ```

   `--root <repo>` (repeatable) overrides the declared list for a one-off run; it never becomes
   the recorded input. A declared root that does not exist is a hard error, never a silent skip.
   Diff `references/CATALOG.md` before committing: it is generated, and a rebuild nobody diffed
   is a rebuild nobody verified.

6. **Verify retrieval.** Query by title/alias, capability, and served project. A saved file that
   cannot be retrieved is not complete.
7. **Handoff only when warranted.** `core` evidence may feed an audit, ContextPack or prototype.
   It never becomes an ADR, architecture claim, or implementation issue automatically.

## Fail-closed rules

- Only documents with `catalog: true` enter the catalog. Vendor clones and incidental Markdown are
  ignored rather than guessed into the knowledge base.
- `reference_status: verified|adopted` requires both `source_version` and `last_verified_at`.
- Missing title, source URL, analysis date, depth, relevance, status, serves, domains, aliases,
  capabilities or summary blocks.
- Unknown enum values block.
- Duplicate normalized `source_url` blocks and names every claimant.
- The generated catalog is replaced atomically only after all opted-in dossiers validate.
- The scanned roots come from `references/CATALOG.roots` in the commit. A missing roots file, an
  empty one, or a declared root that does not exist all block: a build cannot silently scan less
  than it claims to, because an omitted root is indistinguishable from an absent dossier.
- Roots and links are resolved against the repo's main checkout, so the catalog is a function of
  the commit and not of the directory it was built in. `scripts/gate_purity.py lint` covers this
  script.
- The catalog must be written inside the repo that declared the roots. Elsewhere its links resolve
  from that one directory and nowhere else — a plausible-looking file that is wrong the moment it
  moves — so the build refuses instead of producing it.

## When NOT to use

- The user only wants an answer and did not ask to retain it: return the answer; do not manufacture
  permanent knowledge.
- The research is still incomplete or disputed: finish the research first, or save it as
  `status: captured`; never label it verified.
- The artifact is a project decision, current architecture, active plan, lesson or current status:
  use the canonical Polaris destination for that document type.
- The source is already represented by a canonical dossier: update it; do not create a second page.
- The user wants a broad personal-wiki concept graph: use `wiki-research`/`wiki-ingest`.
- The task is to improve ranking or recall internals: that is issue #37, not this skill.

## Quick reference

| command | when | blocks? |
|---|---|---|
| `python3 scripts/reference_catalog.py --selfcheck` | before any promotion | yes |
| `python3 scripts/reference_catalog.py --lookup <canonical-url>` | before writing | yes on collision |
| `python3 scripts/reference_catalog.py --output <CATALOG.md>` | after capture/update | yes |
| `python3 ../../scripts/polaris_query_index.py "<alias capability project>"` | three retrieval probes | yes; fix retrieval before shipping |

## Origin

NEW job from the 2026-08-18 document-control-plane audit and issue
the tracker issue #86. Boundaries were checked
against `autoresearch`, `best-practice-research`, `wiki-research`, `wiki-ingest`,
`wiki-context-pack`, `wiki-capture`, `research`, Firecrawl knowledge/competitor workflows,
archived GSD capture/import and `polaris-memory`; no donor text or implementation was copied.
Full census and paired Memora eval: [`../../audit/2026-08-18-reference-capture-donor-eval.md`](../../audit/2026-08-18-reference-capture-donor-eval.md).

Bypass proof: [references/bypass-test.md](references/bypass-test.md).
