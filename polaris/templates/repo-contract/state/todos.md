# Todos

The live view of the week that `team/<login>/weeks/YYYY-Www.md` already committed to — not a second
tracker. The durable todos are the issues; this file shows the slice of them that is this week's.

Rows are bullets, not the donor's tables, on purpose: the package ships ONE fence-aware line parser
(`skills/update/scripts/state_lines.py`) and every writer asks it what a line is. A table row would
need a second notion of "line", which is the exact root cause that made seven state-file writers
disagree.

## Active

<!-- `Added:` is the age signal — it is NEVER re-stamped. This section is never zeroed: a row leaves
     only when its work actually landed. -->
- #<issue> — <one-line result> · Added: W<week>

## Completed

<!-- Current week only. `/end` moves a row here; `/plan-week` drops what belongs to an older week. -->
- #<issue> — <one-line result> · Completed: YYYY-MM-DD

## Follow-ups

<!-- The only section that crosses weeks: an issue can be open, it cannot be dormant until a date. -->
- <item> · Review: YYYY-MM-DD

---
*Contract — a task that closes MOVES to Completed, it is not deleted. `/start` reads Active and any
overdue Follow-up; `/end` closes; `/plan-week` reconciles this file from the weekly plan.*
