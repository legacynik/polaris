#!/usr/bin/env bash
# session_commit.sh — land session-state in git with commit-hygiene enforced IN CODE, not prose.
# Both /update (checkpoint) and /end (--end handoff) go through here: one guard, one implementation.
#
# Single-physical-path rule (founder decision 2026-07-25, supersedes Option A of 2026-07-19):
# session-state lives in the MAIN worktree and commits ONLY from the default branch. On any other
# branch it is DEFERRED — the file stays on disk as the single copy and the next default-branch
# session lands it. Committing a daily session file on a feature branch strands it (invisible to
# `/start` until that branch merges — observed: handoffs lost on branches never merged) and N branch
# copies of one append-only file diverge.
#
# Commit hygiene, enforced here so a model following the skill can't skip it:
#   • pathspec-ONLY (never `git add -A`): staging just the named file(s) means parallel panels sharing
#     one working tree can never drag each other's uncommitted work.
#   • forbidden paths refused (on input AND on the staged set): state/current.md (gitignored
#     convergence point) and .env* (secrets) in BOTH modes; decisions.md / lessons.md in checkpoint
#     mode only — they are `/end`'s vetted promotion, so `--end` may commit them.
#   • branch is reported, never changed; never a push.
#
# ponytail: known ceiling of DEFER — the pending append sits in a TRACKED path, so if the tree later
# switches back to the default branch git may REFUSE the checkout (it never clobbers: the append is
# safe on disk, proven by tests/real_session_commit.sh R7). Recovery is manual: copy the file aside,
# switch, re-append, run this script. Upgrade path if that friction shows up in practice: spool the
# pending content under `$(git rev-parse --git-common-dir)/polaris-deferred/` (branch-independent,
# shared by every worktree) and drain it on the next default-branch run.
#
#   session_commit.sh <session_log> [<weekly_plan>]      # /update checkpoint
#   session_commit.sh --end <path>...                    # /end handoff (may include the ledgers)
#   session_commit.sh --selfcheck                        # adversarial gate tests, no real repo touched
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
_wt_on_default() {
    local def="$1" wt="" line
    while IFS= read -r line; do
        case "$line" in
            worktree\ *) wt="${line#worktree }" ;;
            branch\ refs/heads/"$def") [ -n "$wt" ] && { echo "$wt"; return 0; } ;;
        esac
    done < <(git worktree list --porcelain 2>/dev/null)
    return 1
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

_commit() {
    local mode="$1"; shift
    local p; for p in "$@"; do
        _forbidden "$mode" "$p" && { echo "session_commit: refuse forbidden path ${p}" >&2; return 2; }
    done
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "session_commit: not a git repo, skip"; return 0; }
    local branch def; branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"; def="$(_default_branch)"
    if [ "$branch" != "$def" ]; then
        local wt; wt="$(_wt_on_default "$def")" || wt=""
        if [ -n "$wt" ] && [ -d "$wt" ]; then
            # Hand the work to the worktree that is already on the default branch. The file itself
            # travels through the spool, because that worktree holds the default branch's copy.
            _spool_put "$@" || { echo "session_commit: spool write failed — file stays on disk" >&2; return 1; }
            echo "session_commit: on '${branch}' — committing from the ${def} worktree at ${wt}"
            ( cd "$wt" && _commit "$mode" ) && return 0
            echo "session_commit: the ${def} worktree refused it — entry is in the spool, not lost" >&2
            return 1
        fi
        _spool_put "$@" && {
            echo "session_commit: on '${branch}' (not ${def}) and no ${def} worktree — spooled to $(_spool_dir), drains on the next ${def} run"
            return 0
        }
        echo "session_commit: on '${branch}' and the spool is unwritable — file stays on disk, commit it by hand" >&2
        return 1
    fi
    local extra; extra="$(_spool_drain "$mode")" && [ -n "$extra" ] && {
        echo "$extra" | head -1 >/dev/null
        while IFS= read -r f; do case "$f" in session_commit:*) ;; "") ;; *) set -- "$@" "$f" ;; esac; done <<< "$extra"
    }
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
        # never claim success on a failed commit (hook rejection, missing identity, index lock, bad pathspec):
        # the skill would report the handoff landed while it sits uncommitted.
        echo "session_commit: git commit FAILED on ${branch} — NOT landed (${staged//$'\n'/, })" >&2
        return 1
    fi
}

commit_checkpoint() { _commit checkpoint "$@"; }
commit_end() { _commit end "$@"; }

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

    # S6 off-default branch: DEFER — no commit here, the checkpoint stays on disk as the single copy
    git checkout -q -b feat/other
    echo foreign2 > lessons.md; git add lessons.md
    echo branchwork >> "$LOG"; before="$(git rev-parse HEAD)"
    commit_checkpoint "$LOG" > out.txt 2>&1; [ $? -eq 0 ] || { echo "FAIL S6 defer must exit 0"; exit 1; }
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S6 committed on a feature branch"; exit 1; }
    grep -q deferred out.txt || { echo "FAIL S6 defer not reported"; exit 1; }
    git diff --quiet -- "$LOG" && { echo "FAIL S6 checkpoint lost from disk"; exit 1; }

    # S7 the deferred checkpoint lands on the next default-branch session, content intact
    git checkout -q "$DEF"
    commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q branchwork || { echo "FAIL S7 deferred content never landed"; exit 1; }

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

    # S10 --end obeys the same default-branch guard (a handoff must never ride a feature branch)
    git checkout -q feat/other; echo "## d2" >> decisions.md; before="$(git rev-parse HEAD)"
    commit_end "$LOG" decisions.md >/dev/null 2>&1
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S10 --end committed on a feature branch"; exit 1; }
    git checkout -q -- decisions.md; git checkout -q "$DEF"   # harness cleanup: the deferred edit stays uncommitted by design

    # S11 default branch comes from origin/HEAD, not the literal name "main"
    git checkout -q -b trunk; git update-ref refs/remotes/origin/trunk HEAD
    git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk
    echo trunkwork >> "$LOG"; commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q trunkwork || { echo "FAIL S11 did not commit on origin/HEAD default (trunk)"; exit 1; }
    git checkout -q "$DEF"; echo mainwork >> "$LOG"; before="$(git rev-parse HEAD)"
    commit_checkpoint "$LOG" >/dev/null
    [ "$(git rev-parse HEAD)" = "$before" ] || { echo "FAIL S11 committed on $DEF while origin/HEAD says trunk"; exit 1; }

    # S12 no origin/HEAD and the default is `master` → still commits (client repos are not all `main`)
    git symbolic-ref -d refs/remotes/origin/HEAD; git update-ref -d refs/remotes/origin/trunk
    git branch -m "$DEF" master; echo masterwork >> "$LOG"
    commit_checkpoint "$LOG" >/dev/null
    git show HEAD:"$LOG" | grep -q masterwork || { echo "FAIL S12 deferred forever on a master-default repo"; exit 1; }

    cd / && rm -rf "$d"
    echo "SELF-CHECK OK: first-of-day · foreign-drag(decisions+lessons) · gitignored-state+secret · forbidden-input · empty-skip · off-default-defer · deferred-lands-later · end-promotes-ledgers · end-refuses-state+secret · end-defers-off-default · origin/HEAD-default · master-default-repo"
}

main() {
    [ "${1:-}" = "--selfcheck" ] && { _selfcheck; return; }
    if [ "${1:-}" = "--end" ]; then
        shift
        [ -n "${1:-}" ] || { echo "usage: session_commit.sh --end <path>..." >&2; return 1; }
        commit_end "$@"; return
    fi
    [ -n "${1:-}" ] || { echo "usage: session_commit.sh <session_log> [<weekly_plan>] | --end <path>... | --selfcheck" >&2; return 1; }
    commit_checkpoint "$@"
}

main "$@"
