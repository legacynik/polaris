#!/usr/bin/env bash
# git-hook.sh — installato da install-hook.sh come .git/hooks/pre-commit e
# .git/hooks/pre-push REALI. Root-cause fix di EVAL-real-test-bypass.md §4
# vie B e C: gate.sh da solo si aggira spoofando tool_name o incapsulando
# "git commit" in un wrapper/alias, perche' fa pattern-matching su un PAYLOAD
# di tool — un evento che l'ambiente PUO' falsificare. Questo script non
# indovina niente dal comando: gira dentro la macchina hook di git stessa,
# quindi git lo invoca SEMPRE quando avviene un commit/push reale, a
# prescindere da quale tool/harness/terminale l'ha chiesto. Sintetizza il
# payload che gate.sh si aspetta (lo sa gia' per certo, non lo deve sniffare)
# e delega tutta la logica di decisione (marker/branch/hash/verdetto) a lui —
# stessa regola, un solo posto, mai duplicata (root-cause fix, non un guard
# per ogni chiamante).
#
# ponytail: non difende da `git commit --no-verify` / `git push --no-verify`
# — git stesso salta pre-commit/pre-push per contratto quando richiesto, nessun
# hook puo' vedere un evento che gli viene esplicitamente nascosto. Upgrade
# path: pre-receive lato server o branch-protection su un check CI che valida
# il ref pushato indipendentemente da come e' stato creato (non costruito qui
# — vedi SKILL.md "Quando NON usarla" e la nota in non_fatto della review).
#
# Uso: git-hook.sh <pre-commit|pre-push>   # installato da install-hook.sh
#      git-hook.sh --selfcheck

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

  # 1) nessun verdetto sul ramo non-default -> blocca, esattamente come gate.sh da solo
  printf 'y=2\n' >> "$repo/a.py"; git -C "$repo" add a.py
  set +e; (cd "$repo" && "$DIR/git-hook.sh" pre-commit) >/dev/null 2>&1; rc=$?; set -e
  [ "$rc" -ne 0 ] || { echo "FAIL: senza verdetto doveva bloccare"; exit 1; }

  # 2) verdetto valido presente -> consente (stesso esito di gate.sh via CLI)
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
  [ "$rc" -ne 0 ] || { echo "FAIL: NOT-MERGEABLE doveva restare bloccato"; exit 1; }
  python3 -c "import json; d=json.load(open('$repo/.real-test/verdicts/$HASH.json')); d['verdetto']='MERGEABLE-CON-GAP'; d['raccolto']=[{'tipo':'tetto','nota':'ok'}]; json.dump(d, open('$repo/.real-test/verdicts/$HASH.json','w'))"
  set +e; (cd "$repo" && "$DIR/git-hook.sh" pre-commit) >/dev/null 2>&1; rc=$?; set -e
  [ "$rc" -eq 0 ] || { echo "FAIL: verdetto valido doveva consentire, rc=$rc"; exit 1; }

  rm -rf "$td"
  echo "SELFCHECK OK — 2 rami provati (blocca senza verdetto/consente con verdetto valido)"
}

case "${1:-}" in
  --selfcheck) _selfcheck ;;
  pre-commit|pre-push) run ;;
  *) run ;;
esac
