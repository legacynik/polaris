# Polaris Team OS

Polaris Team OS is a small, repository-first workflow for a product team. It makes ownership,
weekly outcomes, session handoffs and delivery evidence visible from the product repository.

It is not a founder vault, an issue tracker or a second project manager.

## The five commands

| Command | Purpose |
|---|---|
| `/start` | Read the person’s active plan, ownership, decisions and relevant memory before acting. |
| `/update` | Leave a concise checkpoint in the session and weekly plan. |
| `/end` | Close a session with a handoff and an optional commit proposal. |
| `/plan-week` | Prepare a capacity-bounded proposal from live tracker evidence. |
| `/report` | Compare the approved plan with actual delivery evidence. |

No bootstrap command, generic development manifesto or duplicate report command is shipped.

## Install

```text
/plugin marketplace add legacynik/polaris
/plugin install polaris-team-os@polaris-team-os
```

`legacynik/polaris` is the public plugin marketplace. It ships workflow only: never put project
data, customer information, private decisions or repository-local state into this plugin. Restart
Claude Code after installing or updating a plugin. Then follow
[`docs/TEAM-ONBOARDING.md`](docs/TEAM-ONBOARDING.md) from the product repository.

## What belongs in a product repository

Each product keeps one existing root, never two:

```text
_polaris/ or polaris/
  config.yml
  team/niccolo/{profile.yml,weeks/,reports/} # example only
  sessions/
  decisions.md
  lessons.md
  state/                     # only ephemeral local files are ignored
```

GitHub or Linear remains the execution tracker. Polaris records who owns an outcome, why it
matters, what proof is needed and what is blocked.

## Tooling

Context7 is installed from its official plugin. Polaris declares Sequential Thinking and Codebase
Memory. The team workstation still needs a one-time preflight; see the onboarding document. Polaris
does not silently install tools, credentials, MCP servers or domain plugins.

## polmem — the repository's memory

`polmem` is a small command-line tool that recalls what a repository already knows. It reads the
repository's committed `.wiki/` (decisions, references, architecture, journal) and returns the most
relevant entries for a query — no server, no account, no external call. **The CLI is the interface
teammates use.** Polaris ships an MCP adapter too, but it is optional; the `polmem` command is the
reliable path.

One-time setup (adds `polmem` to your shell PATH):

```bash
bash "$CLAUDE_PLUGIN_ROOT/polaris/scripts/install-polmem-cli.sh"
```

The three commands that matter on day one, run from inside a memory-wired product repository:

```bash
polmem recall "confirmation gate"   # rank the repo's memory for a query
polmem health                       # confirm the repo is wired (bundle + index + journal)
polmem remember "short note"        # append a durable note to the repo journal
```

`recall` returns ranked entries — score, source path, title, and a one-line summary:

```text
$ polmem recall "confirmation gate" --top 3
[70] _polaris/decisions.md#2026-05-07 — Production runtime = ECS Fargate + Terraform …
[70] references/cardaq-gateway-integration — Cardaq Gateway Integration …
[70] synthesis/orbit-adversarial-gate-framework — Orbit Producer/Validator/Gate Framework …
```

If `recall` says the repo is not memory-wired, `git pull` (the `.wiki` is committed and arrives with
the code). `python3` must be installed. `polmem` is repository-scoped: it only ever reads the repo
you run it in.

## Non-negotiable boundary

`/plan-week` can create a proposal, but it cannot assign work. A CEO proposal stays non-executable
until its signature says so. `/start`, `/update`, `/end` and `/report` never create tracker work or
write outside the current product repository.
