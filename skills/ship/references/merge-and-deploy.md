# ship — the proposal, the merge and the deploy (Phase B)

Read by `ship` at step 10, after `babysit` reports READY. This file is also the repository's
deploy procedure where `config.yml` `ship.sop` points here. Every script runs from the
repository root as `python3 <skill-dir>/scripts/<script>.py`.

## The proposal — one screen, then stop

When `babysit` is READY, requery once (`merge_gate.py decide`) and stop with **one** message:

```text
<one plain line: exactly what the owner says yes to, e.g. "merge PR #N, deploy to staging, then production">

Evidence (each on head <sha>):
- CI: <green, required checks> · <link>
- Real-test: <verdict> · <environment> · <receipt link>
- Review: review tier <n> · <no blocking finding> · <link>
- Threads: none open, none escalated · Base: conflict-free, up to date
Needs attention: <DB migrations and their order · schema change · prod deploy order>, or "nothing"
Rollback plan: trigger <the window's ROLLBACK line, or a named failure> · steps <the contract's
  rollback:> · expected time <minutes, or UNKNOWN> · migration <reversible / not> · data it writes <...>
Pre-deploy: env vars and secrets the change needs present in <target env> <yes/no/UNKNOWN> ·
  migrations ready, order <...> · dependency audit <no critical/high / list / UNKNOWN> ·
  changelog <done / not declared>
Rollout: <feature flag or percentage, only if ship.flags declares a flag system; else "no flag
  system declared"> · error budget <only if ship.slo declares SLOs; else skipped>
```

Anything the evidence cannot show is `UNKNOWN`, never a pass. The audit uses the ecosystem's own
tool (`npm audit --audit-level=high`, `pip-audit`, `cargo audit`, `go vet` plus `govulncheck`).
*Done when the message is sent with every evidence line linked; nothing runs until the owner says
yes.* A changed head after the message voids it: back to `babysit`.

## Phase B, on the owner's yes

| # | Step | Command | Done when |
|---|---|---|---|
| 1 | Requery | `merge_gate.py decide --pr-json <(gh pr view N --json state,mergeable,mergeStateStatus,statusCheckRollup,updatedAt)` | READY; ALREADY_DONE skips to 3; BLOCKED_* stops and says why |
| 2 | Merge once | `merge_gate.py execute --pr N` | exit 0; a non-zero exit is requeried, never a second `gh pr merge`, never `gh pr merge --auto` |
| 3 | Converge | `git-power phase finalize --repo "$PWD" --confirm "$PWD"` | the merge is proven on the base, worktree and branch closed |
| 4 | Baseline | `canary_check.py baseline --urls <health> --state .ship/canary.json`, plus the metrics file below | taken before the deploy |
| 5 | Deploy | the workflows the contract names, staging then `real_test.deploy_prod_workflow`, with the commits it carries listed first | the environment serves the merge SHA, never a branch |
| 6 | Window | `canary_check.py check --urls <health> --state .ship/canary.json`, then `canary_check.py verdict --baseline B.json --now N.json` | ADVANCE reported; ROLLBACK proposed or HOLD go to the owner |
| 7 | Drift | `canary_check.py drift --local-sha … --deployed-sha … --repo .` | deployed SHA equals the base, or the gap is reported |

Report each step as it completes. The verification window compares what the repository exposes
before and after the production deploy: health, error rate and p95 latency in
`{"health_ok": bool, "error_rate": float, "p95_ms": float}` (from the contract's health URL or
metrics endpoint), and the critical user flow through `real-testing` on production when the
contract allows it there.

| Window signal | Verdict |
|---|---|
| every metric within its limit | ADVANCE |
| error rate above 1.25× or p95 above 1.2× baseline, or a metric UNKNOWN | HOLD: the owner reads it |
| health turned bad, error rate above 2× baseline, or p95 above +50% | ROLLBACK proposed with the plan's steps; never automatic |

