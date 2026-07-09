---
name: pol-report
description: Polaris skill — weekly report of the current repo — aggregates _polaris/sessions/ of the period + new decisions + git log into _polaris/weekly/YYYY-Wnn.md (Done / Decisions / Open threads / Next). Use at end of week, before a review with the team, or when the user asks "report", "weekly", "cosa abbiamo fatto questa settimana".
---

# pol-report

Weekly report of THIS repo. Repo layer only (no vault needed).

## Process
1. Determine the period: ISO week of today (`date +%G-W%V`), or the range the user asked.
2. Gather, in this order (skip silently what doesn't exist):
   - `_polaris/sessions/*.md` with dates in the period — extract Done/Decisions/Next blocks
   - `_polaris/decisions.md` — entries dated in the period
   - `git log --since=<period-start> --oneline --no-merges` (cap 100 lines)
   - `_polaris/state/current.md` — open threads
3. Write `_polaris/weekly/YYYY-Wnn.md`:

    # Weekly — YYYY-Wnn (repo <name>)
    ## Done            ← merged sessions Done + commit clusters (group by feature, not per-commit)
    ## Decisions       ← from decisions.md + session Decisions blocks
    ## Open threads    ← from state/current.md + session Open threads
    ## Next            ← from session Next blocks, deduped

4. Keep it ≤80 lines — a report nobody reads is theater. Fold detail into links.
5. Propose the commit (`git add _polaris/weekly/... && git commit`) — do NOT push, do NOT auto-commit.

## Notes
- If `_polaris/` is missing entirely → tell the user to run /pol-bootstrap first, stop.
- Existing weekly file for the period → APPEND a `## Update <date>` section, never overwrite.
