---
title: bypass-test — status
description: The ways the full view lied or acted on its own, and the check that now stops each.
status: active
---

# Bypass cases — status

## B1 — decided and not done stays invisible

`DEC-polaris-retrieval-rebuild-001` was `accepted` on 2026-08-24 and still not enacted two months
later; no view showed it. Step 4 prints the gate's `--not-done` rows verbatim, oldest first. The
ordering and the verdict are the script's own (`scripts/test/test_decision_execution.py`,
`TestTheDebtListIsOldestFirst`); the skill never recomputes them.

```bash
python3 scripts/check_decision_execution.py --root . --not-done --timeout 90
```

## B2 — a stale vault presented as current

A failed fetch or a stale freshness check read as live truth. Step 3 names an offline fetch, and a
stale freshness exit (2) becomes a risk line, never a fact.

## B3 — a thread rounded to LANDED

An investigation agent that could not verify a lane reported it closed. UNCLEAR is a valid verdict
and is never rounded up; a lane owned by another panel is reported, never proposed for removal.

## B4 — cleanup without consent

Deleting branches or closing threads during a status read. Step 6 proposes the whole cleanup with
its evidence and acts only on one explicit yes.
