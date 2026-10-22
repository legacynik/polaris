---
name: bugfix
description: ◇ Close a bug in 4 gated phases — find without assuming, fix with TDD, prove the consequence not the SHA, rewrite the tests that lied. Use when a traceback, a bug issue, a red smoke, a log error, or "this doesn't work" arrives. Do NOT use for an urgent production incident (paying user down, corrupted data, blocked revenue) — that needs a hotfix, not an investigation.
version: 1.2.1
user-invocable: true
auto: true
status: active
job: take a bug from symptom to closed through stages that are passed with an exit code, never with a claim
when_not: urgent production incident (hotfix, not investigation) · sub-5-line single-file change with no behavior change · bug in a third-party dependency where the test cannot be written · "doesn't work" with no reproducible symptom
lifecycle: the record lives in the GitHub issue (no local file to drain); rosso_log and mutation-log in .bugfix/evidence/ committed with the PR; lesson proposed to the repo ledger, never promoted from here
invokes: [tdd-dev, real-testing, git-power]
invoked-by: [human, issue-contract, cron-sweep]
io: takes a bug identifier (issue, traceback, smoke, log) → produces fix + reproducing test + rewritten tests + mutation-log + staged record, all attached to the issue
---

# bugfix

## In two lines

A bug is not just broken code: it is **proof that the test that should have caught it lied**.
On a production repo, **79 bugs closed in 30 days and 7 caught by a gate** — 91% sailed through the tests.
So this skill does not end with the fix: it ends when the rewritten test **goes red with the bug
re-inserted** and when that test is **collected by CI**, not merely committed.

**The gate lives in the workflow**: every stage is passed with

```bash
python3 scripts/fix_gate.py check --stage <stage> --record <path> --repo <repo-path>
```

Exit `0` pass · `1` no (stderr says what is missing) · `2` usage error. **Fail-closed**: missing
record, missing contract, placeholder values (`.`, `TBD`, `n/a`) never produce 0. It does not
ask, does not advise: it blocks or stays silent.

```
        issue · traceback · red smoke · log
                      │
                      ▼
   ┌── PRE-FLIGHT ── urgent? ──► yes ──► STOP: hotfix, not here
   │                  │ no
   │                  ▼
   │   ① FIND ───── ingresso → riproduzione → causa → raggio
   │      │          no cause without the command that proves it
   │      ▼
   │   ② FIX ────── tdd-dev: rosso provato → minimal fix → verde + regressione
   │      │
   │      ▼
   │   ③ PROVE ──── realtest: the consequence, not the diff. Real IO, no mocks
   │      │
   │      ▼
   │   ④ REWRITE ── mutazione: re-insert the bug → MUST go red
   │                 raccolto: the new test is in CI, or it is an orphan
   └──────────────────────► firma → prod → deposito · issue = the record
```

State does not live in a local file: **it is the issue**, via the record's `stato` field
(`aperto → fixato → staging-provato → prod-verified → sorvegliato/chiuso`, `bloccato`). Whoever
resumes reads the record and knows the stage. Panel switch, dead session, another machine: the
record survives.

## First of all — is it urgent?

| condition | action |
|---|---|
| paying user down · corrupted data · blocked revenue · 5xx > 5% | **STOP.** You need a hotfix. This skill investigates, and investigation costs time you don't have in an emergency |
| everything else | continue |

The missing hotfix path here is not an oversight: it is a choice. A path that repairs fast and
one that understands deeply have opposite rules, and merging them produces the worst of both.

## Phase ① — FIND, assuming nothing (stages: ingresso, riproduzione, causa, raggio)

**Exit rule: a cause is declared only with the command that proves it** — stage `causa` wants
`path:line` on an existing file, stage `riproduzione` wants a command that exits ≠ 0. A plausible
hypothesis does not open phase ②. `unverified-assumption` is the most frequent class in the
corpus (38% of corrections).

1. **Real context before hypotheses.** The per-repo contract says where errors and logs live
   (DB, CloudWatch, files): read them **from there**, and verify **which code is actually
   running** (deployed commit, not the disk: a real-test has already been run against a worktree
   30 commits stale).
2. **Perimeter from the graph, never by grep.** `find_symbol` on the traceback symbol, then
   `find_referencing_symbols` for callers. Stage `raggio` demands both axes: `chiamanti` AND
   `issue_prese`/`issue_lasciate` — zero callers is **declared**, not omitted.
3. **Archive: has it happened before?** Search it actively (module + exception type) and declare
   the outcome in the record's `ricorrenza` field — stage `causa` blocks without it, even for
   "0 matches". A recurrence is not a new bug, it is an incomplete fix that regressed.
4. **Known traps, excluded first**: DB schema drifted from the code · mocks hiding real
   behavior · a gate that was green and lying · **a doc stating something false** (~46% of
   claims in contract docs, measured across 3 repos) · another panel's fix changing state
   underneath.
5. **Architecture docs are hypotheses, not facts.** When doc and graph diverge, the divergence
   is a finding — and often the cause.

Into the issue: verbatim symptom · perimeter with the command that produced it · **discarded
hypotheses with the evidence that killed them** · proven cause.

## Phase ② — FIX, RED first (stages: rosso, verde)

1. **The code change belongs to `tdd-dev`.** It registers RED on an unchanged test, applies the
   minimum fix, proves targeted GREEN, then runs the repo-authoritative relevant regression suite.
   Stage `rosso` calls its `red_check.py verify`: without that receipt, this gate blocks.
2. **Blast radius before the fix, not after.** Callers from the graph are fix targets — and they
   are **proven, not listed**: stage `raggio` demands `chiamanti_cmd`, the command that produced
   them (a fix to the primary site whose callers nobody looked at ships mute).
3. **Minimal fix.** No "while I'm here" refactors: the fix and the improvement are two commits.
   Simplification is welcome but OPTIONAL and post-green — and any simplify that touches code
   after `verde` re-opens the gates by construction (content-hashed receipts, SHA-bound
   verdicts): green and mutation re-run, or the gate denies on its own.
4. **Green = the module's suite passes** (stage `verde`, command from the contract), not just the
   new test: no collateral damage.
5. **Circuit breaker**: 4+ red runs of the same test in the `rosso_log` means you are thrashing —
   stage `verde` blocks and demands `architettura_riesaminata: <conclusion>` instead of fix #4.
   Three failed fixes are not asking for a fourth; they are questioning the design.

## Phase ③ — PROVE the consequence, not the SHA (stage: realtest)

The test's perimeter is **what the fix causes**, not the diff. Touches a contract → prove the
contract. Touches persistence → round-trip on a real store: 1,006 green tests hid a record that
vanished on the real DB. Stage `realtest` **propagates** `real-testing`'s verdict, it does not
write a new one. Every new branch the fix introduces must be exercised, or the gate is incomplete.

## Phase ④ — REWRITE the tests that missed it (stages: mutazione, raccolto)

1. **Which tests should have caught it, and why did they pass?** Real causes from the corpus:
   mocks instead of real IO · trivial asserts · subset instead of equality · the test never
   touches the production path.
2. **Rewrite them**, don't add one alongside.
3. **Prove it**: `scripts/mutation.py` re-inserts the bug and reruns — stage `mutazione` demands
   the log attributed to the **same** `fix_sha` with `tornato_rosso: true`.
4. **The harvest** (stage `raccolto`): the new test must appear in the output of the CI's
   collection command (`ci.collect` in the contract). A committed test no workflow runs is an
   **orphan**: it protects only whoever runs it by hand — it happened in this skill's own eval.
5. If the hole is a **class** (*"every test in this module mocks the DB"*), the phase produces a
   ledger entry, not just a test.
6. **Self-heal exit question**: was this bug one-off or
   systemic? If a gate, skill, or hook let the pattern through, the answer patches THAT — the
   door corrects itself, or it stays a static list of past mistakes.
7. **Commit boundary**: invoke `git-power commit-check` on the staged diff. Exit 3 means split
   the fix by behavior, or record why the boundary is indivisible before calibrating the limit.

## Closing (stages: firma, prod, deposito)

`firma` wants evidence + `firma: founder` readable by a script · `prod` wants an observation
with an exit code ("I deployed" is not proof) · `deposito`, for non-deterministic classes, wants
a window + a detector. In the **AFK** pipeline the stages are fail-closed with no exceptions; in
a human session the gate stays manually invocable, never a default blocking hook.

**Self-answered checkpoints**: every nominally interactive point ("may I move to the next
phase?") is crossed with the stage's criteria and the answer **written in the issue**, never in
silence.

## When NOT to use it

- **Urgent production incident** — see pre-flight. You need a hotfix.
- **Sub-5-line, single-file, zero behavior change** (typo, formatting) with the module's
  coverage already green: the protocol costs more than the bug.
- **Bug in a third-party dependency** where you cannot write the test: tracked workaround and
  upstream issue, not this cycle.
- **"Doesn't work" with no reproducible symptom**: first you need a symptom. Reproducing is not
  phase ① — it is its prerequisite.

## What the repo must provide

`.fix/contract.yml` — **that** repo's ceremony: `dominii` vocabulary (or `dominii_da` pointing
at an existing catalog), `test.suite`, `ci.collect`, `tdd_dev`, `real_test`, `prod.osserva`,
`deployabili`. Template in `references/contract-template.yml`. **Without a contract the gate
exits 1 and says so** — exit code, not a promise: it does not guess, it does not assume defaults.

## Anti-patterns, from real cases

- **"Quick fix, we'll track it later"** → 10 fixes for the same bug in 7 days.
- **Test written after the fix with no registered red** → documentation, not a gate.
- **New test committed but orphaned from CI** → R5 of the 2026-08-16 eval: the net that isn't there.
- **Skipping the blast radius** → the mute fix, and residual bugs surface at the proof gate.
- **Declaring "done" in the same turn without proof** → 5-6 times in one session, each caught by
  whoever was reading.

## Proofs

`references/bypass-test.md` — B1–B8 with `fails_before` and before/after output ·
`python3 scripts/fix_gate.py --selfcheck` (76 checks) ·
`python3 scripts/mutation.py --selfcheck` (11 checks).
