# Polaris

Polaris is a Claude Code plugin that installs a working method: a session
lifecycle (`/start` · `/update` · `/end`), a repo-local memory CLI (`polmem`),
and a bootstrap skill that wires the rest — MCP servers, team settings, and a
`CLAUDE.md` — into any repo. Install it once; every repo you bootstrap gets
the same setup.

---

## Install

```
/plugin marketplace add legacynik/polaris
/plugin install polaris@polaris
```

### Prerequisites

- **`node` / `npx`** on PATH — the plugin runs `context7` and
  `sequential-thinking` via `npx -y ...`.
- **`python3`** on PATH — the `polmem` CLI and the memory bundle it talks to
  are plain-stdlib Python.
- **`codebase-memory-mcp` on PATH (optional)** — the plugin's manifest wires
  a `codebase-memory` MCP server unconditionally. If the binary isn't
  installed, that one server fails to start; everything else in the plugin
  (skills, `polmem`, the other two MCP servers) still works. Install it
  separately if you want the code-graph capability.

---

## Teammate onboarding

1. Install the plugin (commands above).
2. Clone the product repo you'll be working in — one that's already been
   through `/pol-bootstrap` (ask whoever owns it if you're not sure).
3. Open Claude Code in that repo.
4. Run `/start`.

`/start` loads whatever is present — repo-local state always, memory recall
if the repo is wired for it, cross-repo context if a vault is configured.
Nothing errors if a piece is missing; it just skips that section.

---

## The two legs

Polaris deliberately splits into two things that install differently:

| | Comes from the **plugin** (installed once, global) | Comes from the **product repo** (per repo, via `git clone`/`pull`) |
|---|---|---|
| Skills | `start`, `update`, `end`, `pol-report`, `pol-base-workflow`, `pol-bootstrap` | — |
| MCP servers bundled | `context7`, `sequential-thinking`, `codebase-memory` | `polaris-memory` (repo-specific — lives in that repo's `.mcp.json`, not in the plugin) |
| Memory data | — | `.wiki/` (index + journal) and `scripts/polaris_memory_repo.py`, the bundle `polmem` talks to |
| Project rules | — | `CLAUDE.md`, `.claude/rules/`, `_polaris/decisions.md`, `_polaris/lessons.md` |
| CI gates | — | whatever the repo owner wired (e.g. a pre-commit smoke gate on the memory bundle) |
| Team permissions | `templates/settings.team.json` (the template) | `.claude/settings.json` (installed/merged by `/pol-bootstrap`) |

The plugin gives every repo the same *method*. The product repo carries its
own *memory and rules* — that's why cloning the repo, not just installing the
plugin, is step 2 of onboarding.

---

## Skills

All six skills are namespaced so they never collide with a repo's own
skills, and every one of their descriptions starts with `Polaris skill —` —
search `polaris` in your skill picker to find all six at once.

- **`/start`** — load context at the beginning of a session: repo-local
  state always, plus cross-repo portfolio context and memory recall when
  available.
- **`/update`** — mid-session checkpoint. Saves progress, no commit.
- **`/end`** — close a session: saves state, surfaces decisions, offers a
  commit.
- **`/pol-report`** — weekly report of the current repo, built from
  `_polaris/sessions/`, decisions, and `git log`.
- **`/pol-base-workflow`** — the always-on build method (understand the
  code, spec, strict TDD, real test) for any change that touches code.
- **`/pol-bootstrap`** — align a repo to the standard: Polaris structure,
  team settings, MCP servers, domain plugins, `CLAUDE.md`. Idempotent —
  rerun anytime.

Naming convention: the three session-lifecycle skills keep their short names
(`start`/`update`/`end`) for fast typing; everything else is prefixed
`pol-*` to stay unambiguous.

---

## `polmem` — the memory CLI

`polaris/bin/polmem` is a thin, stdlib-only CLI that speaks JSON-MCP to
whatever memory bundle the *current repo* ships at
`scripts/polaris_memory_repo.py`. It doesn't carry any memory itself — it's
a shim onto the product repo's own bundle (see "the two legs" above).

```
polmem recall "pricing calibration" --top 5
polmem remember "decided to cap retries at 3, see incident 2026-07-02"
polmem health
```

- `recall` — keyword search weighted on page frontmatter (title/summary/tags)
  over the repo's `.wiki/` — no embeddings, no vector index.
- `remember` — writes a journal entry (unreviewed capture, distilled later).
- `health` — reports the bundle path, whether `.wiki/index.md` exists, and
  how many journal entries are pending.

If the repo isn't memory-wired (no `scripts/polaris_memory_repo.py` up the
directory tree from where you run it), every subcommand except `init` prints:

```
this repo is not memory-wired (no scripts/polaris_memory_repo.py) —
ask Niccolò or run: polmem init
```

and exits 1. `polmem init` explains the situation — in this v0, teammates
are consumer-only (recall + remember against a repo the founder's machine
already writes to); there's nothing to activate on your end.

---

## For repo owners

Run `/pol-bootstrap` in a repo to align it to the standard: it sets up the
`_polaris/` structure, installs/merges `.claude/settings.json` from
`templates/settings.team.json`, adds the missing core MCP servers, detects
the stack and enables matching domain plugins, and writes or tightens
`CLAUDE.md`. It's idempotent — safe to rerun, and it never overwrites what's
already there.
