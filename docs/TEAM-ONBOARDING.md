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

### GitHub CLI

The first `/start` resolves and caches your exact login through `gh`; `/plan-week` and `/report`
read delivery evidence through it. Without authenticated `gh`, those setup/evidence paths stop:

```bash
gh --version   # missing → install it (macOS: brew install gh; see cli.github.com)
gh auth status # not logged in → gh auth login
```

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
`python3` must be installed. `recall` only reads the repo you run it in; `remember` **writes** one
line to the repo’s committed journal — never put secrets, customer data or personal information in
it. `recall` is assumed context to verify, not current state.

## 4. Check the repo contract

The repository owns **one** Polaris root: `_polaris/`, committed with the code. The repository owner
provides:

```text
_polaris/config.yml
_polaris/decisions.md
_polaris/lessons.md              # optional but standard
```

Your own path is **not** pre-created for you. On your first `/start`, the plugin reads your exact
GitHub login (`gh api user --jq .login`) and creates:

```text
_polaris/team/<your-github-login>/profile.yml
_polaris/team/<your-github-login>/weeks/
_polaris/team/<your-github-login>/reports/
_polaris/team/<your-github-login>/sessions/
```

The folder name and the `github:` field in both `config.yml` and your `profile.yml` are your
**exact GitHub login** (case-sensitive) — the skills query `gh` by that string, so a nickname
silently returns no evidence. Never create a `team/` folder for a teammate: each person's path is
created on their machine by their own `/start`. If the root or `config.yml` is missing, ask the
repository owner — do not create the contract yourself.

> **Migrating from ≤0.4.4:** sessions moved from the shared `<root>/sessions/` to the per-contributor
> `<root>/team/<login>/sessions/` — move your own files: `git mv <root>/sessions/*-@<login>.md
> <root>/team/<login>/sessions/`. Repositories that carried a `polaris/` root (no underscore) or
> pre-created placeholder `team/` folders: the repo owner renames the root (`git mv polaris
> _polaris`) and deletes the placeholders — real paths are recreated by each contributor's `/start`.

## 5. First day

1. Open Claude Code from the product repo.
2. Run `/start`: read your authorized outcome, latest handoff/checkpoint, blocker, and next action.
3. Use the explicit Polaris status workflow when you need repo pulse, team collisions, memory, or a
   portfolio-wide view.
4. Before planning an ambiguous product or technical change, run `/polaris-grill`: it checks live
   repo evidence, durable decisions, backend/schema contracts, memory, and versioned Context7 docs,
   then hands off a testable brief without implementing or creating tracker work.
5. Run `/update` after real progress or a real blocker.
6. Run `/end` when you stop: leave one concrete next action.

## 6. The week

- Each contributor runs `/plan-week` for **their own** week — a focus grounded in real issues/PRs
  and capacity. Commit it and let it travel into your PRs: a plan visible in the repo is reviewable
  whenever the lead wants, which is the point.
- **It does not wait for a signature.** The lead reads it and may reorder or correct the scope —
  that is priority alignment, not permission, and their silence is not a block. You own bounded,
  reversible work: decide, proceed, and record `Decision / Why / Risk / Next step` in the issue or
  PR. Only **red** work waits for a **named** approver (access/RLS/auth expansion, personal-data
  use/retention/deletion, new processor/vendor, irreversible migration, legal/customer commitment,
  audited production promotion, material outcome/architecture change). If your repo ships a workflow
  charter (`profile.yml` → `workflow:`), that charter's boundaries win over this list.
- Each person maintains their own plan in the repo as reality changes.
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
