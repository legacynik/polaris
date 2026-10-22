# Polaris Team OS

Polaris Team OS is a repository-first operating model for a product team working in Claude Code. It
makes ownership, weekly outcomes, session handoffs and delivery evidence visible **from inside the
product repository** — the same place the code lives. Seven slash commands (`/start`,
`/polaris-status`, `/polaris-grill`, `/update`, `/end`, `/plan-week`, `/report`). It is
not a founder vault, an issue
tracker, or a second project manager: GitHub or Linear stays the source of execution truth, and
Polaris records who owns an outcome, why it matters, what proof closes it, and what is blocked.

## Install

In Claude Code:

```text
/plugin marketplace add legacynik/polaris
/plugin install polaris-team-os@polaris-team-os
```

`legacynik/polaris` is the public plugin marketplace; `polaris-team-os@polaris-team-os` is
`plugin@marketplace`. Restart Claude Code after installing or updating. The plugin ships **workflow
only** — never put project data, customer information, private decisions or repository-local state
into it. Then follow [`docs/TEAM-ONBOARDING.md`](docs/TEAM-ONBOARDING.md) from the product repository
for the one-time, per-machine setup.

For Codex, Cursor, Claude Code, and other Agent Skills clients, install the same versioned skills
through the Vercel Skills CLI:

```bash
npx skills add legacynik/polaris --list
npx skills add legacynik/polaris --skill '*' -a codex -a claude-code
```

The marketplace manifest declares all shipped skill paths, so the plugin and Skills CLI consume
the same `SKILL.md` files; there is no provider-specific duplicate.

`/pol-ship` is the one command once the work is done: real-test, commit hygiene, push, the PR body
(`/pol-pr`), the babysit loop (`/pol-babysit`) to the owner's label, then one merge-and-deploy
proposal it acts on only after the owner's yes. `/pol-pr` alone writes a PR body the owner judges
without reading code. `/retro`
reviews an agent session only when requested and proposes improvements; it does not silently
change CI or shared instructions. All of them ship in the same skills set as the session commands.

## The seven commands

| Command | One-line purpose |
|---|---|
| `/start` | Resume the authorized outcome from the latest local handoff/checkpoint; first use also provisions your own path. |
| `/polaris-status` | Explicit full portfolio/repository pulse, team collisions, freshness, memory and health. |
| `/polaris-grill` | Clarify an ambiguous product or technical change against live repo evidence, durable decisions, backend/schema contracts and versioned docs; emit an execution handoff without implementing. |
| `/update` | Leave a concise, verified checkpoint in the session log and weekly plan. |
| `/end` | Close a session with a handoff, decision proposals, and an optional pathspec-only commit. |
| `/plan-week` | Build **your own** weekly focus from live tracker issues and current ownership. |
| `/report` | Compare your plan with real delivery evidence from the tracker — planned versus actual. |

No bootstrap, generic development manifesto, or duplicate report command ships. `/polaris-grill`
is the read-only clarification gate; it proposes durable entries but never implements or mutates the
tracker. Full portfolio/repository pulse is explicit `/polaris-status`, not work paid on every
`/start`. `/plan-week` writes a plan and nothing else: it never creates issues, branches, PRs or
assignments. **The plan does not wait for a signature** — you own bounded, reversible work; the
lead reads and may reorder your focus (priority alignment, not permission), and only **red** work
waits for a **named** approver. `/start`, `/update`, `/end` and `/report` never create tracker work
or write outside the current product repository.

## The contract model

Each product repository carries **one** Polaris root: **`_polaris/`**. The contract is committed
with the code, so it travels with a `git clone` and is shared by the whole team:

```text
_polaris/                        # the Polaris root — one, committed with the code
├── config.yml                   # tracker.github_repo, optional linear_team, contributors[].github
├── team/
│   └── <github-login>/          # folder name == exact GitHub login (case-sensitive)
│       ├── profile.yml          # weekly_capacity, assignment_mode, preferred/excluded areas
│       ├── weeks/YYYY-Www.md    # weekly focus (from /plan-week) — yours, not a permission request
│       ├── reports/YYYY-Www.md  # weekly reports (from /report) — planned vs actual
│       ├── sessions/            # per-day handoffs (from /update and /end), committed
│       └── handoff/             # optional: rich multi-session handoff docs
├── decisions.md                 # durable decisions, append-only
├── lessons.md                   # durable lessons, append-only (optional but standard)
└── state/                       # ephemeral, gitignored (current.md — a live pointer only)
```

Per-contributor: sessions live under each contributor's own `team/<login>/sessions/`, same isolation
as `weeks/` and `reports/`, so contributors never write to a shared, collision-prone directory. Each
contributor's `team/<login>/` path is created **by their own first `/start`**, from the exact login
`gh api user` returns on their machine — never pre-created for someone else, never a nickname.

Templates for every one of these files ship in
[`polaris/skills/start/templates/repo-contract/`](polaris/skills/start/templates/repo-contract). Filenames are the ISO week
(`date +%G-W%V`, e.g. `2026-W29`), so plan and report line up by construction.

## Requirements

- **Claude Code** with plugin support.
- **`python3`** (3.8+) on PATH — the skills' scripts and the `/report` week computation use it.
- **`gh`** (GitHub CLI), authenticated (`gh auth status`) — first `/start` resolves and caches the
  contributor login; `/plan-week` and `/report` read the tracker through it. Recurring `/start`
  remains local. Optionally the Linear tooling if `tracker.linear_team` is set.
- **Superpowers** and **Context7** plugins for planning/delivery and live docs; **Sequential
  Thinking** and **Codebase Memory** MCP servers are declared by the plugin. See onboarding for the
  per-machine preflight. Polaris never silently installs tools, credentials, MCP servers or plugins.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/report` filed under the wrong ISO week | Run it on the Friday of the week you are reporting, or set `WEEK` explicitly (e.g. `WEEK=2026-W28`) — a rolling "7 days ago" straddles two ISO weeks. |
| `/report` finds no evidence for a teammate | The contributor's `github:` login must be the **exact** GitHub login (case-sensitive); the skill queries `gh` by that string. |
| `/start` or `/plan-week` stops on a missing contract | The repo has no committed Polaris root — follow onboarding; do not bootstrap a personal vault. |

## Versioning

Semantic-ish, tracked in [`CHANGELOG.md`](CHANGELOG.md). The current release is pinned in
`polaris/.claude-plugin/plugin.json`.
