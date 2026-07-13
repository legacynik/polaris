# Polaris Team OS — team onboarding

This is the day-one checklist for a person opening a product repository for the first time. The
README covers *what* Polaris is; this covers *what you run* to get set up. If a command below fails,
stop and report the blocker — do not create a personal vault or improvise a second configuration.

## 1. Install the plugin

`legacynik/polaris` is the public plugin marketplace. The plugin contains workflow only — never put
project data, private decisions, customer information or repository state into it. In Claude Code:

```text
/plugin marketplace add legacynik/polaris
/plugin install polaris-team-os@polaris-team-os
```

Restart Claude Code, then verify:

```bash
claude plugin list
```

You must see `polaris-team-os@polaris-team-os` enabled.

## 2. Tool preflight — once per machine

### Superpowers

Polaris does not replace Superpowers — it uses it for planning and delivery when the work needs code.
Install/verify the official plugin:

```text
/plugin install superpowers@claude-plugins-official
```

Confirm with `claude plugin list`. If the official marketplace is not available in your install, ask
the maintainer for the configured marketplace command — do not guess an ID.

### Context7

Context7 provides up-to-date SDK and library documentation:

```text
/plugin install context7@claude-plugins-official
```

### Plugin MCP servers

Polaris declares Sequential Thinking and Codebase Memory; Context7 comes from the official plugin
above. After the restart, check the real connection state, not just the file:

```bash
claude mcp list
```

They must show connected or carry an explicit reason. `codebase-memory` also needs the
`codebase-memory-mcp` binary. If `claude mcp list` reports it missing, install it with your machine's
Python manager (for example `pipx install codebase-memory-mcp`), then re-run `claude mcp list`. Never
store keys or credentials in the repo.

## 3. Put `polmem` on your PATH

`polmem` is the repo's memory CLI: it runs `recall` over what the repo already knows (decisions,
references, architecture, journal committed in `.wiki/`). **The CLI is the interface you use.** The
MCP adapter is optional; the CLI is the reliable path.

Install the launcher once per machine (a version-independent shim at `~/.local/bin/polmem`):

```bash
bash "$CLAUDE_PLUGIN_ROOT/polaris/scripts/install-polmem-cli.sh"
```

If it reports that `~/.local/bin` is not on your PATH, add to your shell profile:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

Then, from inside a memory-wired product repository, verify:

```bash
polmem health
polmem recall "confirmation gate"
```

`recall` returns ranked entries — score, source path, title, one-line summary. The three day-one
commands are `polmem recall "<query>"`, `polmem health`, `polmem remember "<short note>"`. If
`recall` says the repo is not memory-wired, `git pull` (the `.wiki` is committed and arrives with the
code); if it is still missing, ask the repo owner to wire it — **do not run `polmem init` yourself**.
`python3` must be installed. `polmem` only reads the repo you run it in, and `recall` is assumed
context to verify, not current state.

## 4. Check the repo contract

The repository owns **one** root: `polaris/` or `_polaris/`. It must contain:

```text
<root>/config.yml
<root>/team/<your-github-login>/profile.yml
<root>/team/<your-github-login>/weeks/
<root>/team/<your-github-login>/reports/
<root>/team/<your-github-login>/sessions/
<root>/decisions.md
```

> **Migrating from ≤0.4.3:** sessions moved from the shared `<root>/sessions/` to the per-contributor
> `<root>/team/<login>/sessions/`. Move your existing files: `git mv <root>/sessions/*-@<login>.md
> <root>/team/<login>/sessions/`.

Your `team/<login>/` folder name and the `github:` field in both `config.yml` and your `profile.yml`
must be your **exact GitHub login** (case-sensitive) — the skills query `gh` by that string, so a
nickname silently returns no evidence. If the profile or root is missing, ask the repository owner.
Do not run a bootstrap and do not create a personal Polaris folder.

## 5. First day

1. Open Claude Code from the product repo.
2. Run `/start`: read your outcome, proof, blockers, and other people's ownership.
3. Before proposing a branch, check your plan and the work already active.
4. Run `/update` after real progress or a real blocker.
5. Run `/end` when you stop: leave one concrete next action.

## 6. The week

- The CEO or lead runs `/plan-week` for a proposal grounded in real issues/PRs and capacity.
- A CEO proposal with `ceo_signature: pending` **does not authorize work**.
- After sign-off, each person maintains their own plan in the repo.
- At week end, `/report` compares plan versus reality: deliveries, proof, blockers, next priority.
  Run it on the Friday of the week you are reporting (or set `WEEK` explicitly for a past week).

### Minimal example

```md
# Week 2026-W29 — @octocat

## Outcome
Make the confirmation gate verifiable, with staging proof.

| Issue | Status | Proof |
|---|---|---|
| #573 | in review | PR + staging test |

## Not starting
- New features until #573 is verifiable.
```

The report never counts messages or tokens: it states what was planned, what was actually delivered,
and what is needed to close the rest.
