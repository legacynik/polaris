---
name: report
description: Polaris skill — produce a concise weekly repository report comparing the approved plan with actual delivery evidence from git and the tracker. Trigger at week end, before a team review, or on "weekly report / what shipped this week / planned vs actual".
user-invocable: true
---

# /report — planned versus actual

Resolve the single Polaris root and `team/<login>/profile.yml` exactly as `/start` does. Set
`REPO="$(config.yml tracker.github_repo)"` and `WEEK="$(date +%G-W%V)"`. The report compares the
week's approved plan with real evidence — never volume of commits, tokens or messages.

## Step 1 — Read the week's plan

Open `team/<login>/weeks/$WEEK.md`. Its rows (issue, intended result, proof, branch) are the
baseline you measure against. If there is no plan for the week, say so and report only what shipped;
do not invent a baseline.

## Step 2 — Gather delivery evidence (read-only)

Commits by this contributor in the week:

```bash
git log --since="7 days ago" --author="$(git config user.email)" --oneline
```

Expected shape:

```text
5ae3deb chore: Team OS contract provisioning for JP/Giovanni onboarding
628daad chore: add CODEOWNERS for workflows/apex-gate/code-refs paths
```

Closed issues and merged PRs in the window (link these as proof):

```bash
gh issue list --repo "$REPO" --state closed --search "closed:>$(date -v-7d +%F)" --json number,title,closedAt
gh pr list    --repo "$REPO" --state merged --search "merged:>$(date -v-7d +%F)" --json number,title,mergedAt
```

Expected shape:

```json
[{"mergedAt":"2026-07-08T18:27:43Z","number":47,"title":"Onboarding human-in-the-loop (epic #45)"}]
```

Failure branches: `gh`/`git` not found or auth error → report the failure and continue with the
evidence you do have; never fabricate a PR link or a closed issue. On a Linux box use
`--since="7 days ago"` and `date -d '7 days ago' +%F` instead of the BSD `-v-7d` form.

## Step 3 — Diff plan versus done

For each plan row, mark it shipped (with a linked PR/issue/test), partially done, or not started —
and why. A blocked item is useful information when its blocker and next decision are explicit. Use
`polmem recall "<topic>" --top 3` if you need the decision context behind a blocker.

## Step 4 — Write the report file

Create or update `team/<login>/reports/YYYY-Www.md` (exact convention: ISO week, e.g.
`team/jeanpierre/reports/2026-W29.md`) from `polaris/templates/repo-contract/weekly-report.md`. Keep
it under one screen and answer:

1. What outcome was planned?
2. What was actually shipped or verified? Link the PR, issue, deployment or test evidence.
3. What did not happen, and why (blocker + next decision)?
4. What was learned about scope, quality or collaboration?
5. What is the single best next-week starting point?

## Boundaries

- Do not overwrite an earlier report for the same week; append a dated update if new evidence arrives.
- Do not create tracker issues, assignments, branches, pull requests or deployments.
- Do not write outside the current repository or infer performance judgments unsupported by evidence.

## Worked example

`team/jeanpierre/reports/2026-W29.md`:

```md
# Report 2026-W29 — @jeanpierre

## Planned versus actual
| Issue | Planned | Actually delivered | Evidence | Status |
|---|---|---|---|---|
| #55 | fix stale OPENROUTER key, green judge | key rotated, judge green | PR #58, staging run log | closed |
| #54 | slim docs/index dangling links | not started | — | open |

## What we learned
- Secret rotation needed staging access we did not have on Monday — request it before planning #55-type work.

## Blocker and next week
- Blocker: #54 untouched (spent the week on #55). Next: start #54 first, it is small and unblocked.
```
