# Todos — the current week

The live view of the weekly plan. The **history** lives in `team/<login>/weeks/YYYY-Www.md`, one file
per week that is never rewritten; **this file is state**. Same append/overwrite cut the repo already
uses one level down between the session log (append) and `state/current.md` (overwrite), applied at
the weekly rhythm.

**Who writes what** — three commands touch this file and each owns one move, so a row can never be
created twice or aged by the wrong hand:

| Command | May do | May never do |
|---|---|---|
| `week` | reconcile `Active`, roll `Completed`, promote a `Follow-up` whose Review Date arrived | re-stamp `Added`, empty `Active` |
| `/end checkpoint` | refresh the text of a row the current thread cites | add a row, move a row, touch `Added` |
| `/end` close | move a landed row from `Active` to `Completed` | add a row, prune `Follow-ups` |

**Why it sits beside GitHub instead of replacing it**: the todos *are* the issues (decision
2026-04-29, not reversed). Here is this week's slice — exactly what a tracker with hundreds of open
issues per project cannot give you.

---

## Active

<!-- Reconciled by `week`, NEVER emptied: rebuilt from scratch, everything in flight and
     unfinished would vanish. A row leaves for one reason only — its work actually landed (the same
     bar `/end` applies to a thread; a turning calendar is not evidence). `Added` is the date of the
     FIRST entry and is never re-stamped: it is the signal that says how many weeks something has
     gone undone, and re-stamping destroys it. -->

| Task | Added | Context |
|------|-------|---------|
| | | |

---

## Completed

<!-- Current week only. It is not carried forward: the history, with the why, already lives in
     `team/<login>/weeks/`, which keeps it better. Whoever does not know the rule tends to "help" by
     dragging old rows along — that is exactly how this file would become the diary three decisions
     had already killed. -->

| Task | Completed | Note |
|------|-----------|------|
| *None* | | |

---

## Follow-ups

<!-- The only section that CROSSES weeks, and the reason the file exists beside GitHub: an issue can
     be open, it cannot be *dormant until a date*. Review Date in the past => the row returns to
     `Active` at the next `week` (`todos_roll.py`), stamped with the week it CAME DUE — never
     with today, which would erase the age `Added` exists to carry. -->

| Item | Review Date | Note |
|------|-------------|------|
| | | |

<!-- pol:state-contract -->
*File contract — the live view of the weekly focus, not a second ledger: the history lives in `team/<login>/weeks/YYYY-Www.md`, which is never rewritten. `week` RECONCILES `Active` — it adds the new week's rows, removes only those whose work really landed, and never re-stamps the `Added` date; an `end` checkpoint edits the TEXT of a row the current thread cites, without adding one; the `end` close moves a landed row to `Completed`. `Completed` holds the current week only. `Follow-ups` is the only section that crosses weeks: once its Review Date has passed, the row returns to `Active`.*
