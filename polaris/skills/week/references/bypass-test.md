---
title: bypass-test — week
description: The ways the week skill was skipped or produced a wrong week before, and the check that now stops each.
status: active
---

# Bypass cases — week

## B1 — the decided-and-not-done list is skipped

`fails_before:` plan-week 1.4.3 / report 1.3.3. Neither skill named the decision register, so a
decision accepted on 2026-08-24 stayed undone for two months while every weekly focus ignored it.

After: step 2 runs `check_decision_execution.py --not-done` and prints its rows verbatim, oldest
first. The ordering and the verdict are the script's (`scripts/test/test_decision_execution.py`
`TestTheDebtListIsOldestFirst`); the skill never recomputes them.

```bash
python3 scripts/check_decision_execution.py --root . --not-done --timeout 90
# expected: NOT_DONE <decided_at> <DEC id> — <title> rows, oldest first, or NOT_DONE: none
```

## B2 — the weekend focus lands in the ending week

A focus written on Sunday landed in the ISO week that was ending, and Monday's `start` found no
file. Forward rolls a weekend date to the next Monday (`references/forward.md`, one-liner).

## B3 — `Active` rebuilt by hand

Rewriting `state/todos.md` by hand re-stamped carried work as new and dropped work in flight.
Step 5 goes through `state_upsert.py week`, which keeps each row's `Added:`; the writer's own
selfcheck proves it (`python3 skills-suite/end/scripts/state_upsert.py --selfcheck`).

## B4 — a live week reported

A report on a week still running publishes a number that changes after it is read. Step 6 refuses
a window whose Saturday is today or later, and waits for an explicit "yes" before any query.

## B5 — docs counted as code

`gh` additions count Markdown. Step 7 splits `code` and `docs` per PR and writes `UNKNOWN`, never
`0`, for a PR it cannot measure (`references/report.md`, "Per-PR size").
