#!/usr/bin/env bash
# lane_phase.sh — ask git-power what phase this lane is in, and refuse to ask when the question
# has no meaning here.
#
# `/end` calls `cantiere.py phase post-push` twice: once to classify the lane before the handoff,
# once after it. On a repo with NO remote that command answered «push presente ma nessuna PR
# verificabile» (live proof 2026-09-03) — a refusal that reads like a problem with the branch and
# is really a question that cannot be asked: nothing was pushed anywhere, because there is nowhere
# to push. Guarding it in prose means guarding it twice and forgetting it once, so the guard is
# here, in the one place both call sites go through.
#
#   lane_phase.sh [<repo>]   # default: the current directory
#   lane_phase.sh --selfcheck
set -uo pipefail

_git_power() {
    local gp="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/git-power/scripts/cantiere.py"
    [ -f "$gp" ] || gp="$HOME/.agents/skills/git-power/scripts/cantiere.py"
    [ -f "$gp" ] && echo "$gp"
}

phase() {
    local repo="${1:-$PWD}"
    git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
        echo "lane_phase: non è un checkout git — nessuna classificazione della lane"; return 0; }
    [ -n "$(git -C "$repo" remote 2>/dev/null)" ] || {
        echo "nessun remote: push non applicabile — nessuna classificazione della lane"; return 0; }
    local gp; gp="$(_git_power)"
    [ -n "$gp" ] || { echo "NOTA: git-power non installato — nessuna classificazione della lane"; return 0; }
    python3 "$gp" phase post-push --repo "$repo"
}

# Every branch the guard introduces gets an input that forces it. A probe that only walks the
# happy path proves the script ran, not that it guards anything.
_selfcheck() {
    local d out pass=0 fail=0
    d="$(mktemp -d)"
    want() {  # $1 name · $2 expected substring · $3 expected exit
        local rc; out="$(phase "$d" 2>&1)"; rc=$?
        if [ "$rc" = "$3" ] && case "$out" in *"$2"*) true ;; *) false ;; esac
        then pass=$((pass+1)); echo "  ok   $1"
        else fail=$((fail+1)); echo "  FAIL $1 (rc=$rc want=$3) :: $out"; fi
    }
    want "a directory that is not a checkout is not a lane" "non è un checkout git" 0
    git -C "$d" init -q -b main .; git -C "$d" config user.email t@t; git -C "$d" config user.name t
    echo x > "$d/a"; git -C "$d" add a; git -C "$d" commit -qm init
    want "no remote: the question cannot be asked" "nessun remote" 0
    git -C "$d" remote add origin "$d/../bare.git"
    CLAUDE_PLUGIN_ROOT="$d/absent" HOME="$d/absent" want \
        "a remote and no git-power degrades, it does not crash" "git-power non installato" 0
    rm -rf "$d"
    echo "lane_phase selfcheck: $pass passed, $fail failed"
    [ "$fail" = "0" ]
}

[ "${1:-}" = "--selfcheck" ] && { _selfcheck; exit; }
phase "${1:-$PWD}"
