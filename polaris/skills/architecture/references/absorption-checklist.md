# Absorption checklist — 26 load-bearing items, mechanically reconciled

One row per item this skill must keep: the interface and contract items (13) and the
component-boundary items (13). Each row names the **file** it lives in and the exact **heading**
it lives under, so the claim is checkable rather than asserted.

Reconciled by [`../scripts/check_absorption.py`](../scripts/check_absorption.py): it parses this
table, confirms each `File` exists and each `Heading` appears verbatim as a line in it, and exits
1 naming the row the moment the count drifts from 26 or a heading goes missing.

```bash
python3 scripts/check_absorption.py   # from the skill's root
```

## Interface and contract items (13)

| # | Item | File | Heading |
|---|---|---|---|
| 1 | The deletion test | interface-and-seam.md | ## The deletion test |
| 2 | The two-adapter rule, valid only where you own the callers | interface-and-seam.md | ## The two-adapter rule — and where it stops applying |
| 3 | Rejected framings kept as a section of their own | interface-and-seam.md | ## Rejected framings |
| 4 | Depth as leverage, not a line-count ratio | interface-and-seam.md | ## Depth as leverage |
| 5 | Internal seam vs external seam | interface-and-seam.md | ## Internal seam vs external seam |
| 6 | One vocabulary: module, interface, seam, adapter | interface-and-seam.md | ## Vocabulary |
| 7 | The four dependency categories when deepening | interface-and-seam.md | ## Four dependency categories |
| 8 | Replace the old tests, don't layer new ones on top | interface-and-seam.md | ## Replace, don't layer |
| 9 | Every observable behaviour becomes a contract | contract-and-commitment.md | ## Every observable behaviour is a contract |
| 10 | One live version at a time, and the diamond dependency it avoids | contract-and-commitment.md | ## The One-Version rule |
| 11 | Idempotency: three outcomes, key from intent, atomic claim, loud mismatch, chosen in-flight response, retention on the longest re-delivery chain | contract-and-commitment.md | ## Idempotency — the full section |
| 12 | The rationalizations table as a form: shortcut left, cost right | contract-and-commitment.md | ## Common Rationalizations |
| 13 | Where validation stays out: shared-type internal calls, own-database data | contract-and-commitment.md | ## Where validation does NOT go |

## Component-boundary items (13)

| # | Item | File | Heading |
|---|---|---|---|
| 14 | The inflection point — when to build a boundary | decision-rules/component-boundary.md | ## 1. The inflection point — when to build a boundary |
| 15 | Partial boundaries that decay without an owner | decision-rules/component-boundary.md | ## 2. Partial boundaries decay without an owner |
| 16 | Four physical forms with their chattiness budget | decision-rules/component-boundary.md | ## 3. Four physical forms and their chattiness budget |
| 17 | The cross-cutting feature test | decision-rules/component-boundary.md | ## 4. The cross-cutting feature test, and why services alone aren't architecture |
| 18 | Services are not architecture on their own | decision-rules/component-boundary.md | ## 4. The cross-cutting feature test, and why services alone aren't architecture |
| 19 | Dependency direction, stated operationally (A protected from B → B depends on A) | decision-rules/component-boundary.md | ## 5. Dependency direction, stated operationally |
| 20 | Invert on volatility, not abstractness — violations collect in Main | decision-rules/component-boundary.md | ## 6. Depend on volatility, not abstractness — and let violations collect in Main |
| 21 | The three cohesion pulls and their drift over a project's life | decision-rules/component-boundary.md | ## 7. The REP/CCP/CRP tension, and why structure isn't designed top-down |
| 22 | One actor per module, with its two violation symptoms | decision-rules/component-boundary.md | ## 8. SRP is one actor, not one responsibility |
| 23 | The Humble Object as a testability delta | decision-rules/component-boundary.md | ## 9. The Humble Object as a testability delta |
| 24 | A framework is an asymmetric marriage | decision-rules/component-boundary.md | ## 10. A framework is an asymmetric marriage |
| 25 | The database is a detail; the data model is not | decision-rules/component-boundary.md | ## 11. The database is a detail; the data model is not |
| 26 | Mechanical enforcement over review (pointer to the governance rules that hold the mechanism) | decision-rules/component-boundary.md | ## 12. The compiler enforces it, not the reviewer |
