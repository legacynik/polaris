#!/usr/bin/env bash
# install-hook.sh — wires gate.sh into the target repo: hooks.PreToolUse on Bash,
# the .real-test/enabled marker (explicit opt-in), .gitignore for ephemeral files.
#
# The settings.json merge is done ONLY in python3 (`json.load`/`json.dump`),
# never by appending text — that is exactly the bug class measured in G2 item 3
# ("an installer appended the Polaris block at the END of a pre-existing
# pre-commit hook that ended with exit 0: the appended block was unreachable
# and the gate NEVER ran"). jq is fine as an alternative if preferred, but
# here it is not a requirement: python3 is already gate.sh's only dependency.
#
# Usage:
#   install-hook.sh --repo <path> [--yes]     # install (idempotent)
#   install-hook.sh --repo <path> --verify    # prove it is wired AND working
#   install-hook.sh --selfcheck

set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="$DIR/gate.sh"
GITHOOK="$DIR/git-hook.sh"
# The marker text is matched by hooks already installed in other repos: keep it verbatim.
MARKER="# real-test-git-hook-v1 (installato da install-hook.sh, non modificare a mano)"

_merge_settings() {
  local settings="$1" gate="$2"
  python3 - "$settings" "$gate" <<'PY'
import json, sys, pathlib
path, gate = pathlib.Path(sys.argv[1]), sys.argv[2]
data = {}
if path.exists() and path.read_text().strip():
    data = json.loads(path.read_text())
data.setdefault("hooks", {}).setdefault("PreToolUse", [])
data["hooks"]["PreToolUse"] = [
    e for e in data["hooks"]["PreToolUse"]
    if gate not in [h.get("command") for h in e.get("hooks", [])]
]
data["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [{"type": "command", "command": gate}]})
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

_hooks_dir() {
  # `git rev-parse --git-path hooks` returns a relative path for a normal repo, but
  # ABSOLUTE for a worktree (it points at the main repo's SHARED hooks
  # — correct: a hook installed once applies to all worktrees).
  local repo="$1" p
  p=$(git -C "$repo" rev-parse --git-path hooks)
  case "$p" in
    /*) echo "$p" ;;
    *) echo "$repo/$p" ;;
  esac
}

_gitignore_add() {
  local repo="$1" entry="$2" gi="$1/.gitignore"
  touch "$gi"
  grep -qxF "$entry" "$gi" || echo "$entry" >> "$gi"
}

# Real git hook (pre-commit/pre-push) — root-cause fix for EVAL-real-test-bypass.md
# routes B/C (gate.sh alone is bypassed by spoofing tool_name or wrapping the command;
# a real git hook ALWAYS runs on a real commit/push, it does not sniff a payload).
# Chain, never clobber: if a pre-existing hook (husky, another tool) is already there and is not
# ours, it is preserved and called FIRST — this is exactly the append-at-the-end installer
# bug measured in G2 item 3 ("unreachable block"), avoided here by
# calling the pre-existing hook at the top, not at the tail of a file that may already end with
# an implicit exit.
_install_git_hook() {
  local hooks_dir="$1" name="$2" hook
  hook="$hooks_dir/$name"
  if [ -f "$hook" ] && ! grep -qF "$MARKER" "$hook"; then
    cp "$hook" "$hook.bak-$(date -u +%Y%m%d-%H%M%S)"
    mv "$hook" "$hooks_dir/$name.real-test-chain"
    chmod +x "$hooks_dir/$name.real-test-chain"
  fi
  cat > "$hook" <<EOF
#!/usr/bin/env bash
$MARKER
set -eu
chain="\$(dirname "\$0")/$name.real-test-chain"
[ -x "\$chain" ] && "\$chain" "\$@"
exec "$GITHOOK" "$name"
EOF
  chmod +x "$hook"
}

install() {
  local repo="$1" settings="$1/.claude/settings.json" hooks_dir
  if [ -f "$settings" ]; then
    cp "$settings" "$settings.bak-$(date -u +%Y%m%d-%H%M%S)"
  fi
  _merge_settings "$settings" "$GATE"
  hooks_dir=$(_hooks_dir "$repo")
  mkdir -p "$hooks_dir"
  _install_git_hook "$hooks_dir" "pre-commit"
  _install_git_hook "$hooks_dir" "pre-push"
  mkdir -p "$repo/.real-test"
  touch "$repo/.real-test/enabled"
  _gitignore_add "$repo" ".real-test/verdicts/"
  _gitignore_add "$repo" ".real-test/bypass.log"
  echo "installed: Claude Code hook wired in $settings, real git hooks in $hooks_dir/{pre-commit,pre-push}, marker .real-test/enabled created."
  echo "verify:     install-hook.sh --repo '$repo' --verify"
}

verify() {
  local repo="$1" settings="$1/.claude/settings.json" hooks_dir
  python3 -c "
import json,sys
d = json.load(open('$settings'))
cmds = [h.get('command') for e in d.get('hooks',{}).get('PreToolUse',[]) for h in e.get('hooks',[])]
sys.exit(0 if '$GATE' in cmds else 1)
" || { echo "VERIFY FAIL: $GATE is not in hooks.PreToolUse of $settings"; return 1; }
  [ -f "$repo/.real-test/enabled" ] || { echo "VERIFY FAIL: marker .real-test/enabled missing"; return 1; }
  hooks_dir=$(_hooks_dir "$repo")
  for name in pre-commit pre-push; do
    [ -x "$hooks_dir/$name" ] && grep -qF "$MARKER" "$hooks_dir/$name" \
      || { echo "VERIFY FAIL: $hooks_dir/$name is not our hook (installer B/C not closed)"; return 1; }
  done
  bash "$GATE" --selfcheck || { echo "VERIFY FAIL: gate.sh --selfcheck does not pass"; return 1; }
  bash "$GITHOOK" --selfcheck || { echo "VERIFY FAIL: git-hook.sh --selfcheck does not pass"; return 1; }
  echo "VERIFY OK: Claude Code hook + real git hooks wired, marker present, selfchecks pass."
}

_selfcheck() {
  local td repo hooks_dir
  td=$(mktemp -d); repo="$td/r"; mkdir -p "$repo"
  git init -q "$repo"

  install "$repo" >/dev/null
  grep -q "$GATE" "$repo/.claude/settings.json" || { echo "FAIL: not wired"; exit 1; }
  [ -f "$repo/.real-test/enabled" ] || { echo "FAIL: marker missing"; exit 1; }
  grep -qxF ".real-test/verdicts/" "$repo/.gitignore" || { echo "FAIL: gitignore entry missing"; exit 1; }

  hooks_dir=$(_hooks_dir "$repo")
  [ -x "$hooks_dir/pre-commit" ] && grep -qF "$MARKER" "$hooks_dir/pre-commit" \
    || { echo "FAIL: git pre-commit hook not installed/executable (closes EVAL-bypass B/C)"; exit 1; }
  [ -x "$hooks_dir/pre-push" ] || { echo "FAIL: git pre-push hook not installed"; exit 1; }

  install "$repo" >/dev/null   # idempotence: no duplicated entry/chain
  n=$(python3 -c "import json; d=json.load(open('$repo/.claude/settings.json')); print(sum(1 for e in d['hooks']['PreToolUse'] for h in e['hooks'] if h['command']=='$GATE'))")
  [ "$n" = "1" ] || { echo "FAIL: repeated install duplicated the entry ($n copies)"; exit 1; }
  [ -f "$hooks_dir/pre-commit.real-test-chain" ] && { echo "FAIL: reinstall over an already-ours hook chained itself"; exit 1; }

  verify "$repo" >/dev/null || { echo "FAIL: verify must pass"; exit 1; }

  # pre-existing hook (e.g. husky) -> must be CHAINED, never silently overwritten
  # (G2 item 3: "appended block unreachable" — here it is SOMEONE ELSE'S hook that must
  # stay reachable, the mirror image of the same bug)
  repo="$td/r2"; mkdir -p "$repo"; git init -q "$repo"
  hooks_dir=$(_hooks_dir "$repo")
  mkdir -p "$hooks_dir"
  cat > "$hooks_dir/pre-commit" <<EOF
#!/usr/bin/env bash
touch "\$(git rev-parse --show-toplevel)/sentinel-preexisting"
EOF
  chmod +x "$hooks_dir/pre-commit"
  install "$repo" >/dev/null
  [ -x "$hooks_dir/pre-commit.real-test-chain" ] || { echo "FAIL: pre-existing hook not chained, 'unreachable' risk"; exit 1; }
  grep -q "sentinel-preexisting" "$hooks_dir/pre-commit.real-test-chain" \
    || { echo "FAIL: the pre-existing hook's content was lost"; exit 1; }
  # The hook's exit code is not the subject of this test (a gate may legitimately exit ≠0):
  # the subject is the EFFECT. But it is not discarded — it is captured, so the intent is visible.
  hook_rc=0; (cd "$repo" && "$hooks_dir/pre-commit") >/dev/null 2>&1 || hook_rc=$?
  [ -f "$repo/sentinel-preexisting" ] || { echo "FAIL: pre-existing hook chained but NEVER executed (unreachable)"; exit 1; }

  rm -rf "$td"
  echo "SELFCHECK OK — install/idempotence/verify/git-hook-installed/pre-existing-hook-chained, 6 assertions"
}

repo="."; mode="install"
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) repo="$2"; shift 2 ;;
    --verify) mode="verify"; shift ;;
    --yes) shift ;;
    --selfcheck) mode="selfcheck"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

case "$mode" in
  selfcheck) _selfcheck ;;
  verify) verify "$(cd "$repo" && pwd)" ;;
  install) install "$(cd "$repo" && pwd)" ;;
esac
