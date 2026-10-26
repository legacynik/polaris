# Polaris Team OS — team onboarding

This is the day-one checklist for a person opening a product repository for the first time. The
README covers *what* Polaris is; this covers *what you run* to get set up. If a command below fails,
stop and report the blocker — do not create a personal vault or improvise a second configuration.

## 1. Install the skills

Install and update the package as the [README](../README.md#install) says: the skills CLI, global,
every skill. Nothing else is required from this package. It carries workflow only — never put
project data, private decisions, customer information or repository state into it. Then confirm the
skills are installed:

```bash
npx skills list -g
```

You must see `start`, `end`, `base-workflow` and `ship` among them.

## 2. Tool preflight — once per machine

### GitHub CLI

The first `/start` resolves and caches your exact login through `gh`; `/week` reads delivery
evidence through it. Without authenticated `gh`, those setup/evidence paths stop:

```bash
gh --version   # missing → install it (macOS: brew install gh; see cli.github.com)
gh auth status # not logged in → gh auth login
```

### Optional tools

None is required; install one when you use the skill that needs it. Never store keys or
credentials in the repo.

| Tool | Used by | Without it |
|---|---|---|
| Beads (`bd`) | `plan-area`, `implement-plan`, `issue-contract`, the gates | required by those skills: they stop and say `brew install beads` |
| Codex CLI (`codex` on `PATH`) | `review`'s second-opinion mode | another model family, or the mode is skipped and said |
| `browser-harness` | `real-testing`, `crasher` UI walks | API-only walk, UI boxes left unticked |
| Context7 | `grill`, for a version-specific dependency question | the official docs, with the fallback disclosed |

## 3. Check the repo contract

The repository owns **one** Polaris root: `_polaris/`, committed with the code. The repository owner
provides:

```text
_polaris/config.yml
_polaris/decisions.md
_polaris/lessons.md              # optional but standard
```

Your own path is **not** pre-created for you. On your first `/start`, the skill reads your exact
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

## 4. First day

1. Open your agent CLI (Claude Code, Codex, ...) from the product repo.
2. Run `/start`: read your authorized outcome, latest handoff/checkpoint, blocker, and next action.
3. Run `/status` when you need the full repository or portfolio pulse, team collisions or the
   decisions still not done.
4. For anything that touches code, a plan or the tracker, let `base-workflow` route it: an idea goes
   to `grill`, a bug to `bugfix`, finished work to `ship`. How the whole cycle works:
   [delivery-cycle.md](delivery-cycle.md).
5. Run `/end checkpoint` after real progress or a real blocker.
6. Run `/end` when you stop: leave one concrete next action.

## 5. The week

- Each contributor runs `/week` for **their own** week — a focus grounded in real issues/PRs
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
- At week end, `/week` reports plan versus reality: deliveries, proof, blockers, next priority.
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
