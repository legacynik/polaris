---
name: plan-week
description: Polaris skill — build a capacity-bounded weekly plan for one contributor from live GitHub/Linear issues and current team ownership. Trigger at the start of a week, when a CEO asks for a proposal, or on "plan my week / propose work / weekly plan".
user-invocable: true
---

# /plan-week — propose one week of useful work

This produces a **proposal**, not an assignment. It does not create issues, branches, pull requests
or assignments, and performs no tracker mutations.

## Step 1 — Resolve contract, contributor, capacity

Resolve the single Polaris root and `team/<login>/profile.yml` exactly as `/start` does. Read from
the contract:
- `config.yml` → `tracker.github_repo` (e.g. `owner/name`) and optional `tracker.linear_team`;
- `team/<login>/profile.yml` → **`weekly_capacity`** (the hard cap on primary items), plus
  `preferred_areas` / `excluded_areas` used to bias and filter triage.

If any is missing, stop and point to `docs/TEAM-ONBOARDING.md`. Set `REPO="$(tracker.github_repo)"`
and `WEEK="$(date +%G-W%V)"` (ISO year-week, e.g. `2026-W29`).

## Step 2 — Pull live issues (read-only)

```bash
gh issue list --repo "$REPO" --state open --json number,title,labels,updatedAt --limit 50
```

Expected shape:

```json
[{"labels":[],"number":55,"title":"Staging: stale OPENROUTER_API_KEY breaks MCC-judge","updatedAt":"2026-07-12T14:29:00Z"}]
```

For work already aimed at this person, add an assignee filter:

```bash
gh issue list --repo "$REPO" --assignee @me --state open --json number,title,labels --limit 50
```

If this returns `[]`, the contributor has no assigned issues yet — plan from the open backlog and
`preferred_areas`, and say the assignment is a proposal. Failure branches: `gh: command not found`
→ tell the user to install/auth the GitHub CLI (`gh auth status`); non-zero exit or auth error →
report it and stop, do not fabricate issues. If `tracker.linear_team` is set, also list Linear
issues for that team; otherwise GitHub is the only tracker.

## Step 3 — Triage and fit to capacity

Rank candidates by, in order:
1. explicit priority labels (`[High]`, `priority:high`, `blocker`) over unlabeled;
2. issues that unblock others (a title/label saying it blocks another) over standalone;
3. staleness — older `updatedAt` first once priority ties, so nothing rots;
4. `preferred_areas` match; drop anything matching `excluded_areas`.

**Capacity rule (hard):** select at most `weekly_capacity` **primary** items. If more qualify, keep
the top `weekly_capacity` and list the rest under "Not starting". Secondary/quick items may be added
only if they plausibly fit alongside the primaries — never exceed capacity on primary outcomes.

## Step 4 — Recall prior context

```bash
polmem recall "<issue keywords>" --top 3
```

Use it to catch prior decisions and pitfalls for the chosen issues. `polmem` failure branches are
the same as `/start` (install script, then `git pull`).

## Step 5 — Write the plan file

Write `team/<login>/weeks/YYYY-Www.md` (exact convention: ISO week, e.g.
`team/jeanpierre/weeks/2026-W29.md`) from `polaris/templates/repo-contract/weekly-plan.md`. Do not
overwrite an existing plan for the week without saying so. It must contain:
- one outcome that matters to the product or customer;
- only capacity-fitting secondary work;
- an explicit proof of done for every item;
- what is deliberately **not** being started;
- dependencies and ownership collisions (from other contributors' current-week files);
- state the evidence date and separate verified facts from assumptions.

## Step 6 — Approval boundary

A `/plan-week` output is a **proposal until reviewed** (typically in the weekly call). When the user
asked for a CEO proposal, mark the file:

```yaml
status: proposed
ceo_signature: pending
execution_authorized: false
```

Only a direct approval flips `execution_authorized: true`. After approval the contributor may pick a
branch and update the plan; this command still performs no tracker mutations.

## Worked example

`team/jeanpierre/weeks/2026-W29.md`:

```md
# Week 2026-W29 — @jeanpierre
status: proposed
ceo_signature: pending
execution_authorized: false

## Outcome
Staging MCC-judge runs green again — the stale OPENROUTER_API_KEY (#55) no longer 401s any job.

## Proposed work (capacity: 1 of 3 used on the primary)
| Issue | Result | Branch | Status | Proof | Blocker |
|---|---|---|---|---|---|
| #55 | rotate + wire secret, re-run judge | `fix/55-openrouter-key` | planned | green staging job log | needs staging secret access |
| #54 | slim docs/index.md dangling links | `docs/54-index-slim` | secondary | link-check clean | — |

## Not starting
- #49 Orbit assistant — larger than one week; propose separately.

## Evidence
gh issue list @ 2026-07-13; #55 updated 2026-07-12. Assumption: secret rotation is unblocked.
```
