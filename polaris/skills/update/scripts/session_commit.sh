#!/usr/bin/env bash
# session_commit.sh — land session-state in git with commit-hygiene enforced IN CODE, not prose.
# Both /update (checkpoint) and /end (--end handoff) go through here: one guard, one implementation.
#
# Commit hygiene, enforced here so a model following the skill can't skip it:
#   • pathspec-ONLY (never `git add -A`), absent paths dropped first because `git add -- a missing`
#     stages NOTHING: parallel panels sharing one tree never drag each other's uncommitted work.
#   • forbidden paths refused on input AND on the staged set: `state/current.md` and `.env*` in BOTH
#     modes; `decisions.md`/`lessons.md` in checkpoint mode only — `--end` may promote those.
#   • branch reported, never changed; never a push; nothing ever left staged.
# WHERE it lands (polaris-os#202 AC4, live proof 2026-09-03):
#   • a sibling worktree already on the default branch → spool, and IT commits; this tree keeps no
#     untracked copy — a duplicate left here is exactly the dirt AC4 forbids.
#   • ONE checkout, on any branch → commit HERE: there is no "next default-branch session" to wait for. Before this rule, `/end` left two dirty lines and the next session swallowed the log.
#   • TWO or more checkouts and none on the default, `polaris.commit-policy no-direct-default`, a
#     detached HEAD, or a hook that refuses → `deferred` to the spool `/start` counts, never a
#     forced commit (polaris#12, polaris-os#141, #243).
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

# The spool and the worktree lookup live next door. Sourced, never re-implemented.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/session_spool.sh"

# `git add -- a b missing` stages NOTHING and exits 128, so one absent optional file landed the whole
# handoff nowhere. `/end` names five paths and usually wrote two: the normal case, not the edge.
_present() { local p; for p in "$@"; do [ -e "$p" ] && printf '%s\n' "$p"; done; return 0; }

_drop_landed() {
    local left=() p
    for p in "$@"; do
        [ -f "$p" ] || continue
        if git ls-files --error-unmatch -- "$p" >/dev/null 2>&1
        then left+=("$p")
        else rm -f "$p"; fi
    done
    [ ${#left[@]} -gt 0 ] && echo "session_commit: tracked and still modified here: ${left[*]}"
    return 0
}

_spool_put() {
    local spool; spool="$(_spool_dir)"; [ -n "$spool" ] || return 1
    local p; for p in "$@"; do
        [ -f "$p" ] || continue
        mkdir -p "$spool/$(dirname "$p")" && cp -f "$p" "$spool/$p" || return 1
    done
}

# Drain runs on every default-branch commit: whatever a parked checkout spooled lands here.
_spool_drain() {
    local mode="$1" spool; spool="$(_spool_dir)"
    [ -n "$spool" ] && [ -d "$spool" ] || return 0
    local drained=() f rel
    while IFS= read -r f; do
        rel="${f#$spool/}"
        _forbidden "$mode" "$rel" && continue
        mkdir -p "$(dirname "$rel")"
        # NOT a blind copy. The spooled version is not always a superset: the target may have been
        # appended to after the spool was written, and overwriting would delete that. These files are
        # append-only journals, so reconcile by lines and never lose either side.
        # (Caught by S11 on 2026-08-11: a blind cp silently dropped an entry written after spooling.)
        if [ ! -f "$rel" ]; then
            cp -f "$f" "$rel"
        elif cmp -s "$f" "$rel"; then
            :                                             # already landed, nothing to do
        elif [ -z "$(grep -Fxv -f "$rel" "$f" 2>/dev/null)" ]; then
            :                                             # target already contains every spooled line
        else
            grep -Fxv -f "$rel" "$f" >> "$rel" 2>/dev/null \
                || { echo "session_commit: cannot reconcile ${rel} — left in the spool" >&2; continue; }
        fi
        drained+=("$rel"); rm -f "$f"
    done < <(find "$spool" -type f 2>/dev/null)
    [ ${#drained[@]} -gt 0 ] || return 0
    find "$spool" -type d -empty -delete 2>/dev/null
    echo "session_commit: drained ${#drained[@]} deferred file(s) from the spool"
    printf '%s\n' "${drained[@]}"
}

# `/end` names its files with ABSOLUTE paths, and the sibling-worktree hand-off then asked that
# worktree to `git add` a path outside itself: git refuses, the spool wrote back to the original
# absolute location, and the run reported "no session-state change, skip" while the handoff sat
# uncommitted. Everything downstream — the spool layout, the pathspec, the recursion — assumes a
# repo-relative path, so it is normalised once, here, at the only door in.
_relativise() {
    local top; top="$(git rev-parse --show-toplevel 2>/dev/null)"
    local p; for p in "$@"; do
        case "$p" in "$top"/*) printf '%s\n' "${p#"$top"/}" ;; *) printf '%s\n' "$p" ;; esac
    done
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
    local branch def; branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"; def="$(_default_branch)"
    # Detached HEAD: a commit here is reachable only through the reflog until gc takes it. An UNBORN branch also reports `HEAD` and is NOT this case — there the commit is the repo's first.
    if ! git symbolic-ref -q HEAD >/dev/null 2>&1 && git rev-parse -q --verify HEAD >/dev/null 2>&1; then
        _spool_put "$@" && { _drop_landed "$@"
            echo "session_commit: deferred — HEAD is detached, a commit here would be reachable only through the reflog; spooled to $(_spool_dir)"
            return 0; }
        echo "session_commit: HEAD is detached and the spool is unwritable — commit it by hand" >&2
        return 1
    fi
    if [ "$branch" != "$def" ]; then
        local wt; wt="$(_wt_on_default "$def")" || wt=""
        if [ -n "$wt" ] && [ -d "$wt" ]; then
            # Hand the work to the worktree that is already on the default branch. The file itself
            # travels through the spool, because that worktree holds the default branch's copy.
            # The paths ride along: a recursion with no pathspec commits whatever ANOTHER panel
            # happened to leave staged there the moment the spool drains nothing.
            _spool_put "$@" || { echo "session_commit: spool write failed — file stays on disk" >&2; return 1; }
            echo "session_commit: on '${branch}' — committing from the ${def} worktree at ${wt}"
            ( cd "$wt" && _commit "$mode" "$@" ) && { _drop_landed "$@"; return 0; }
            echo "session_commit: the ${def} worktree refused it — entry is in the spool, not lost" >&2
            return 1
        fi
        [ "$(_wt_count)" -gt 1 ] && { _defer_no_default "$def" "$@"; return $?; }   # polaris#12
        echo "session_commit: on '${branch}' and this repo has one checkout — committing here"
    elif _policy_defers; then
        _spool_put "$@" && {
            _drop_landed "$@"
            echo "session_commit: deferred — this repo forbids a direct commit on ${def} (polaris.commit-policy); spooled to $(_spool_dir), 0 commits"
            return 0
        }
        echo "session_commit: deferred on ${def} and the spool is unwritable — commit it by hand" >&2
        return 1
    fi
    local extra; extra="$(_spool_drain "$mode")" && [ -n "$extra" ] && {
        echo "$extra" | head -1 >/dev/null
        while IFS= read -r f; do case "$f" in session_commit:*) ;; "") ;; *) set -- "$@" "$f" ;; esac; done <<< "$extra"
    }
    local here=(); while IFS= read -r p; do [ -n "$p" ] && here+=("$p"); done < <(_present "$@")
    [ ${#here[@]} -gt 0 ] || { echo "session_commit: none of the named files exist yet, skip"; return 0; }
    set -- "${here[@]}"
    git add -- "$@" 2>/dev/null || true
    local staged; staged="$(git diff --cached --name-only -- "$@")"
    [ -n "$staged" ] || { echo "session_commit: no session-state change on ${branch}, skip"; return 0; }
    local f; while IFS= read -r f; do
        _forbidden "$mode" "$f" && { git reset -q -- "$f" 2>/dev/null; echo "session_commit: ABORT — forbidden file staged (${f})" >&2; return 2; }
    done <<< "$staged"
    local login; login="$(git config --local --get polaris.login 2>/dev/null || echo session)"
    local msg="chore(session): checkpoint @${login} $(date +%F)"
    [ "$mode" = end ] && msg="chore(polaris): session handoff $(date +%F) @${login}"
    # commit with explicit pathspec: only these paths land, even if another panel pre-staged something
    if git commit -q -m "$msg" -- "$@"; then
        echo "session_commit: committed on ${branch} — ${staged//$'\n'/, }"
    else
        # Never claim success on a failed commit (a pre-commit hook refusing, missing identity, an
        # index lock, a bad pathspec). And never leave it STAGED either: the honest error message was
        # already there, but the files our own `git add` staged stayed in the index, so the next
        # commit without a pathspec swallowed the handoff — the AC4 regression, one step later.
        git restore --staged -- "$@" 2>/dev/null || git reset -q -- "$@" 2>/dev/null || true
        _spool_put "$@"
        echo "session_commit: commit REFUSED on ${branch} — index restored, deferred to $(_spool_dir) (${staged//$'\n'/, })" >&2
        return 1
    fi
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
