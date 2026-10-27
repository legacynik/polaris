---
name: tdd-dev
description: ◇ Polaris — Drive one behaviour change test-first — a hash-bound RED, the minimum fix, a break proving the test guards the code, then the repo's regression suite. Use when implementing a feature or behaviour change, fixing a reproducible bug through a regression test, proving an existing fix's test, or when a test was accepted without an observed RED. Requires python ≥ 3.9; pytest for the break step. Not for prototypes or configuration-only edits.
version: 2.7.4
user-invocable: true
status: active
job: drive one code change from an agreed public seam through proven RED, minimum implementation, GREEN receipt, and the repo-authoritative regression suite
when_not: load/performance thresholds · production observability probes · test-only cleanup · throwaway prototypes · generated code · configuration-only edits · third-party defects that cannot be reproduced in our code
io: consumes one acceptance criterion or reproducible defect, a test node id, its targeted command, the relevant suite command, and a rosso_log path → produces the minimum code change, hash-bound RED/GREEN receipt, regression result, and a review/deploy-ready handoff
lifecycle: the rosso_log and regression evidence are committed with the work item; the workflow that owns the change drains them when the item closes
invoked-by: [bugfix, implement-plan, human]
---

# tdd-dev

## How tests are written

- Test what the code does through its public seam (output, side effect, exit code), never a name,
  path, file text, wording, config value, private structure, timing or order, unless callers see it.
- One behaviour per test; assert only what proves it, nothing another test already asserts.
- Deterministic: no real clock, network, order or shared state; pass time, seeds and order in at
  the seam. Doubles only for external or slow boundaries, never asserted on.
- The oracle is derived without the code under test: the contract, a hand-computed literal.
- Name = subject, scenario, result: `checkout_with_empty_cart_is_refused`.
- Unit tests design the unit; a regression of the whole is caught by an integration test or
  `real-testing`, not by more unit tests.
- A test that cannot name the behavioural break it catches is not written.

## What it does

Certifies one behavioural test through the public seam from a valid RED, through the minimum
production change, to GREEN on the unchanged test hash, a red break, and the repo's regression
suite. **No production behaviour changes before one test has a recorded RED.**

## When

- A behaviour change (a tiny bead or a plan's build phase), one acceptance criterion at a time.
- A reproducible bug needs its regression test (`bugfix` phase ② calls this skill).
- A fix exists, or a green test was accepted, and nobody has seen its test fail.

## Steps

1. **Test list, then admission.** List the behaviours (happy path, errors, boundaries); for the
   next, declare CONSUMER, SEAM, BEHAVIOUR, ORACLE, REAL PATH, REFACTOR INVARIANT, BREAK and admit
   it only if it obeys *How tests are written* (`references/test-admission.md`). A requested test
   of a name, path, text, wording or config value is refused aloud and replaced by the behavioural
   one, the unit fed its own inputs, settings included. Fix the suite command now.
2. **Write one test** (`references/writing-tests.md`). A guard's test is the bypass, a recovery's
   test is the disaster (`references/red-proof.md`).
3. **Record RED, read it, implement the minimum, then prove it** — same node, command and log:
   ```bash
   python3 scripts/red_check.py record --test <node> --cmd "<one-test-cmd>" --out <log>
   # minimum production change, then the same record again for GREEN
   python3 scripts/red_check.py verify --log <log> --test <node>
   python3 scripts/red_check.py break --test <node> --cmd "<one-test-cmd>" --out <log> \
     --file <production-file> --old "<exact text>" --new "<broken text>"
   python3 scripts/red_check.py suite --test <node> --cmd "<suite-cmd>" --out <log>
   python3 scripts/red_check.py verify --log <log> --test <node> --break --suite-cmd "<suite-cmd>"
   ```
   A setup, import or environment failure is not RED. A green break means rewrite the test, never
   the break. A regression is fixed in production code, never by weakening a test.
4. **Refactor after GREEN**, rerun the step-3 receipt, then the next item; never a bulk RED phase
   (`references/cycle.md`).

## Output

The declaration (CONSUMER … SUITE) and the closing receipt `PROOF` · `REGRESSION` · `HANDOFF`
exactly as `references/cycle.md` → *Output contract* gives it; never deploys. **Next:** back to the caller (`implement-plan`, `bugfix`); alone, `ship`.

## Not for

- Load or performance thresholds; production probes; test-only cleanup; generated code.
- Throwaway prototypes (`prototype`), configuration-only edits, third-party defects not ours.
