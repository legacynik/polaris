#!/usr/bin/env bash
# The deferral spool — where a session entry waits when this tree may not commit it, and how it
# comes back. Sourced by session_commit.sh; it has no entry point of its own.
#
# Deferral that never drains is data loss with a reassuring message. The rule this file replaced
# left the entry on a TRACKED path waiting for "the next default-branch session", which on a
# checkout parked on a long-lived branch never comes: measured 2026-08-11, one repo's main checkout
# sat on a recovery branch 184 commits behind with 16 entries piled up, another's was detached, so
# its deferral was permanent (45 files). The spool lives under the COMMON git dir instead: one per
# repo, shared by every worktree, independent of what branch any of them is on. Nothing here ever
# switches a branch.

# The upgrade path this file declared in 2026-07-25 and never got: DEFER used to leave the entry
# on disk on a tracked path, waiting for "the next default-branch session" — which on a checkout
# parked on a long-lived branch never comes. Measured 2026-08-11: one repo's main checkout sat on a
# recovery branch 184 commits behind, the journal was drained by hand three days earlier and had
# already refilled with 16 entries; another repo's main checkout is detached, so its deferral was
# permanent (45 files). Deferral that never drains is data loss with a reassuring message.
#
# The spool lives under the COMMON git dir: one per repo, shared by every worktree, independent of
# what branch any of them is on. Nothing here ever switches a branch.
_spool_dir() { echo "$(git rev-parse --git-common-dir 2>/dev/null)/polaris-deferred"; }

# A worktree already sitting on the default branch is the cheapest drain: no checkout, no risk.
# NEVER this worktree. On an unborn or detached HEAD `git rev-parse --abbrev-ref HEAD` says `HEAD`
# while `git worktree list` still reports `branch refs/heads/main`, so the tree handed the work to
# ITSELF and `_commit` recursed forever (168 identical lines in 15s, pre-existing on origin/main).
_wt_on_default() {
    local def="$1" here wt="" line
    here="$(git rev-parse --show-toplevel 2>/dev/null)" && here="$(cd "$here" && pwd -P)"
    while IFS= read -r line; do
        case "$line" in
            worktree\ *) wt="${line#worktree }" ;;
            branch\ refs/heads/"$def")
                [ -n "$wt" ] && [ "$(cd "$wt" 2>/dev/null && pwd -P)" != "$here" ] \
                    && { echo "$wt"; return 0; } ;;
        esac
    done < <(git worktree list --porcelain 2>/dev/null)
    return 1
}

# A repository may declare that its default branch is never committed to directly (branch
# protection, or a rule the contract states). Declared, never guessed: asking the remote would make
# every offline run either hang or fail open, and #141 asks for a deterministic `deferred`.
_policy_defers() {
    case "$(git config --get polaris.commit-policy 2>/dev/null)" in
        no-direct-default|no-direct|deferred) return 0 ;;
    esac
    return 1
}

# Once the content has landed elsewhere — a sibling worktree, or the spool — the copy this tree
# still holds is a duplicate, and an untracked duplicate is a dirty line. It goes. A TRACKED one
# stays and is named: removing it would be a deletion, i.e. another dirty line, and this tree's
# history is not ours to rewrite.
