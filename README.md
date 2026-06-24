# legacy

A complete, opinionated way of working for AI-assisted development — packaged as a
Claude Code plugin. Install it once; every repo gets the same setup: a persistent
memory layer, a battle-tested build process, and a single command that wires it in.

Two things ship together:

- **Polaris** — a file-based memory & session layer. Context, decisions, and lessons
  survive across sessions and machines instead of evaporating in a chat.
- **The team-workflow standard** — the *mantra* (how you build) and the *conduct*
  (how you ship), written once and portable to any repo.

---

## What is Polaris

Polaris is a **markdown-first PM operating system** for running one or several
repos — solo, or as a small team. No database, no SaaS: **priorities, memory,
decisions, and cross-repo state** live as plain files you (and your AI) can read,
review, and version. It's not a product — it's the founder's operating system, and
its core idea is **a place for every kind of thing**, so nothing gets lost in a chat.

**Per repo:**

```
_polaris/
  state/current.md     where you are now / today's priorities
  state/goals.md       the goals the work connects to
  sessions/            daily logs — what happened
  decisions.md         decisions made, append-only, with the why
  lessons.md           distilled lessons — the rules learned
```

Plus an optional **cross-repo vault** that aggregates every repo's state in one
place, so you see the whole portfolio.

**The lifecycle (3 commands):** `/start` loads context when you begin · `/update`
checkpoints mid-session · `/end` wraps up and surfaces decisions.

**The memory (3 layers):** raw **scratchpad** → distilled **lessons** (the rule, not
the incident) → the best ones promoted into **CLAUDE.md / a preflight gate**. The
system learns from corrections instead of forgetting them.

---

## Multiple contributors

Polaris is built for several people — and several parallel AI panels — on the same
repo. The rule: **personal/volatile state stays local or per-person; shared/durable
state is append-only and never clobbered.**

- **`state/current.md`** — your local "where I am now". It's **gitignored** (personal
  scratch): each contributor keeps their own, nobody's overwrites anybody's. (Want it
  shared instead? Split per person: `current-<name>.md`.)
- **`sessions/`** — daily logs are **per-contributor-per-day**: `2026-06-24-@gio.md`,
  `2026-06-24-@nik.md`. Each writes their own file → no collision, and the team sees
  everyone's.
- **`sessions/scratch/<contributor>/`** — raw scratchpad, namespaced by the
  contributor's git email → never shared, never clobbered.
- **`decisions.md` / `lessons.md`** — **append-only** (new blocks added, never
  rewritten) → concurrent edits merge cleanly, history is preserved.
- **`state/goals.md`** — shared, changes by explicit decision (not per-session) → low
  churn.

`/start` `/update` `/end` follow this: they **append** their checkpoint, they don't
rewrite the file — so N panels can checkpoint the same day without stepping on each
other.

---

## The skills

- **`/base-workflow`** — the always-on **build method**: read the code (code-graph),
  map dependencies, brainstorm, write a spec with error paths + fallbacks following
  clean architecture, plan, then build with strict TDD and 360° tests, fresh-eyes
  review, and a real test. Applied to any change that touches code.
- **`/start` · `/update` · `/end`** — the Polaris session lifecycle.
- **`/workflow-bootstrap`** — align a repo to the standard (see below).

The portable standard (mantra + conduct + core rules) lives in
`legacy/skills/workflow-bootstrap/assets/TEAM-WORKFLOW-STANDARD.md`.

---

## Running it on a repo

`/workflow-bootstrap` aligns any repo to the standard. It is **idempotent and
non-destructive** — safe on a fresh repo or one that's already set up, because it
respects what's already there instead of clobbering it:

- **MCPs already configured** — it checks what's present (global + project) and adds
  only the missing core ones (code-graph, context7, sequential-thinking). No
  duplicates.
- **Domain plugins** — it detects the stack (AWS, Odoo, Vercel, Supabase, Stripe…)
  and **enables the matching plugin only if it isn't already on**. For a stack with
  no plugin, it falls back to live docs via context7 — nothing is hardcoded, so
  nothing goes stale.
- **Existing skills** — it creates none. The plugin's skills coexist with yours
  (plugin skills are namespaced, so there's no name collision).
- **Existing files** — `CLAUDE.md`, `_polaris/`, `docs/TEAM-WORKFLOW.md`: it
  **integrates and tightens, never overwrites**. A CLAUDE.md that's already there
  gets sharpened; a `_polaris/` that exists gets its gaps filled.

Rerun it anytime — it only ever fills what's missing.

---

## Install

```
/plugin marketplace add legacynik/legacy-plugin
/plugin install legacy@legacy
```

Then, in any repo: `/workflow-bootstrap` to align it, `/start` to begin a session.

---

## The two layers

- **Layer 0 (this plugin):** the method + the memory. Installed everywhere.
- **Layer 1 (Archon, separate):** the autonomous loop that *executes* the mantra over
  the agent-ready pool. Optional, per repo.

> The cross-repo vault path and the launchd auto-runners (wiki indexing, lesson
> distillation) are machine-specific — set up per machine; the bootstrap wires them
> when present.
