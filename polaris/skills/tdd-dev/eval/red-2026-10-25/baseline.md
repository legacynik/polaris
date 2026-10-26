# Run transcript — tdd-dev 2.6.0 (baseline), 2026-10-25

Agent: fresh context, a fast model, read-only dry run. Given the skill at version 2.6.0 (SKILL.md and
its `references/`), the repository in `fixture/` and the five requests in `fixture/requests.md`.
Asked for, per request, the declaration and the exact test it would write, or its refusal and the
replacement, plus any production change. The reply below is verbatim.

---

## Request 1

I would not write the test as asked. It only checks that `config.yml` contains `5`, so it is a change detector that fails on a legitimate config change and never on a bug. This is what I'd write instead: the behaviour that depends on the setting.

```
CONSUMER: caller of call_with_retry
SEAM: app.retry.load_settings + app.retry.call_with_retry (config.yml is real, not mocked)
BEHAVIOUR: a call that always fails is attempted 6 times (1 + 5 retries) and then the last exception is re-raised
ORACLE: config contract (max_retries 5), literal 6
REAL PATH: load_settings("config.yml") -> call_with_retry -> fn called N times -> exception raised
REFACTOR INVARIANT: rewriting the loop (while/for) must stay green
BREAK: app/retry.py · "settings["max_retries"] + 1" → "settings["max_retries"]"
TEST: tests/test_retry.py::test_failing_call_is_attempted_once_plus_five_retries_then_raises
EXPECTED RED: none naturally, because the behaviour already exists. RED is recovered by applying the BREAK in an isolated mutation run (iron law, "a fix already exists"). It must show 5 attempts instead of 6.
SUITE: python3 -m pytest tests -q
```

```python
from pathlib import Path
import pytest
from app.retry import load_settings, call_with_retry

CONFIG = Path(__file__).resolve().parent.parent / "config.yml"

def test_failing_call_is_attempted_once_plus_five_retries_then_raises():
    calls = []
    def always_down():
        calls.append(1)
        raise RuntimeError("down")

    with pytest.raises(RuntimeError, match="down"):
        call_with_retry(always_down, load_settings(CONFIG))

    assert len(calls) == 6
```

No production change is needed.

## Request 2

I would not write either test. Both grep source or prose: "GUIDE.md contains RED" and "sessions.py has a function named parse_quote". Neither runs anything, and a rename or reword would break them while real bugs pass. The function does exist, so the useful test runs it.

```
CONSUMER: quote-handling caller
SEAM: app.sessions.parse_quote
BEHAVIOUR: parses "<amount> <CUR>" into (amount in cents, currency)
ORACLE: hand-computed literals
REAL PATH: parse_quote(text) -> split -> round(float*100) -> tuple
REFACTOR INVARIANT: replacing float math with Decimal must stay green
BREAK: app/sessions.py · "* 100" → "* 10"
TEST: tests/test_sessions.py::test_parse_quote_returns_cents_and_currency
EXPECTED RED: none naturally, because the behaviour exists. It is recovered via the isolated BREAK, which gives 125 instead of 1250.
SUITE: python3 -m pytest tests -q
```

```python
import pytest
from app.sessions import parse_quote

@pytest.mark.parametrize("text, expected", [
    ("12.50 EUR", (1250, "EUR")),
    ("0.29 EUR", (29, "EUR")),
    ("100 USD", (10000, "USD")),
])
def test_parse_quote_returns_cents_and_currency(text, expected):
    assert parse_quote(text) == expected
```

## Request 3

This is a good test and I would write it. One change from the request: I would not use the real `datetime.now()`. The skill says to freeze the clock, and the clock is an allowed double. I would patch `app.sessions.datetime` with a fixed subclass, so no production change is needed. I would also add the exact-30-minute boundary, because the code uses a strict `>`.

```
CONSUMER: session-handling caller
SEAM: app.sessions.is_expired
BEHAVIOUR: a session older than the 30-minute TTL is expired; one exactly at the TTL or newer is not
ORACLE: contract TTL = 30 minutes, literal table
REAL PATH: is_expired(session) -> datetime.now() (frozen) - created_at > TTL
REFACTOR INVARIANT: renaming TTL or restructuring the comparison must stay green
BREAK: app/sessions.py · "> TTL" → ">= TTL"
TEST: tests/test_sessions.py::test_session_expires_only_after_the_ttl
EXPECTED RED: none naturally, because the behaviour exists. It is recovered via the isolated BREAK (the exactly-30-minutes row fails).
SUITE: python3 -m pytest tests -q
```

```python
from datetime import datetime, timedelta
import pytest
import app.sessions as sessions

NOW = datetime(2026, 1, 1, 12, 0, 0)

class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW

@pytest.mark.parametrize("age_minutes, expired", [
    (31, True),
    (30, False),   # boundary: exactly at TTL is still valid
    (0, False),    # just created
])
def test_session_expires_only_after_the_ttl(monkeypatch, age_minutes, expired):
    monkeypatch.setattr(sessions, "datetime", FrozenDatetime)
    session = {"created_at": NOW - timedelta(minutes=age_minutes)}

    assert sessions.is_expired(session) is expired
```

## Request 4

I would not write "a unit test for every function" in bulk. That is a horizontal slice, which the skill forbids, and it would not prevent the incident. The failure was an interaction between retry, config and expiry. A per-function test of `load_settings` would also just restate the library.

What I would do:

- **Declare a TEST LIST first.** The skill requires a test list before any test. I would take it from the incident, not from the list of functions. I need the actual production failure (logs or a repro) so the first test can name a real break. That is the `bugfix` path.
- **List items so far.**
  1. Retry count honours the config (Request 1's test, already admitted).
  2. A session just past the TTL is rejected (Request 3).
  3. `parse_quote` returns cents (Request 2).
  4. A retry attempt that straddles the TTL: an expired session mid-retry is not reused. I'd add this only once the incident confirms it, because there is currently no function in `app/` that composes the three.
- **Write one test at a time, each with its own RED, break and suite receipt.** The first one is Request 1's test. No production change.

## Request 5

I would not combine these. The skill's rule is one concept per test, and the extra asserts are weak anyway:

- "config.yml loads" is a structural check, not behaviour.
- "result is a tuple of length 2" is already implied by `== (1250, "EUR")`.
- `is_expired` of a fresh session is a separate concept, covered by Request 3's `(0, False)` row.

I would write the single `parse_quote` test from Request 2. Its `"12.50 EUR"` row is exactly the requested assertion, and it keeps the same declaration. If a single assertion is wanted, this is the one:

```python
from app.sessions import parse_quote

def test_parse_quote_returns_cents_and_currency_for_12_50_eur():
    assert parse_quote("12.50 EUR") == (1250, "EUR")
```

The declaration is the same as Request 2, with `TEST: tests/test_sessions.py::test_parse_quote_returns_cents_and_currency_for_12_50_eur`.
