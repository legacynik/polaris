#!/usr/bin/env bash
# session_commit.sh — land a /update checkpoint in git with commit-hygiene enforced IN CODE, not prose.
#
# Design (founder decision 2026-07-19, Option A): a /update checkpoint describes the work on the
# CURRENT branch, so it commits THERE — pathspec-only. It is branch-WIP, not yet shared truth; `/end`
# is what promotes durable history to main. This only stops the checkpoint from being orphaned.
#
# Commit hygiene, enforced here so a model following the skill can't skip it:
#   • pathspec-ONLY (never `git add -A`): staging just the named file(s) means parallel panels sharing
#     one working tree can never drag each other's uncommitted work.
#   • forbidden paths refused (on input AND on the staged set): state/current.md (gitignored
#     convergence point), decisions.md / lessons.md (those are `/end`'s vetted promotion), .env* (secrets).
#   • branch is reported, never changed; never a push.
#
#   session_commit.sh <session_log> [<weekly_plan>]     # commit the checkpoint files
#   session_commit.sh --selfcheck                        # adversarial gate tests, no real repo touched
set -uo pipefail

_forbidden() {
    case "$1" in *state/current.md) return 0 ;; *.env|*.env.*) return 0 ;; esac
    case "$(basename "$1")" in decisions.md|lessons.md) return 0 ;; esac
    return 1
}

commit_checkpoint() {
    local log="$1" plan="${2:-}"
    _forbidden "$log" && { echo "session_commit: refuse forbidden path ${log}" >&2; return 2; }
    [ -n "$plan" ] && _forbidden "$plan" && { echo "session_commit: refuse forbidden path ${plan}" >&2; return 2; }
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "session_commit: not a git repo, skip"; return 0; }
    local branch; branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
    git add -- "$log" ${plan:+"$plan"} 2>/dev/null || true
    local staged; staged="$(git diff --cached --name-only -- "$log" ${plan:+"$plan"})"
    [ -n "$staged" ] || { echo "session_commit: no checkpoint change on ${branch}, skip"; return 0; }
    local f; while IFS= read -r f; do
        _forbidden "$f" && { git reset -q -- "$f" 2>/dev/null; echo "session_commit: ABORT — forbidden file staged (${f})" >&2; return 2; }
    done <<< "$staged"
    local login; login="$(git config --local --get polaris.login 2>/dev/null || echo session)"
    # commit with explicit pathspec: only these paths land, even if another panel pre-staged something
    if git commit -q -m "chore(session): checkpoint @${login} $(date +%F)" -- "$log" ${plan:+"$plan"}; then
        echo "session_commit: committed on ${branch} — ${staged//$'\n'/, }"
    else
        # never claim success on a failed commit (hook rejection, missing identity, index lock, bad pathspec):
        # /update would report the checkpoint landed while it sits uncommitted.
        echo "session_commit: git commit FAILED on ${branch} — checkpoint NOT landed (${staged//$'\n'/, })" >&2
        return 1
    fi
}

_selfcheck() {
    local d; d="$(mktemp -d)"; cd "$d" || exit 1
    git init -q; git config user.email t@t; git config user.name t; git config polaris.login legacynik
    mkdir -p team/legacynik/sessions state
    local LOG=team/legacynik/sessions/2026-07-19.md
    echo init > README; git add README; git commit -qm init

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

    # S6 on another panel's branch: commits there, drags nothing (foreign lessons.md pre-staged)
    git checkout -q -b feat/other
    echo foreign2 > lessons.md; git add lessons.md
    echo branchwork >> "$LOG"; commit_checkpoint "$LOG" >/dev/null
    [ "$(git rev-parse --abbrev-ref HEAD)" = feat/other ] || { echo "FAIL S6 wrong branch"; exit 1; }
    git show --name-only --format= HEAD | grep -q lessons.md && { echo "FAIL S6 dragged lessons.md"; exit 1; }

    cd / && rm -rf "$d"
    echo "SELF-CHECK OK: first-of-day · foreign-drag(decisions+lessons) · gitignored-state+secret · forbidden-input · empty-skip · other-panel-branch"
}

main() {
    [ "${1:-}" = "--selfcheck" ] && { _selfcheck; return; }
    [ -n "${1:-}" ] || { echo "usage: session_commit.sh <session_log> [<weekly_plan>] | --selfcheck" >&2; return 1; }
    commit_checkpoint "$@"
}

main "$@"
