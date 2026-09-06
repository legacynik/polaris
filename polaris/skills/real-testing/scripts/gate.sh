#!/usr/bin/env bash
# gate.sh — hook di rilevamento condiviso: chiamato sia dal PreToolUse di Claude
# Code (fast-path, blocca prima che il comando parta) sia da git-hook.sh (vero
# hook git — pre-commit/pre-push, l'ancora che NON si aggira cambiando tool_name
# o incapsulando il comando in uno script, vedi EVAL-real-test-bypass.md vie B/C:
# git-hook.sh sintetizza il payload perche' sa gia', dall'evento git stesso, che
# un commit sta accadendo — non lo indovina da una substring).
#
# Corregge il bug misurato in CRITIC-1 (§1 riga 12) sull'hook gemello di
# parallel-issue-flow: quello usa `sed -E 's/.../\s.../'` — `\s` e' un'estensione
# GNU assente nel sed BSD di macOS, quindi il match fallisce sempre e il gate e'
# EXIT 0 (consente) qualunque comando. Qui il parsing e' SOLO `python3 -c
# "import json"` sullo stdin — mai regex su JSON.
#
# Attivo solo se il repo ha `.real-test/enabled` (creato da install-hook.sh) —
# opt-in esplicito, nessuna repo viene gated a sorpresa.
#
# Exit: 0 = consenti, 2 = blocca (stderr va al modello).
#
# Uso: gate.sh < payload.json          # come lo chiama Claude Code / git-hook.sh
#      gate.sh --selfcheck             # prova ogni ramo su fixture usa-e-getta

set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_log_bypass() {
  local repo="$1" hash="$2" reason="$3"
  mkdir -p "$repo/.real-test"
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${USER:-unknown}" "$hash" \
    "$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null)" "$reason" >> "$repo/.real-test/bypass.log"
}

_default_branch() {
  # NON una pipe: `git ... | sed ...` maschera il fallimento di git dietro
  # l'exit-status di sed (che su stdin vuoto esce comunque 0) — il fallback
  # "echo main" non scattava mai, trovato eseguendo per la prima volta questo
  # ramo in selfcheck (nessun repo con origin/HEAD -> _default_branch tornava
  # stringa vuota, mai "main": l'esenzione sul branch default non scattava MAI
  # su un repo locale senza remote, comportamento diverso da un clone reale).
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
  # invocazione reale di `git commit` (inizio comando o dopo ; && || |), non la
  # stringa citata dentro un echo/messaggio (rosso R2, fusione 2026-08-16).
  # grep SENZA -q: con pipefail, -q che matcha chiude lo stdin e uccide printf
  # con SIGPIPE — la pipeline "fallisce" proprio sui match veri.
  printf '%s' "$cmd" | grep -E '(^|[;&|][[:space:]]*|&&[[:space:]]*|\|\|[[:space:]]*)git[[:space:]]+commit([[:space:]]|$)' >/dev/null || return 0

  repo=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
  [ -f "$repo/.real-test/enabled" ] || return 0

  hash=$(python3 "$DIR/perimeter.py" --repo "$repo" --head STAGED --hash-only 2>/dev/null) || return 0
  branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

  # Esenzione sul branch di default (handoff cross-panel, CLAUDE.md utente): resta
  # un'esenzione, MAI silenziosa — G2#8 ("il gate, quando non sa decidere, approva
  # in silenzio") e R8 (208 bypass non tracciati) valgono anche per questa via,
  # trovata aperta e non loggata da EVAL-real-test-bypass.md via A.
  if [ "$branch" = "$(_default_branch "$repo")" ]; then
    _log_bypass "$repo" "$hash" "default-branch-exempt"
    echo "real-test: branch di default ($branch) esente dal gate — loggato in .real-test/bypass.log (mai silenzioso)." >&2
    return 0
  fi

  if [ "${REAL_TEST_BYPASS_GATE:-0}" = "1" ]; then
    _log_bypass "$repo" "$hash" "explicit-bypass"
    echo "real-test: BYPASS usato e loggato in .real-test/bypass.log (mai silenzioso)." >&2
    return 0
  fi

  verdict_file="$repo/.real-test/verdicts/$hash.json"
  if [ ! -f "$verdict_file" ]; then
    cat >&2 <<MSG
real-test: gate BLOCCATO. Nessun verdetto per l'albero corrente ($hash).
  1. python3 $DIR/verdict.py new --repo "$repo" --out "$verdict_file"
  2. Compila matrix/raccolto seguendo SKILL.md, poi:
     python3 $DIR/verdict.py validate "$verdict_file" --repo "$repo"
  3. Ripeti il commit.
Bypass (solo emergenza, viene loggato): REAL_TEST_BYPASS_GATE=1
MSG
    return 2
  fi

  if ! python3 "$DIR/verdict.py" validate "$verdict_file" --repo "$repo" >&2; then
    echo "real-test: verdetto presente ma NON VALIDO (vedi FAIL sopra). Correggi e ripeti." >&2
    return 2
  fi

  verdetto=$(python3 -c "import json; print(json.load(open('$verdict_file')).get('verdetto'))")
  if [ "$verdetto" = "NOT-MERGEABLE" ]; then
    echo "real-test: verdetto e' NOT-MERGEABLE per $hash. Il commit resta bloccato finche' non risale a MERGEABLE/MERGEABLE-CON-GAP." >&2
    return 2
  fi
  return 0
}

_selfcheck() {
  local td repo out rc
  td=$(mktemp -d)
  repo="$td/r"
  mkdir -p "$repo" && git init -q "$repo"
  git -C "$repo" symbolic-ref HEAD refs/heads/main   # deterministico: _default_branch fallback e' "main"
  git -C "$repo" config user.email t@t; git -C "$repo" config user.name t
  printf 'x=1\n' > "$repo/a.py"; git -C "$repo" add .; git -C "$repo" commit -q -m base

  # 1) niente marker .real-test/enabled -> allow silenzioso (skill non installata qui)
  printf 'y=2\n' >> "$repo/a.py"; git -C "$repo" add .
  out=$(cd "$repo" && printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh")
  echo "$out" | grep -q . && { echo "FAIL: senza marker doveva essere silenzioso"; exit 1; }

  mkdir -p "$repo/.real-test"; touch "$repo/.real-test/enabled"

  # 2) marker presente, SUL BRANCH DI DEFAULT -> allow, MA loggato con motivo (mai muto)
  out=$(cd "$repo" && printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh")
  [ -z "$out" ] || { echo "FAIL: esenzione branch default deve restare silenziosa su stdout"; exit 1; }
  [ -s "$repo/.real-test/bypass.log" ] || { echo "FAIL: esenzione branch default doveva essere loggata (EVAL-bypass via A)"; exit 1; }
  grep -q "default-branch-exempt" "$repo/.real-test/bypass.log" || { echo "FAIL: motivo dell'esenzione assente dal log"; exit 1; }

  # 3) marker presente, ramo non-default, nessun verdetto -> blocca EXIT 2
  git -C "$repo" checkout -q -b feat/x
  set +e
  (cd "$repo" && printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh" 2>/tmp/rt_selfcheck_err)
  rc=$?
  set -e
  [ "$rc" -eq 2 ] || { echo "FAIL: senza verdetto doveva bloccare EXIT 2, ha dato $rc"; exit 1; }
  grep -q "BLOCCATO" /tmp/rt_selfcheck_err || { echo "FAIL: messaggio di blocco assente"; exit 1; }

  # 4) bypass esplicito -> allow MA loggato
  rm -f "$repo/.real-test/bypass.log"
  set +e
  REAL_TEST_BYPASS_GATE=1 bash -c "cd '$repo' && printf '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git commit -m x\"}}' | '$DIR/gate.sh'" >/dev/null 2>&1
  rc=$?
  set -e
  [ "$rc" -eq 0 ] || { echo "FAIL: bypass doveva consentire"; exit 1; }
  grep -q "explicit-bypass" "$repo/.real-test/bypass.log" || { echo "FAIL: bypass doveva essere loggato col motivo"; exit 1; }

  # 5) tool_name diverso da Bash -> allow silenzioso sul FAST-PATH (difesa 1 di 2 —
  #    la difesa reale e' il git hook vero, non simulabile qui senza installarlo:
  #    vedi install-hook.sh --selfcheck e bypass-test.md #7 per la prova end-to-end)
  out=$(cd "$repo" && printf '{"tool_name":"Edit","tool_input":{"command":"git commit -m x"}}' | "$DIR/gate.sh")
  [ -z "$out" ] || { echo "FAIL: tool_name!=Bash doveva essere silenzioso sul fast-path"; exit 1; }

  rm -rf "$td" /tmp/rt_selfcheck_err
  echo "SELFCHECK OK — 5 rami provati (no-marker/default-branch-loggato/blocca/bypass-loggato/tool-diverso)"
}

if [ "${1:-}" = "--selfcheck" ]; then
  _selfcheck
else
  run_gate
fi
