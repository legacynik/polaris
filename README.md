# Polaris

Polaris is a set of agent skills that carry a piece of work from an ambiguous idea to a merged,
verified change, with every decision, plan and proof kept in the product repository and on GitHub.
The size of the work picks the path: a small change goes test-first straight to a pull request; a
large one is grilled, prototyped, planned, built phase by phase and shipped through one PR chain
that merges only on its owner's yes. The skills work in Claude Code, Codex and any agent CLI the
skills CLI supports, and adapt to each repository through its `_polaris/config.yml`.

## Install

```bash
npx skills add legacynik/polaris -g --skill '*'
```

This installs every skill into `~/.agents/skills` and links it into each agent CLI on the machine.
Then follow [docs/TEAM-ONBOARDING.md](docs/TEAM-ONBOARDING.md) once per machine and per product
repository.

**Hard requirements** (a skill that needs one stops and says how to install it): `git`, `gh`
(authenticated), `python3` ≥ 3.9, and [Beads](https://github.com/gastownhall/beads) (`bd`) for
`plan-area`, `implement-plan`, `issue-contract` and the gates.
**Optional** (the skill degrades and says what it skipped): Serena, Context7, Sequential Thinking
and ai-memory as MCP servers; `browser-harness` for the UI walks of `real-testing` and `crasher`.

<details>
<summary>Claude Code plugin, other harnesses</summary>

**Claude Code plugin.** The same `SKILL.md` files are published as a plugin marketplace:

```text
/plugin marketplace add legacynik/polaris
/plugin install polaris-team-os@polaris-team-os
```

Use either the plugin or the skills CLI on one machine, not both: the same skill installed twice is
listed twice.

**A harness the skills CLI does not support.** Clone this repository and point the harness at
`polaris/skills/`. Skills find their own scripts through
`${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/<skill>/`, so set `CLAUDE_PLUGIN_ROOT` to the clone's
`polaris/` directory.

</details>

## Update

```bash
npx skills update -g -y
```

**Upgrading from a release before 2026-10-26:** fourteen skills were renamed, merged or retired.
The update does not delete them; remove them once:

```bash
npx skills remove -g ambitious-goal codex-review plan-week pol-babysit pol-pr pol-ship \
  polaris-grill polaris-review polaris-status polaris-sweep reference-capture report retro update
```

| Was | Now |
|---|---|
| `polaris-grill` · `polaris-review` · `polaris-status` | `grill` · `review` · `status` |
| `pol-ship` · `pol-pr` · `pol-babysit` | `ship` · `pr` · `babysit` |
| `update` | `end` (`/end checkpoint`) |
| `plan-week` · `report` | `week` |
| `codex-review` | `review`'s second-opinion mode |
| `ambitious-goal` | `plan-area` (outcome and DoD) |
| `polaris-sweep` · `reference-capture` · `retro` | retired from the public package |

## How it works

| Page | The question it answers |
|---|---|
| [Delivery cycle](docs/delivery-cycle.md) | How does an idea become a merged change, and which skill runs each step? |
| [Plan file](docs/plan-file.md) | What is a plan, what states does it go through, and when does it close? |
| [Work tracking](docs/work-tracking.md) | What goes on GitHub, what goes in Beads, and why nothing mirrors? |
| [Decision records](docs/decision-records.md) | When is a choice a decision, where is it written, how do we know it is done? |
| [Documents](docs/documents.md) | Where does each kind of document live, and what happens when it stops being true? |
| [Context pack](docs/context-pack.md) | What does an agent receive before it works, and how does it know a row is still true? |
| [Sessions](docs/sessions.md) | How does a session resume, and what does it leave behind? |
| [Memory](docs/memory.md) | What does the agent remember, what does it consult, and what never goes in memory? |

## Skills

27 skills. `base-workflow` is the router: it names the case, invokes the skill that owns it and
proposes the next one, so nobody has to remember the chain. Each `SKILL.md` is the authority;
[docs/skills.md](docs/skills.md) lists every skill with its version and description.

| Phase | Skills |
|---|---|
| Route | `base-workflow` |
| Discover · define | `grill` (scope, assumptions, size) · `prototype` (one question, throwaway code) · `problem-solver` (stuck, or a plan to flip: the crux, many hypotheses, the cheapest telling experiment) · `plan-area` (one plan file, Beads epic) · `architecture` (decisions) · `domain` (language and boundaries) · `database-schema` (the real schema first) |
| Build | `implement-plan` (phase by phase from `bd ready`) · `tdd-dev` (RED first) · `bugfix` (12 gated stages) |
| Verify | `review` (six-axis audit) · `real-testing` (the real product, a fresh breaker) · `critic` (attack from fresh context) · `crasher` (hunt the deployed app) · `eval` (measure prompts, agents and skills) |
| Ship | `ship` (one coordinator) · `pr` (a body the owner judges without reading code) · `babysit` (to the owner's label) · `git-power` (commits, PR boundaries, destructive Git) |
| Track | `issue-contract` (the one door to the tracker) |
| Words | `prompt-engineering` (then `eval` measures them) |
| Session | `start` · `end` · `status` · `week` · `init` (bring a repository in) |

## How a repository adapts

Commit `_polaris/config.yml` in the product repository; the template ships with
[`start`](polaris/skills/start/templates/repo-contract/config.yml). The main keys:

| Key | Meaning |
|---|---|
| `outputs.<kind>` | where each kind of document lands: `plan`, `spec`, `audit`, `review`, `validation`, `diagram`, `decision`, `archive` ([documents](docs/documents.md)) |
| `tracker.*` | the GitHub repository and the labels for work a person must do and work an agent may claim |
| `ship.*` | the repository's own ship cycle: verify command, environments, rollback, owner label |
| `real_test.*` | how `real-testing` serves and walks the product: staging, health, smoke, browser profile |

A skill that needs a key the file does not declare says so instead of guessing. `bugfix` reads its
own contract, `.fix/contract.yml`, whose template ships with the skill.

## More

- [docs/skills.md](docs/skills.md): every skill, its version and its description.
- [docs/TEAM-ONBOARDING.md](docs/TEAM-ONBOARDING.md): first-day setup for a contributor.
- [CHANGELOG.md](CHANGELOG.md): what changed, release by release.
- [CONTRIBUTING.md](CONTRIBUTING.md): how to propose a skill change and the gates it must pass.
- [CREDITS.md](CREDITS.md): the upstream work the skills build on.
