---
name: workflow-bootstrap
description: >
  Bootstrap the standard way of working into ANY repo (Polaris OS + team workflow
  + MCP + domain plugins). Use it when you enter a new repo or want to align one to
  the standard: it sets up the Polaris structure (state, sessions, decisions,
  lessons, scratchpad via Loop B), installs the TEAM-WORKFLOW standard (the "mantra"
  + conduct), writes a blunt powerful CLAUDE.md, wires the issue/triage flow, adds
  the core MCPs (code-graph, context7, sequential-thinking) + superpowers, and
  enables the right domain plugins (AWS, Odoo, Vercel, Stripe, Supabase…) by
  detecting the stack. Trigger it when the user says "set up the workflow",
  "bootstrap this repo", "mount Polaris here", "align to the standard", "prep the
  repo", or enters a repo missing the Polaris/decisions/lessons machinery. It is
  idempotent: rerun anytime, it won't break what's already there.
user-invocable: true
---

# Workflow Bootstrap

Mount the whole way of working into a repo, **idempotently** (safe to rerun) and
**stack-adaptive**. It does not reinvent: it orchestrates the existing Polaris
installers and enables plugins/MCPs that already exist.

Principle: this skill is a **thin detection + orchestration layer**. Domain
knowledge lives in the plugins and in context7 (always live), never hardcoded here
— so it never goes stale.

VAULT = the cross-repo `_polaris/` folder (usually `~/Desktop/All Vibe Proj/_polaris/`).
If you can't find it, ask the user where it is.

## 1. Understand where you are

- `git rev-parse --show-toplevel`, `git log --oneline -20`.
- Read `CLAUDE.md` / `README*` / `docs/DECISIONS.md` if present.
- **Detect the stack** from markers (needed for steps 3-4):

| Marker in repo | Domain | Plugins / skills to enable |
|---|---|---|
| `cdk.json`, `*.tf`, `aws-sdk`, `serverless.yml` | AWS / IaC | `aws-dev-toolkit`, `deploy-on-aws`, `cicd-automation` |
| `__manifest__.py`, `addons/` | Odoo | `odoo`, `odoo-<version>` |
| `vercel.json`, `next.config.*` | Next.js / Vercel | `vercel` |
| `supabase/`, `@supabase/*` | Supabase | `supabase` |
| `stripe` in deps | Stripe | `stripe` |
| `expo`, RN `app.json` | Expo / React Native | `expo` |
| `pyproject.toml` / `requirements.txt` | Python backend | (core only) |
| no match | unknown | → **context7 fallback** (step 3) |

Add rows when you meet a new domain that has an existing plugin: this table is the
only thing maintained by hand, and it's small.

## 2. Core (always) — MCP + superpowers

These are needed everywhere (confirmed by real usage — superpowers + code-graph +
linear + context7 top every repo):

- **superpowers** (skill plugin) — the backbone of the mantra: brainstorming,
  writing-plans, subagent-driven-development, test-driven-development,
  finishing-a-development-branch. Ensure it's installed/available.
- **code-graph** — the "code-graph" mantra step. **Default: codebase-memory** (recommended — self-contained, indexes the repo into a queryable graph; no external DB). Power alternative: CodeGraphContext (`cgc`) — richer Cypher but needs the `cgc` binary + a graph backend (Neo4j).
- **context7** — live docs for libraries/SDKs (for "documentation" + domain fallback).
- **sequential-thinking** — structured reasoning.
- **linear** (or the repo's tracker) — issues as the work contract.

They're probably already in the global config. Verify; if a repo wants them
project-scoped, add to `.mcp.json` / `.claude/settings.json`. Don't duplicate
(idempotency).

### 2b. Installing the missing ones

Verify first with `claude mcp list`; add ONLY what's missing (idempotent). Keys
always via env/placeholder, never committed.

- **code-graph (default = codebase-memory):** a standalone Python MCP server
  (`codebase-memory-mcp`). Install it (pip/pipx per its package), then
  `claude mcp add codebase-memory -- codebase-memory-mcp`; it indexes the repo
  into the graph itself (no external DB). Recommended for the mantra step.
  The companion `codebase-memory` skill (query-syntax guidance) is OPTIONAL —
  base-workflow already triggers the code-graph step, so the MCP alone suffices.
  Power alternative — CodeGraphContext: `claude mcp add CodeGraphContext -- cgc mcp start`
  (requires the `cgc` binary **and** a graph backend such as Neo4j).
- **sequential-thinking:** `claude mcp add sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking`
- **context7:** via the Claude plugin marketplace (hosted), or `npx -y @upstash/context7-mcp` (API key via env).
- **superpowers / linear:** via the plugin marketplace.

Don't hardcode one machine's exact server config into this plugin — name the
tool + canonical install, and let the host's global config win where it exists.

## 3. Domain plugins (cascading, no hardcoding)

1. **Known domain** (table match) → enable the existing plugin. Don't generate
   knowledge: the plugin already has it, kept current.
2. **No plugin for the domain** → **context7 fallback**: when needed, pull the
   library's live docs via context7 instead of writing knowledge here. This is the
   "generate from documentation" path — on the fly, always fresh.

Note in `current.md` (step 7) which plugins you enabled.

## 4. Polaris OS

If the repo lacks the structure, mount it by calling the VAULT installers (do NOT
rewrite them — read them first):

```bash
bash "$VAULT/scripts/install-team-member.sh"   # contributor wiring (scratchpad, identity)
bash "$VAULT/scripts/install-hook.sh"          # hooks: Stop→scratchpad, post-commit→distill (Loop B)
```

Then ensure these exist (create the missing ones, empty or with a header):
```
_polaris/state/current.md      _polaris/state/goals.md
_polaris/sessions/             _polaris/sessions/scratch/
_polaris/decisions.md          _polaris/lessons.md
_polaris/weekly/
```
This gives decisions, lessons, scratchpad, sessions — the Polaris OS.

## 5. CLAUDE.md — blunt, powerful, not verbose

Every repo needs a CLAUDE.md that is **short, sharp, and load-bearing** — not a
wall of text nobody reads. Generate (or tighten) one with:
- the 3-5 hard rules that actually matter for this repo (from the standard + repo specifics);
- pointers (one line each) to: TEAM-WORKFLOW, DECISIONS, the mantra, Polaris;
- the repo's non-negotiables (multi-tenancy, security, stack constraints) in 1 line each.

Rule of thumb: if a line isn't load-bearing, cut it. No filler, no pleasantries.

## 6. Team workflow

- The **standard** lives in the VAULT as `TEAM-WORKFLOW-STANDARD.md` (the mantra +
  conduct + core rules). If missing in the vault, copy it from this skill's
  `assets/TEAM-WORKFLOW-STANDARD.md`.
- Create/update the repo's `docs/TEAM-WORKFLOW.md` as a **thin layer**: one line
  pointing to the standard + ONLY the repo's technical specifics. Detect or ask:
  lint/type/test commands, staging URL, test user, deploy command, stack.

The standard already enforces **short-lived branches** (rule 4: merge to main right
after the real-test gate → small, fast-to-resolve conflicts for everyone). Make
sure the repo layer states its real-test gate concretely.

## 7. Issue & triage flow

Wire the issue lifecycle — don't reinvent, point to the existing skills:
- **Create**: use `to-issues` (break a plan/PRD into independently-grabbable issues)
  or `triage-issue` (bug → root cause → issue with a TDD fix plan).
- **Triage**: `daily-triage` decides the day's `agent-ready` pool (pull-based, human
  gate before any autonomous loop).
- **Attribution**: every issue gets a single end-to-end owner at creation; tracker =
  control plane, GitHub = execution.
- **Dependencies**: map `depends-on` between issues (an issue blocked by another is
  not `agent-ready`). Record the dependency in the issue (and in `current.md`) so
  the order is explicit, not discovered mid-flight.

## 8. Seed the state

Write an initial `_polaris/state/current.md` from `git log` + existing sessions:
recent work, open threads, what's in flight. Keep it under 100 lines.

## Optional module: Archon (autonomous loop)

Archon is the **autonomous execution** layer (runs agents over `agent-ready`
issues — Archon + Polaris Sweep). It's separate from the foundation: the foundation
always goes in, Archon **only if you want the repo to run on its own**.

- **Off by default.** Wire it only if the user explicitly asks for that repo.
- When wired: it starts from the hand-picked `agent-ready` pool (the `/daily-triage`
  gate), never free-picking. Tracker = control plane, execution on GitHub.
- Known operational caveats: the cron can die silently, and Archon can conflict with
  other runners that already own the Claude invocation — check before turning it on.

## Don't

- **No bonus/feedback docs.** Compensation and evaluation are private (the user
  handles them verbally / in `_private/`). This skill never generates or touches them.
- Don't overwrite what exists: update/integrate, stay idempotent.

## Wrap-up

Summarize what you mounted: MCPs activated, domain plugins enabled, Polaris
structure created, CLAUDE.md + `docs/TEAM-WORKFLOW.md` written, issue/triage flow
wired. Then suggest `/start` for the first briefing.
