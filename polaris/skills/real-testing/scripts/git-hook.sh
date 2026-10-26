#!/usr/bin/env bash
# git-hook.sh — installed by install-hook.sh as the REAL .git/hooks/pre-commit and
# .git/hooks/pre-push. Root-cause fix for EVAL-real-test-bypass.md §4
# routes B and C: gate.sh alone is bypassed by spoofing tool_name or wrapping
# "git commit" in a wrapper/alias, because it pattern-matches a tool
# PAYLOAD — an event the environment CAN forge. This script guesses nothing
# from the command: it runs inside git's own hook machinery,
# so git ALWAYS invokes it when a real commit/push happens, regardless of
# which tool/harness/terminal asked for it. It synthesizes the payload gate.sh
# expects (it knows for sure, it need not sniff) and delegates all the
# decision logic (marker/branch/hash/verdict) to it — same rule, one place,
# never duplicated (root-cause fix, not a guard per caller).
#
# ponytail: does not defend against `git commit --no-verify` / `git push --no-verify`
# — git itself skips pre-commit/pre-push by contract when asked, no
# hook can see an event that is explicitly hidden from it. Upgrade
# path: server-side pre-receive or branch protection on a CI check that validates
# the pushed ref regardless of how it was created (not built here
# — see references/merge.md "Not for" and the note in the review's non_fatto).
#
# Usage: git-hook.sh <pre-commit|pre-push>   # installed by install-hook.sh
#        git-hook.sh --selfcheck

set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run() {
  printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh"
}

_selfcheck() {
  local td repo rc
  td=$(mktemp -d); repo="$td/r"; mkdir -p "$repo"
  git init -q "$repo"; git -C "$repo" symbolic-ref HEAD refs/heads/main
  git -C "$repo" config user.email t@t; git -C "$repo" config user.name t
  printf 'x=1\n' > "$repo/a.py"; git -C "$repo" add .; git -C "$repo" commit -q -m base
  mkdir -p "$repo/.real-test"; touch "$repo/.real-test/enabled"
  git -C "$repo" checkout -q -b feat/x

  # 1) no verdict on a non-default branch -> block, exactly like gate.sh alone
  printf 'y=2\n' >> "$repo/a.py"; git -C "$repo" add a.py
  set +e; (cd "$repo" && "$DIR/git-hook.sh" pre-commit) >/dev/null 2>&1; rc=$?; set -e
  [ "$rc" -ne 0 ] || { echo "FAIL: without a verdict it must block"; exit 1; }

  # 2) valid verdict present -> allow (same outcome as gate.sh via CLI)
  HASH=$(python3 "$DIR/perimeter.py" --repo "$repo" --head STAGED --hash-only)
  mkdir -p "$repo/.real-test/verdicts"
  python3 - "$repo" "$HASH" <<'PY'
import json, sys
repo, h = sys.argv[1], sys.argv[2]
json.dump({"verdetto": "NOT-MERGEABLE", "content_hash": h, "matrix": [
    {"file": "a.py", "class": "symbol", "evidence": "not-applicable", "branches_exercised": []}],
    "raccolto": [], "new_branches_da_coprire": []},
    open(f"{repo}/.real-test/verdicts/{h}.json", "w"))
PY
  set +e; (cd "$repo" && "$DIR/git-hook.sh" pre-commit) >/dev/null 2>&1; rc=$?; set -e
  [ "$rc" -ne 0 ] || { echo "FAIL: NOT-MERGEABLE must stay blocked"; exit 1; }
  python3 -c "import json; d=json.load(open('$repo/.real-test/verdicts/$HASH.json')); d['verdetto']='MERGEABLE-CON-GAP'; d['raccolto']=[{'tipo':'tetto','nota':'ok'}]; json.dump(d, open('$repo/.real-test/verdicts/$HASH.json','w'))"
  set +e; (cd "$repo" && "$DIR/git-hook.sh" pre-commit) >/dev/null 2>&1; rc=$?; set -e
  [ "$rc" -eq 0 ] || { echo "FAIL: a valid verdict must allow, rc=$rc"; exit 1; }

  rm -rf "$td"
  echo "SELFCHECK OK — 2 branches proven (blocks without verdict/allows with valid verdict)"
}

case "${1:-}" in
  --selfcheck) _selfcheck ;;
  pre-commit|pre-push) run ;;
  *) run ;;
esac
