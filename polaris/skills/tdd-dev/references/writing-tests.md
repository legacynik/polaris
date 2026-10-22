---
title: tdd-dev — writing tests that catch the break
description: How to write the body of a test, read before writing every test - the break it names, the oracle, the level, the doubles, the inputs, determinism, the boundaries that need special handling, and the mutation check that ends it. Admission (which test to write) is test-admission.md; RED semantics are red-proof.md.
status: active
---

# Writing tests

A test exists to catch one specific break. Two rules govern everything below: **every test names
the break it catches**, and **every test exercises the real thing**. A test written first and
watched failing against real code has already proven it can fail; it earns a double only when the
real dependency proves slow or external.

Which test to write next, and through which seam, is decided in `test-admission.md`. This file is
how to write its body.

## 1. Name the break before the body

Before writing the body, answer: **what production change should make this test fail — and is
that change a bug or a decision?** A test earns its place by catching a wrong branch, a missing
side effect, a wrong argument, a boundary case or a broken contract. That answer is the `BREAK`
line of the output contract, and `red_check.py break` applies it.

- **No change detectors.** If only intentional decisions can fail the test — a constant's value,
  exact message wording, private structure — it fires on redesign and sleeps through bugs. Test
  the behaviour that depends on the decision: not `MAX_RETRIES == 5` but "a failing call is
  retried 5 times and the 6th attempt never happens".
- **Behaviour, not text.** Asserting that a script, config or document contains a line proves
  only that the source is the source. Run the artifact against controlled input and assert its
  output, side effect or exit code.
- **Your code, not the framework.** Test the contract your code makes at its boundary — the route
  it registers, the query it emits, the payload it produces. A router calling a registered handler
  is the framework's test. Constructors, getters and trivial forwarding earn a test only when they
  validate, normalise, default, derive or cause a side effect; otherwise assert the first
  caller-visible result that depends on them.

```text
Cannot name a break              -> redesign around an observable behaviour
"The source text changed"        -> run the artifact and assert its effects
Only intentional decisions break -> change detector; test what depends on the decision
```

## 2. Derive the oracle without the code under test

The expected value comes from the contract, a worked example, a literal you computed by hand, or
real data whose result was checked independently. An expectation computed by the code under test
— or by its helpers, or by re-running its algorithm — passes whatever the code does.

```python
# mirror: the expected value is recomputed the way the code computes it
def test_total():
    items = [{"price": 10}, {"price": 5}]
    assert total(items) == sum(i["price"] for i in items)

# oracle: an independent literal
def test_total_sums_line_items():
    assert total([{"price": 10}, {"price": 5}]) == 15
```

```typescript
// mirror: the same builder computes both sides
expect(buildSearchQuery({ tag: "urgent" })).toBe(buildSearchQuery({ tag: "urgent" }));
// oracle: hand-derived literal
expect(buildSearchQuery({ tag: "urgent" })).toBe('tag:"urgent"');
```

**Mirror tests** repeat the code's branches back to it: same branches, same order, same words.
They pass by construction, and the day someone adds a branch with the wrong result they stay
green. Recognise one by its symptom: changing the implementation without changing the behaviour
breaks it.

```python
def classify(text):
    if "urgent" in text: return "P0"
    if "important" in text: return "P1"
    return "P2"

# mirror — reads the code aloud
def test_classify():
    assert classify("urgent") == "P0"
    assert classify("important") == "P1"

# contract — includes what the code does not name
def test_classify_from_real_tickets():
    assert classify("customer is down, urgent") == "P0"
    assert classify("blocks the release") == "P0"    # no keyword at all
    assert classify("whenever you have time") == "P2"
```

The second line is the one that matters: it uses a word the list does not hold.

**Word lists, regexes, matchers: test the misses.** Anything driven by a list or a pattern needs
cases the list does not cover, and must fail when coverage is short. A test of only the words
already in the list proves the list contains them.

```python
@pytest.mark.parametrize("q", ["how much is it", "what does it cost me", "what's the figure"])
def test_price_intent_without_the_keyword(q):
    assert intent(q) == "price"
```

That test is red today, and correctly so: it says keyword matching does not survive real
language.

**Real fixtures over invented ones.** Hand-written fixtures resemble the implementation because
they are written after reading it. Take at least a few cases from a real source: past bug records
of the same area, the error logs or production traces the path goes through, the project's eval
corpus, the inputs that originated the bug. Real input carries what nobody invents — empty
fields, unicode, odd ordering, values at the limit — which is exactly where defects live.

## 3. Choose the level by the seam

The admitted seam fixes the level; prefer the smallest that still reaches the real behaviour.

| Size | Resources | Speed | Typical subject |
|---|---|---|---|
| Small | one process, no I/O, no network, no database | milliseconds | pure logic, transforms, parsers |
| Medium | several processes, localhost only, test database | seconds | API handler with a test DB, component with its children |
| Large | external services, several machines | minutes | end-to-end user flow, staging integration |

Pure logic with no side effect → small. Crosses a boundary you own (API, database, filesystem) →
medium, with the real thing on localhost. A critical user flow that must work end to end → large,
and only for the critical paths. Most of a healthy suite is small; a behaviour that only a large
test can reach is often a design finding (`test-admission.md` → *Oracle and seam*).

## 4. Doubles: the real thing first

Preference order: **real implementation > fake** (in-memory working version) **> stub** (canned
answers) **> mock** (records calls). Each step down buys speed or control and costs confidence.

- **Mock only external or slow boundaries**: third-party APIs, payment and email, the clock and
  randomness, sometimes the filesystem. Keep owned code real — your modules, classes and internal
  collaborators. If mock setup outgrows the test, or the test breaks when the mock changes,
  switch to real components.
- **The mock earns no assertions.** An assertion on a mock passes when the mock is present and
  fails when it is absent; it says nothing about your code. Assert the real component's behaviour.

  ```typescript
  expect(screen.getByRole("navigation")).toBeInTheDocument();   // real behaviour
  expect(screen.getByTestId("sidebar-mock")).toBeInTheDocument(); // tests the mock
  ```

- **Mock the level below the side effects the test depends on.** Before replacing a method, list
  what it really does; replace only the slow or external operation and keep what the test reads.

  ```python
  # wrong: the mock swallows the cache write that duplicate detection reads
  monkeypatch.setattr(catalog, "discover_and_cache_tools", lambda: None)
  # right: replace only the slow server start; the cache write stays real
  monkeypatch.setattr(server_manager, "start", fake_start)
  ```

- **Mirror the full real structure.** A canned response carries every field the real one does,
  not only the ones this test reads; a partial shape passes while the integration breaks on the
  field you left out. Capture one real response and trim nothing that downstream code may read.
- **Make doubles specific.** When arguments, call counts or order are part of the contract (what
  the external recipient actually receives), assert them on the boundary double. Give success,
  error and malformed responses their own fixture, so the wrong branch cannot satisfy the test.
- **State, not interactions.** Inside your own code assert the outcome, not which methods ran.

  ```typescript
  // state: what the caller observes
  expect(tasks.map(t => t.id)).toEqual(["t3", "t2", "t1"]);
  // interaction: how it was done internally — breaks on any refactor
  expect(db.query).toHaveBeenCalledWith(expect.stringContaining("ORDER BY created_at DESC"));
  ```

- **Design the boundary for substitution.** Pass external clients in (dependency injection)
  rather than building them inside, and expose one function per external operation (an SDK-style
  interface: `get_user(id)`, `create_order(data)`) rather than one generic `fetch(endpoint,
  options)` whose double needs conditional logic.

  ```python
  def charge(order, payments):          # easy: the client is a parameter
      return payments.charge(order.total)

  def charge(order):                    # hard: the client is built inside
      return StripeClient(os.environ["KEY"]).charge(order.total)
  ```

- **Production classes carry production methods only.** Cleanup only tests need (`reset()`,
  `destroy()`) lives in test utilities, never on the production class.

When a port is earned at all, and how to split logic away from a hard-to-test framework entry
point, is design: `test-admission.md` → *Oracle and seam*.

## 5. Shape: one story per test

- **Arrange, Act, Assert**, in that order, visibly separated.
- **One concept per test.** A test named "validates titles" with three unrelated asserts hides
  which one failed; split it into "rejects empty titles", "trims whitespace", "enforces max length".
  Several asserts on one result of one action are one concept.
- **DAMP over DRY.** Each test reads as a complete specification without tracing shared helpers.
  Repeat the input shape when that keeps the test self-explanatory; extract a helper only for
  mechanics (building a valid object), never for the values the assertion depends on.
- **Names read as a spec**: `[unit] [expected behaviour] [condition]` —
  `complete_task sets status and records the timestamp`, `throws NotFoundError for an unknown
  id`. Never `works`, `handles errors`, `test 3`.

```python
def test_overdue_when_the_deadline_has_passed():
    task = Task(title="report", deadline=date(2025, 1, 1))       # arrange
    result = check_overdue(task, today=date(2025, 1, 2))          # act
    assert result.is_overdue is True                              # assert
```

## 6. Choose the inputs

- **Equivalence partitions.** Group inputs the contract treats the same and take one
  representative per group: valid, each invalid kind, empty, missing.
- **Boundary values.** On every limit test just below, at, and just above: `0`, `1`, `max`,
  `max+1`, empty string, one element, the first and last day of a month, midnight.
- **Tables with literal expectations.** Parametrize over cases; every expected value is a literal
  in the table, never computed in the loop.

  ```python
  @pytest.mark.parametrize("raw, cents", [("1.005", 101), ("0", 0), ("-0.004", 0), ("1e3", 100000)])
  def test_round_price_half_up(raw, cents):
      assert round_price(raw) == cents
  ```

  ```typescript
  test.each([["1.005", 101], ["0", 0], ["-0.004", 0]])("round %s -> %d", (raw, cents) => {
    expect(roundPrice(raw)).toBe(cents);
  });
  ```

- **Property-based tests for parsers, round-trips and invariants.** When the rule holds for every
  input (`parse(format(x)) == x`, sorting keeps every element, a total never goes negative), state
  the property and let the tool generate inputs (Hypothesis in Python, fast-check in TypeScript).
  Keep one example-based test beside it so the intent is readable.

  ```python
  @given(st.text())
  def test_escape_round_trips(s):
      assert unescape(escape(s)) == s
  ```

## 7. Determinism

A test that sometimes fails is worse than none: people learn to rerun it.

- **Clock**: inject the time or freeze it; never compare against the real `now()`.
- **Randomness**: inject the generator or fix the seed, and print the seed on failure.
- **Timezone and locale**: set them in the test (`TZ=UTC`), never inherit the machine's.
- **Ordering**: do not assert the order of sets, of maps whose iteration order the language does
  not guarantee, or of query results without `ORDER BY`; sort first, or compare as sets.
- **Network**: none in small and medium tests; an external call is a boundary double.
- **Concurrency and async**: await every promise; wait for a condition by polling with a timeout,
  never `sleep(n)`.

  ```python
  def wait_until(predicate, timeout=5.0, step=0.05):
      deadline = time.monotonic() + timeout
      while time.monotonic() < deadline:
          if predicate():
              return
          time.sleep(step)
      raise AssertionError(f"condition not met within {timeout}s")
  ```

## 8. Boundaries that need their own handling

- **Databases: real, disposable.** Run against the same engine as production — each test in a
  transaction rolled back at the end, or a throwaway database or schema per run. Never mock the
  ORM or the query builder: the SQL is the behaviour. Seed each test's own rows.
- **HTTP and external services: fakes kept honest.** Replace the service with a fake at the
  network boundary (a local stub server, a recorded response) built from a real captured
  response. Keep it honest with a contract test that runs the same assertions against the real
  service or its sandbox on a schedule; a fake nobody re-checks drifts from reality silently.
- **Errors: assert precisely.** Assert the error type and the part of the message or code the
  caller relies on, not just "something raised". An unexpected exception must fail the test, not
  satisfy a broad `except`.

  ```python
  with pytest.raises(ValidationError, match="title is required"):
      create_task(title="")
  ```

  ```typescript
  await expect(createTask({ title: "" })).rejects.toThrow(ValidationError);
  ```

- **UI: query as the user sees.** Find elements by role, label and visible text — what a user and
  a screen reader use — not by test ids, CSS classes or DOM structure.

  ```typescript
  await user.type(screen.getByRole("textbox", { name: /title/i }), "New task");
  await user.click(screen.getByRole("button", { name: /create/i }));
  expect(await screen.findByText(/title is required/i)).toBeInTheDocument();
  ```

- **Snapshots: small and reviewed.** Snapshot a small, stable output a person reads in review;
  never a whole page or a large object nobody reads. Updating a snapshot is a code change: read
  the diff before accepting it.
- **Legacy code: characterise before you touch it.** With no tests, first pin what the code does
  today on real inputs (characterisation tests, the current output as the literal), then change
  it. A characterisation test records behaviour, not correctness: mark the cases you believe
  wrong, and turn each into a proper test when you fix it.
- **Isolation.** Every test builds and removes its own state; none depends on another having run
  first, and the suite passes in any order. Write files only under a temporary directory the test
  creates; never into the repository or the user's home.

## 9. Before finishing: the mutation check

Mentally mutate the production code; at least one test must fail for each realistic mutation:

- a wrong constant or argument;
- the wrong branch taken;
- a missing state change or side effect;
- an empty or default return;
- missing validation for zero, empty, null, unauthorised or malformed input.

Pick the most realistic of these as the `BREAK` and let `red_check.py break` apply it. A mutation
nothing catches marks the behaviour as unprotected or the test as tautological: rewrite the test,
never the break.

## Warning signs

- Setup and assertion share the same object, so equality is guaranteed.
- The expected value is computed by a loop, builder or helper instead of written down.
- The test can fail only through a crash, a missing selector or an import error.
- It fails on every intentional change and never on an accidental one.
- It greps source text, or asserts a removed symbol stays removed.
- It would still pass if only the framework remained.
- It exists for coverage and checks no outcome or side effect.
- An assertion targets a mock or a `*-mock` test id, or fails if the mock is removed.
- A method on a production class is called only from tests.
- Mock setup is more than half the test, or nobody can say why the mock is needed.
- It sleeps for a fixed time, reads the real clock, or needs the network.
- It passes alone and fails in the suite, or the reverse.
