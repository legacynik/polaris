---
name: tdd-dev
description: ◇ Use when implementing a feature or behaviour change test-first, when fixing a reproducible bug through a regression test, when a written fix needs proof its test catches the old defect, or when a passing test is accepted without an observed RED. Serves bugfix and approved feature workflows. Do NOT use for throwaway prototypes or configuration-only edits.
version: 2.1.1
user-invocable: true
status: active
job: drive one code change from an agreed public seam through proven RED, minimum implementation, GREEN receipt, and the repo-authoritative regression suite
when_not: load/performance thresholds · production observability probes · test-only cleanup · throwaway prototypes · generated code · configuration-only edits · third-party defects that cannot be reproduced in our code
io: consumes one acceptance criterion or reproducible defect, a test node id, its targeted command, the relevant suite command, and a rosso_log path → produces the minimum code change, hash-bound RED/GREEN receipt, regression result, and a review/deploy-ready handoff
lifecycle: the rosso_log and regression evidence are committed with the work item; the workflow that owns the change drains them when the item closes
invoked-by: [bugfix, planning-and-task-breakdown, human]
---

# tdd-dev

One house workflow: design one behavioural test through the public seam, then certify that same
unchanged test from valid RED through minimum code, GREEN receipt, and relevant regression.

**No production behaviour changes before one test has a valid recorded RED.** A targeted GREEN is
not completion: the same test must prove GREEN on the unchanged hash, then the repo-authoritative
relevant regression suite must pass before review or deploy handoff.

## The iron law

- **New work written before RED:** remove it from the active diff and do not use it as a reference.
  Let the public test drive a fresh minimum implementation.
- **A fix already exists:** do not destroy it or use a generic stash. Use the owning workflow's
  isolated mutation runner to reintroduce the old defect, record RED, restore, then prove GREEN.
- **Prototype, generated code, or configuration-only change:** this skill does not own it. An
  explicit human decision may choose another workflow; the agent does not invent an exception.

## The adversarial RED — what the test must be for a guard or a recovery

`red_check.py` makes the RED unfakeable: it hashes the test file, so a red cannot be claimed by
voice. **What it cannot do is record the red of the test you never thought to write** — and for
two kinds of change the obvious test is the wrong one.

- **An authorization or admission guard.** The obvious test asserts *the guard refuses what it
  must refuse*, and it passes for every guard that is bypassable. The RED to register is the
  opposite: **the cheapest call that still gets through**, written first, watched fail, then
  closed. Ask it of the guard's inputs too — an optional field the model itself writes is not a
  protection. Mutation corollary: a **permissive** mutation (`return True`) is visible only to
  assertions that expect a REFUSAL. If it drops one test, the gate is not covered; a gate whose
  permissive mutation drops one test has one bypass proven and the rest unexamined.
- **A recovery, retry, checkpoint or resume path.** The obvious test asserts *the resume works*,
  on a run that was never interrupted. The RED to register is **the disaster itself**: kill the
  process mid-batch, observe the duplicated or lost item, then build the recovery against that
  observation. A resume proven only on a clean run has never resumed anything.

Evidence, 2026-09-05: one authorization gate took four rounds — bind the tool but not the
destination, then the destination through an optional model-written field, then the frozen keys
while every other key went unread (approved `to`, added `bcc`, executed). Every round had a
clean chain — RED by hash, `verify` 0, mutations run — because every round wrote the test that
confirms the guard and none wrote the one that bypasses it. Three reviews, a re-review and a
breaker all asked the same non-adversarial question.

## One vertical cycle

1. **Fix the seam, behaviour, break, and suite.** Name one public interface, one caller-visible
   result, the production mutation that should make the test fail, and the authoritative relevant
   suite command from the repo contract. If no narrower command is authoritative, use the full suite.
2. **Write one test.** Exercise real code through the seam. Derive the expected value from the
   contract, a worked example, or real data — never from the implementation or its helpers.
   **Two kinds of change invert what the test must be, and getting this wrong produces a clean
   chain around a defect** (see *The adversarial RED* below): a guard's test is the **bypass**,
   a recovery's test is the **disaster**.
3. **Record RED and read it.** Run the exact node through `red_check.py record`. It must fail because
   the behaviour is missing. A pass means existing behaviour or a wrong test; an import, fixture,
   credential, network, or setup error is invalid. Repair the harness and repeat.
4. **Implement the minimum.** Add only what this test requires. No later criteria, speculative
   branches, refactors, or nearby cleanup.
5. **Record targeted GREEN and verify.** Same node, command, test file, and `rosso_log`;
   `red_check.py verify` must exit 0.
6. **Record the regression suite.** Run the command fixed in step 1 through `red_check.py suite`;
   it must exit 0 with no new errors or warnings. Then verify the complete receipt with the exact
   `--suite-cmd`. A regression is fixed in production code, not by weakening an existing test.
7. **Close the slice.** Report the receipt and regression command. Refactoring happens after GREEN;
   every production edit after step 5 reruns targeted GREEN, the suite receipt, and final `verify`.
   Only then may review/deploy receive the handoff or the next criterion start.

```bash
python3 scripts/red_check.py record --test <node-id> --cmd "<one-test-command>" --out <rosso-log>
# minimum production change
python3 scripts/red_check.py record --test <same-node-id> --cmd "<same-command>" --out <same-log>
python3 scripts/red_check.py verify --log <same-log> --test <same-node-id>
python3 scripts/red_check.py suite --test <same-node-id> \
  --cmd "<repo-authoritative-regression-command>" --out <same-log>
python3 scripts/red_check.py verify --log <same-log> --test <same-node-id> \
  --suite-cmd "<repo-authoritative-regression-command>"
```

Completion is mechanical: final `verify --suite-cmd` exits 0 only after the unchanged-test
RED→GREEN and a later matching suite GREEN. `tdd-dev` never deploys; it opens the handoff gate.

## Output contract

Before writing the test, state exactly:

```text
SEAM: <public command or interface>
BEHAVIOUR: <one observable result>
BREAK: <production mutation that should make this test fail>
TEST: <one node id>
EXPECTED RED: <missing behaviour named by the failure>
SUITE: <repo-authoritative relevant regression command>
```

Close the slice with:

```text
PROOF: <rosso-log> · unchanged test hash
REGRESSION: <same log> · suite command · final verify exit 0
HANDOFF: review/deploy gate open
```

## The test bar

- **Public behaviour.** A refactor that preserves behaviour must not break the test.
- **Named break.** If no realistic production mutation should fail it, the test is decoration.
- **Independent expectation.** Use known literals or hand-checked fixtures, never mirrored logic.
- **Real components.** Mock only slow or external system boundaries, not code we own.
- **One logical assertion and one slice.** The next test waits for receipt plus regression GREEN.

Read [`references/anti-mirror.md`](references/anti-mirror.md) only for parsers, regexes, word lists,
hand-built fixtures, or a passing test suspected of describing the implementation.

| Excuse | Reality |
|---|---|
| “The targeted test is green; ship.” | It proves the new behaviour, not absence of collateral damage. Run the authoritative suite. |
| “The code already works; add the test now.” | New unproven work leaves the diff. An existing fix uses isolated mutation to recover RED. |
| “Write all acceptance tests first; it is faster.” | Horizontal tests freeze an imagined design. One tracer test teaches the next slice. |
| “Any non-zero exit is RED.” | Setup and environment failures prove the harness is broken, not the behaviour missing. |
| “The full suite is slow, so pick a smaller command.” | Use a narrower command only when the repo contract declares it authoritative. |
| “Clean this nearby code while GREEN.” | Refactor after proof, then rerun targeted GREEN, receipt verification, and regression. |

## Stochastic behaviour and existing fixes

For an existing fix, use the owning isolated mutation runner; for `bugfix`, that is
`scripts/mutation.py`. For stochastic behaviour, wrap N runs and the declared threshold in one
deterministic command whose exit code means PASS or FAIL, then record that command. Load and
performance thresholds remain outside this skill.

`red_check.py verify` proves RED exists, GREEN exists, GREEN is latest, and the test hash is
unchanged. With `--suite-cmd`, it also requires a later matching suite GREEN. It cannot judge the
failure reason; reading step 3 remains mandatory.

`record` has **three** outcomes, not two. Besides RED and GREEN it answers **exit 2 with the cause
and no row written**, whenever the runner never spoke, or spoke and then died: a `cd` into a missing
directory, a shell syntax error, zero tests collected, a collection error, an import that died
first, a process killed by a signal (exit 128+n) with its output already half printed. Such an outcome
belongs to the environment, and recording it as RED is how fourteen reds once had to be thrown away
by hand (#373). What counts as the runner speaking is decided by `scripts/red_signatures.py`: one
entry per runner, every pattern anchored to the start of a line, never a bare substring — `FAILED `
alone also comes out of buildkit, make and git. **A new runner is added there, with a real captured
fixture under `tests/fixtures/`; widening a pattern until an output matches is the defect.**

## When NOT to use it

- Load or performance thresholds.
- Production health, telemetry, and alerting probes owned by the observability workflow.
- Test-only cleanup with no product behaviour change.
- Throwaway prototypes, generated code, or configuration-only edits.
- Third-party defects that cannot be reproduced in our code.

## Selfcheck

```bash
python3 tdd-dev/scripts/red_signatures.py --selfcheck
python3 tdd-dev/scripts/red_check.py --selfcheck
python3 -m pytest tdd-dev/tests/test_red_check.py -q
```

`red_signatures --selfcheck` puts every runner signature against real captured output and then
replaces the constant per runner, so a generic pattern cannot stay green. `red_check --selfcheck`
measures what the shell actually did (`cd`, `;`, a subshell, `pushd`, `cd -`) under every shell
present, and compares the verdict to it. The pytest file carries the rest: missing/corrupt
histories, invalid REDs, unchanged-hash RED→GREEN, stale or failing suite receipts, wrong nodes,
missing files, composed commands, and both CLI paths.
