---
name: pol-ship
description: "◇ Use when the work is done: one command that tests, commits, opens the PR and drives it green — real-test on the head, commit hygiene, push, a PR body the owner judges without code, the babysit loop to the owner's label, then ONE merge-and-deploy proposal. Triggers: ship it, open the PR, submit, finish this branch. Merges and deploys only on the owner's yes."
version: 2.1.0
user-invocable: true
auto: true
lifecycle: "PR, receipt, label and replies live on GitHub, drained by the merge; .ship/ (canary state, merge log, drift alert) is local and overwritten by the next run, delete it to reset; the facts file for the PR body is scratch, deleted once the body is published"
invokes: [real-testing, git-power, polaris-review, pol-pr, pol-babysit]
invoked-by: [human]
io: "finished work on a branch -> local loop to the issue's DoD (tests, tiered review, simplify, local real-test) -> one staging round that signs the PR -> pol-pr writes the body -> pol-babysit brings it to the owner's label -> one proposal (merge, deploy, rollback plan, evidence); on the owner's yes, Phase B merges once, deploys and watches the verification window; a repo without the real_test contract records modalita: ridotta and which field is missing"
status: active
---

# pol-ship

The single entry point once the work is done. Launched once, it runs every step below in order
without asking again, and stops only where a decision is the owner's: the merge, a production
deploy, and the escalations `pol-babysit` reserves (security invariants, public contract, schemas,
release config, scope). Each step ends on a criterion you can check; a step that fails loops back
as written, never forward.

Read the repository's contract once (`_polaris/config.yml`, else `config.yml`): `ship:` (`verify`,
workflows, environments, `rollback`, `owner_label`, `checks_not_gating`, `inert_paths`,
`signing_env`, optional `version_file`, `changelog`, `flags`, `slo`, extra review) and `real_test:`
(`deploy_staging_workflow`, `deploy_prod_workflow`, `health`, `smoke`, `rollback`). Never invent a
command the contract does not name; a missing field is written as `mode: reduced` plus the field,
never skipped in silence. Every script runs from the repository root as
`python3 <skill-dir>/scripts/<script>.py`, so `gh` and `git` read that repository.

The binding control is `pol-babysit`: it reads the owner's label bound to the head SHA from the PR
(server state); branch protection is the server-side wall. The hook is opt-in per repository and is a
tripwire, not a security boundary: a `PreToolUse` hook on shell commands running
`python3 <skill-dir>/scripts/pre_tool_hook.py` (Claude Code: `.claude/settings.json` →
`hooks.PreToolUse`, matcher `Bash`) catches the default spelling of `gh pr create|new|ready|edit`
with a body `pol-pr`'s checker refuses and of a raw `gh pr merge`, and logs the emergency bypass.
Shell wrappers (`bash -c`, `eval`, subshells) and `gh api` calls other than the merge endpoints are
not covered.

## Where this goes

This skill produces: **none (the PR, its body through `pol-pr`, the label through `pol-babysit`)**;
the validation receipt is `real-testing`'s and lands where the host repository's
`outputs.validation` says. Never write a document of your own beside them.

## When NOT to use

- A branch whose work is not finished: keep building, `pol-ship` starts at «done».
- Reviewing a diff only (`polaris-review`), or judging merge-readiness only (`real-testing`).
- Static mockups, or a deploy with no code in it.

## Phase A1, local, repeated until the DoD holds

1. **Tests.** The contract's `verify` plus the change's own tests, each new one seen red first.
   *Done when the command exits 0.*
2. **Review.** Run `polaris-review` on `origin/<base>...HEAD`: its tier script picks the reviewer
   strength (tier 3 adds `codex-review` or a second model). Add to its brief two angles: security
   (input at trust boundaries, auth and permission checks, secrets, injection) and test gaps (each
   changed behaviour has a test that would fail if it broke; no mock asserted on; real data where
   the repository has it). Plus the contract's extra review when declared. Fix every finding you
   agree with; keep a one-line reason for each one you reject. *Done when no critical finding
   stands and every rejection has its reason.*
3. **Simplify.** One pass over the files the diff touches, behaviour unchanged: delete dead code
   and unused parameters, inline one-use indirection, replace hand-rolled code with the standard
   library or a helper the repository already has, flatten nesting. Then, when the contract
   declares them, the version and changelog edits (`version_bump.py`, `changelog_edit.py`). Then
   step 1 again. *Done when the suite is green after it.*
4. **Real-test, locally.** `real-testing` on the branch served locally (the repository's
   local-against-staging-data setup). Defects go back to step 1. *Done on a MERGEABLE verdict for
   the current tree (`realtest_gate.py --root .` exits 0).*
5. **DoD.** Every criterion of every issue the work closes is ✅ with a local proof, or ❌ with its
   reason and a new issue. *Done when nothing is undecided.* Until then, back to step 1.

## Phase A2, staging once, then the hand-off

6. **Commit, branch, PR.** `redact_scan.py --stdin < <(git diff origin/<base>...HEAD)` clean; then
   `git-power commit-check`, `phase pre-pr` (branch level with the base), `phase push`; open the PR
   as a **draft** (`gh pr create --draft`, no body needed yet: the hook asks for one at `ready`);
   then `git-power phase post-push` (an open PR keeps the worktree). *Done when the draft PR
   exists and its head equals the local HEAD.*
7. **Staging.** Shared: the served SHA (the contract's `health`) names who holds it; ask that lane
   and queue, never deploy over a running test. Deploy the branch through
   `real_test.deploy_staging_workflow`. *Done when staging serves HEAD.*
8. **Sign.** `real-testing` on staging, complete, fresh breaker: the receipt goes on the PR, its
   `ambiente:` line naming the signing environment. Give staging back to what it served before and
   check its SHA. A later push that changes only the contract's `inert_paths` keeps the receipt; a
   push that changes code needs a new signature, the one case for a second staging round.
   *Done when the receipt on the PR names the current head.*
9. **Body.** `pol-pr` from `.real-test/fatti/<branch>.md`, then `gh pr ready` (the hook checks the
   body there). *Done when `controlla_pr.py` exits 0 or 3 on the current head.*
10. **Owner's label.** `pol-babysit` until the label sits on the current head. *Done when
    `pr_status.py` exits 0 (READY), or on a hand-off naming only what the owner must decide.*

## The proposal — one screen, then stop

11. When step 10 is READY, requery once (`merge_gate.py decide`) and stop with **one** message:

```text
<one plain line: exactly what the owner says yes to, e.g. "merge PR #N, deploy to staging, then production">

Evidence (each on head <sha>):
- CI: <green, required checks> · <link>
- Real-test: <verdict> · <environment> · <receipt link>
- Review: polaris-review tier <n> · <no blocking finding> · <link>
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
yes.* A changed head after the message voids it: back to step 10.

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

## Gotchas

- A finding a reviewer cannot back with a concrete scenario is noise: drop it, keep the reason.
- A second staging round without a code change after signing means step 4 was skipped.
- The hook never fails open on what it reads: an internal error exits 2, and the emergency bypass
  (`SHIP_BYPASS_GATE=1`) is logged. What it does not read (wrappers, `gh api`) it does not judge.
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
