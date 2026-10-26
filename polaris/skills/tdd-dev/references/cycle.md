# tdd-dev — the full cycle

The detail behind `SKILL.md`: the iron law, test admission, every step of the vertical cycle,
the output contract, the excuses that fail and the selfcheck. Moved here unchanged when the skill
took the 60-line form (2.6.0).

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

## TEST LIST and TEST ADMISSION (before RED)

Before coding, derive a **TEST LIST** from the contract: happy path, each error path, every
boundary/edge and each fallback. List behaviours, not test implementations. Keep adding discoveries;
many tests come from exhausting that list, not from bulk-writing imagined code (horizontal slicing).

For each next test declare **CONSUMER, SEAM** (existing public interface), **BEHAVIOUR, ORACLE**
(independent expectation), **REAL PATH** (entry point → production → effect), and **REFACTOR
INVARIANT** (a private change that must leave this frozen test green). Admit it only when all six
describe caller-visible behaviour. A test is not admitted if it calls a private helper, mocks owned
code, reads production source or prose, inspects generated argv instead of executing it, or asserts
a fixture/stub it authored. These are implementation-coupled or tautological, not tracer bullets.

**If you need to test past the interface, the interface is the design problem.** Test through the
public caller; the seam rules (when a port is earned, the humble object) are in
`test-admission.md` → *Oracle and seam*.

**Structural ≠ behavioural.** Schema, sentinel, parser and shipped-copy tests are allowed, but
never count as the slice's behavioural TEST unless the structure IS the caller-visible contract.
For doubtful admission, read [test-admission.md](test-admission.md): six real weak
patterns, their behavioural replacements and the executable frozen-test grader's limits.

## One vertical cycle

1. **Admit the next TEST LIST item.** Name one public interface, one caller-visible
   result, the production mutation that should make the test fail, and the authoritative relevant
   suite command from the repo contract. If no narrower command is authoritative, use the full suite.
2. **Write one tracer bullet — read [writing-tests.md](writing-tests.md) before every
   test body.** Four rules hold on every test: **name the break** (the production change that must
   make it fail — a bug, not a decision); **derive the oracle without the code under test** (a
   literal, a worked example, or real data checked by hand — never the implementation or its
   helpers); **mock only external or slow boundaries**, owned code stays real; **never assert on
   the mock**, assert what the real code produced. Exercise real code through the admitted seam.
   **Two kinds of change invert what the test must be, and getting this wrong produces a clean
   chain around a defect**: a guard's test is the **bypass**, a recovery's test is the **disaster**.
   Read [red-proof.md](red-proof.md) for these branches and runner failures.
3. **Record RED and read it.** Run the exact node through `red_check.py record`. It must fail because
   the behaviour is missing. A pass means existing behaviour or a wrong test; an import, fixture,
   credential, network, or setup error is invalid. Missing modules/scripts, ImportError, empty
   output and placeholders are staged REDs unless absence itself is the caller-visible defect.
   For new code create the final public skeleton so RED reaches the behavioural assertion.
4. **Implement the minimum.** Add only what this test requires. No later criteria, speculative
   branches, refactors, or nearby cleanup.
5. **Record targeted GREEN, then break it.** Same node, command, test file, and `rosso_log`;
   `red_check.py verify` must exit 0. Then `red_check.py break` applies the BREAK of step 1 (one
   exact text, present once, in one production file, never test code) in a throwaway copy. Red
   counts only when pytest itself shows the named test failing on a check raised in test code; a
   crash, an assert in production code, a skipped test or a non-pytest runner is inconclusive (run
   unittest files through pytest). Still green = the test does not guard that code: rewrite the
   test, never the break; every green break stays printed by `verify --break`.
6. **Record the regression suite.** Run the command fixed in step 1 through `red_check.py suite`;
   it must exit 0 with no new errors or warnings. Then verify the complete receipt with the exact
   `--suite-cmd`. A regression is fixed in production code, not by weakening an existing test.
7. **Refactor after GREEN, then close.** Keep all tests green. Report the receipt and regression command;
   every production edit after step 5 reruns targeted GREEN, the suite receipt, and final `verify`.
   Only then may the next TEST LIST item start. The three laws: no production code without
   a failing test; no more test code than needed to fail; no more production code than makes it pass.
   Repeat one test at a time, never a bulk RED phase followed by a bulk implementation phase.

```bash
python3 scripts/red_check.py record --test <node-id> --cmd "<one-test-command>" --out <rosso-log>
# minimum production change
python3 scripts/red_check.py record --test <same-node-id> --cmd "<same-command>" --out <same-log>
python3 scripts/red_check.py verify --log <same-log> --test <same-node-id>
python3 scripts/red_check.py break --test <same-node-id> --cmd "<same-command>" --out <same-log> \
  --file <production-file> --old "<exact text>" --new "<broken text>"
python3 scripts/red_check.py suite --test <same-node-id> \
  --cmd "<repo-authoritative-regression-command>" --out <same-log>
python3 scripts/red_check.py verify --log <same-log> --test <same-node-id> --break \
  --suite-cmd "<repo-authoritative-regression-command>"
```

Completion is mechanical: final `verify --break --suite-cmd` exits 0 only after the
unchanged-test RED→GREEN, a red break after that GREEN on the same test hash, and a later matching
suite GREEN. The break copy links the ignored `venv`, `.venv` and `node_modules` folders; a command
that needs any other ignored folder cannot start there and is reported inconclusive. `tdd-dev` never deploys; it opens the handoff gate.

## Output contract

Before writing the test, state exactly:

```text
CONSUMER: <caller that observes the promise>
SEAM: <public command or interface>
BEHAVIOUR: <one observable result>
ORACLE: <contract example or independently checked data>
REAL PATH: <entry point -> production -> observed effect>
REFACTOR INVARIANT: <private change this test must survive>
BREAK: <production file> · "<exact text>" → "<broken text>" (applied by `red_check.py break`)
TEST: <one node id>
EXPECTED RED: <missing behaviour named by the failure>
SUITE: <repo-authoritative relevant regression command>
```

Close the slice with:

```text
PROOF: <rosso-log> · unchanged test hash · break red
REGRESSION: <same log> · suite command · final verify exit 0
HANDOFF: review/deploy gate open
```

## Gotchas

- Hash-bound RED proves history, not test value → admission first, refactor and behavioural mutants next.
- Existing tests pin internals → match names/layout, not their defective assertions; say why.
- Green break → rewrite the test, not the declared break; keep every green break in the receipt.

| Excuse | Reality |
|---|---|
| “The targeted test is green; ship.” | It proves the new behaviour, not absence of collateral damage. Run the authoritative suite. |
| “The code already works; add the test now.” | New unproven work leaves the diff. An existing fix uses isolated mutation to recover RED. |
| “Write all acceptance tests first; it is faster.” | Horizontal tests freeze an imagined design. One tracer test teaches the next slice. |
| “RED was recorded, so the test is good.” | A RED proves the test failed once, not that it fails when the code it guards breaks. `red_check.py break` decides; a mirror stays green there. |
| “Any non-zero exit is RED.” | Setup and environment failures prove the harness is broken, not the behaviour missing. |
| “The full suite is slow, so pick a smaller command.” | Use a narrower command only when the repo contract declares it authoritative. |
| “He said to keep the style of the tests that are there.” | Style is names, layout and fixtures. Mock-call assertions and strings copied from another module are a defect the old tests carry, not a convention to extend. |
| “Clean this nearby code while GREEN.” | Refactor after proof, then rerun targeted GREEN, receipt verification, and regression. |

## When NOT to use it

- Load or performance thresholds.
- Production health, telemetry, and alerting probes owned by the observability workflow.
- Test-only cleanup with no product behaviour change.
- Throwaway prototypes, generated code, or configuration-only edits.
- Third-party defects that cannot be reproduced in our code.

## Selfcheck

```bash
python3 skills-suite/tdd-dev/scripts/red_signatures.py --selfcheck
python3 skills-suite/tdd-dev/scripts/red_check.py --selfcheck
python3 -m pytest skills-suite/tdd-dev/tests -q
python3 skills-suite/tdd-dev/scripts/test_value_grade.py --check-fixtures
```

Verification: [ ] every TEST LIST item resolved; [ ] admission justified; [ ] unchanged-hash
RED→GREEN; [ ] break caught; [ ] later authoritative suite GREEN; [ ] private refactor stays GREEN.
The fixture outcome check calibrates the grader, not agent-level skill improvement; the latter
requires the coordinator's held-out baseline comparison.
