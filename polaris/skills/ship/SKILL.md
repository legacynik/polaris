---
name: ship
description: "◇ Polaris — Use when the work is done: one command that tests, audits, real-tests, updates the docs the diff made stale, opens the PR, signs it on staging once, writes the body and drives it to the owner's label, then merges once on the owner's yes and closes the work. Triggers: ship it, open the PR, submit, finish this branch. Requires git, gh and python 3."
version: 3.0.5
user-invocable: true
auto: true
lifecycle: "PR, receipt, label and replies live on GitHub, drained by the merge; .ship/ (canary state, merge log, drift alert) is local and overwritten by the next run, delete it to reset; the facts file for the PR body is scratch, deleted once the body is published"
invokes: [real-testing, git-power, review, pr, babysit, issue-contract, plan-area]
invoked-by: [human]
io: "finished work on a branch -> local loop to the DoD (tests, review audit, local real-test, docs) -> draft PR -> one staging signature for Medium and Large -> pr writes the body -> babysit brings it to the owner's label -> on the owner's yes, one merge, deploy and window, then the work is closed; a repo without the real_test contract records modalita: ridotta (mode: reduced) and the missing field"
status: active
---

# ship

## What it does

Phase 7 of the operating model, then phase 8. Launched once, it runs every step in order and
stops only where a decision is the owner's: the merge, a production deploy, and what `babysit`
escalates. A failed step loops back as written, never forward. It reads the repository's `ship:`
and `real_test:` contract first and never invents a command it does not name; a missing field is
`mode: reduced` plus the field: `references/contract.md`.

## When

- The work on a branch is finished: «ship it», «open the PR», «finish this branch».
- Size (from the plan file or the bead): **Tiny** and **Bug** skip step 7 (no staging);
  **Medium** and **Large** run it once.

## Steps

1. **Local tests.** The contract's `verify` plus the change's own tests, each new one seen red
   first; version and changelog edits when the contract declares them. *Done on exit 0.*
2. **Review.** `review` on `origin/<base>...HEAD`: the six-axis audit, which replaces any separate
   simplify pass or security auditor, plus the contract's extra review when declared. Fix what
   you agree with, one-line reason per rejection, then step 1 again. *Done when no blocking finding stands.*
3. **Real-test locally.** `real-testing` on the branch served locally, breaker from a fresh-context
   agent. Defects go back to step 1. *Done when `realtest_gate.py --root .` exits 0.*
4. **DoD.** Every criterion of every issue or bead the work closes is ✅ with a local proof, or ❌
   with its reason and a new item through `issue-contract`. *Done when nothing is undecided.*
5. **Docs.** List the docs whose claims the diff changed (README, AGENTS.md, the area's canonical
   doc, help text, examples); fix each in this branch, or name it under «Still open» in the PR
   body. *Done when no stale claim is left unnamed.*
6. **Push and PR.** `redact_scan.py --stdin < <(git diff origin/<base>...HEAD)` clean; `git-power`
   `commit-check`, `phase pre-pr`, `phase push`; `gh pr create --draft`; `phase post-push`.
   *Done when the draft's head equals the local HEAD.*
7. **Staging, once.** Queue for staging, deploy through `real_test.deploy_staging_workflow`,
   `real-testing` there signs the receipt on the PR, give staging back. A later code push needs a
   new signature: `references/contract.md`. *Done when the receipt names the current head.*
8. **Body.** `pr` from `.real-test/fatti/<branch>.md`, then `gh pr ready`. *Done when `controlla_pr.py` exits 0 or 3 on the head.*
9. **Owner's label.** `babysit` until `pr_status.py` exits 0, or a hand-off naming only what the
   owner must decide.
10. **Merge and close.** One proposal screen, nothing runs until the owner says yes; then
    `merge_gate.py` merges once (never a raw `gh pr merge`), `git-power phase finalize`, deploy
    and window as the contract names (`deploy_prod_workflow`), all in
    `references/merge-and-deploy.md`; then phase 8 when a plan file exists:
    `python3 <plan-dir>/scripts/plan_close.py --record <plan-file> --repo <root> --merged --pr <N>`.

## Output

A merged PR with its receipt, body and owner label; a deploy report (ADVANCE, HOLD or a proposed
rollback); the plan file closed when one exists; hook: `references/hook.md`. **Next:** STOP before the merge for the owner's yes.

## Where this goes

This skill produces: **none (the PR, its body through `pr`, the label through `babysit`)**; the
receipt is `real-testing`'s and lands where `outputs.validation` says.

## Not for

- Unfinished work: keep building, `ship` starts at «done».
- Reviewing a diff only (`review`) or judging merge-readiness only (`real-testing`).
- Static mockups, or a deploy with no code in it.
