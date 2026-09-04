#!/usr/bin/env bash
# session_commit.sh — land session-state in git ON THE BRANCH YOU ARE ON, always.
# Both /update (checkpoint) and /end (--end handoff) go through here: one guard, one implementation.
#
# Founder decision, 2026-09-04: *«il log di sessione si committa dove sei, sul branch corrente,
# sempre. Niente spool, niente rinvii, niente worktree principale sul default»*. An `/end` that
# postpones instead of committing is an `/end` that did not work — measured over three weeks of
# deferral machinery whose only reliable output was a working tree left dirty and a reassuring
# message. The spool, the sibling-worktree hand-off and the "wait for the next default-branch
# session" rule are removed; a session log belongs to the branch the session happened on.
#
# Commit hygiene, enforced here so a model following the skill can't skip it:
#   • pathspec-ONLY (never `git add -A`), absent paths dropped first because `git add -- a missing`
#     stages NOTHING: parallel panels sharing one tree never drag each other's uncommitted work.
#   • forbidden paths refused on input AND on the staged set: `state/current.md` and `.env*` in BOTH
#     modes; `decisions.md`/`lessons.md` in checkpoint mode only — `--end` may promote those.
#   • `git commit -- <paths>`, never a commit of the index: what another panel pre-staged stays
#     staged, exactly as it was, and never rides along.
#   • branch reported, never changed; never a push; nothing ever left staged.
# THREE declared refusals, exit 2, one line each, never silent and never a copy elsewhere: a
# detached HEAD, a repo with no commit at all, and `polaris.commit-policy no-direct-default` while
# sitting on the default branch. In all three the files stay exactly where the session wrote them.
#   session_commit.sh <log> [<plan>] | --end <path>... | --selfcheck
set -uo pipefail

_forbidden() {
    local mode="$1" path="$2"
    case "$path" in *state/current.md) return 0 ;; *.env|*.env.*) return 0 ;; esac
    [ "$mode" = end ] && return 1
    case "$(basename "$path")" in decisions.md|lessons.md) return 0 ;; esac
    return 1
}

_default_branch() {
    local d c
    d="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
    if [ -z "$d" ]; then
        for c in main master; do
            git show-ref -q --verify "refs/heads/$c" && { d="$c"; break; }
        done
    fi
    echo "${d:-main}"
}

# `git add -- a b missing` stages NOTHING and exits 128, so one absent optional file landed the whole
# handoff nowhere. `/end` names five paths and usually wrote two: the normal case, not the edge.
_present() { local p; for p in "$@"; do [ -e "$p" ] && printf '%s\n' "$p"; done; return 0; }

# `/end` names its files with ABSOLUTE paths and git refuses a pathspec it cannot resolve against
# the worktree. Everything downstream assumes a repo-relative path, so it is normalised once, here,
# at the only door in.
_relativise() {
    local top; top="$(git rev-parse --show-toplevel 2>/dev/null)"
    local p; for p in "$@"; do
        case "$p" in "$top"/*) printf '%s\n' "${p#"$top"/}" ;; *) printf '%s\n' "$p" ;; esac
    done
}

# The three refusals. Prints the reason and returns 2; returns 0 when this tree may commit.
# A repository may DECLARE that its default branch is never committed to directly (branch
# protection, or a rule the contract states). Declared, never guessed: asking the remote would make
# every offline run either hang or fail open.
_refused() {
    local branch="$1"
    if ! git rev-parse -q --verify HEAD >/dev/null 2>&1; then
        echo "session_commit: NOT committed — this repo has no commit yet; make its first commit by hand, then re-run. The files stay where you wrote them." >&2
        return 2
    fi
    if ! git symbolic-ref -q HEAD >/dev/null 2>&1; then
        echo "session_commit: NOT committed — HEAD is detached, a commit here would be reachable only through the reflog; switch to a branch and re-run. The files stay where you wrote them." >&2
        return 2
    fi
    [ "$branch" = "$(_default_branch)" ] || return 0
    case "$(git config --get polaris.commit-policy 2>/dev/null)" in
        no-direct-default|no-direct|deferred)
            echo "session_commit: NOT committed — this repo declares polaris.commit-policy against a direct commit on ${branch}; commit the session files from a branch. They stay where you wrote them." >&2
            return 2 ;;
    esac
    return 0
}

# Stage exactly these paths, refuse a forbidden one that slipped in through a glob, commit with an
# explicit pathspec so a foreign staged file cannot ride along, and never leave anything staged.
_stage_and_commit() {
    local mode="$1" branch="$2"; shift 2
    git add -- "$@" 2>/dev/null || true
    local staged; staged="$(git diff --cached --name-only -- "$@")"
    [ -n "$staged" ] || { echo "session_commit: no session-state change on ${branch}, skip"; return 0; }
    local f; while IFS= read -r f; do
        _forbidden "$mode" "$f" && { git restore --staged -- "$f" 2>/dev/null || git reset -q -- "$f" 2>/dev/null
            echo "session_commit: ABORT — forbidden file staged (${f})" >&2; return 2; }
    done <<< "$staged"
    local login msg; login="$(git config --local --get polaris.login 2>/dev/null || echo session)"
    [ "$mode" = end ] && msg="chore(polaris): session handoff $(date +%F) @${login}" \
                      || msg="chore(session): checkpoint @${login} $(date +%F)"
    if git commit -q -m "$msg" -- "$@"; then
        echo "session_commit: committed on ${branch} — ${staged//$'\n'/, }"
        return 0
    fi
    # Never claim success on a failed commit (a hook refusing, missing identity, an index lock). And
    # never leave it STAGED either: the files our own `git add` staged would otherwise be swallowed
    # by the next commit that carries no pathspec. Never `--no-verify`: a hook's veto is a veto.
    git restore --staged -- "$@" 2>/dev/null || git reset -q -- "$@" 2>/dev/null || true
    echo "session_commit: commit REFUSED on ${branch} — index restored, the files are still in the working tree (${staged//$'\n'/, })" >&2
    return 1
}

_commit() {
    local mode="$1"; shift
    local rel=() p
    while IFS= read -r p; do [ -n "$p" ] && rel+=("$p"); done < <(_relativise "$@")
    [ ${#rel[@]} -gt 0 ] && set -- "${rel[@]}"
    for p in "$@"; do
        _forbidden "$mode" "$p" && { echo "session_commit: refuse forbidden path ${p}" >&2; return 2; }
    done
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "session_commit: not a git repo, skip"; return 0; }
    local branch; branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
    _refused "$branch" || return 2
    local here=(); while IFS= read -r p; do [ -n "$p" ] && here+=("$p"); done < <(_present "$@")
    [ ${#here[@]} -gt 0 ] || { echo "session_commit: none of the named files exist yet, skip"; return 0; }
    _stage_and_commit "$mode" "$branch" "${here[@]}"
}

commit_checkpoint() { _commit checkpoint "$@"; }
commit_end() { _commit end "$@"; }

main() {
    # The adversarial fixtures live in their own file: this one carries the guard, not its proof.
    [ "${1:-}" = "--selfcheck" ] && {
        exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/session_commit_selfcheck.sh"; }
    if [ "${1:-}" = "--end" ]; then
        shift
        [ -n "${1:-}" ] || { echo "usage: session_commit.sh --end <path>..." >&2; return 1; }
        commit_end "$@"; return
    fi
    [ -n "${1:-}" ] || { echo "usage: session_commit.sh <session_log> [<weekly_plan>] | --end <path>... | --selfcheck" >&2; return 1; }
    commit_checkpoint "$@"
}

# Sourced as a library by its own selfcheck; run as a command by everyone else.
[ "${SESSION_COMMIT_LIB:-}" = 1 ] || main "$@"
