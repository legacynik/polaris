#!/usr/bin/env bash
# install-hook.sh — wire gate.sh nel repo target: hooks.PreToolUse su Bash,
# marker .real-test/enabled (opt-in esplicito), .gitignore per gli effimeri.
#
# Il merge di settings.json e' fatto SOLO in python3 (`json.load`/`json.dump`),
# mai append di testo — e' esattamente la classe di bug misurata in G2 voce 3
# ("un installer ha accodato il blocco Polaris alla FINE di un pre-commit hook
# preesistente che terminava con exit 0: il blocco accodato era irraggiungibile
# e il gate non e' MAI girato"). jq va bene come alternativa se preferito, ma
# qui non e' un requisito: python3 e' gia' l'unica dipendenza di gate.sh.
#
# Uso:
#   install-hook.sh --repo <path> [--yes]     # installa (idempotente)
#   install-hook.sh --repo <path> --verify    # prova che sia wired E funzionante
#   install-hook.sh --selfcheck

set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="$DIR/gate.sh"
GITHOOK="$DIR/git-hook.sh"
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
  # `git rev-parse --git-path hooks` torna relativo al repo normale, ma
  # ASSOLUTO per un worktree (punta agli hooks CONDIVISI del repo principale
  # — corretto: un hook installato una volta vale su tutti i worktree).
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

# Vero hook git (pre-commit/pre-push) — root-cause fix di EVAL-real-test-bypass.md
# vie B/C (gate.sh da solo si aggira spoofando tool_name o incapsulando il comando;
# un hook git reale gira SEMPRE su un commit/push vero, non lo sniffa da un payload).
# Chain, mai clobber: se un hook preesistente (husky, altro tool) c'e' gia' e non e'
# nostro, lo si preserva e lo si chiama PRIMA — e' esattamente il bug di installer
# che accodano-alla-fine misurato in G2 voce 3 ("blocco irraggiungibile"), qui evitato
# chiamando il preesistente in testa, non in coda a un file che puo' gia' finire con
# un exit implicito.
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
  echo "installato: hook Claude-Code wired in $settings, hook git reali in $hooks_dir/{pre-commit,pre-push}, marker .real-test/enabled creato."
  echo "verifica:   install-hook.sh --repo '$repo' --verify"
}

verify() {
  local repo="$1" settings="$1/.claude/settings.json" hooks_dir
  python3 -c "
import json,sys
d = json.load(open('$settings'))
cmds = [h.get('command') for e in d.get('hooks',{}).get('PreToolUse',[]) for h in e.get('hooks',[])]
sys.exit(0 if '$GATE' in cmds else 1)
" || { echo "VERIFY FAIL: $GATE non e' in hooks.PreToolUse di $settings"; return 1; }
  [ -f "$repo/.real-test/enabled" ] || { echo "VERIFY FAIL: marker .real-test/enabled assente"; return 1; }
  hooks_dir=$(_hooks_dir "$repo")
  for name in pre-commit pre-push; do
    [ -x "$hooks_dir/$name" ] && grep -qF "$MARKER" "$hooks_dir/$name" \
      || { echo "VERIFY FAIL: $hooks_dir/$name non e' il nostro hook (installer B/C non chiuso)"; return 1; }
  done
  bash "$GATE" --selfcheck || { echo "VERIFY FAIL: gate.sh --selfcheck non passa"; return 1; }
  bash "$GITHOOK" --selfcheck || { echo "VERIFY FAIL: git-hook.sh --selfcheck non passa"; return 1; }
  echo "VERIFY OK: hook Claude-Code + hook git reali wired, marker presente, selfcheck passano."
}

_selfcheck() {
  local td repo hooks_dir
  td=$(mktemp -d); repo="$td/r"; mkdir -p "$repo"
  git init -q "$repo"

  install "$repo" >/dev/null
  grep -q "$GATE" "$repo/.claude/settings.json" || { echo "FAIL: non wired"; exit 1; }
  [ -f "$repo/.real-test/enabled" ] || { echo "FAIL: marker assente"; exit 1; }
  grep -qxF ".real-test/verdicts/" "$repo/.gitignore" || { echo "FAIL: gitignore mancante"; exit 1; }

  hooks_dir=$(_hooks_dir "$repo")
  [ -x "$hooks_dir/pre-commit" ] && grep -qF "$MARKER" "$hooks_dir/pre-commit" \
    || { echo "FAIL: hook git pre-commit non installato/eseguibile (chiude EVAL-bypass B/C)"; exit 1; }
  [ -x "$hooks_dir/pre-push" ] || { echo "FAIL: hook git pre-push non installato"; exit 1; }

  install "$repo" >/dev/null   # idempotenza: nessuna entry/chain duplicata
  n=$(python3 -c "import json; d=json.load(open('$repo/.claude/settings.json')); print(sum(1 for e in d['hooks']['PreToolUse'] for h in e['hooks'] if h['command']=='$GATE'))")
  [ "$n" = "1" ] || { echo "FAIL: install ripetuta ha duplicato l'entry ($n copie)"; exit 1; }
  [ -f "$hooks_dir/pre-commit.real-test-chain" ] && { echo "FAIL: reinstall su hook GIA' nostro ha incatenato se stesso"; exit 1; }

  verify "$repo" >/dev/null || { echo "FAIL: verify doveva passare"; exit 1; }

  # hook preesistente (es. husky) -> deve essere CONCATENATO, mai sovrascritto muto
  # (G2 voce 3: "blocco accodato irraggiungibile" — qui e' l'hook ALTRUI a dover
  # restare raggiungibile, simmetrico allo stesso bug)
  repo="$td/r2"; mkdir -p "$repo"; git init -q "$repo"
  hooks_dir=$(_hooks_dir "$repo")
  mkdir -p "$hooks_dir"
  cat > "$hooks_dir/pre-commit" <<EOF
#!/usr/bin/env bash
touch "\$(git rev-parse --show-toplevel)/sentinel-preesistente"
EOF
  chmod +x "$hooks_dir/pre-commit"
  install "$repo" >/dev/null
  [ -x "$hooks_dir/pre-commit.real-test-chain" ] || { echo "FAIL: hook preesistente non incatenato, rischio 'irraggiungibile'"; exit 1; }
  grep -q "sentinel-preesistente" "$hooks_dir/pre-commit.real-test-chain" \
    || { echo "FAIL: il contenuto dell'hook preesistente e' andato perso"; exit 1; }
  # L'exit code del hook qui non è il soggetto del test (un gate può legittimamente uscire ≠0):
  # il soggetto è l'EFFETTO. Ma non si scarta — si cattura, così l'intenzione è visibile.
  hook_rc=0; (cd "$repo" && "$hooks_dir/pre-commit") >/dev/null 2>&1 || hook_rc=$?
  [ -f "$repo/sentinel-preesistente" ] || { echo "FAIL: hook preesistente incatenato ma MAI eseguito (irraggiungibile)"; exit 1; }

  rm -rf "$td"
  echo "SELFCHECK OK — install/idempotenza/verify/hook-git-installato/hook-preesistente-incatenato, 6 asserzioni"
}

repo="."; mode="install"
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) repo="$2"; shift 2 ;;
    --verify) mode="verify"; shift ;;
    --yes) shift ;;
    --selfcheck) mode="selfcheck"; shift ;;
    *) echo "arg sconosciuto: $1" >&2; exit 1 ;;
  esac
done

case "$mode" in
  selfcheck) _selfcheck ;;
  verify) verify "$(cd "$repo" && pwd)" ;;
  install) install "$(cd "$repo" && pwd)" ;;
esac
