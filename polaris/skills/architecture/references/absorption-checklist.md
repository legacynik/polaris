# Absorption checklist — 26 survival items, mechanically reconciled

Issue polaris-os#87 AC1. One row per survival item named in
`audit/2026-08-17-censimento-skill-architettura.md` §2.0 (13 interface items) and §2.3 (13
Martin items) — the content that dies if the merge treats it as redundant. Every row carries
the **file** it landed in and the exact **heading** under which it lives, so the claim is
checkable, not asserted.

Reconciled by [`../scripts/check_absorption.py`](../scripts/check_absorption.py): parses this
table, confirms each `File` exists and each `Heading` appears verbatim as a markdown heading in
it. `grep -c '^| [0-9]\+ |'` on this file must read **26**; the script exits 1 and names the row
the moment either count drifts or a heading goes missing.

```bash
python3 ../scripts/check_absorption.py   # from architecture/references/
```

## §2.0 — interface items (13), from `codebase-design` + `api-and-interface-design`

| # | Item | File | Heading |
|---|---|---|---|
| 1 | The deletion test | interface-and-seam.md | ## The deletion test |
| 2 | The two-adapter rule, with the "you own the callers" validity condition made explicit | interface-and-seam.md | ## The two-adapter rule — and where it stops applying |
| 3 | "Rejected framings" as a mandatory section, not just its content | interface-and-seam.md | ## Rejected framings |
| 4 | Depth as leverage (not the implementation/interface line-count ratio) | interface-and-seam.md | ## Depth as leverage |
| 5 | Internal seam vs external seam | interface-and-seam.md | ## Internal seam vs external seam |
| 6 | The lexical ban — never "component", "service", "API", "boundary" | interface-and-seam.md | ## Vocabulary |
| 7 | DEEPENING's four dependency categories | interface-and-seam.md | ## Four dependency categories |
| 8 | Replace, don't layer (testing strategy) | interface-and-seam.md | ## Replace, don't layer |
| 9 | Hyrum's Law as an operating premise, not a citation | contract-and-commitment.md | ## Hyrum's Law as an operating premise |
| 10 | The One-Version rule and the diamond-dependency problem | contract-and-commitment.md | ## The One-Version rule |
| 11 | The full idempotency section (three outcomes, key from intent, atomic claim, loud failure on payload mismatch, chosen in-flight response, retention on the longest re-delivery chain) | contract-and-commitment.md | ## Idempotency — the full section |
| 12 | The Common Rationalizations table AS A FORM (shortcut left, cost right) | contract-and-commitment.md | ## Common Rationalizations |
| 13 | Where validation does NOT go (shared-type internal calls, own-DB data) | contract-and-commitment.md | ## Where validation does NOT go |

## §2.3 — Martin items (13), rewritten from scratch (zero verbatim — see `shingle_check.py`)

| # | Item | File | Heading |
|---|---|---|---|
| 14 | The inflection point — when to build a boundary | martin-boundary-rules.md | ## 1. The inflection point — when to build a boundary |
| 15 | Partial boundaries that decay without an owner | martin-boundary-rules.md | ## 2. Partial boundaries decay without an owner |
| 16 | Four physical forms with their chattiness budget | martin-boundary-rules.md | ## 3. Four physical forms and their chattiness budget |
| 17 | The Kitty test | martin-boundary-rules.md | ## 4. The Kitty test, and why services alone aren't architecture |
| 18 | Services are not architecture | martin-boundary-rules.md | ## 4. The Kitty test, and why services alone aren't architecture |
| 19 | Dependency direction, stated operationally (A protected from B → B depends on A) | martin-boundary-rules.md | ## 5. Dependency direction, stated operationally |
| 20 | DIP filtered on volatility, not abstractness — violations collect in Main | martin-boundary-rules.md | ## 6. Depend on volatility, not abstractness — and let violations collect in Main |
| 21 | The REP/CCP/CRP tension and its drift over a project's life | martin-boundary-rules.md | ## 7. The REP/CCP/CRP tension, and why structure isn't designed top-down |
| 22 | SRP as one actor (not one responsibility), with its two violation symptoms | martin-boundary-rules.md | ## 8. SRP is one actor, not one responsibility |
| 23 | The Humble Object as a testability delta | martin-boundary-rules.md | ## 9. The Humble Object as a testability delta |
| 24 | A framework is an asymmetric marriage | martin-boundary-rules.md | ## 10. A framework is an asymmetric marriage |
| 25 | The database is a detail; the data model is not | martin-boundary-rules.md | ## 11. The database is a detail; the data model is not |
| 26 | The compiler enforces it, not the reviewer (pointer to the already-owned extract rules, never re-absorbed) | martin-boundary-rules.md | ## 12. The compiler enforces it, not the reviewer |

## Reconciliation, run

```
$ grep -c '^| [0-9]\+ |' architecture/references/absorption-checklist.md
26
$ python3 architecture/scripts/check_absorption.py
26/26 anchors verified — 0 missing
```
