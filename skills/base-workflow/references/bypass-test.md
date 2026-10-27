---
title: base-workflow — bypass-test (DESIGNED, NOT YET EXECUTED)
description: The ways to skip the build method, and which mechanism is supposed to catch each. This skill ships no script of its own — every gate below belongs to a door it routes to. Honest status — this file existing does NOT mean the cases were run; promotion needs them executed with before/after output and both critics.
status: draft
---

# Bypass-test — base-workflow

This skill is an order of steps; it owns no gate. A bypass is caught by the door that owns the
step, or it is **not caught at all** — the last column says which, without rounding up.

| bypass | caught by | must |
|---|---|---|
| production code edited before a RED exists | `tdd-dev` — its RED verification on the unchanged test | exit ≠ 0: no recorded RED on the unchanged test hash |
| RED staged by deleting the finished implementation | `tdd-dev` breaker reading the rosso_log error text and RED→GREEN distance | rejected; a staged RED is not a RED |
| change adds a module to an import cycle | `/architecture` cycle measure on base vs head (modules inside SCCs) | head > base → the change is refused at review; **no automatic hook today** |
| "fewer cycles" claimed after merging two cycles | the same measure — modules inside SCCs, never the cycle count | the sum rises, the claim fails |
| boundary moved with no Decision | `/architecture doctor` (decision/dependency drift rows) | a drift row naming the moved boundary; **only if someone runs it** |
| default threshold quoted while the repo declares another | nothing mechanical | **NOT CAUGHT** — only a fresh-context `critic` or the spec review reading the repo's rules |
| guard added in each caller instead of the shared function | nothing mechanical | **NOT CAUGHT** — `critic` / review reading the caller list |
| "done" with no real-product verdict | `real-testing` PreToolUse gate on `git commit` | commit refused without a verdict for the served SHA |

## What would make this skill promotable

1. Each row run on a fixture repository with the before/after output pasted here.
2. The two **NOT CAUGHT** rows either get a mechanism (a check that reads the repo's declared
   thresholds; a caller-count diff) or stay declared as judgement-only, by name.
3. Both critics `BLINDATA`, per the suite standard.
