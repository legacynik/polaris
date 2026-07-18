---
name: plan-week
description: Polaris skill — build your own weekly focus from live GitHub/Linear issues and current team ownership. You author it and you execute it; the lead may reorder priorities, but only red work waits for a named approver. Trigger at the start of a week, when the lead asks what you are picking up, or on "plan my week / propose work / weekly plan".
user-invocable: true
---

# /plan-week — propose one week of useful work

This produces a **proposal**, not an assignment. It does not create issues, branches, pull requests
or assignments, and performs no tracker mutations.

## Step 1 — Resolve contract, contributor, capacity

Resolve the single Polaris root and **your own** `team/<login>/profile.yml` exactly as `/start`
does (`LOGIN` from `gh api user --jq .login`). Plans are authored by their owner: the file lives in
your own `team/$LOGIN/weeks/`. Never write another contributor's plan: everyone authors their own,
on their own machine, from their own login. Read from the contract:
- `config.yml` → `tracker.github_repo` (e.g. `owner/name`) and optional `tracker.linear_team`;
- `team/<login>/profile.yml` → **`weekly_capacity`** (the *default* weekly commitment, not a hard
  cap), the `github:` login (exact, case-sensitive — used verbatim as `$LOGIN` in `gh` queries),
  plus `preferred_areas` / `excluded_areas` used to bias and filter triage.

If any is missing, stop and point to `docs/TEAM-ONBOARDING.md`. Set `REPO="$(tracker.github_repo)"`,
`LOGIN="$(profile github)"` and `WEEK="$(date +%G-W%V)"` (ISO year-week, e.g. `2026-W29`).

**Ask this week's commitment — it drives the load.** Before ranking, ask the contributor how much
they want to take on **this** week: a number of primary outcomes, or light / normal / heavy. Their
answer is `CAP`, the load the plan is sized to. `weekly_capacity` is only the default offered if they
don't say — the week's real load is what they commit to now, not a static profile number.

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

## Step 3 — Ground the contributor's scope

If `preferred_areas` is empty in the profile, do not rank blind — find scope evidence in the repo
first, then propose an update:
- onboarding / README / ownership docs and `CODEOWNERS`;
- the contributor's recent work:
  `gh pr list --repo "$REPO" --author "$LOGIN" --state all --limit 20 --json number,title,files`.

Propose adding what you find to `team/<login>/profile.yml` `preferred_areas`, and use it to bias this
week's ranking. Skipping this is how a run planned an area the contributor does not own; grounded
scope is what let a baseline beat the skill here.

## Step 4 — Triage and fit to capacity

Rank candidates in this strict order — **severity outranks age, always**:
1. **priority / severity**: a priority label (`[High]`, `priority:high`, `blocker`, `critical`) OR
   `[CRITICAL]` in the title, over unlabeled. A critical issue never sits behind an older
   non-critical one.
2. **unblocks others**: a title/label saying it blocks another issue, over standalone.
3. **scope fit**: matches `preferred_areas` (from the profile or Step 3); drop anything matching
   `excluded_areas`.
4. **staleness**: older `updatedAt` first — the **final tiebreak only**, once 1–3 are equal, so
   nothing rots. It must never promote an old low-severity issue over a fresh critical one.

**Fit to `CAP` — the commitment from Step 1.** Aim the plan at `CAP` primary outcomes, and list what
does not fit under "Not starting" so the choice is visible instead of silent. `CAP` is a planning
guide, not a quota. If this week's `CAP` differs a lot from the profile `weekly_capacity`, note why
in the weekly file; if the gap is persistent, propose updating `weekly_capacity` to match reality.

## Step 5 — Recall prior context

```bash
polmem recall "<issue keywords>" --top 3
```

Use it to catch prior decisions and pitfalls for the chosen issues. If `polmem` is missing, skip
recall and continue. If it reports the repo is not memory-wired, tell the repo owner — do **not**
run `polmem init` yourself.

## Step 6 — Write the plan file

Write `team/<login>/weeks/$WEEK.md` (exact convention: ISO week — `weeks/YYYY-Www.md`, e.g.
`team/octocat/weeks/2026-W29.md`) from the plugin template
`$CLAUDE_PLUGIN_ROOT/polaris/templates/repo-contract/weekly-plan.md` (copy it into the repo if you
keep local templates). Do not overwrite an existing plan for the week without saying so. It must
contain:
- one outcome that matters to the product or customer;
- only capacity-fitting secondary work;
- an explicit proof of done for every item;
- what is deliberately **not** being started;
- dependencies and ownership collisions (from other contributors' current-week files);
- state the evidence date and separate verified facts from assumptions.

## Step 7 — Ownership boundary (the plan does not wait for permission)

The plan is **yours**: you own the outcome and the evidence — write it, commit it, let it travel
into the PR. What the lead does with it is priority alignment (read, reorder, correct scope), not
permission; their silence is not a block. No signature field, deliberately — mark the file with what
is **true**, not a permission state:

```yaml
status: active         # active | carried | superseded
lead_review: pending   # pending | read | reordered — priority alignment, never a gate
```

**Where approval IS required — the red stop-lines.** Not ceremony: the places where being wrong is
irreversible, or where someone else carries the risk.

- material expansion of access/RLS/auth, or personal-data use, retention or deletion;
- a new processor/vendor, or an irreversible data migration;
- a legal or customer commitment;
- production promotion where a signed control (e.g. a segregation-of-duties matrix) names an
  approver — that approver, not the lead by default;
- a material change to the agreed outcome or architecture direction.

A red item is **proposed with evidence and waits for its named approver** before execution or
promotion. Everything else — bounded, reversible work inside the agreed outcome — you decide and
proceed, recording `Decision / Why / Risk / Next step` in the issue or PR.

**The repo's own `workflow:` charter wins over this section** — if `profile.yml` points to one, its
boundaries are the real contract. This command performs no tracker mutations.
