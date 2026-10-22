# Polaris

Polaris is a set of agent skills that carry a product team from an ambiguous idea to a merged,
deployed and verified change, with the evidence kept in the product repository and on GitHub. The
skills define the work (outcome, Definition of Done, domain terms), build it test-first, prove it on
a real environment, review it on two separate axes, and ship it through one PR chain that merges and
deploys only on its owner's yes. Session skills (`start`, `update`, `end`) keep a handoff in the
repository so the next session, or the next person, resumes without a transcript. Each skill adapts
to a repository through that repository's `_polaris/config.yml`; GitHub stays the source of truth for
issues and PRs.

## Install

```bash
npx skills add legacynik/polaris -g --skill '*'
```

This installs every skill globally into `~/.agents/skills` and links it into each agent CLI on the
machine (Claude Code, Codex, Cursor and the other clients the skills CLI supports). Then follow
[docs/TEAM-ONBOARDING.md](docs/TEAM-ONBOARDING.md) once per machine and per product repository.

Requirements: `git`, `python3` 3.8+, and an authenticated GitHub CLI (`gh auth status`).
`codex-review` also needs the Codex CLI on `PATH`; `reference-capture` uses `yt-dlp` for videos.

<details>
<summary>Other harnesses</summary>

**Claude Code plugin.** The same `SKILL.md` files are published as a plugin marketplace:

```text
/plugin marketplace add legacynik/polaris
/plugin install polaris-team-os@polaris-team-os
```

Restart Claude Code afterwards. Use either the plugin or the skills CLI on one machine, not both:
the same skill installed twice is listed twice.

**A harness the skills CLI does not support.** Clone this repository and point the harness at
`polaris/skills/`. Skills find their own scripts and templates through
`${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/<skill>/`, so set `CLAUDE_PLUGIN_ROOT` to the clone's
`polaris/` directory.

</details>

## Update

```bash
npx skills update -g -y
```

**Upgrading from an earlier release:** six skills were retired or renamed (`review` is now
`polaris-review`, `pr` is folded into `pol-pr`). The update does not delete them; remove them once:

```bash
npx skills remove -g skill-meta pol-apex-curate pol-adr pr polaris-memory review
```

## Skills

28 skills, grouped by the phase they serve. "Auto" means the agent may load the skill on its own
when the trigger matches; "on request" means only when you name it. The full reference, with what
each skill invokes, the config keys it reads and what it never does, is
[docs/skills.md](docs/skills.md).

### Define

| Skill | What it does | When it fires |
|---|---|---|
| `polaris-grill` | Interviews you against live repo evidence until an ambiguous change is decision-complete, then hands off a brief. | "grill this idea", "clarify this feature", an ambiguous requirement before planning |
| `ambitious-goal` | Turns a feature or epic into one outcome, a scope and a verifiable Definition of Done. | Auto, when scope or acceptance evidence needs sharpening |
| `domain` | Settles one question of domain language or boundary: canonical term, subdomain type, integration pattern, context map. | Auto, on an overloaded term or two contexts that must integrate |
| `issue-contract` | Opens or updates a GitHub issue with a Definition of Done, regression checks and a checked AFK label. | Auto, "open an issue", "track this bug", handing work to another lane |
| `init` | Audits an existing repository and writes its first `CONTEXT.md`, `ARCHITECTURE.md` and `DOMAIN.md`. | On request, the first time a repository has no typed backbone |

### Plan

| Skill | What it does | When it fires |
|---|---|---|
| `architecture` | Decides one architectural commitment, reversibility first, and records it with its cost and enforcement. | Auto, when a change moves a boundary, interface, data contract or dependency |
| `database-schema` | Reads the real schema (migrations, models, generated types) and checks every column a task will touch. | Auto, before any query, migration, model, RLS policy or data fix |
| `plan-week` | Builds your own weekly focus from live tracker issues and current ownership. | Start of the week, "plan my week" |
| `reference-capture` | Writes one canonical, actionable dossier for an external source already read (video, repo, article, release). | On request, "index this", a transcript with no dossier |

### Build

| Skill | What it does | When it fires |
|---|---|---|
| `base-workflow` | Fixes the order of any code change (understand, spec, test first, verify, ship) and routes each step to its skill. | Auto, before writing any change that touches code |
| `tdd-dev` | Drives one change through an observed RED, the minimum implementation, GREEN and the regression suite. | Auto, a feature test-first or a reproducible bug through a regression test |
| `bugfix` | Closes a bug in four gated phases: find without assuming, fix with TDD, prove the consequence, rewrite the tests that lied. | Auto, a traceback, a bug issue, a red smoke, "this doesn't work" |

### Verify

| Skill | What it does | When it fires |
|---|---|---|
| `real-testing` | Serves the commit on a real environment, walks the user journey, lets a fresh agent try to break it, returns a merge-readiness verdict. | Auto, before merge or promotion, or when someone says "it works" |
| `crasher` | Drives a deployed app like a user, confirms crashes and proposes one deduplicated issue each; files only the ones a person picks. | On request, "does staging still work", "smoke the deployment" |

### Review

| Skill | What it does | When it fires |
|---|---|---|
| `polaris-review` | Reviews a diff on two separate axes, Standards and Specification, with the reviewer tier picked from the diff. | Auto, before a commit or merge |
| `codex-review` | Runs an independent, read-only Codex review on a diff and keeps only the findings checked against the source. | On request, a risky diff or a cross-model second opinion |
| `critic` | Attacks a diff, spec, plan or claim from fresh context and returns only quoted, falsified findings. | On request, before promoting a non-mechanical artifact |
| `polaris-sweep` | Reviews one PR end-to-end and posts one durable review comment with an exit-code verdict. | On request or from a scheduled trigger polling new PRs |

### Ship

| Skill | What it does | When it fires |
|---|---|---|
| `pol-ship` | The single entry point once work is done: runs the whole PR chain, then proposes merge and deploy with a rollback plan. | Auto, "ship it", "open the PR", "finish this branch" |
| `pol-pr` | Writes a PR body the owner can judge without reading code: verdict, every criterion with proof, visual, risk. | Auto, before `gh pr create` or `gh pr ready` |
| `pol-babysit` | Drives an open PR to the owner's label on its current head, or hands off what only the owner decides. | Auto, after a PR is opened or pushed, "get this PR green" |
| `git-power` | Guards every commit, PR boundary and destructive Git action; censuses and safely closes worktrees and branches. | On request and from other skills, before a commit, a PR or a `reset --hard` |

### Session

| Skill | What it does | When it fires |
|---|---|---|
| `start` | Resumes the current objective from your latest local handoff; the first run creates your own team path. | Start of a session, `/start` |
| `update` | Appends a checkpoint to your session log and rewrites your lane in the cockpit. | After real progress, a blocker or a context switch, `/update` |
| `end` | Closes the session: handoff, decisions and lessons to the repo ledgers, plan tick, pathspec-only commit. | When you stop, `/end` |
| `polaris-status` | Full repository or portfolio pulse: live Git and GitHub state, outcomes, collisions, freshness. | On request, "polaris status" |
| `report` | Weekly report for a finished week: planned versus actual, every claim linked to evidence. | End of week, "weekly report" |
| `retro` | Reviews a coding session and proposes improvements to navigation, checks and information access. | On request only |

## How a repository adapts

Commit `_polaris/config.yml` in the product repository (template:
[polaris/skills/start/templates/repo-contract/config.yml](polaris/skills/start/templates/repo-contract/config.yml)).
These are the keys the skills read; a skill that needs a missing key says so instead of guessing.

| Key | Read by | Meaning |
|---|---|---|
| `tracker.github_repo` | `plan-week`, `report` | `owner/name` of the issue tracker |
| `tracker.linear_team` | `plan-week` | optional Linear team; `null` when GitHub is the only tracker |
| `tracker.afk_human`, `tracker.afk_agent` | `issue-contract` | label names for work a person must do and work an agent may claim |
| `outputs.<kind>` | `architecture`, `domain`, `critic`, `crasher`, `real-testing`, `polaris-review`, `base-workflow`, `init`, `end`, `pol-pr`, `pol-ship` | where each kind of document lands: `spec`, `plan`, `audit`, `review`, `validation`, `diagram`, `decision`, `archive` |
| `review.risk_paths` | `polaris-review` | one regex of paths that always get the strongest reviewer tier |
| `ship.*` | `pol-ship`, `pol-babysit`, `real-testing` | `verify`, workflows, environments, `rollback`, `owner_label`, `checks_not_gating`, `inert_paths`, `signing_env`, optional `version_file`, `changelog`, `flags`, `slo` |
| `real_test.*` | `pol-ship` | `deploy_staging_workflow`, `deploy_prod_workflow`, `health`, `smoke`, `rollback` |

`bugfix` reads its own contract, `.fix/contract.yml`, whose template ships with the skill. Each
contributor's `_polaris/team/<login>/profile.yml` (created by their first `start`) carries the
login, language, capacity and areas.

## The PR chain

1. Work is done: run `pol-ship`, the only entry point.
2. Locally, until the Definition of Done holds: tests, `polaris-review` at the tier the diff calls for, `real-testing` on the branch.
3. `git-power` checks the commits and pushes a draft PR; `real-testing` signs the head on staging.
4. `pol-pr` writes the body, and `pol-babysit` drives the PR to the owner's label on its current head.
5. `pol-ship` sends one merge-and-deploy proposal with its rollback plan and acts only on the owner's yes; it never merges on its own.

## More

- [docs/skills.md](docs/skills.md): the reference for every skill.
- [docs/TEAM-ONBOARDING.md](docs/TEAM-ONBOARDING.md): first-day setup for a contributor.
- [CHANGELOG.md](CHANGELOG.md): what changed, release by release.
- [CONTRIBUTING.md](CONTRIBUTING.md): how to propose a skill change and the gates it must pass.
- [CREDITS.md](CREDITS.md): the upstream work the skills build on.
