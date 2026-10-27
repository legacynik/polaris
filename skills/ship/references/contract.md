# ship — the repository contract, staging, scripts and gotchas

Read by `ship` once per run, before step 1.

## The contract

Read the repository's contract once (`_polaris/config.yml`, else `config.yml`): `ship:` (`verify`,
workflows, environments, `rollback`, `owner_label`, `checks_not_gating`, `inert_paths`,
`signing_env`, optional `version_file`, `changelog`, `flags`, `slo`, extra review) and `real_test:`
(`deploy_staging_workflow`, `deploy_prod_workflow`, `health`, `smoke`, `rollback`). Never invent a
command the contract does not name; a missing field is written as `mode: reduced` plus the field,
never skipped in silence. Every script runs from the repository root as
`python3 <skill-dir>/scripts/<script>.py`, so `gh` and `git` read that repository.

The binding control is `babysit`: it reads the owner's label bound to the head SHA from the PR
(server state); branch protection is the server-side wall. The optional hook (`references/hook.md`)
is a tripwire, not a security boundary.

## Where this goes

The PR, its body (through `pr`) and the label (through `babysit`). The validation receipt is
`real-testing`'s and lands where the repository's `outputs.validation` says. Never write a
document of your own beside them.

## Staging in full (step 7)

1. **Hold staging.** Shared: the served SHA (the contract's `health`) names who holds it; ask that lane
   and queue, never deploy over a running test. Deploy the branch through
   `real_test.deploy_staging_workflow`. *Done when staging serves HEAD.*
2. **Sign.** `real-testing` on staging, complete, fresh breaker: the receipt goes on the PR, its
   `ambiente:` line naming the signing environment. Give staging back to what it served before and
   check its SHA. A later push that changes only the contract's `inert_paths` keeps the receipt; a
   push that changes code needs a new signature, the one case for a second staging round.
   *Done when the receipt on the PR names the current head.*

## Gotchas

- A finding a reviewer cannot back with a concrete scenario is noise: drop it, keep the reason.
- A second staging round without a code change after signing means the local real-test (step 3) was skipped.
- The hook never fails open on what it reads: an internal error exits 2, and the emergency bypass
  (`SHIP_BYPASS_GATE=1`) is logged. What it does not read (wrappers, `gh api`) it does not judge.
- Size decides staging: Tiny and Bug never hold it; Medium and Large hold it once.
- Every script answers `--selfcheck`; `references/bypass-test.md` must fail if a gate is skipped.

## Quick reference

```
redact_scan.py    --paths F... | --stdin              exit 1 = BLOCKED
version_bump.py   --root .                             exit 1 = DRIFT_*, 2 = NO_VERSION_FILE
changelog_edit.py --file F --bullet "..." [--anchor]    exit 2 = NO_ANCHOR/NO_FILE
realtest_gate.py  --root .                             exit 1 = no fresh verdict on this tree
merge_gate.py     decide --pr-json F|- / execute --pr N
canary_check.py   baseline|check --urls U... --state F / drift --local-sha S --deployed-sha S
canary_check.py   verdict --baseline B.json --now N.json   0 ADVANCE · 1 ROLLBACK proposed · 3 HOLD
```
