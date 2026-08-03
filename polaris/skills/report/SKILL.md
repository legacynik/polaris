---
name: report
description: Polaris skill — produce a real weekly repository report for a FINISHED Sunday-to-Saturday week (asks confirmation first, refuses the current week) — TL;DR, day-by-day from session logs, merged-PR ground truth from gh, decisions, metrics, PM actions — anchored on the approved plan (planned versus actual). Trigger at week end, before a team review, or on "weekly report / what shipped this week / planned vs actual".
user-invocable: true
version: 1.1.0
---

# /report — the week, with evidence

Resolve the single Polaris root and `team/<login>/profile.yml` exactly as `/start` does. Read
`REPO` from `config.yml` (`tracker.github_repo`) and `LOGIN` from the contributor's profile
(`github:` — the exact GitHub login, case-sensitive, used verbatim in `gh` queries). The report is
**ground-truth-first**: every claim links a PR, commit, issue, test run or session log — never
volume of messages or tokens, never memory of what "should" have happened. It is anchored on the
approved plan (planned versus actual) but it is a full report, not just a diff table.

## Step 0 — Fix the reporting week, and confirm it (before any query)

**A week runs Sunday → Saturday and is reported only once it is over** (founder rule, 2026-07-28).
Reporting a live week produces a number that changes after you publish it, which is worse than no
report. The default target is therefore the **last completed** week, never the current one. Pass
`WEEK_START` (a Sunday, `YYYY-MM-DD`) to report an older week; a week that has not ended is refused.

```bash
read WEEK SINCE UNTIL PLANWEEK < <(python3 - "${WEEK_START:-}" <<'PY'
import datetime, sys
today = datetime.date.today()
ov = sys.argv[1] if len(sys.argv) > 1 else ""
if ov:
    start = datetime.date.fromisoformat(ov)
    if start.weekday() != 6:
        raise SystemExit(f"WEEK_START must be a Sunday, got {start:%A}")
else:                                    # last COMPLETED Sunday→Saturday week
    start = today - datetime.timedelta(days=(today.weekday() + 1) % 7, weeks=1)
end = start + datetime.timedelta(days=6)
if end >= today:
    raise SystemExit(f"week {start}..{end} has not ended — only finished weeks are reported")
mon = start + datetime.timedelta(days=1)          # the Monday inside this week
print(start, start, end, "%d-W%02d" % mon.isocalendar()[:2])
PY
)
# WEEK = the Sunday that starts it (the report's filename)
# SINCE..UNTIL = Sunday..Saturday, the evidence window
# PLANWEEK = the ISO week label of the plan this measures against
```

`PLANWEEK` exists because plans are still filed under ISO (Monday-start) weeks: the Sunday-week
`SINCE..UNTIL` contains exactly one Monday, so the mapping is unambiguous. **Known seam:** the plan
week's own Sunday belongs to the *next* report week, so a proof landed on that Sunday appears one
report later. Say so in the report rather than silently reconciling it.

**Then stop and confirm before running a single query.** Show the resolved window and wait:

```
Reporting <REPO> for <SINCE> (Sun) → <UNTIL> (Sat), against plan <PLANWEEK>. Proceed? [yes / other week]
```

Never generate a report without that confirmation, and never widen the window to "catch" work that
landed outside it.

## Step 1 — Read the week's plan

Open `team/<login>/weeks/$PLANWEEK.md` (plans are filed by ISO week; `$WEEK` names the report, not
the plan — see the seam in Step 0). Its rows (issue, intended result, proof, branch) are the
baseline you measure against — the contributor's own stated intent, which is exactly what makes
planned-versus-actual worth reading. If `lead_review:` shows the lead reordered the week, measure
against the reordered focus and say the priority changed mid-week; a plan overtaken by a real
priority is not a miss. If there is no plan for the week, say so and report only what shipped; do
not invent a baseline.

## Step 2 — Gather ground-truth evidence (read-only)

Sync the remote first — a report written against a stale local view misses merges and misstates
branch state:

```bash
git fetch --prune origin
```

Then collect, by GitHub login. **Never use `git log --author="$(git config user.email)"`**: it
resolves to the local machine's git identity, not the teammate's, so on any shared checkout it
returns nothing useful. Use `$LOGIN` and the `$SINCE..$UNTIL` window from Step 0:

```bash
# Tracker: merged PRs and closed issues authored by the contributor
gh pr list    --repo "$REPO" --state merged --search "author:$LOGIN merged:$SINCE..$UNTIL" --limit 200 --json number,title,mergedAt,additions,deletions,mergeCommit
gh issue list --repo "$REPO" --state closed --search "author:$LOGIN closed:$SINCE..$UNTIL"  --limit 200 --json number,title,closedAt

# Commits in the window, login->commits resolved SERVER-SIDE by GitHub.
# Not git log --author: squash commits carry the user's configured (often
# personal) email, so a guessed pattern silently returns zero.
gh api --paginate "repos/$REPO/commits?author=$LOGIN&since=${SINCE}T00:00:00Z&until=${UNTIL}T23:59:59Z&per_page=100" \
  --jq '.[] | "\(.sha[0:8]) \(.commit.author.date[0:10]) \(.commit.message | split("\n")[0])"'

# PRs open NOW (branch debt) — not reconstructable "as of" a past week: for a
# historical report label this "open at report time", never "open at end of range".
gh pr list --repo "$REPO" --author "$LOGIN" --state open --limit 200 --json number,title,createdAt
```

Expected shape:

```json
[{"mergedAt":"2026-07-08T18:27:43Z","number":47,"title":"Onboarding human-in-the-loop (epic #45)"}]
```

Verify authorship, not just the PR list: a PR *authored* by `$LOGIN` can be a branch-sync
("merge main into …") whose commits belong to someone else — counting it would credit their work to
this contributor. Confirm with `gh pr view <n> --json commits` before you cite it.

### Local work that never reached the remote (or `gh` reports a fraction of the week)

`gh` only knows what was pushed. Work committed on a local branch, or in a worktree that was never
pushed, is invisible to every query above — and it is not an edge case: measured on one real week,
**186 commits across four repos** existed only locally (one repo: 106 of 467, 23% of its week).
A report that omits them tells the contributor they did a fraction of what they did.

```bash
# commits in the window that exist on NO remote ref, across every branch and worktree
git log --all --not --remotes --since="$SINCE" --until="$UNTIL" \
        --pretty='%h %ad %d %s' --date=short
# which branches carry them, and how far ahead they are
git for-each-ref --format='%(refname:short) %(upstream:track)' refs/heads | grep -v '\[gone\]$'
git worktree list                      # a parked worktree is live work, not abandoned work
```

This is **local evidence, not ground truth**: it is unreviewed, unpushed, and may be rebased away.
Report it in its own section, labelled, never merged into the merged-PR table, and deduplicate
against `gh` by subject line (a commit can appear here and land squashed later). Attribution caveat:
these commits carry the *machine's* git identity, so on a shared checkout only claim them for
`$LOGIN` when the branch or worktree is that contributor's — otherwise report them as unattributed.

Two sources are in the repo, not the tracker:

- **Session logs** — read the range's files in `team/<login>/sessions/` (`YYYY-MM-DD*.md` within
  `$SINCE..$UNTIL`). They are the day-by-day backbone: what was verified each day, incidents and
  their resolution, handoffs. Link each day you cite.
- **Decisions and lessons** — scan `<root>/decisions.md` (and `lessons.md`) for entries dated in
  the window carrying the contributor's `@<login>` marker (the `/end` proposal format includes it).
  An entry without an owner marker is ambiguous — say so instead of guessing.

Failure branches: `gh` not found or an auth error → report the failure and continue with the
evidence you do have; never fabricate a PR link or a closed issue. No session logs in range → say
so; the tracker evidence still stands.

## Step 3 — Diff plan versus done

For each plan row, mark it shipped (with a linked PR/issue/test), partially done, or not started —
and why. A blocked item is useful information when its blocker and next decision are explicit. Use
`polmem recall "<topic>" --top 3` if you need the decision context behind a blocker (if recall says
the repo is not memory-wired, tell the repo owner — do not run `polmem init` yourself).

## Step 4 — Write the report file

Create or update `team/<login>/reports/$WEEK.md` (exact convention: the week's **Sunday**, dated —
`reports/YYYY-MM-DD.md`, e.g. `team/octocat/reports/2026-07-19.md` for Sun 19 → Sat 25. Dated, not
`YYYY-Www`, precisely so a Sunday-start report is never confused with the Monday-start ISO plan week
it measures against) from the plugin template
`$CLAUDE_PLUGIN_ROOT/templates/repo-contract/weekly-report.md`. Sections, in order:

1. `## TL;DR` — three sentences max: the week's outcome, the biggest thing shipped (with its
   evidence), the top outstanding item.
2. `## Planned versus actual` — the plan-row diff from Step 3, one row per planned item.
3. `## Day by day` — one short block per working day, distilled from the session logs, each linked
   (`[log](../sessions/YYYY-MM-DD-@login.md)`). Skip days with no session log.
4. `## Merged PRs` — the table from `gh` (number, title, +/− LOC, merge SHA, date) plus the closed
   issues. This is ground truth, not the logs' claims — where they disagree, `gh` wins and the
   discrepancy is worth a line.
5. `## Local, not pushed` — work that exists only on this machine: commits on no remote ref, the
   branches and worktrees carrying them, and how far ahead each is. Labelled as local evidence,
   never mixed into section 4, deduplicated against it by subject. Omit the section only when the
   query returns nothing — an empty section is information, a missing one is a blind spot.
6. `## Decisions in range` — entries the contributor logged in `decisions.md`/`lessons.md` this week.
7. `## Blockers and incidents` — resolved in-week (with how) and carry-over (with the blocker and
   the next decision).
8. `## Metrics` — small table: PRs merged, issues closed, LOC delta, decisions logged, open PRs at
   report time, incidents. Counts are **derived from the evidence above at report time** — never
   copied from a previous report or estimated.
9. `## Bottleneck` — **mandatory, never "none"**: the single biggest thing that slowed this week
   (a wait, a flaky gate, a missing access, a review queue — from the evidence, not vibes) + ONE
   concrete removal proposal. This is the continuous bottleneck-hunt, run per-person and async —
   the loop that keeps the system fast without a meeting. A week with no named bottleneck means
   the report author didn't look.
10. `## PM action` — the decisions someone else must take for this work to move, each one line with
   its **named** owner. Not "things to approve": blockers only you cannot clear — a red item waiting
   on its approver, an access someone must grant, a priority call between two real options. This is
   the section the reader acts on; if nothing is needed, say "none", which is the healthy default.
11. `## Next week` — a short ordered priority list for the contributor's own scope.

**Scale honestly.** The report's length is proportional to the evidence: a quiet week is a short
report — never pad a section to look busy, never repeat the same item in three sections. Keep it
under two screens unless the merged-PR table itself is bigger. State the evidence date and separate
verified facts from assumptions.

## Boundaries

- Do not overwrite an earlier report for the same week; append a dated update if new evidence arrives.
- Do not create tracker issues, assignments, branches, pull requests or deployments.
- Do not write outside the current repository or infer performance judgments unsupported by evidence.
