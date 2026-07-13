---
name: start
description: Polaris skill — begin a repository-first team session. Verify the branch, resolve the repo contract, recall memory with polmem, and brief the contributor before any work. Trigger at session start, after a pause, or when asked "where do I start / what's my status / start session".
user-invocable: true
---

# /start — orient before acting

Read-only. This command makes the next choice visible. It never creates a workspace, issue, branch,
pull request or assignment, and never writes `state/current.md`.

## Step 1 — Verify the branch FIRST

Before reading anything, confirm you are where you think you are (checkouts are shared across panels):

```bash
git rev-parse --abbrev-ref HEAD
```

Hold the result. After Step 3 you will compare it to the active plan's branch. If the repo is not a
git checkout, stop and say so — this command needs a repository.

## Step 2 — Resolve the repository contract

From the repository root, use **one** Polaris root:

1. `polaris/` if `polaris/config.yml` exists;
2. otherwise `_polaris/` if `_polaris/config.yml` exists;
3. otherwise **stop**: the repository has no committed Team OS contract. Point the contributor to
   `docs/TEAM-ONBOARDING.md` (section "Verifica il contratto della repo"). Do not run a bootstrap
   command and do not create personal state.

Identify the contributor from the matching `team/<github-login>/profile.yml`. The `github:` field and
the `team/<login>/` folder are the exact GitHub login, verbatim (case-sensitive) — the same string
`gh` queries use. Prefer the login for the current checkout (`gh api user --jq .login`); if it is
ambiguous, list the available `team/*/` profiles and ask which is theirs. If no profile matches, stop
and point to onboarding.

## Step 3 — Read in this order

1. `team/<login>/profile.yml` — `weekly_capacity`, `assignment_mode`, preferred/excluded areas.
2. The current ISO-week plan `team/<login>/weeks/$(date +%G-W%V).md` — outcome, branch, proof,
   blockers. If absent, say there is no signed plan for this week; planning happens in `/plan-week`.
3. Other current-week files under `team/*/weeks/` and recent entries under `team/*/sessions/` —
   titles, owners and active branches only, to avoid collisions.
4. `<root>/decisions.md`, then `<root>/state/current.md` if it exists. `current.md` is a compact,
   gitignored pointer: if it conflicts with the approved plan or evidence, treat it as stale.
5. The most recent relevant session log in `<root>/team/<login>/sessions/`.

**Branch check:** compare Step 1's branch to the plan's `Branch` cell. If they differ (and the plan
has a branch), STOP and ask before proceeding — you may be on another panel's checkout.

## Step 4 — Recall memory (polmem CLI, mandatory)

`polmem` is the repository's memory and the CLI is the interface — use it for any context question
before answering from assumption. Run a targeted recall on the active plan's issue or domain:

```bash
polmem recall "confirmation gate" --top 3
```

Expected shape — ranked entries (score, source, title, one-line summary):

```text
[70] _polaris/decisions.md#2026-05-07 — Production runtime = ECS Fargate + Terraform …
[70] references/cardaq-gateway-integration — Cardaq Gateway Integration …
```

Failure branches:
- `command not found: polmem` → run `bash "$CLAUDE_PLUGIN_ROOT/polaris/scripts/install-polmem-cli.sh"`, then retry.
- `not memory-wired (no scripts/polaris_memory_repo.py)` → this repo does not carry the memory
  bundle yet. `git pull` in case it is arriving with the code; if it is still missing, say memory is
  unavailable once and continue. **Do not run `polmem init` yourself** and do not invent a fallback
  store — tell the repo owner / CEO the repo needs wiring.
- missing `.wiki` index after the bundle loads → `git pull`, then retry once.

`recall` is repository memory, not current state: on the founder's own machine it may surface
founder-vault entries. Treat every recalled page as **assumed** context to verify against the
tracker or code — never cite it as evidence of what is true now.

## Step 5 — Brief (at most seven lines)

```text
<repo> — <date>
Your outcome this week: <one sentence>
Active item: <issue / branch / status>
Proof needed: <one sentence>
Collision or blocker: <one sentence, or none>
Relevant decision or recall: <one sentence, or none>
What do you want to move forward first?
```

If there is no signed plan, say so plainly. Planning happens in `/plan-week`; implementation still
needs an explicit user request. Do not overwrite `state/current.md` from `/start` — `/update` and
`/end` keep it short.
