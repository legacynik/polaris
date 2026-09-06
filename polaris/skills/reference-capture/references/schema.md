---
title: External reference dossier schema
description: Minimal frontmatter and body contract consumed by reference-capture.
status: draft
---

# External reference dossier schema

```yaml
---
title: Atono — product and architecture study
description: Verified feature and mechanism inventory relevant to Polaris document workflows.
catalog: true
source_url: https://example.com/source
source_version: commit-or-release-or-published-date
analyzed_at: 2026-08-18
last_verified_at: 2026-08-18
reference_depth: deep
reference_relevance: core
reference_status: verified
serves: [polaris]
domains: [wiki, memoria]
aliases: [atono, document workflow]
capabilities: [source lineage, item context, version restore]
license: proprietary
---
```

Required body headings — deliberately only four, so a ten-line note remains valid:

```md
## Why relevant
## Reusable mechanisms
## What not to copy
## Promotion status
```

Rules:

- `reference_depth`: `note | study | deep` describes research effort, not importance.
- `reference_relevance`: `core | adjacent | watch` is relative to `serves`.
- `serves` must be evidenced by the request or the current repository contract/remote. Never infer
  it from unrelated memory or a prior project; unresolved ownership is `BLOCKED_OWNER`, not a guess.
- `reference_status`: `captured | verified | adopted | rejected | stale`.
- `domains`: stable internal domain IDs from the served repo's glossary. External vocabulary does
  not enter the glossary automatically; keep it in `aliases` until an architecture/domain decision
  maps or adopts it.
- Internal `ARCHITECTURE.md`, domain/glossary docs and ADRs never use this schema: they are authority,
  not external evidence. A ContextPack may join them to selected dossiers without merging their
  lifecycles or source-of-truth roles.
- Prefixes are deliberate: existing dossiers already use generic `status` and `relevance` with
  incompatible repo-local vocabularies. Admission must not rewrite those meanings.
- `captured` may omit version/verification date; it cannot prove a decision.
- `verified` and `adopted` require `source_version` and `last_verified_at`.
- `source_url` owns dedup. Use the canonical upstream URL, not a search result or local clone path.
- Before writing, `--lookup` also checks legacy `source:` fields so an older uncatalogued dossier is
  upgraded in place instead of shadowed by a cleaner duplicate.
- `aliases` and `capabilities` carry the vocabulary people will actually query.
- `catalog: true` is explicit admission. Absence means ignored.
- Everything else is free-form: deep dossiers may add inventories, changelogs, evidence tables and
  open questions without forcing that weight onto small notes.
