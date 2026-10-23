# RED proof branches

Read from [the cycle](../SKILL.md) for guards, recovery, stochastic behaviour or runner errors.
The hash-bound RED/GREEN, production break and later suite receipt remain mandatory.

## Adversarial RED

An admission or authorization guard needs the cheapest **bypass**, not just a refusal on its
obvious input. Include optional model-written fields and unexamined keys. A permissive
`return True` mutant only gets caught by an assertion expecting REFUSAL; one caught bypass
does not prove that the other inputs are protected.

A recovery/retry/checkpoint needs the **disaster**: interrupt mid-batch and observe duplicated
or lost work, then build recovery. A clean run proves no resume.

Evidence, 2026-09-05: an authorization gate needed four rounds: tool without destination,
destination through optional model-written input, then frozen keys while an extra `bcc`
escaped. Every round had hash-bound RED, verify and mutation evidence; the tests confirmed
the guard instead of attacking it. This is why admission precedes mechanics.

## Existing fixes and stochastic behaviour

Use the owning workflow's isolated mutation runner for an existing fix (`bugfix` owns
`scripts/mutation.py`), not a generic stash. For stochastic behaviour wrap N runs and the
declared threshold in one deterministic PASS/FAIL command; load/performance is another workflow.

## Three runner outcomes

`record` writes RED or GREEN, or exits **2 with a cause and no row**. Missing cwd, syntax
errors, zero tests, collection/import errors and signal deaths belong to the harness.
Fourteen staged REDs once needed manual removal.

`red_signatures.py` owns anchored, runner-specific signatures against real captured fixtures.
A new runner needs a new signature and capture, not widened patterns: bare `FAILED` can come
from make, buildkit or git. `red_signatures --selfcheck` mutates each signature; `red_check
--selfcheck` measures shell forms, including `cd`, subshells, `pushd` and `cd -`.

`verify` proves RED exists, GREEN is latest and the file hash is unchanged. `--break` requires
a later caught production mutation; `--suite-cmd` requires a matching suite GREEN after it.
It does not judge semantic failure reasons: reading RED is still mandatory.

The break runner copies production, links ignored `.venv`, `venv` and `node_modules`, and
refuses inconclusive runs. Pytest must show the named test failing on a check raised in
test code, not an assert in production, a crash, skip, doctest or non-pytest runner.
