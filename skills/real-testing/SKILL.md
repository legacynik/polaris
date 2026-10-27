---
name: real-testing
description: "◇ Polaris — Verdict from the real product: serve the commit, walk the customer journey through the UI on every surface it reaches, let a fresh agent try to break it, leave the tests in CI. Modes: local, merge (receipt bound to the tree), production check. Use before merge or promotion, on 'test the app', or when someone says it works. Requires git, python3, gh, bd; browser-harness for UI walks. Not diff reading (review)."
version: 4.2.1
user-invocable: true
auto: true
lifecycle: "merge mode produces .real-test/verdicts/<hash>.json (local, never committed, drained by verdict.py once the hash is unreachable) + tests left in CI (permanent); local findings live on as beads (src:real-test) until closed; .real-test/bypass.log local, drained by hand"
invokes: [git-power]
invoked-by: [bugfix, sweep, ship, babysit, implement-plan, human]
io: "a served commit (branch or production) -> merge: verdict MERGEABLE|MERGEABLE-CON-GAP|NOT-MERGEABLE naming the environment and served SHA, read by the pre-commit gate and by ship; local: pass or rewrite beads blocking the work; production: a health report whose defects go through issue-contract"
status: active
---

# real-testing

## What it does

Proves a change on the running product, never by reading it. One method in three modes: serve
the commit, walk the journey as the customer, let a fresh agent try to break it, record what
held with evidence.

| Mode | Served where | Yardstick | Result |
|---|---|---|---|
| local | this machine | the work's DoD | pass, or rewrite beads blocking the work |
| merge | staging (the repo's `signing_env`) | acceptance + perimeter | receipt bound to the tree |
| production check | production, no diff | `real_test:` journey | health report |

## When

- Never as a phase gate: a Beads phase closes on green tests. Per-phase mode only when asked.
- Before a merge or promotion, on the branch served, never on `main` after the merge.
- "Test the app" on a live product, or a scheduled health check: production check.
- Someone says "it works" with no served SHA and no evidence.

## Steps

1. **Serve and prove parity.** The served commit (health `commit`, build marker) equals the one
   you test; not equal, stop. Merge: staging through the repo's `ship:` contract, never by hand.
2. **Promises and perimeter.** One line per promise: the DoD, the acceptance, or the journey
   steps. Merge and local add `python3 scripts/perimeter.py --repo . --head <sha>` and the
   code graph: every surface the change reaches.
3. **Walk as the customer.** A UI is reached: browser-harness over CDP, its own instance, tabs
   listed before any action, on `real_test.browser_profile` when set. Never type a password; an
   expired session stops the run: "session expired, log in again in profile X". An API-only
   pass ticks backend boxes only.
4. **Break it from fresh context.** A fresh-context agent from your harness, on the strongest
   model it has, gets the URL with the SHA, the promises and the contract; never the diff or
   your session. Every attempt names its attack class (`references/merge.md` step 6).
5. **Verdict.** Merge: `python3 scripts/verdict.py new|validate` binds it to the tree; post the
   PR receipt. Per-phase: each misaligned DoD line → `bd create "rewrite: …"
   -t task -l src:real-test,kind:finding,area:<a> --parent <epic>
   --deps discovered-from:<phase>,blocks:<phase>` (no `bd`: stop). Production: each defect through `issue-contract`. Details: `references/modes.md`.
6. **Leave the tests.** A defect gets its test seen red before the fix; an untested combination
   its test. What could not be proven is said, with the blocker named.
7. **Close what you opened**, every mode, before the report: `references/teardown.md`.

## Output

- Merge: `.real-test/verdicts/<hash>.json` (`MERGEABLE`, `MERGEABLE-CON-GAP`, `NOT-MERGEABLE`)
  naming the environment and served SHA; the `<!-- real-test v1 sha=… -->` PR comment; facts
  for `pr` in `.real-test/fatti/<branch>.md`.
- Per-phase: a local receipt (`references/modes.md`) and rewrite beads; production: healthy, or defects with evidence.
**Next:** MERGEABLE → the caller goes on (`ship`); NOT-MERGEABLE → back to `implement-plan` or `bugfix` with the beads.

## Where this goes

This skill produces: **validation** — at the path the host's `outputs:` map gives that kind; the
local verdict file is a pointer, never the document.

## Not for

- Reading a diff, or a cross-model second opinion: `review`. Attacking a plan or claim: `critic`.
- A docs-only change: say so and stop. An environment you cannot reach is a block, not a pass.
