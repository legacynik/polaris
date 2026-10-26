"""The body never disagrees with the flags on the contract's own fields.

Breaker round 2, 2026-10-09: `--field domain=made-up` (or `priority=p0`, `afk=yes`) next to
`--domain billing --priority p1 --afk no` rendered the override in the body with exit 0 while the
labels said `domain:billing`, `p1`, `afk:human`, and `made-up` was outside the repo's domain list.
An override that repeats the flag is the old double-entry workaround and still works; one that
differs is refused.
"""

from __future__ import annotations

from test_template_override_refused import builder


def test_an_override_that_contradicts_a_flag_is_refused_and_one_that_repeats_it_passes():
    cases = {("domain=made-up",): 2, ("priority=p0",): 2, ("afk=yes",): 2,
             ("domain=billing", "priority=p1", "afk=no"): 0}
    seen = {}
    for fields in cases:
        extra = [arg for f in fields for arg in ("--field", f)]
        seen[fields] = builder(*extra).returncode
    assert seen == cases
