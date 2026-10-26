# Run transcript — tdd-dev 2.7.0 (this change), 2026-10-25

Agent: fresh context, a fast model, read-only dry run. Same brief as `baseline.md`: the skill at
version 2.7.0 (SKILL.md and its `references/`), the repository in `fixture/` and the five
requests in `fixture/requests.md`. The reply below is verbatim.

---

## Request 1

I would refuse this test aloud. `config.yml has max_retries: 5` only copies a setting into a second place, and editing the shipped file would turn it red without any bug. I would write the behaviour that depends on the setting instead.

```text
CONSUMER: any caller of call_with_retry
SEAM: app.retry.call_with_retry(fn, settings)
BEHAVIOUR: with max_retries=2 a failing fn is attempted 3 times, then its last exception is re-raised
ORACLE: contract in the docstring, hand-counted literal 3
REAL PATH: test -> call_with_retry -> fn raises -> observed attempt count and exception
REFACTOR INVARIANT: loop shape, variable names, how last is kept
BREAK: app/retry.py · "settings[\"max_retries\"] + 1" → "settings[\"max_retries\"]"
TEST: tests/test_retry.py::test_failing_call_is_attempted_max_retries_plus_one_times_then_raises
EXPECTED RED: the code already works, so no RED by absence. I recover RED with the isolated break, and the receipt records that.
SUITE: python3 -m pytest tests -q
```

```python
import pytest
from app.retry import call_with_retry

def test_failing_call_is_attempted_max_retries_plus_one_times_then_raises():
    calls = []
    def always_fails():
        calls.append(1)
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        call_with_retry(always_fails, {"max_retries": 2})

    assert len(calls) == 3
```

The settings are handed in, so `config.yml` is never read. Whether the shipped file is wired in is a `real-testing` or integration check.

## Request 2

I would refuse both halves. `GUIDE.md` containing "RED" is a prose-text assertion. A function named `parse_quote` existing is a name/structure assertion. Neither runs anything. I would write the behaviour of `parse_quote`, with a table of literal oracles.

```text
CONSUMER: any caller that turns a quote string into money
SEAM: app.sessions.parse_quote(text)
BEHAVIOUR: "<decimal> <CUR>" is parsed into (integer minor units, currency)
ORACLE: hand-computed literals (12.50 -> 1250, 0.05 -> 5)
REAL PATH: test -> parse_quote -> returned tuple
REFACTOR INVARIANT: how the split and rounding are written
BREAK: app/sessions.py · "* 100" → "* 10"
TEST: tests/test_sessions.py::test_quote_text_parses_to_minor_units_and_currency
EXPECTED RED: the code already works, so I recover RED with the break.
SUITE: python3 -m pytest tests -q
```

```python
import pytest
from app.sessions import parse_quote

@pytest.mark.parametrize("text, expected", [
    ("12.50 EUR", (1250, "EUR")),
    ("0.05 USD", (5, "USD")),
])
def test_quote_text_parses_to_minor_units_and_currency(text, expected):
    assert parse_quote(text) == expected
```

I would write nothing for `GUIDE.md`.

## Request 3

I would admit this one, with one change. `is_expired` reads the real clock, and the skill says time is passed in at the seam (`is_expired(session, now)`). So I would make a production change first, to make the test possible.

```python
def is_expired(session, now=None):
    now = now or datetime.now()
    return now - session["created_at"] > TTL
```

The default keeps existing callers working.

```text
CONSUMER: session handling that rejects stale sessions
SEAM: app.sessions.is_expired(session, now)
BEHAVIOUR: a session older than 30 minutes is expired; one at or under 30 minutes is not
ORACLE: contract (TTL 30 min, strictly greater), literal offsets 0, 30 and 31 minutes
REAL PATH: test -> is_expired -> bool
REFACTOR INVARIANT: how the timedelta is computed or where TTL lives
BREAK: app/sessions.py · "> TTL" → ">= TTL"
TEST: tests/test_sessions.py::test_session_is_expired_only_after_thirty_minutes
EXPECTED RED: the first run is a TypeError on the unknown `now` argument. That is staged, not a valid RED. So I first add `now=None` ignoring its value, and the 30-minute case then fails on the real clock (True instead of False). That is a behavioural RED.
SUITE: python3 -m pytest tests -q
```

```python
from datetime import datetime, timedelta
import pytest
from app.sessions import is_expired

NOW = datetime(2026, 1, 1, 12, 0, 0)

@pytest.mark.parametrize("age_minutes, expected", [(0, False), (30, False), (31, True)])
def test_session_is_expired_only_after_thirty_minutes(age_minutes, expected):
    session = {"created_at": NOW - timedelta(minutes=age_minutes)}
    assert is_expired(session, NOW) is expected
```

I added the 30-minute boundary to your 31-minute and just-created cases. The `>= TTL` break needs it to go red.

## Request 4

I would not write this. Per-function unit tests do not catch a regression of the whole, because each one sets its own preconditions and the parts never run together. I would say so aloud and do two things.

1. The production break (retry, config and session expiry interacting) is caught by an integration test or `real-testing`. That is the "whole flow" path, so it is a separate item, not a pile of unit tests.
2. Unit tests come one slice at a time, each admitted with its declaration. The test list is:
   - `call_with_retry`: the retry count, re-raise of the last error, and a success on the Nth attempt.
   - `parse_quote`: minor units, plus the invalid-input behaviour the contract names.
   - `is_expired`: the boundary at 0, 30 and 31 minutes.
   - `load_settings`: it returns the mapping from a path the test writes in `tmp_path`.

   The first is the Request 1 test. I would not bulk-write RED tests for the rest.

## Request 5

I would refuse the bundling. One test has one behaviour, and each extra assertion is excluded for a specific reason:

- `config.yml loads` is a configuration assertion.
- `len == 2` is already implied by `== (1250, "EUR")`.
- `is_expired` of a fresh session is a different behaviour with its own test, which is Request 3.

I would write the Request 2 test with the single row `("12.50 EUR", (1250, "EUR"))`, with that declaration.
