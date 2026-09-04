#!/usr/bin/env bash
# Adversarial fixtures for session_commit.sh — every branch the guard introduces gets an input that
# forces it. Split out of the script itself so neither file carries two jobs (and neither goes over
# the declared 200-line limit). Sources the real implementation; never a re-implementation of it.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_COMMIT_LIB=1 . "$HERE/session_commit.sh"

_selfcheck() {
    local d; d="$(mktemp -d)"; cd "$d" || exit 1
    git init -q; git config user.email t@t; git config user.name t; git config polaris.login acme-dev
    mkdir -p team/acme-dev/sessions state
    local LOG=team/acme-dev/sessions/2026-07-19.md
    echo init > README; git add README; git commit -qm init
    local DEF; DEF="$(git rev-parse --abbrev-ref HEAD)"   # this repo's default branch (init.defaultBranch)

    # S1 first-of-day: untracked log → committed
    echo "## checkpoint" > "$LOG"; commit_checkpoint "$LOG" >/dev/null
    git ls-files --error-unmatch "$LOG" >/dev/null 2>&1 || { echo "FAIL S1 first-of-day not committed"; exit 1; }

    # S2 foreign-drag: another panel pre-staged decisions.md → must NOT enter my commit
    echo foreign > decisions.md; git add decisions.md
    echo more >> "$LOG"; commit_checkpoint "$LOG" >/dev/null
    git show --name-only --format= HEAD | grep -q decisions.md && { echo "FAIL S2 dragged decisions.md"; exit 1; }
    git show --name-only --format= HEAD | grep -q "sessions/2026-07-19.md" || { echo "FAIL S2 log not committed"; exit 1; }

    # S3 gitignored state + secret never committed
    printf 'state/current.md\n.env\n' > .gitignore; git add .gitignore; git commit -qm ignore
    echo live > state/current.md; echo "SECRET=x" > .env
    echo more2 >> "$LOG"; commit_checkpoint "$LOG" >/dev/null
    git ls-files | grep -qE 'state/current.md|(^|/)\.env$' && { echo "FAIL S3 secret/state committed"; exit 1; }

    # S4 forbidden input refused (decisions.md as arg)
    commit_checkpoint decisions.md >/dev/null 2>&1; [ $? -eq 2 ] || { echo "FAIL S4 forbidden input accepted"; exit 1; }

    # S5 empty checkpoint → skip, no new commit
    local before; before="$(git rev-parse HEAD)"; commit_checkpoint "$LOG" >/dev/null
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S5 empty produced a commit"; exit 1; }

    # S6 ONE checkout on a feature branch: it commits HERE, and the foreign staged file stays out.
    # There is no other tree to hand it to, and a spool nobody drains is the dirt AC4 forbids.
    git checkout -q -b feat/other
    echo foreign2 > lessons.md; git add lessons.md
    echo branchwork >> "$LOG"
    commit_checkpoint "$LOG" > out.txt 2>&1 || { echo "FAIL S6 single-checkout commit failed"; exit 1; }
    git show HEAD:"$LOG" | grep -q branchwork || { echo "FAIL S6 did not commit on the only checkout"; exit 1; }
    git show --name-only --format= HEAD | grep -q lessons.md && { echo "FAIL S6 dragged lessons.md"; exit 1; }
    [ -z "$(git status --short -- "$LOG")" ] || { echo "FAIL S6 left the session log dirty"; exit 1; }

    # S7 a DECLARED policy against direct commits on the default branch defers instead (#141),
    # and what it deferred drains on the next run that is allowed to commit.
    git checkout -q "$DEF"; git config polaris.commit-policy no-direct-default
    echo policywork >> "$LOG"; before="$(git rev-parse HEAD)"
    commit_checkpoint "$LOG" > out.txt 2>&1; [ $? -eq 0 ] || { echo "FAIL S7 defer must exit 0"; exit 1; }
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S7 committed against the policy"; exit 1; }
    grep -q deferred out.txt || { echo "FAIL S7 policy defer not reported"; exit 1; }
    git config --unset polaris.commit-policy
    commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q policywork || { echo "FAIL S7 deferred content never drained"; exit 1; }

    # S8 --end mode: decisions.md / lessons.md ARE its vetted promotion → allowed, committed together
    echo "## decision" > decisions.md; echo "## lesson" > lessons.md
    commit_end "$LOG" decisions.md lessons.md >/dev/null
    for f in decisions.md lessons.md; do
        git show --name-only --format= HEAD | grep -qx "$f" || { echo "FAIL S8 --end did not commit $f"; exit 1; }
    done
    git log -1 --format=%s | grep -q handoff || { echo "FAIL S8 --end wrong commit subject"; exit 1; }

    # S9 --end still refuses the gitignored pointer and secrets
    commit_end state/current.md >/dev/null 2>&1; [ $? -eq 2 ] || { echo "FAIL S9 --end accepted state/current.md"; exit 1; }
    commit_end .env >/dev/null 2>&1; [ $? -eq 2 ] || { echo "FAIL S9 --end accepted .env"; exit 1; }

    # S10 --end lands on the only checkout too, and leaves nothing behind for the next session
    git checkout -q feat/other; echo "## d2" >> decisions.md
    commit_end "$LOG" decisions.md >/dev/null 2>&1 || { echo "FAIL S10 --end refused"; exit 1; }
    git show --name-only --format= HEAD | grep -qx decisions.md || { echo "FAIL S10 --end did not land decisions.md"; exit 1; }
    [ -z "$(git status --short -- decisions.md "$LOG")" ] || { echo "FAIL S10 --end left the tree dirty"; exit 1; }
    git checkout -q "$DEF"

    # S11 default branch comes from origin/HEAD, not the literal name "main"
    git checkout -q -b trunk; git update-ref refs/remotes/origin/trunk HEAD
    git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk
    echo trunkwork >> "$LOG"; commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q trunkwork || { echo "FAIL S11 did not commit on origin/HEAD default (trunk)"; exit 1; }
    # With one checkout there is nowhere else to put it, so `main` commits on `main` — the point of
    # resolving origin/HEAD is WHICH tree may take the handoff, not renaming the branch we are on.
    git checkout -q "$DEF"; echo mainwork >> "$LOG"
    commit_checkpoint "$LOG" >/dev/null
    [ "$(git rev-parse --abbrev-ref HEAD)" = "$DEF" ] || { echo "FAIL S11 changed branch"; exit 1; }
    git show HEAD:"$LOG" | grep -q mainwork || { echo "FAIL S11 stranded the checkpoint on $DEF"; exit 1; }

    # S12 no origin/HEAD and the default is `master` → still commits (client repos are not all `main`)
    git symbolic-ref -d refs/remotes/origin/HEAD; git update-ref -d refs/remotes/origin/trunk
    git branch -m "$DEF" master; echo masterwork >> "$LOG"
    commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q masterwork || { echo "FAIL S12 deferred forever on a master-default repo"; exit 1; }

    # S13 a pre-commit hook refuses: honest failure, but NOTHING may stay staged (the next commit
    # without a pathspec would swallow the handoff — AC4's regression, one step later).
    printf '#!/bin/sh\nexit 1\n' > .git/hooks/pre-commit; chmod +x .git/hooks/pre-commit
    echo hooked >> "$LOG"
    commit_checkpoint "$LOG" > out.txt 2>&1; [ $? -eq 1 ] || { echo "FAIL S13 refused commit must exit 1"; exit 1; }
    [ -z "$(git diff --cached --name-only -- "$LOG")" ] || { echo "FAIL S13 left the log staged"; exit 1; }
    [ -f "$(git rev-parse --git-common-dir)/polaris-deferred/$LOG" ] || { echo "FAIL S13 nothing deferred"; exit 1; }
    rm -f .git/hooks/pre-commit; commit_checkpoint "$LOG" >/dev/null

    # S14 one absent path must not take the whole pathspec down with it (git add is all-or-nothing)
    echo more3 >> "$LOG"
    commit_checkpoint "$LOG" "$d/team/acme-dev/weeks/never-written.md" >/dev/null
    git show HEAD:"$LOG" | grep -q more3 || { echo "FAIL S14 an absent file blocked the commit"; exit 1; }

    # S15 detached HEAD: never a commit only the reflog can reach
    git checkout -q --detach HEAD
    echo detached >> "$LOG"; before="$(git rev-parse HEAD)"
    commit_checkpoint "$LOG" > out.txt 2>&1; [ $? -eq 0 ] || { echo "FAIL S15 detached must exit 0"; exit 1; }
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S15 committed onto a detached HEAD"; exit 1; }
    grep -q detached out.txt || { echo "FAIL S15 silent about the detached HEAD"; exit 1; }
    git checkout -q master

    # S16 a repo with no commit at all: the unborn branch is not a detached HEAD, and the dispatch
    # must not hand the work to the worktree it is already in (that recursed forever)
    local u; u="$(mktemp -d)"; ( cd "$u" && git init -q -b main . && git config user.email t@t \
        && git config user.name t && mkdir -p team/acme-dev/sessions \
        && echo "## first" > team/acme-dev/sessions/s.md \
        && commit_checkpoint team/acme-dev/sessions/s.md >/dev/null 2>&1
        git show HEAD:team/acme-dev/sessions/s.md 2>/dev/null | grep -q first ) \
        || { echo "FAIL S16 unborn branch never landed the first checkpoint"; exit 1; }
    rm -rf "$u"

    cd / && rm -rf "$d"
    echo "SELF-CHECK OK: first-of-day · foreign-drag(decisions+lessons) · gitignored-state+secret · forbidden-input · empty-skip · single-checkout-commits-here · policy-defers-and-drains · end-promotes-ledgers · end-refuses-state+secret · end-lands-on-the-only-checkout · origin/HEAD-default · master-default-repo · hook-refusal-unstages-and-defers · absent-path-does-not-block · detached-HEAD-defers · unborn-branch-lands"
}

_selfcheck
