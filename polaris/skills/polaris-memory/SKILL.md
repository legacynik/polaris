---
name: polaris-memory
description: >
  Search and record team memory with the `polmem` CLI — the Polaris developer memory that every repo
  carries and that gets more useful the more you ship. Use this skill BEFORE grepping/searching to
  answer "where's the doc for X", "what did we decide about Y", "why did we choose Z", "have we hit
  this bug before", or whenever you're about to build/decide something and want to know if it already
  exists. Also use it to record a decision or lesson worth keeping. Works from any repo, in any coding
  CLI (Claude Code, Codex, …). If the user mentions memory, recall, "remember this", past decisions,
  lessons, or "did we already…", reach for this skill.
user-invocable: true
---

# Polaris Memory (`polmem`)

Every product repo carries a **canonical wiki** of distilled decisions, lessons, and architecture that
maintains itself on commit. `polmem` is how you read and write it from the terminal — from any repo,
any harness. It uses grep + a typed-edge graph (no vectors), so it's instant and deterministic.

## The one rule: recall FIRST

Before you `grep`/`find`/`ls` your way through a repo to answer *"where's the doc for X"* or *"what did
we decide about Y"*, and before you build or re-invent anything — **query memory first** — *except for
current-state questions* (what is deployed right now, what a PR does today): those never come from
recall, they resolve against code/GitHub/DB (see "recall ≠ current state" below). For the design/
decision/history questions it does cover, recall costs one command and routinely saves reading dozens
of files (or re-solving a solved problem).

```bash
polmem recall "cardaq deadline sprint"          # search everything
polmem recall "auth flow" --repo noemi-ai        # scope to one repo
polmem recall "pricing" --tag decision --top 8   # filter + widen
```

Recall ranks **titles/summaries/tags**, not full document bodies. If the first query returns weak hits,
**don't conclude "it doesn't exist"** — rephrase with words likelier to appear in a title, or open the
top candidate and read it. Recall is triage; the answer is in the doc you then read.

## recall ≠ current state (the contract that bites)

A wiki page tells you what was **decided/learned**, not what is **true right now**. Never cite a recall
result as proof of live state (what's deployed, what a PR does, what's in the DB) — that's **ASSUMED**.
Resolve current state against code, GitHub, or the database, and treat the page as background.

## Record what's worth keeping

```bash
polmem remember "Chose Hetzner over Railway" "Cost + control; revisit at 10 paying users" --kind decision
polmem remember "grep-only usage-drift misses renamed callers" "Use the LSP resolver in prod" --kind lesson
```

`--kind` is `decision` (a choice made, with the why), `lesson` (a mistake→rule, so it isn't repeated),
or `outcome` (a shipped result). A `remember` is recallable immediately in the same working tree.
Prefer recording at `/end`, which vets and commits these into shared history — teammates go blind on
uncommitted decisions/lessons.

## Find the memory behind a piece of code

```bash
polmem code src/pricing/engine.py     # which wiki pages reference this file/symbol
polmem code apply_discount
```

Reverse lookup via the `code_refs` join key — the fast way to answer *"what do we know about this
module before I touch it"*.

## Health (weekly, RED only)

```bash
polmem health     # queue, journals, stale servers, apex budget, sync state — read Monday, act on RED
```

## When NOT to use polmem

- To learn **current** state of a system → check code/GitHub/DB, not memory.
- As a substitute for reading the ranked doc → recall points you at the doc; still read it.
- Full-vault `grep` when recall exists → don't; recall is faster and ranked.
