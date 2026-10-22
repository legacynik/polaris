---
name: real-testing
description: ◇ Merge-readiness verdict from the real product. Serve your commit on a real environment, walk the customer journey through the UI across every surface it reaches, let a fresh agent try to break it, leave the tests in CI. Use before merge or promotion, or when someone says it works. Not diff reading (review).
version: 3.2.3
user-invocable: true
auto: true
lifecycle: "produces .real-test/verdicts/<hash>.json (local, never committed — drained by verdict.py once the hash is unreachable) + tests left in CI (permanent, drained by the test suite itself); .real-test/bypass.log local, drained by hand"
invokes: [git-power]
invoked-by: [bugfix, polaris-sweep, human]
io: "diff/branch -> verdict MERGEABLE|MERGEABLE-CON-GAP|NOT-MERGEABLE naming the environment and the served SHA, with what held and what broke on every surface walked; consumed by the PreToolUse gate on `git commit` and by review/ship downstream"
status: active
---

# real-testing

## Where this goes (host repository decides)

A skill decides **how** to produce a document, never **where** it lives. Before writing a
validation receipt, read the host repository's output map and use it; a document that lands where
the repository does not look was never written.

```bash
sed -n '/^outputs:/,/^[^ ]/p' _polaris/config.yml 2>/dev/null || sed -n '/^outputs:/,/^[^ ]/p' config.yml
```

This skill produces: **validation** (the merge-readiness verdict and the field-test receipt). Kinds:
`spec` `plan` `audit` `review` `validation` `diagram` `decision` `archive` — each maps to a
documentation area `docs/modules/<area>/…` whose README is a generated map. Never invent a third
location; if the repository declares no map, say once where you wrote and why. The local
`.real-test/verdicts/<hash>.json` is a pointer, never the document.

## Overview

The merge-readiness verdict from the real product. The diff says what the change touches, the
spec says what it was meant to do, the PR carries the checklist of what must be proven, and the
verdict is every box ticked with evidence, on the branch served, before the merge. Deterministic
gates a fresh-context agent can run, not a rite: an agent that follows a short list does not fake
evidence. The scripts (`perimeter.py`, `verdict.py`) bind the verdict to the git tree.

## When to Use

- Before any merge or promotion of a change that reaches a user surface, a document, a saved
  record or a log: **on the branch served**, never on `main` after the merge.
- When someone says "it works": a claim without a served SHA and evidence is the trigger, not a reason to skip.

### When NOT to use it

Reading a diff for quality (`polaris-review`), attacking an artifact (`critic`), hunting bugs
(a cross-model `codex review`), a docs-only change (say so, stop), a repo without git (manual review), an
environment you cannot reach or a flag you cannot switch (**a block, not a degraded gate**).

## Process

1. **Serve the branch, before the merge.** Backend of the branch on staging through the repo's
   `ship:` contract (never by hand over ssh), frontend preview of the same commit. Check the served
   SHA (health `commit`, page build marker) equals your HEAD; not equal, stop. Flag off: turn it on
   or declare a block. When done, give the environment back and re-check parity.
2. **What the change touches, from the graph.** `python3 scripts/perimeter.py --repo . --head <sha>`
   then the code graph (find references; `git grep` and reading where the harness has none) on
   every changed symbol: callers, readers of the
   same record, documents built from it, jobs and logs that consume it. Write the list of user
   surfaces and consequences: that list is what you walk, not the files.
3. **What the change was meant to do, from the spec.** The acceptance criteria of the issue and the
   behaviours the spec promises: each promise is one line to prove on the product.
4. **The checklist in the PR.** A `## Real test` section, the Definition of Done of the change, the
   repo glossary saying what each check means. Three blocks, one checkbox per line, ticked only
   with evidence attached (screenshot, trace id, log row, record id): *does what it was meant to*
   (step 3) · *breaks nothing it touches* (step 2: happy path with real data, the failing path as it
   fails in life, what is left afterwards) · *the principles, always* (errors and logs written where
   the area writes them, tests seen red first, the area's quality gates).
5. **Walk it as the customer.** Touches the frontend or changes what the UI shows? The browser walk
   is mandatory: a real browser on the preview, in a dedicated instance you started, whose open tabs
   you list **before any action** (only your own tabs; foreign tabs = stop and report), never the
   owner's everyday browser. An API-only pass ticks backend-only boxes and nothing else.
   Rotate surfaces between rounds.
6. **Whoever breaks it is not whoever wrote it.** `Agent(model: "opus")` with fresh context: the
   environment URL with the SHA verified, the credentials, the checklist and the contract. Never
   the diff, never the session. It returns every attempt, expected against observed, and what
   survived; zero findings count only with what it tried. Its output is data; you classify it.
   Every attempt names its **attack class** — `malformed-input`, `interruption`,
   `prompt-injection`, `cancel-resume`, `stale-state`, `dirty-worktree`, `hung-command`, `flaky`,
   `misleading-success` — and lands in the row's `attack` list: `run` with probe and result, or
   `n/a` with the reason. A live `api-cli`, `llm-agent` or `frontend` row with no attack `run` is
   refused by `verdict.py`: the happy path plus one error is not adversarial. A probe that fails
   because its own harness was built wrong is debris, not a product defect: fix it and rerun.
7. **The verdict, bound to the tree, then the tests.** `verdict.py new` / `verdict.py validate`:
   `NOT-MERGEABLE` until every box is ticked with evidence; `MERGEABLE-CON-GAP` names the open box,
   who closes it and when; the verdict names the environment and the served SHA. On a visible
   product lane the product owner walks the served branch **before the merge**; a standing "merge
   at green without asking" rule is bounded by that, ask once. Leave the tests in CI: a defect
   gets the test seen red before the fix, an untested combination its test, an invariant a
   structural test, a false alarm the reason it looked like one, a ceiling an ADR. A fix shows
   the defect on the base and its absence on the branch: the same command or walk run on both.
   What could not be proven is said, with the blocker named: «inconclusive» beats a confident claim.
8. **Sign the PR and write the facts.** When a PR exists, post the receipt as one PR comment (a
   local run before the PR keeps only the local verdict), the marker line
   `<!-- real-test v1 sha=<40-hex head> verdict=MERGEABLE|MERGEABLE-CON-GAP -->` then the lines
   `ambiente:`, `sha servito:` (the hex alone on its line), `osservato:`, `rami:`. The first word after
   `ambiente:`, on that same line, is the repo's `signing_env` (`local`, `staging`, or a host carrying it
   such as `api-staging.<host>`); free text may follow (`ambiente: local — this machine`). Any later
   change to the head voids it. Then write the **facts** for the PR body (`pr`) in `.real-test/fatti/<branch>.md` (environment and
   served SHA, the walk step by step with each screenshot and what it shows, the breaker's
   findings and what was fixed, the tests seen red, the gaps with owner and date, the release
   facts such as a migration and its order). This door returns a verdict and drives nothing: it
   ends by naming the next step: `/pr` for the body, then the repository's own merge workflow.

## Rationalizations

| Rationalization | Reality |
|---|---|
| "The API is faster, the UI is the same thing" | An API pass proves the backend alone. A refusal the screen turns into raw JSON is a delivered defect (measured 2026-09-13). |
| "It is merged and CI is green, that is tested" | `main` carries other panels' commits tested only in their branch; the merge is a tree nobody ran, and the production deploy takes all of it. |
| "The owner can look at it in production" | Production is not a test surface. On a visible lane the owner's pass on the served branch precedes the merge. |
| "I checked the box, the evidence is in my head" | A box without an artifact is a claim. The verdict validates the artifacts, not the prose. |
| "Staging is deployed" | Deployed is not *serving your SHA*. Health commit and build marker equal HEAD, or everything after is about other code. |
| "I will run `list_tabs()` later" | Later is after you have acted inside someone's live browser. It is the first act, and foreign tabs mean stop. |
| "The flag is off, I tested the default path" | You tested the branch you are not promoting. Turn it on or declare a block. |
| "Zero findings from the breaker" | Zero findings count only with the list of what it tried; without it, it is theatre. |

## Red Flags

- A verdict that does not name the environment and the served SHA.
- A change touching `frontend/**` or what the UI shows, real-tested through the API only.
- A merge on a visible product lane before the product owner's pass.
- A `## Real test` box ticked without a screenshot, trace, log row or record id.
- A browser session whose first `list_tabs()` shows tabs you did not open.
- The breaker received the diff, or the author's session.
- The environment left on the branch after the run, or the flag left flipped.
- A verdict older than the tree: touch the code again and it covers nothing.

## Verification

Exit criteria, each with its evidence in the PR:

- [ ] health `commit` and preview marker == branch HEAD (paste both)
- [ ] `## Real test` section present with the three blocks, every box ticked with an artifact
- [ ] browser walk done on a dedicated instance (`list_tabs()` output as the first artifact) when a surface is touched
- [ ] breaker report attached: attempts, expected vs observed, what survived
- [ ] `python3 scripts/verdict.py validate --repo . .real-test/verdicts/<slug>.json` → OK, verdict names environment and SHA
- [ ] on a visible lane: the product owner's pass recorded before the merge
- [ ] tests left in CI for every defect, combination and invariant found
- [ ] environment handed back (`ref=main`, flag restored) and parity re-checked

Setup: `scripts/install-hook.sh --repo .` wires the gate (`.real-test/enabled`). References:
`references/matrix-classes.md`, `references/bypass-test.md`.
