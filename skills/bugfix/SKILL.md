---
name: bugfix
description: ◇ Polaris — Close a bug through 12 stages, each passed by an exit code — find without assuming, fix with TDD, prove the consequence, rewrite the tests that lied — with a fix-loop breaker and side findings filed as beads. Use when a traceback, a bug issue, a red smoke, a log error or "this doesn't work" arrives. Requires python ≥ 3.9, gh and tdd-dev; bd (Beads) for side findings. Not for an urgent production incident, which needs a hotfix.
version: 1.3.1
user-invocable: true
auto: true
status: active
job: take a bug from symptom to closed through stages that are passed with an exit code, never with a claim
when_not: urgent production incident (hotfix, not investigation) · sub-5-line single-file change with no behavior change · bug in a third-party dependency where the test cannot be written · "doesn't work" with no reproducible symptom
lifecycle: the record lives in the GitHub issue (no local file to drain); rosso_log and mutation-log in .bugfix/evidence/ committed with the PR; side findings live as beads; a class-level hole becomes a lesson through the repo's lesson recorder, never promoted from here
invokes: [tdd-dev, real-testing, git-power]
invoked-by: [human, issue-contract, cron-sweep]
io: takes a bug identifier (issue, traceback, smoke, log) → produces fix + reproducing test + rewritten tests + mutation-log + staged record, all attached to the issue, and one bead per side finding
---

# bugfix

## What it does

A bug is proof that the test meant to catch it lied. This skill closes it in twelve stages —
`ingresso riproduzione causa raggio` (find) · `rosso verde` (fix) · `realtest` (prove) ·
`mutazione raccolto` (rewrite) · `firma prod deposito` (close) — and each stage passes only with
`python3 scripts/fix_gate.py check --stage <stage> --record <path> --repo <repo>` (exit 0 pass,
1 missing evidence, 2 usage; fail-closed). State lives in the issue (record field `stato`).

## When

- A traceback, a bug issue, a red smoke, a log error or "this doesn't work" with a symptom.
- Not urgent: a paying user down, corrupted data, blocked revenue or 5xx > 5% → stop, hotfix.

## Steps

1. **Find, assuming nothing** (`ingresso` → `raggio`). Read errors where the repo contract says
   they live and check which commit is actually running. The perimeter comes from your harness's
   code graph (`references`, `call_hierarchy`), declared with the command in `chiamanti_cmd`.
   Recurrence before cause: search the tracker and `records/`, and ask the agent memory
   (`ai-memory-retrieval`, skipped if absent); write the outcome in `ricorrenza`, even "0 matches".
   A cause is `causa_in: path:line` plus the command that reproduces it.
2. **Fix, RED first** (`rosso`, `verde`) through `tdd-dev`: RED on an unchanged test, minimum
   fix, the module suite green. Callers from `raggio` are fix targets. No "while I'm here".
   Four red runs of the same test block `verde` until `architettura_riesaminata` is written.
3. **Fix-loop breaker** — before each new attempt and after anything you undo, score the loop:
   +15 per attempt of yours undone (a revert commit, a reset, an edit backing it out), +20 per file
   changed outside the `raggio` perimeter (cause file, its callers, the tests you rewrite,
   `.bugfix/`), +5 when one attempt touches more than 3 files. Files: `git diff --name-only
   $(git merge-base origin/main HEAD)` plus uncommitted ones. **Above 20, stop**: write the score
   and what was tried in the issue, set `stato: bloccato`, ask the owner. Unattended: `afk:blocked`.
4. **Side findings become beads.** A defect found while fixing that is not this bug is not fixed
   here and not filed as its own issue: hand it to `issue-contract`, whose `route.py` makes it a
   bead — with `--from <this bug's bead>` (`discovered-from`) when the bug has one, else naming
   this bug's issue in the bead's description. GitHub only when that filter says so.
5. **Prove the consequence** (`realtest`): `real-testing` on what the fix causes, real IO.
6. **Rewrite the tests that missed it** (`mutazione`, `raccolto`): replace them under tdd-dev's
   `references/writing-tests.md`; `scripts/mutation.py run` re-inserts the bug and must go red on
   the same `fix_sha`; the new test must appear in the contract's `ci.collect` output. A hole
   that is a class becomes a lesson. Commit boundary: `git-power commit-check`.
7. **Close** (`firma`, `prod`, `deposito`): signature, a prod observation with an exit code, and
   for non-deterministic classes a watch window. Each checkpoint answer goes in the issue.

## Output

The issue carries the record: verbatim symptom, perimeter with its command, discarded hypotheses
with the evidence that killed them, proven cause, rosso_log and mutation log, every stage's exit.
Plus the PR with fix and rewritten tests, and the bead ids of side findings. Full stages:
`references/phases.md`; repo contract: `references/contract-template.yml` (`.fix/contract.yml`).
**Next:** `ship`; stopped by the fix-loop breaker → STOP, ask the owner with what was tried.

## Not for

- An urgent production incident — hotfix, not investigation.
- A sub-5-line, single-file change with no behaviour change and green coverage.
- A third-party bug you cannot test here: workaround plus upstream issue.
- "Doesn't work" with no reproducible symptom: get the symptom first.
