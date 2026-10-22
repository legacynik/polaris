---
name: reference-capture
description: ◇ THE door for keeping an external source already read — a YouTube video or tutorial, a repo, a competitor, an article, paper, release or changelog. Fetches video transcripts via yt-dlp, writes ONE canonical dossier detailed enough to act on without reopening it, then rebuilds the cross-repo catalog and refuses duplicate source ownership. Triggers on "index this", "fammi il report di questo video", or a transcript with no dossier. Never for a source nobody has read yet — that is research.
version: 0.3.1
user-invocable: true
auto: false
lifecycle: "canonical dossier remains with its owning repo; generated references/CATALOG.md is rebuilt after capture and may be replaced at any time; adopted/rejected/stale status is drained by the next refresh or linked audit/ADR"
invokes: []
invoked-by: []
io: "receives a source URL or already-gathered evidence plus canonical repo owner -> fetches the source when it is a video, then writes/updates exactly one catalog:true Markdown dossier carrying the schema_version 2 extraction spine, and rebuilds a cross-repo CATALOG.md, or blocks with the missing/duplicate/dangling evidence named"
status: active
---

# reference-capture

## Overview

One source gets one canonical dossier, complete metadata, resolved links, and one generated catalog
entry. Research depth may vary; retrieval shape and extraction depth must not.

The bar this skill exists to hold, and the one to fall back on whenever anything below is ambiguous:

> **Can someone act on the source using only the dossier, without going back to the original?
> If no, it is incomplete — however good the metadata is.**

That bar is not decoration. Version 1 of this contract specified only frontmatter and left the body
free-form beyond four verdict headings, all of which describe *our judgment of* a source and none of
which ask what the source actually says. The measured result across the archive: dossiers that
passed every gate and held no command, no version, no reproducible step, while ten downloaded video
transcripts sat beside zero dossiers. A source you summarised into uselessness is a source you will
study again from scratch.

It writes one canonical dossier per source and the catalog derived from the dossiers, and
nothing else: researching an unread source, building a multi-page wiki, deciding an architecture,
opening implementation issues and recalling prior decisions are other jobs.

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

1. **Choose the canonical owner.** The dossier lives in the current repository
   (`git rev-parse --show-toplevel`), under `references/` (or `docs/research/` when the repo
   already keeps research there). Never copy the same dossier into two repos. `serves` must come from the user's stated target or
   current-repo evidence (remote/repo contract), never from unrelated conversation history. If the
   owner cannot be proved, stop with `BLOCKED_OWNER`; do not invent a project just to satisfy schema.
2. **Deduplicate by source.** Search `references/CATALOG.md`, then run `reference_catalog.py --lookup`
   from the repository, against every declared root. It checks both admitted dossiers (`source_url`) and legacy
   reference notes (`source`): update the single owner, create only on `NONE`, and stop on
   `COLLISION`. The catalog build independently blocks duplicate opted-in ownership.
3. **Get the source in front of you.** An article is fetched, a repository is cloned and read
   through the code graph — both are already within reach, so nothing here wraps them. A video is
   the exception: without subtitles the source cannot be read at all, so fetch it first.

   ```bash
   python3 scripts/ingest_youtube.py '<url>' --out <dossier-dir>   # quote the URL: zsh globs on ?
   ```

   It writes `source/transcript.md` (timestamped, rolling-caption repetition collapsed),
   `source/meta.json` and `imgs/cover.jpg`. YouTube rate-limits the subtitle endpoint per IP
   (HTTP 429 while `yt-dlp --list-subs` lists the captions, 2026-10-07): the script spaces the
   subtitle requests, asks through the android client and retries a 429 three times with growing
   pauses. If it still fails, download the `.vtt` by hand (another network, another client, or
   `--sub-langs it` when only the auto-translation gets through) and rerun with `--vtt <file>`:
   metadata and cover are still fetched from the url, and the dossier must say which language the
   captions are in. That transcript is **raw material, never a dossier**:
   it carries no `catalog: true`, so it never competes in the catalog or in search. Leaving a
   transcript without a dossier beside it leaves nothing retrievable — that is how the archive
   accumulated ten unusable videos.

4. **Write or update one Markdown file** using [references/schema.md](references/schema.md).
   Declare `schema_version: 2` and the matching `source_type`. Small findings use `depth: note` and
   keep the four verdict headings alone; `study` and `deep` carry the full extraction spine, and the
   gate enforces it heading by heading.

   The spine's shape is in the schema; what matters here is the instinct behind it. Sections 1–4
   (executive summary, problems solved, **problems NOT solved**, related) are the reading head —
   enough for someone to decide whether this source is worth their afternoon. Everything after is
   the detail, and the detail never compresses: every command, flag, version, price and product name
   verbatim, every claim in a video carrying its `[HH:MM:SS]`. For a tutorial this is the whole
   point — the reader will follow your dossier instead of watching the video, so a step you dropped
   is a step they will never perform. Failed attempts and caveats are the highest-value content in
   any source and the first thing a summary throws away; keep them.

   Metadata completeness does not shrink with body length.
5. **Classify without a fake score.** `reference_relevance: core|adjacent|watch` is meaningful
   only with `serves`. `domains` links the dossier to the owning repo's domain glossary;
   `capabilities` says what mechanism can be learned. `reference_status` records lifecycle
   separately from relevance. Prefixed keys avoid overwriting each repo's existing generic
   `status`/`relevance` vocabulary.
6. **Rebuild the catalog** from the declared roots. The list lives in the commit, at
   `references/CATALOG.roots` in the repository's top level: one root per line, resolved against
   that `references/` directory, `#` for comments. A repository without one starts it with the
   single line `..` (this repository); a sibling repository is `../../<name>`. Entries resolve
   against the **main checkout**, so the same commit produces the same catalog from any worktree:

   ```bash
   python3 scripts/reference_catalog.py --output "$(git rev-parse --show-toplevel)/references/CATALOG.md"
   ```

   `--root <repo>` (repeatable) overrides the declared list for a one-off run; it never becomes
   the recorded input. A declared root that does not exist is a hard error, never a silent skip.
   Diff `references/CATALOG.md` before committing: it is generated, and a rebuild nobody diffed
   is a rebuild nobody verified.

7. **Verify retrieval.** Three probes, by title/alias, by capability and by served project:
   `grep -ril '<term>' "$(git rev-parse --show-toplevel)/references"` must list the dossier each
   time. A saved file that cannot be retrieved is not complete.
8. **Handoff only when warranted.** `core` evidence may feed an audit, ContextPack or prototype.
   It never becomes an ADR, architecture claim, or implementation issue automatically.

## Fail-closed rules

- Only documents with `catalog: true` enter the catalog. Vendor clones and incidental Markdown are
  ignored rather than guessed into the knowledge base.
- `reference_status: verified|adopted` requires both `source_version` and `last_verified_at`.
- Missing title, source URL, analysis date, depth, relevance, status, serves, domains, aliases,
  capabilities or summary blocks.
- Unknown enum values block.
- At `schema_version: 2`: an unknown or missing `source_type` blocks; a missing spine heading at
  `study`/`deep` blocks; `related` absent at `study`/`deep` blocks; a `related` target that does not
  resolve to an existing file blocks. A dangling link is worse than no link, because it looks like a
  connection.
- Absence of `schema_version` means version 1 and is validated exactly as before. The spine is not
  retroactive on purpose: a contract that invalidates the whole corpus the day it lands does not get
  adopted, it gets bypassed. Migrate a dossier the next time you have it open anyway.
- Duplicate normalized `source_url` blocks and names every claimant.
- The generated catalog is replaced atomically only after all opted-in dossiers validate.
- The scanned roots come from `references/CATALOG.roots` in the commit. A missing roots file, an
  empty one, or a declared root that does not exist all block: a build cannot silently scan less
  than it claims to, because an omitted root is indistinguishable from an absent dossier.
- Roots and links are resolved against the repo's main checkout, so the catalog is a function of
  the commit and not of the directory it was built in.
- The catalog must be written inside the repo that declared the roots. Elsewhere its links resolve
  from that one directory and nowhere else — a plausible-looking file that is wrong the moment it
  moves — so the build refuses instead of producing it.

## When NOT to use

- The user only wants an answer and did not ask to retain it: return the answer; do not manufacture
  permanent knowledge.
- The research is still incomplete or disputed: finish the research first, or save it as
  `status: captured`; never label it verified.
- The artifact is a project decision, current architecture, active plan, lesson or current status:
  write it where the repository keeps that document type (decisions, `ARCHITECTURE.md`, plans,
  lessons, state).
- The source is already represented by a canonical dossier: update it; do not create a second page.
- The user wants a broad personal-wiki concept graph: that is a multi-page wiki, not a dossier.
- The task is to improve ranking or recall internals: that is search work, not capture.

## Quick reference

| command | when | blocks? |
|---|---|---|
| `python3 scripts/ingest_youtube.py '<url>' --out <dir>` | a video source, before writing | yes on no-captions; a 429 is retried, then points to `--vtt` |
| `python3 scripts/ingest_youtube.py '<url>' --out <dir> --vtt <file.vtt>` | a subtitle already downloaded after a persistent 429 | yes on a missing file |
| `python3 scripts/reference_catalog.py --selfcheck` | before any promotion | yes |
| `python3 scripts/reference_catalog.py --lookup <canonical-url>` | before writing | yes on collision |
| `python3 scripts/reference_catalog.py --output <CATALOG.md>` | after capture/update | yes |
| `grep -ril '<alias\|capability\|project>' "$(git rev-parse --show-toplevel)/references"` | three retrieval probes | yes; fix retrieval before shipping |

Bypass proof: [references/bypass-test.md](references/bypass-test.md).
