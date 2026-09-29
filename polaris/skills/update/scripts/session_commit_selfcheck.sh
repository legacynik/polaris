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

    # S2 foreign-drag: another panel pre-staged decisions.md → must NOT enter my commit, and must
    # stay staged exactly as it was: `git commit -- <paths>` commits the paths, never the index.
    echo foreign > decisions.md; git add decisions.md
    echo more >> "$LOG"; commit_checkpoint "$LOG" >/dev/null
    git show --name-only --format= HEAD | grep -q decisions.md && { echo "FAIL S2 dragged decisions.md"; exit 1; }
    git show --name-only --format= HEAD | grep -q "sessions/2026-07-19.md" || { echo "FAIL S2 log not committed"; exit 1; }
    git diff --cached --name-only | grep -q decisions.md || { echo "FAIL S2 unstaged another panel's work"; exit 1; }

    # S3 gitignored state + secret never committed
    printf 'state/current.md\n.env\n' > .gitignore; git add .gitignore; git commit -qm ignore
    echo live > state/current.md; echo "SECRET=x" > .env
    echo more2 >> "$LOG"; commit_checkpoint "$LOG" >/dev/null
    git ls-files | grep -qE 'state/current.md|(^|/)\.env$' && { echo "FAIL S3 secret/state committed"; exit 1; }

    # S4 a staged archive from another panel is not ours to absorb, even if named explicitly.
    echo "foreign-again" >> decisions.md; git add -- decisions.md
    local before; before="$(git rev-parse HEAD)"
    commit_checkpoint "$LOG" decisions.md >/dev/null 2>&1
    [ $? -eq 2 ] || { echo "FAIL S4 foreign staged archive accepted"; exit 1; }
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S4 foreign archive entered a commit"; exit 1; }
    git diff --cached --name-only | grep -qx decisions.md \
        || { echo "FAIL S4 foreign archive was unstaged"; exit 1; }
    git restore --staged -- decisions.md

    # S4b a checkpoint promotes its own durable lesson and decision before /end.
    echo "## decided now" > decisions.md
    echo "## learned now" > lessons.md
    commit_checkpoint "$LOG" decisions.md lessons.md >/dev/null 2>&1 \
        || { echo "FAIL S4b checkpoint refused owned archives"; exit 1; }
    for f in decisions.md lessons.md; do
        git show --name-only --format= HEAD | grep -qx "$f" \
            || { echo "FAIL S4b checkpoint did not commit $f"; exit 1; }
    done

    # S5 empty checkpoint → skip, no new commit
    local before; before="$(git rev-parse HEAD)"; commit_checkpoint "$LOG" >/dev/null
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S5 empty produced a commit"; exit 1; }

    # S6 a feature branch commits HERE, on the branch you are on, and leaves the tree clean.
    git checkout -q -b feat/other
    echo foreign2 > lessons.md; git add lessons.md
    echo branchwork >> "$LOG"
    commit_checkpoint "$LOG" > out.txt 2>&1 || { echo "FAIL S6 commit on the current branch failed"; exit 1; }
    git show HEAD:"$LOG" | grep -q branchwork || { echo "FAIL S6 did not commit on the current branch"; exit 1; }
    grep -q "committed on feat/other" out.txt || { echo "FAIL S6 silent about where it landed"; exit 1; }
    git show --name-only --format= HEAD | grep -q lessons.md && { echo "FAIL S6 dragged lessons.md"; exit 1; }
    [ -z "$(git status --short -- "$LOG")" ] || { echo "FAIL S6 left the session log dirty"; exit 1; }

    # S6b a SECOND checkout, on another branch, changes nothing: this tree still commits its own log.
    # Before 2026-09-04 this shape deferred forever and left the tree dirty.
    git worktree add -q "$d/wt-two" -b feat/two >/dev/null 2>&1
    echo twowork >> "$LOG"; commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q twowork || { echo "FAIL S6b a sibling worktree blocked the commit"; exit 1; }
    [ -d "$(git rev-parse --git-common-dir)/polaris-deferred" ] && { echo "FAIL S6b something wrote a spool"; exit 1; }

    # S7 a DECLARED policy against direct commits on the default branch REFUSES (exit 2) and says so;
    # the file stays in the working tree, and the same policy on a feature branch does not apply.
    git checkout -q "$DEF"; git config polaris.commit-policy no-direct-default
    echo policywork >> "$LOG"; before="$(git rev-parse HEAD)"
    commit_checkpoint "$LOG" > out.txt 2>&1; [ $? -eq 2 ] || { echo "FAIL S7 policy must exit 2"; exit 1; }
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S7 committed against the policy"; exit 1; }
    grep -q "polaris.commit-policy" out.txt || { echo "FAIL S7 policy refusal not named"; exit 1; }
    [ -n "$(git status --short -- "$LOG")" ] || { echo "FAIL S7 the file left the working tree"; exit 1; }
    # Same policy, same dirty file, a feature branch cut from here: it applies to the default only.
    git checkout -q -b feat/policy
    commit_checkpoint "$LOG" >/dev/null || { echo "FAIL S7 the policy leaked onto a feature branch"; exit 1; }
    git show HEAD:"$LOG" | grep -q policywork || { echo "FAIL S7 never landed off the default"; exit 1; }
    git config --unset polaris.commit-policy
    git checkout -q "$DEF"; git merge -q --ff-only feat/policy; git checkout -q feat/other
    git merge -q -m sync "$DEF" >/dev/null 2>&1; git checkout -q "$DEF"

    # S8 --end mode: decisions.md / lessons.md ARE its vetted promotion → allowed, committed together
    git restore --staged -- lessons.md
    echo "## decision" > decisions.md; echo "## lesson" > lessons.md
    commit_end "$LOG" decisions.md lessons.md >/dev/null
    for f in decisions.md lessons.md; do
        git show --name-only --format= HEAD | grep -qx "$f" || { echo "FAIL S8 --end did not commit $f"; exit 1; }
    done
    git log -1 --format=%s | grep -q handoff || { echo "FAIL S8 --end wrong commit subject"; exit 1; }

    # S9 --end still refuses the gitignored pointer and secrets
    commit_end state/current.md >/dev/null 2>&1; [ $? -eq 2 ] || { echo "FAIL S9 --end accepted state/current.md"; exit 1; }
    commit_end .env >/dev/null 2>&1; [ $? -eq 2 ] || { echo "FAIL S9 --end accepted .env"; exit 1; }

    # S10 --end on a feature branch lands there too, and leaves nothing behind for the next session
    git checkout -q feat/other; echo "## d2" >> decisions.md
    commit_end "$LOG" decisions.md >/dev/null 2>&1 || { echo "FAIL S10 --end refused"; exit 1; }
    git show --name-only --format= HEAD | grep -qx decisions.md || { echo "FAIL S10 --end did not land decisions.md"; exit 1; }
    [ -z "$(git status --short -- decisions.md "$LOG")" ] || { echo "FAIL S10 --end left the tree dirty"; exit 1; }
    git checkout -q "$DEF"

    # S11 the default branch comes from origin/HEAD, not the literal name "main" — it is what the
    # policy refusal is measured against, and nothing else.
    git checkout -q -b trunk; git update-ref refs/remotes/origin/trunk HEAD
    git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk
    git config polaris.commit-policy no-direct-default
    echo trunkwork >> "$LOG"
    commit_checkpoint "$LOG" >/dev/null 2>&1; [ $? -eq 2 ] || { echo "FAIL S11 origin/HEAD default not honoured"; exit 1; }
    git config --unset polaris.commit-policy
    commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q trunkwork || { echo "FAIL S11 did not commit on trunk"; exit 1; }
    [ "$(git rev-parse --abbrev-ref HEAD)" = trunk ] || { echo "FAIL S11 changed branch"; exit 1; }

    # S12 no origin/HEAD and the default is `master` → still commits (client repos are not all `main`)
    git symbolic-ref -d refs/remotes/origin/HEAD; git update-ref -d refs/remotes/origin/trunk
    git checkout -q "$DEF"; git branch -m "$DEF" master; echo masterwork >> "$LOG"
    commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q masterwork || { echo "FAIL S12 stranded the checkpoint on a master-default repo"; exit 1; }

    # S13 a pre-commit hook refuses: exit 1, the hook's own line reaches the session, NOTHING stays
    # staged (the next commit without a pathspec would swallow the handoff) and no copy is made.
    printf '#!/bin/sh\necho "the hook says no" >&2\nexit 1\n' > .git/hooks/pre-commit; chmod +x .git/hooks/pre-commit
    echo hooked >> "$LOG"
    commit_checkpoint "$LOG" > out.txt 2>&1; [ $? -eq 1 ] || { echo "FAIL S13 refused commit must exit 1"; exit 1; }
    grep -q "the hook says no" out.txt || { echo "FAIL S13 swallowed the hook's reason"; exit 1; }
    [ -z "$(git diff --cached --name-only -- "$LOG")" ] || { echo "FAIL S13 left the log staged"; exit 1; }
    [ -n "$(git status --short -- "$LOG")" ] || { echo "FAIL S13 the file left the working tree"; exit 1; }
    [ -d "$(git rev-parse --git-common-dir)/polaris-deferred" ] && { echo "FAIL S13 wrote a spool"; exit 1; }
    rm -f .git/hooks/pre-commit; commit_checkpoint "$LOG" >/dev/null

    # S14 one absent path must not take the whole pathspec down with it (git add is all-or-nothing)
    echo more3 >> "$LOG"
    commit_checkpoint "$LOG" "$d/team/acme-dev/weeks/never-written.md" >/dev/null
    git show HEAD:"$LOG" | grep -q more3 || { echo "FAIL S14 an absent file blocked the commit"; exit 1; }

    # S15 detached HEAD: exit 2, never a commit only the reflog can reach, file left where it is
    git checkout -q --detach HEAD
    echo detached >> "$LOG"; before="$(git rev-parse HEAD)"
    commit_checkpoint "$LOG" > out.txt 2>&1; [ $? -eq 2 ] || { echo "FAIL S15 detached must exit 2"; exit 1; }
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S15 committed onto a detached HEAD"; exit 1; }
    grep -q detached out.txt || { echo "FAIL S15 silent about the detached HEAD"; exit 1; }
    [ -n "$(git status --short -- "$LOG")" ] || { echo "FAIL S15 the file left the working tree"; exit 1; }
    git checkout -q master

    # S16 a repo with no commit at all is NOT a refusal: the unborn branch takes the first
    # checkpoint. It is also not a detached HEAD, which is what the guard used to read it as.
    local u; u="$(mktemp -d)"
    ( cd "$u" && git init -q -b main . && git config user.email t@t && git config user.name t \
        && mkdir -p team/acme-dev/sessions && echo "## first" > team/acme-dev/sessions/s.md \
        && commit_checkpoint team/acme-dev/sessions/s.md >/dev/null 2>&1
      git show HEAD:team/acme-dev/sessions/s.md 2>/dev/null | grep -q first ) \
        || { echo "FAIL S16 unborn branch never landed the first checkpoint"; exit 1; }
    rm -rf "$u"

    # S17 a path git REFUSES because it is gitignored: named with its reason, exit 2, and the
    # OTHER paths of the same run still land. Before this, the run said "no change, skip".
    git checkout -q master 2>/dev/null || true
    printf 'ignored/\n' >> .gitignore; git add .gitignore; git commit -qm ignore-dir
    mkdir -p ignored; echo "## ignored log" > ignored/log.md
    echo "## kept" > lessons.md
    commit_end ignored/log.md lessons.md > out.txt 2>&1; [ $? -eq 2 ] || { echo "FAIL S17 an ignored path must exit 2"; exit 1; }
    grep -q "git refuses ignored/log.md (ignored)" out.txt || { echo "FAIL S17 the refusal is unnamed"; exit 1; }
    git show --name-only --format= HEAD | grep -qx lessons.md || { echo "FAIL S17 the other paths did not land"; exit 1; }

    # S18 a path inside an untracked NESTED repo: `git add` returns 0 and stages nothing there, so
    # the index is the test — otherwise the pathspec took the whole commit down with it.
    mkdir -p nested/journal && git -C nested init -q -b main
    echo "session line" > nested/journal/j.md
    echo "## kept2" >> lessons.md
    commit_end nested/journal/j.md lessons.md > out.txt 2>&1; [ $? -eq 2 ] || { echo "FAIL S18 a nested-repo path must exit 2"; exit 1; }
    grep -q "git refuses nested/journal/j.md (nested repo)" out.txt || { echo "FAIL S18 the refusal is unnamed"; exit 1; }
    git show HEAD:lessons.md | grep -q kept2 || { echo "FAIL S18 the other paths did not land"; exit 1; }

    cd / && rm -rf "$d"
    echo "SELF-CHECK OK: first-of-day · foreign-drag-stays-staged · gitignored-state+secret · foreign-staged-archive-refuses · checkpoint-promotes-ledgers · empty-skip · commits-on-the-branch-you-are-on · a-sibling-worktree-changes-nothing · policy-refuses-only-on-the-default · end-promotes-ledgers · end-refuses-state+secret · end-lands-on-the-current-branch · origin/HEAD-default · master-default-repo · hook-refusal-exits-1-and-unstages · absent-path-does-not-block · detached-HEAD-refuses · unborn-branch-lands · ignored-path-named-others-land · nested-repo-path-named-others-land"
}

_selfcheck
