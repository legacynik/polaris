---
title: real-test — bypass-test (deve fallire se qualcuno aggira il gate)
description: 9 tentativi di aggiramento contro un repo git usa-e-getta (5 originali + 4 da un attacco adversariale). Ognuno DEVE essere bloccato tranne l'esenzione sul branch default e il bypass esplicito, che devono passare MA lasciare traccia in bypass.log — mai un aggiramento silenzioso (208 occorrenze misurate).
status: active
---

# Bypass-test

Materializza un repo git vero (non una directory finta), prova 9 modi di aggirare il gate:
5 contro `gate.sh` (il fast-path Claude-Code), 4 contro l'ancora reale — il git hook installato
da `install-hook.sh` — che sono le vie laterali trovate dall'attacco adversariale quando la
sola simulazione via payload JSON non basta piu' a fermare un `git commit` VERO.
Se anche UNO di questi passa senza dover bloccare, il gate e' dichiarato, non blindato.

```bash
#!/usr/bin/env bash
set -eu
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts"
REPO="$(mktemp -d)"
git init -q "$REPO"
git -C "$REPO" config user.email t@t; git -C "$REPO" config user.name t
printf 'def charge(amount):\n    if amount > 0:\n        return "ok"\n    return "zero"\n' > "$REPO/app.py"
git -C "$REPO" add . && git -C "$REPO" commit -q -m base
bash "$SKILL/install-hook.sh" --repo "$REPO" >/dev/null
git -C "$REPO" add . && git -C "$REPO" commit -q -m "chore: install"
git -C "$REPO" checkout -q -b feat/issue-1

payload() { printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'; }
gate() { (cd "$REPO" && payload | bash "$SKILL/gate.sh"); }

# --- introduce un ramo nuovo mai testato -----------------------------------
printf 'def charge(amount):\n    if amount > 0:\n        return "ok"\n    elif amount < 0:\n        raise ValueError("neg")\n    return "zero"\n' > "$REPO/app.py"
git -C "$REPO" add .
HASH=$(python3 "$SKILL/perimeter.py" --repo "$REPO" --head STAGED --hash-only)
VFILE="$REPO/.real-test/verdicts/$HASH.json"

# 1) TENTATIVO: dichiarare MERGEABLE senza mai citare il ramo `elif` nuovo.
python3 "$SKILL/verdict.py" new --repo "$REPO" --out "$VFILE"
python3 - "$VFILE" <<'PY'
import json, sys
v = json.load(open(sys.argv[1]))
for row in v["matrix"]:
    row["exception_ticket"] = "N/A"
v["verdetto"] = "MERGEABLE"                      # <-- dichiarazione bugiarda
v["raccolto"] = [{"tipo": "falso-allarme", "nota": "sembrava a posto"}]
json.dump(v, open(sys.argv[1], "w"), indent=2)
PY
set +e; gate; rc=$?; set -e
[ "$rc" -eq 2 ] || { echo "BYPASS-TEST FALLITO (1): MERGEABLE senza branches_exercised e' passato"; exit 1; }
echo "1/5 bloccato: dichiarare MERGEABLE non basta, il ramo scoperto e' cercato da perimeter.py"

# 2) TENTATIVO: rinominare un vecchio verdetto passato col nome-hash nuovo
#    (il content_hash INTERNO resta quello vecchio: il filename non e' la fonte di verita').
OLDV="$REPO/.real-test/verdicts/deadbeefdeadbeefdeadbeefdeadbeefdeadbeef.json"
python3 -c "import json; d=json.load(open('$VFILE')); d['content_hash']='deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'; json.dump(d, open('$OLDV','w'))"
cp "$OLDV" "$VFILE"     # verdetto vecchio, rinominato col nome-file giusto
set +e; python3 "$SKILL/verdict.py" validate "$VFILE" --repo "$REPO"; rc=$?; set -e
[ "$rc" -eq 1 ] || { echo "BYPASS-TEST FALLITO (2): content_hash interno disallineato e' passato"; exit 1; }
echo "2/5 bloccato: il content_hash DENTRO il file conta, non il nome del file"

# 3) TENTATIVO: evidence=live su una classe live-required con artefatto vuoto.
python3 "$SKILL/verdict.py" new --repo "$REPO" --out "$VFILE"
python3 - "$VFILE" "$REPO" <<'PY'
import json, sys
v, repo = json.load(open(sys.argv[1])), sys.argv[2]
for row in v["matrix"]:
    row["exception_ticket"] = "N/A"
    if row["file"] == "app.py":
        row["branches_exercised"] = ["app.py:4"]
        row["class"] = "api-cli"          # forza live-required per il test
        row["evidence"] = "live"
        row["evidence_artifact"] = "empty.json"
v["verdetto"] = "MERGEABLE"
v["raccolto"] = [{"tipo": "difetto", "artifact": "tests/x.py::y"}]
json.dump(v, open(sys.argv[1], "w"), indent=2)
open(f"{repo}/empty.json", "w").close()   # artefatto VUOTO
PY
set +e; python3 "$SKILL/verdict.py" validate "$VFILE" --repo "$REPO"; rc=$?; set -e
[ "$rc" -eq 1 ] || { echo "BYPASS-TEST FALLITO (3): artefatto vuoto spacciato per prova live e' passato"; exit 1; }
echo "3/5 bloccato: un artefatto vuoto non e' una prova"

# 4) TENTATIVO: continuare a modificare il codice DOPO aver ottenuto un verdetto valido.
python3 - "$VFILE" "$REPO" <<'PY'
import json, sys, pathlib
v, repo = json.load(open(sys.argv[1])), pathlib.Path(sys.argv[2])
row = next(r for r in v["matrix"] if r["file"] == "app.py")
row["evidence"], row["evidence_artifact"] = "assumed", None
(repo / "trace.json").write_text('{"ok":true}')
row["class"], row.pop("evidence_artifact", None)
json.dump(v, open(sys.argv[1], "w"), indent=2)
PY
gate >/dev/null 2>&1 && echo "4a verdetto valido: commit consentito" || { echo "setup 4 rotto"; exit 1; }
printf '\n# riga aggiunta DOPO il verdetto\n' >> "$REPO/app.py"
git -C "$REPO" add .
set +e; gate; rc=$?; set -e
[ "$rc" -eq 2 ] || { echo "BYPASS-TEST FALLITO (4): codice cambiato dopo il verdetto, gate non l'ha visto"; exit 1; }
echo "4/5 bloccato: qualunque riga in piu' dopo il verdetto cambia l'hash e invalida la prova (G2.6)"

# 5) TENTATIVO: bypass esplicito — DEVE passare, ma DEVE lasciare traccia.
rm -f "$REPO/.real-test/bypass.log"
set +e; REAL_TEST_BYPASS_GATE=1 gate >/dev/null 2>&1; rc=$?; set -e
[ "$rc" -eq 0 ] || { echo "BYPASS-TEST FALLITO (5a): bypass esplicito doveva consentire"; exit 1; }
[ -s "$REPO/.real-test/bypass.log" ] || { echo "BYPASS-TEST FALLITO (5b): bypass non ha lasciato traccia — e' esattamente R8 (208 bypass silenziosi misurati)"; exit 1; }
echo "5/5 corretto: il bypass passa ma e' loggato, mai silenzioso"

rm -rf "$REPO"
echo "BYPASS-TEST OK — 5/5 tentativi si comportano come devono"
```

**Se un giorno uno di questi 5 passa senza dover bloccare (tranne il 5, che deve bloccare
`rc=0` ma con log non vuoto), il gate e' regredito a dichiarazione — non spedire, fixalo prima.**

## Perché questi 5 e non altri

Ognuno riproduce un caso reale del registro, non un caso di fantasia:

| # | Riproduce | Voce |
|---|---|---|
| 1 | verdetto self-reported che ignora il ramo nuovo introdotto dal fix | G1.6 / F6 |
| 2 | evidenza copiata/rinominata invece che ricalcolata | G2.6 (evidenza slegata dal digest runtime corrente) |
| 3 | mock/artefatto vuoto spacciato per IO reale | G2.1 (34 osservazioni, "il verde certifica il mock") |
| 4 | verdetto valido al momento T, codice cambiato dopo, nessuno se ne accorge | G2.6 (caso reale: newline-collapse validato sulla funzione vecchia, 3 giorni in prod) |
| 5 | bypass esistente ma silenzioso | R8 (208 bypass espliciti misurati in MISURE.md, nessuno tracciato) |


## R1 — un branch `main` stale non deve mai diventare la base in silenzio (fusione 2026-08-16)

fails_before: real-test v0.1.0 (`resolve_base` provava il nome letterale `main` dopo il default
branch — contro la dottrina §0 del plugin: «Non assumere main»).

Setup: repo `-b develop`, branch `main` creato al primo commit e mai avanzato, 3 commit.
Comando: `perimeter.py --repo . --head HEAD` senza `--base`.
**PRIMA (v0.1.0)**: base = sha di `main` (stale), in silenzio — perimetro sbagliato = falso verde. Osservato 2026-08-16.
**DOPO (v2.0.0)**: base = HEAD~1 col ripiego DICHIARATO su stderr; il nome `main` non viene mai
provato. Repo a un solo commit: ripiega su HEAD (dichiarato). Selfcheck: asserzione R1 dedicata.

## R2 — un comando che CITA `git commit` non deve far scattare il gate (fusione 2026-08-16)

fails_before: real-test v0.1.0 (`gate.sh` matchava la sottostringa `*"git commit"*`).

Comando: payload PreToolUse con `command: echo "do not git commit yet"` su repo con marker attivo.
**PRIMA (v0.1.0)**: exit 2 — bloccava un echo innocuo (falso positivo: un guard che scatta sulla
prosa insegna a ignorarlo). Osservato 2026-08-16.
**DOPO (v2.0.0)**: exit 0; `git commit -m x` vero senza verdetto → exit 2 (controprova).
Nota di fusione: il fix ha scovato un secondo difetto reale — `grep -q` sotto `pipefail` uccide
`printf` con SIGPIPE proprio sui match veri; risolto con grep senza `-q`.
