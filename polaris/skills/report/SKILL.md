---
name: report
description: Polaris skill — produce a concise weekly repository report comparing the approved plan with actual delivery evidence from the tracker (gh). Trigger at week end, before a team review, or on "weekly report / what shipped this week / planned vs actual".
user-invocable: true
---

# /report — planned versus actual

Resolve the single Polaris root and `team/<login>/profile.yml` exactly as `/start` does. Read
`REPO` from `config.yml` (`tracker.github_repo`) and `LOGIN` from the contributor's profile
(`github:` — the exact GitHub login, case-sensitive, used verbatim in `gh` queries). The report
compares the week's approved plan with real evidence — never volume of commits, tokens or messages.

## Step 0 — Fix the reporting week (before any query)

The report's week is the ISO week of the *period being reported*. On the normal cadence you run
`/report` on the Friday of that week, so the current ISO week is the right one:

```bash
WEEK="$(date +%G-W%V)"   # e.g. 2026-W29 — the week you are reporting
```

If you are reporting a *past* week (for example running it the following Monday), set `WEEK` to that
week explicitly (`WEEK=2026-W28`). Never rely on a rolling "7 days ago": from a Monday it straddles
two ISO weeks and files the report under the wrong one — the defect a live run hit. Derive the
evidence window from `WEEK` so the filename and the evidence can never disagree:

```bash
read SINCE UNTIL < <(python3 - "$WEEK" <<'PY'
import datetime, sys
year, week = sys.argv[1].split("-W")
mon = datetime.date.fromisocalendar(int(year), int(week), 1)
sun = datetime.date.fromisocalendar(int(year), int(week), 7)
print(mon.isoformat(), sun.isoformat())
PY
)
# SINCE = Monday, UNTIL = Sunday of WEEK
```

## Step 1 — Read the week's plan

Open `team/<login>/weeks/$WEEK.md`. Its rows (issue, intended result, proof, branch) are the
baseline you measure against. If there is no plan for the week, say so and report only what shipped;
do not invent a baseline.

## Step 2 — Gather delivery evidence (read-only)

Query the tracker for *this contributor's* work in the window, by GitHub login. **Never use
`git log --author="$(git config user.email)"`**: it resolves to the local machine's git identity,
not the teammate's, so on any shared checkout it returns nothing useful (a live run proved it). Use
`$LOGIN` and the `$SINCE..$UNTIL` window from Step 0:

```bash
gh pr list    --repo "$REPO" --state merged --search "author:$LOGIN merged:$SINCE..$UNTIL" --json number,title,mergedAt
gh issue list --repo "$REPO" --state closed --search "author:$LOGIN closed:$SINCE..$UNTIL"  --json number,title,closedAt
```

Expected shape:

```json
[{"mergedAt":"2026-07-08T18:27:43Z","number":47,"title":"Onboarding human-in-the-loop (epic #45)"}]
```

Verify authorship, not just the PR list: a PR *authored* by `$LOGIN` can be a branch-sync
("merge main into …") whose commits belong to someone else — counting it would credit their work to
this contributor. Confirm with `gh pr view <n> --json commits` before you cite it.

Failure branches: `gh` not found or an auth error → report the failure and continue with the
evidence you do have; never fabricate a PR link or a closed issue.

## Step 3 — Diff plan versus done

For each plan row, mark it shipped (with a linked PR/issue/test), partially done, or not started —
and why. A blocked item is useful information when its blocker and next decision are explicit. Use
`polmem recall "<topic>" --top 3` if you need the decision context behind a blocker (if recall says
the repo is not memory-wired, see `/start` Step 4 — do not run `polmem init`).

## Step 4 — Write the report file

Create or update `team/<login>/reports/$WEEK.md` (exact convention: ISO week — `reports/YYYY-Www.md`,
e.g. `team/jeanpierre/reports/2026-W29.md`) from the plugin template
`$CLAUDE_PLUGIN_ROOT/polaris/templates/repo-contract/weekly-report.md` (copy it into the repo if you
keep local templates). Keep it under one screen and answer:

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
