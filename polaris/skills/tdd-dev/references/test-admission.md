# Test admission

Read from [tdd-dev](../SKILL.md) when a seam or oracle is doubtful. These examples distil six
observed weak tests, not hypothetical style preferences. A receipt cannot rescue a bad oracle.

| Observed weak pattern | Why it fails admission | Behavioural replacement |
|---|---|---|
| Menu Markdown contains every verdict row | Pins human prose; never runs the command | Run the public command for each verdict and parse its machine-consumed record |
| Hand-written trace passes a grep evaluator | The fixture/stub authored its own success | Execute the real emission path, then independently check the record |
| Eval and skill text both contain `ASSUMED` | Two strings do not prove emitted fields | Invoke each public emission path; parse and validate the returned field |
| Source lacks `or True` | Implementation text, not guard behaviour | Send the cheapest invalid input through the public guard; assert refusal |
| Direct call to private `_thrashing` | A harmless rename breaks the test | Drive the public stage/CLI with break rows and observe admission/refusal |
| Generated argv contains a script path | Existence is not executed wiring | Run the public dry-run path and inspect the downstream contract |
| A file exists, a doc holds a word, a function has a name, a config value equals 5 | Pins a name, a path, text or a setting; fires on a rename, sleeps through a bug | Refuse it aloud (`SKILL.md` → *How tests are written*); run the unit with inputs the test supplies, settings included, and assert its output, side effect or exit code |

The fixture corpus under `eval/behaviour/` reproduces these patterns with neutral features.
Source/prose greps and argv inspection may remain diagnostic checks, never the behavioural TEST.
A schema/parser/sentinel/shipped-copy assertion qualifies only when that exact structure is
the caller's contract. A public serializer can legitimately be tested by parsing its result;
reading its Python source does not test serialization.

## Oracle and seam

How to write the oracle and the doubles is `writing-tests.md` (§2 and §4). What stays here is the
design side: the interface is the test surface, so a behaviour reachable only past it is a design
finding, not a reason for a deeper mock.

- **A port is earned by volatility.** Add one only for a dependency that genuinely churns (a vendor
  SDK, a framework whose major versions reshape its API). Use a stable dependency (standard-library
  types, settled formats) directly; one hypothetical second adapter earns nothing. The concrete
  wiring sits in one composition root, not in every module that needs an object built.
- **Humble object.** Logic testable only with a real server, database or framework entry point is
  split in two: the decisions move into a plain unit tested in isolation, and the thin remainder
  only talks to the hard-to-test thing, too thin to hold anything worth a test. That split is
  usually the boundary the design needed.

## Frozen-test outcome grader

```bash
python3 skills-suite/tdd-dev/scripts/test_value_grade.py <feature-dir> <candidate-test.py>
python3 skills-suite/tdd-dev/scripts/test_value_grade.py --check-fixtures
```

The feature directory contains `spec.md` (public contract only), `base/`, `solution/`,
`refactor/`, and at least two `mutants/<name>/`. Each is a complete runnable implementation.
The grader copies the candidate bytes unchanged into an isolated temporary copy of each variant,
runs `python3 -m pytest`, and reads pytest's reports, not console phrases.

VALUABLE requires a behavioural failure on base (a test assertion, or an exception the production
code raises on the new input; import errors, placeholders, unbound names and attributes missing from a
module are `staged_red`, decided on the exception object the probe records), a full pass on solution and private refactor,
an assertion failure on every public-behaviour mutant, and byte identity before/after every run.
WEAK reasons name the failed outcomes: `base_passed`, `staged_red`, `base_not_assertion`,
`solution_failed`, `refactor_failed`, `mutant_survived:<name>`, `mutant_not_assertion:<name>`,
or `test_changed`. Missing variants and runner failures fail closed.

The grader is not a static linter or semantic authority. It cannot infer public ownership from
names or detect a self-authored oracle that happens to track every mutant. Admission remains a
contract judgement; the independent refactor and multiple mutants falsify that judgement.
Equivalent mutants or an incorrect refactor invalidate calibration: validate them against the
public spec before trusting the verdict. Held-out fixtures are evaluator inputs, not examples
for an agent to copy. No claim of agent-level uplift follows from passing this corpus alone.
