# PR conflict resolution — decision tree

> Loaded by `polaris-sweep` Phase 1.5 when `gh pr view --json mergeable` reports `CONFLICTING`. Stays unloaded for non-conflicting PRs (progressive disclosure — keeps default sweep tick cheap).

## Why this exists

Hand ships PRs faster than main can absorb them. Two PRs from different ticks can touch overlapping files; whichever lands second becomes `CONFLICTING`. Without auto-rebase, conflicting PRs accumulate and block the queue.

**Observed pattern (2026-05-16)**: 8 PRs merged in one day, 3 ended `CONFLICTING` waiting for human rebase. The bottleneck moved from "writing code" to "resolving stale base".

This reference contains the decision tree polaris-sweep follows when it detects `CONFLICTING`. Decision should always be deterministic — same state in → same action out — so re-runs are idempotent.

## Decision tree

```
PR is CONFLICTING
       │
       ▼
Step 0: Setup isolated worktree   ←── MANDATORY before any rebase
   │
   ▼
Step 1: Classify conflict source
   │
   ├─ "behind main only" (no overlap, just stale base)
   │     → Step 2a: trivial rebase
   │
   ├─ "auto-resolvable overlap" (different lines in same files)
   │     → Step 2b: clean rebase
   │
   └─ "real code conflict" (same lines, opposing semantics)
         → Step 3: escalate

Step 4: Teardown worktree  (always runs, regardless of outcome)
```

## Step 0 — Setup isolated worktree (MANDATORY)

**Why**: `/workspace/<repo>/` is the shared main checkout. Multiple parallel agents (afk-poll, polaris-sweep, manual sessions) can be cd'd into it at the same time. Running `git checkout <branch> && git rebase` on the shared checkout corrupts the active branch in other panels and races the workspace lock.

Always create a dedicated, disposable worktree before touching anything:

```bash
# Anchor to the main repo root, not whatever cwd we inherited
REPO_ROOT="$(git rev-parse --show-toplevel)"
SWEEP_WT="/tmp/sweep-rebase-$PR_N"

# Idempotent: if a previous tick left a worktree, wipe and recreate.
# A stale worktree can mask a real upstream change.
if [ -d "$SWEEP_WT" ]; then
    git -C "$REPO_ROOT" worktree remove --force "$SWEEP_WT" 2>/dev/null || rm -rf "$SWEEP_WT"
    git -C "$REPO_ROOT" worktree prune 2>/dev/null
fi

# Fetch the PR branch fresh so the worktree starts from origin tip
git -C "$REPO_ROOT" fetch origin "$PR_HEAD_REF":"refs/remotes/origin/$PR_HEAD_REF"
git -C "$REPO_ROOT" fetch origin main

# Detached checkout — we don't want to claim/move the local tracking branch
git -C "$REPO_ROOT" worktree add --detach "$SWEEP_WT" "origin/$PR_HEAD_REF" || {
    echo "Worktree create failed — abort tick"
    exit 0
}

# All subsequent commands run from the isolated worktree
cd "$SWEEP_WT"
```

Hard rules:
- **Never** `cd` back into `$REPO_ROOT` during a sweep tick.
- **Never** reuse a sweep worktree across PRs — one PR per worktree, teardown at end.
- The `/tmp/sweep-rebase-$PR_N` path is fixed so concurrent ticks on the same PR collide loudly (one wins, the other aborts at `worktree add`).

## Step 1 — Classify

All commands run inside `$SWEEP_WT` from Step 0. The fetch was already done; just rebase.

```bash
# Try a dry-run rebase against origin/main. We don't push yet — just see what happens.
git rebase --no-update-refs origin/main 2>&1 | tee /tmp/rebase-dryrun-$PR_N.log
REBASE_RC=$?

if [ "$REBASE_RC" -eq 0 ]; then
    classify="trivial"          # rebase succeeded, no conflict
elif grep -q "CONFLICT (content)" /tmp/rebase-dryrun-$PR_N.log; then
    classify="real"             # same lines, manual resolution needed
elif grep -q "CONFLICT" /tmp/rebase-dryrun-$PR_N.log; then
    classify="auto-resolvable"  # rare case: tree conflict but no content overlap
fi

# If REBASE_RC was 0, we have the rebased tree IN the worktree — keep it,
# Step 2a pushes it. If non-zero, abort and continue to Step 2b/3 decision.
if [ "$classify" != "trivial" ]; then
    git rebase --abort 2>/dev/null || true
fi
```

## Step 2a — Trivial rebase (no conflict)

If Step 1 reported `classify=trivial`, the branch was just behind main. The rebase already ran in the worktree — just push:

```bash
# Detached HEAD in the worktree must be pushed to the *named* remote ref.
git push --force-with-lease="$PR_HEAD_REF:$(git rev-parse origin/$PR_HEAD_REF)" \
    origin "HEAD:refs/heads/$PR_HEAD_REF"
PUSH_RC=$?

if [ "$PUSH_RC" -ne 0 ]; then
    echo "Push refused — someone updated the branch since fetch. Re-classify next tick."
    # Step 4 teardown still runs.
    exit 0
fi
```

`--force-with-lease=<ref>:<expected>` is stricter than the bare flag: it aborts if anyone pushed to the PR branch since Step 0's fetch (race-safe even across concurrent sweep ticks). After push, CI re-runs and GitHub auto-merge fires when the required check passes.

Comment on the PR for the audit trail:

```bash
gh pr comment "$PR_N" --body "🤖 Sweep auto-rebased on main ($(git rev-parse --short origin/main)). CI re-running, auto-merge will fire on green."
```

## Step 2b — Auto-resolvable overlap

Rare. Tree-level conflict (e.g. file rename + edit) that git can resolve with `-X theirs` or `-X ours` strategy without dropping semantics. Use ONLY when classify=auto-resolvable AND we're sure preferring the PR's version is safe.

```bash
# Re-run the rebase with strategy flag (the dry-run was aborted in Step 1)
git rebase -X theirs origin/main || {
    echo "Strategic rebase failed — fall through to Step 3 escalate"
    git rebase --abort 2>/dev/null
    classify="real"
}

if [ "$classify" = "auto-resolvable" ]; then
    git push --force-with-lease="$PR_HEAD_REF:$(git rev-parse origin/$PR_HEAD_REF)" \
        origin "HEAD:refs/heads/$PR_HEAD_REF"
    gh pr comment "$PR_N" --body "🤖 Sweep auto-rebased with \`-X theirs\` strategy. **Verify** the auto-resolution before merge."
fi
```

Always add a comment flagging the strategy choice. Don't auto-merge after this step — the comment serves as a manual-review trigger.

## Step 3 — Real conflict (escalate)

If Step 1 reported `classify=real`, manual judgment is required. Polaris-sweep should:

```bash
# Capture the conflict markers for the human to inspect
CONFLICT_FILES=$(grep -oE "^CONFLICT.*in [^ ]+" /tmp/rebase-dryrun.log | sort -u)

# Label for human triage
gh pr edit "$PR_N" --add-label "needs-human-rebase"
gh pr edit "$PR_N" --remove-label "afk:done-pending-merge" 2>/dev/null

# Comment with diagnosis
gh pr comment "$PR_N" --body "🔴 Sweep detected **real code conflict** with main. Auto-rebase aborted — manual resolution needed.

**Conflicting files**:
$CONFLICT_FILES

**Reproduction**:
\`\`\`bash
git checkout $PR_HEAD_REF
git rebase origin/main  # will produce the same conflict
\`\`\`

Three recovery paths:
1. **Manual rebase**: resolve, push --force-with-lease.
2. **Re-implement**: discard branch, re-pick the issue (\`afk:eligible\` label), Hand re-attempts on fresh main.
3. **Drop**: close the PR, revisit later."

# Telegram alert via the lib helper
. /usr/local/lib/holyclaude/notify.sh 2>/dev/null
notify_telegram "PR needs human rebase" "#$PR_N: real conflict on $CONFLICT_FILES"
```

Re-poll cycle (option 2 above) is implemented by removing `afk:eligible` from the issue, deleting `afk:done-pending-merge` from the issue, closing the PR, then adding `afk:eligible` back — Hand's next tick will re-claim. Only do this autonomously for `scope:trivial` or `scope:small` issues; for medium/large, escalation stops at the Telegram message.

## Step 4 — Teardown (always runs)

After Step 2a / 2b / 3 completes (success OR failure), remove the worktree. Leftover worktrees confuse future ticks and consume disk on the container.

```bash
# Must cd OUT of the worktree before removing it
cd "$REPO_ROOT"

git worktree remove --force "$SWEEP_WT" 2>/dev/null || rm -rf "$SWEEP_WT"
git worktree prune 2>/dev/null

# Audit log (host-mounted path on the holyclaude container)
echo "$(date -Iseconds) sweep PR=$PR_N classify=$classify" >> /var/log/sweep-conflicts.log
```

Why `--force`: the worktree's HEAD is detached and may contain a successful local rebase that was pushed — no value in keeping it.

## What polaris-sweep should NOT do

- **Never** push a rebase that overwrites work without `--force-with-lease`. If lease fails (someone else pushed), abort and re-classify.
- **Never** auto-resolve with `-X theirs` or `-X ours` for `risk:medium+` PRs. Those need human judgment.
- **Never** delete a worktree. Leave it for human inspection.
- **Never** merge a PR that just got auto-rebased without re-running CI. Auto-rebase invalidates prior CI results.
- **Never** re-poll (recreate issue as `afk:eligible`) more than 2 times for the same issue — if it conflicts repeatedly, the issue or main is unstable.

## Idempotence guarantees

Every step is idempotent:
- Rebase produces same result given same inputs → re-running on a CONFLICTING PR yields same decision.
- Comment upsert via `<!-- polaris-sweep-id:... -->` marker (see Phase 5 in SKILL.md) means re-runs edit existing comments.
- Label changes are no-ops when the label is already in the target state.

Multiple sweep ticks on the same conflicting PR converge to the same outcome — no thrashing, no double-rebase.

## Concurrency with a live implementation session

If a Hand session is currently mid-implementation on the same branch (Hand-owned worktree alive, session attached), polaris-sweep MUST NOT touch the branch. Check **before Step 0** (creating the sweep worktree is itself a write):

```bash
# Hand's worktrees live at .worktrees/<branch> inside $REPO_ROOT
HAND_WT="$REPO_ROOT/.worktrees/$PR_HEAD_REF"
if [ -d "$HAND_WT" ] && pgrep -f "claude.*$HAND_WT" >/dev/null; then
    echo "Active Hand session on $HAND_WT — skipping rebase, will retry next tick"
    exit 0
fi
```

Hand and Sweep are independent agents. Hand's worktree path (`.worktrees/$BRANCH`) and Sweep's worktree path (`/tmp/sweep-rebase-$PR_N`) are deliberately disjoint — neither agent can clobber the other's checkout. The pgrep guard above is the extra belt that prevents Sweep from rebasing an in-flight branch even if its paths don't collide.

## Edge cases

- **PR base != main**: if the PR targets a feature branch (not main), do nothing. Polaris-sweep only resolves main-targeting PRs.
- **PR contains merge commits from main**: someone manually pulled main in. Refuse to rebase (`git log` shows merge commits in the diff) → escalate.
- **Force-push history exists**: the branch has been force-pushed before. Still safe — `--force-with-lease` respects the current remote tip.
- **PR labeled `needs-human-rebase` already**: don't re-attempt. Means a previous sweep gave up; let the human handle it. Skip and continue.
