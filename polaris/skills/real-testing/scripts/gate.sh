#!/usr/bin/env bash
# gate.sh — shared detection hook: called both by Claude Code's PreToolUse
# (fast-path, blocks before the command starts) and by git-hook.sh (the real
# git hook — pre-commit/pre-push, the anchor that CANNOT be bypassed by changing tool_name
# or wrapping the command in a script, see EVAL-real-test-bypass.md routes B/C:
# git-hook.sh synthesizes the payload because it already knows, from the git event itself,
# that a commit is happening — it does not guess from a substring).
#
# Fixes the bug measured in CRITIC-1 (§1 row 12) on the twin hook of
# parallel-issue-flow: that one uses `sed -E 's/.../\s.../'` — `\s` is a GNU
# extension missing from macOS's BSD sed, so the match always fails and the gate is
# EXIT 0 (allow) for any command. Here parsing is ONLY `python3 -c
# "import json"` on stdin — never regex on JSON.
#
# Active only if the repo has `.real-test/enabled` (created by install-hook.sh) —
# explicit opt-in, no repo is gated by surprise.
#
# Exit: 0 = allow, 2 = block (stderr goes to the model).
#
# Usage: gate.sh < payload.json          # as called by Claude Code / git-hook.sh
#        gate.sh --selfcheck             # exercises every branch on throwaway fixtures

set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_log_bypass() {
  local repo="$1" hash="$2" reason="$3"
  mkdir -p "$repo/.real-test"
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${USER:-unknown}" "$hash" \
    "$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null)" "$reason" >> "$repo/.real-test/bypass.log"
}

_default_branch() {
  # NOT a pipe: `git ... | sed ...` masks git's failure behind sed's
  # exit status (which on empty stdin still exits 0) — the "echo main"
  # fallback never fired, found by running this branch in selfcheck for the
  # first time (no repo with origin/HEAD -> _default_branch returned an empty
  # string, never "main": the default-branch exemption NEVER fired on a local
  # repo without a remote, unlike a real clone).
  local ref
  ref=$(git -C "$1" symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null) && { echo "${ref##*/}"; return; }
  echo main
}

run_gate() {
  local input tool_name cmd repo branch hash verdict_file verdetto
  input="$(cat)" || return 0
  [ -z "$input" ] && return 0

  tool_name=$(printf '%s' "$input" | python3 -c \
    "import json,sys; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null) || return 0
  [ "$tool_name" != "Bash" ] && return 0

  cmd=$(printf '%s' "$input" | python3 -c \
    "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null) || return 0
  # real `git commit` invocation (command start or after ; && || |), not the
  # string quoted inside an echo/message (red R2, merge 2026-08-16).
  # grep WITHOUT -q: with pipefail, a matching -q closes stdin and kills printf
  # with SIGPIPE — the pipeline "fails" exactly on real matches.
  printf '%s' "$cmd" | grep -E '(^|[;&|][[:space:]]*|&&[[:space:]]*|\|\|[[:space:]]*)git[[:space:]]+commit([[:space:]]|$)' >/dev/null || return 0

  repo=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
  [ -f "$repo/.real-test/enabled" ] || return 0

  hash=$(python3 "$DIR/perimeter.py" --repo "$repo" --head STAGED --hash-only 2>/dev/null) || return 0
  branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

  # Default-branch exemption (cross-panel handoff, user CLAUDE.md): it stays
  # an exemption, NEVER silent — G2#8 ("the gate, when it cannot decide, approves
  # silently") and R8 (208 untracked bypasses) apply to this route too,
  # found open and unlogged by EVAL-real-test-bypass.md route A.
  if [ "$branch" = "$(_default_branch "$repo")" ]; then
    _log_bypass "$repo" "$hash" "default-branch-exempt"
    echo "real-test: default branch ($branch) exempt from the gate — logged in .real-test/bypass.log (never silent)." >&2
    return 0
  fi

  if [ "${REAL_TEST_BYPASS_GATE:-0}" = "1" ]; then
    _log_bypass "$repo" "$hash" "explicit-bypass"
    echo "real-test: BYPASS used and logged in .real-test/bypass.log (never silent)." >&2
    return 0
  fi

  verdict_file="$repo/.real-test/verdicts/$hash.json"
  if [ ! -f "$verdict_file" ]; then
    cat >&2 <<MSG
real-test: gate BLOCKED. No verdict for the current tree ($hash).
  1. python3 $DIR/verdict.py new --repo "$repo" --out "$verdict_file"
  2. Fill in matrix/raccolto following references/merge.md, then:
     python3 $DIR/verdict.py validate "$verdict_file" --repo "$repo"
  3. Retry the commit.
Bypass (emergency only, it is logged): REAL_TEST_BYPASS_GATE=1
MSG
    return 2
  fi

  if ! python3 "$DIR/verdict.py" validate "$verdict_file" --repo "$repo" >&2; then
    echo "real-test: verdict present but INVALID (see FAIL above). Fix it and retry." >&2
    return 2
  fi

  verdetto=$(python3 -c "import json; print(json.load(open('$verdict_file')).get('verdetto'))")
  if [ "$verdetto" = "NOT-MERGEABLE" ]; then
    echo "real-test: verdict is NOT-MERGEABLE for $hash. The commit stays blocked until it goes back up to MERGEABLE/MERGEABLE-CON-GAP." >&2
    return 2
  fi
  return 0
}

_selfcheck() {
  local td repo out rc
  td=$(mktemp -d)
  repo="$td/r"
  mkdir -p "$repo" && git init -q "$repo"
  git -C "$repo" symbolic-ref HEAD refs/heads/main   # deterministic: the _default_branch fallback is "main"
  git -C "$repo" config user.email t@t; git -C "$repo" config user.name t
  printf 'x=1\n' > "$repo/a.py"; git -C "$repo" add .; git -C "$repo" commit -q -m base

  # 1) no .real-test/enabled marker -> silent allow (skill not installed here)
  printf 'y=2\n' >> "$repo/a.py"; git -C "$repo" add .
  out=$(cd "$repo" && printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh")
  echo "$out" | grep -q . && { echo "FAIL: without marker it must be silent"; exit 1; }

  mkdir -p "$repo/.real-test"; touch "$repo/.real-test/enabled"

  # 2) marker present, ON THE DEFAULT BRANCH -> allow, BUT logged with a reason (never mute)
  out=$(cd "$repo" && printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh")
  [ -z "$out" ] || { echo "FAIL: default-branch exemption must stay silent on stdout"; exit 1; }
  [ -s "$repo/.real-test/bypass.log" ] || { echo "FAIL: default-branch exemption must be logged (EVAL-bypass route A)"; exit 1; }
  grep -q "default-branch-exempt" "$repo/.real-test/bypass.log" || { echo "FAIL: exemption reason missing from the log"; exit 1; }

  # 3) marker present, non-default branch, no verdict -> block EXIT 2
  git -C "$repo" checkout -q -b feat/x
  set +e
  (cd "$repo" && printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh" 2>/tmp/rt_selfcheck_err)
  rc=$?
  set -e
  [ "$rc" -eq 2 ] || { echo "FAIL: without a verdict it must block with EXIT 2, got $rc"; exit 1; }
  grep -q "BLOCKED" /tmp/rt_selfcheck_err || { echo "FAIL: block message missing"; exit 1; }

  # 4) explicit bypass -> allow BUT logged
  rm -f "$repo/.real-test/bypass.log"
  set +e
  REAL_TEST_BYPASS_GATE=1 bash -c "cd '$repo' && printf '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git commit -m x\"}}' | '$DIR/gate.sh'" >/dev/null 2>&1
  rc=$?
  set -e
  [ "$rc" -eq 0 ] || { echo "FAIL: bypass must allow"; exit 1; }
  grep -q "explicit-bypass" "$repo/.real-test/bypass.log" || { echo "FAIL: bypass must be logged with the reason"; exit 1; }

  # 5) tool_name other than Bash -> silent allow on the FAST-PATH (defence 1 of 2 —
  #    the real defence is the real git hook, not simulable here without installing it:
  #    see install-hook.sh --selfcheck and bypass-test.md #7 for the end-to-end proof)
  out=$(cd "$repo" && printf '{"tool_name":"Edit","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh")
  [ -z "$out" ] || { echo "FAIL: tool_name!=Bash must be silent on the fast-path"; exit 1; }

  rm -rf "$td" /tmp/rt_selfcheck_err
  echo "SELFCHECK OK — 5 branches proven (no-marker/default-branch-logged/block/bypass-logged/other-tool)"
}

if [ "${1:-}" = "--selfcheck" ]; then
  _selfcheck
else
  run_gate
fi
