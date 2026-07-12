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

## Non-negotiable boundary

`/plan-week` can create a proposal, but it cannot assign work. A CEO proposal stays non-executable
until its signature says so. `/start`, `/update`, `/end` and `/report` never create tracker work or
write outside the current product repository.
