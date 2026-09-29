#!/usr/bin/env python3
"""red_check.py — prova che un test E' STATO rosso prima del fix.

Un test mai fallito non e' un test: e' uno specchio dell'implementazione. Ogni run
porta l'hash del FILE di test, cosi' un test riscritto fra il rosso e il verde non
puo' spacciare il rosso di un altro per il proprio. Se un esito sia un rosso lo
decide red_signatures.py (#373); senza la firma del runner non si scrive nulla.

Exit: 0 PASS · 1 FAIL · 2 errore d'uso. Fail-closed ovunque.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import red_signatures  # noqa: E402  — file accanto a questo, non un pacchetto


# AC3: `pushd` non esiste in dash, `cd -` senza OLDPWD fallisce in bash e passa in dash.
_FORME = ("mkdir -p n && cd n && python3 -m pytest ../t.py", "cd nope; python3 -m pytest t.py",
          "( cd nope && python3 -m pytest t.py )", "pushd nope && python3 -m pytest t.py",
          "unset OLDPWD; cd - && python3 -m pytest t.py")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else "assente"


def _test_file(nodeid: str) -> Path:
    """pytest node id: path::classe::test — il file e' la parte prima di ::"""
    return Path(nodeid.split("::")[0])


def _run(cmd: str):
    """(run, rosso) se il runner ha parlato, None se l'esito non si registra.
    shell=True: il contratto scrive comandi di shell, ed e' la shell a poter morire
    prima del runner — decide l'output, mai la forma del comando."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired:
        print(f"comando oltre 3600s: {cmd!r}", file=sys.stderr)
        return None
    rosso, causa = red_signatures.verdetto((r.stdout or "") + (r.stderr or ""), r.returncode)
    if rosso is None:
        print(f"{causa} — {cmd!r}", file=sys.stderr)
        return None
    return r, rosso


def _entry(a, esito, suite: bool) -> dict:
    r, rosso = esito
    e = {"ts": datetime.now(timezone.utc).isoformat(), "test": a.test,
         "cmd": str(a.cmd).strip(), "exit": r.returncode,
         "tail": ((r.stdout or "") + (r.stderr or ""))[-800:]}
    if suite:
        e["suite"] = True
    else:
        e["rosso"], e["file_sha"] = rosso, _sha(_test_file(a.test))
    return e


def cmd_record(a, suite: bool = False) -> int:
    """record e suite: stesso guard, stesso log, campi diversi."""
    if not str(a.cmd).strip():
        print("--cmd vuoto: non c'e' niente da registrare", file=sys.stderr)
        return 2
    if not _test_file(a.test).is_file():
        # Difetto C: file_sha "assente" degrada in silenzio e fallisce solo al verify.
        print(f"il file di test non si risolve da questa cwd: {_test_file(a.test)} — "
              "lancia record dalla directory giusta o correggi il node id", file=sys.stderr)
        return 2
    esito = _run(str(a.cmd).strip())
    if esito is None:
        return 2
    entry, out = _entry(a, esito, suite), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"{'suite' if suite else ('ROSSO' if entry['rosso'] else 'verde')} "
          f"exit={entry['exit']} -> {out}")
    return 0


def cmd_suite(a) -> int:
    return cmd_record(a, suite=True)


def cmd_verify(a) -> int:
    log = Path(a.log)
    if not log.is_file():
        print(f"nessun log di run: {log}", file=sys.stderr)
        return 1
    try:
        runs = [json.loads(r) for r in log.read_text(encoding="utf-8").splitlines() if r.strip()]
    except json.JSONDecodeError:
        print(f"log corrotto: riga non JSON in {log}", file=sys.stderr)
        return 1
    mine = [r for r in runs if r.get("test") == a.test and not r.get("suite")]
    rossi, verdi = [r for r in mine if r.get("rosso")], [r for r in mine if not r.get("rosso")]
    if not mine:
        print(f"nessun run registrato per {a.test}", file=sys.stderr)
    elif not rossi:
        print(f"nessun run ROSSO per {a.test}: non ha mai fallito", file=sys.stderr)
    elif not verdi:
        print(f"{a.test} e' stato rosso ma mai verde: il fix non c'e'", file=sys.stderr)
    else:
        return _verdetto_ciclo(a, (rossi[-1], verdi[-1]), runs)
    return 1


def _verdetto_ciclo(a, ciclo, runs) -> int:
    """Rosso prima del verde, stesso file di test, e — se dichiarata — una suite
    verde DOPO il GREEN mirato: senza, l'handoff non e' provato."""
    ultimo_rosso, ultimo_verde = ciclo
    if ultimo_rosso["ts"] > ultimo_verde["ts"]:
        print(f"l'ultimo run di {a.test} e' rosso: il fix non regge", file=sys.stderr)
        return 1
    if ultimo_rosso.get("file_sha") != ultimo_verde.get("file_sha"):
        print(f"il file di test e' cambiato fra rosso e verde ({ultimo_rosso.get('file_sha')} ->"
              f" {ultimo_verde.get('file_sha')}): quel rosso non prova QUESTO test", file=sys.stderr)
        return 1
    if ultimo_rosso.get("file_sha") == "assente":
        print(f"il file di test non esiste: {_test_file(a.test)}", file=sys.stderr)
        return 1
    suite_cmd = getattr(a, "suite_cmd", None)
    if not suite_cmd:
        return 0
    suites = [r for r in runs if r.get("suite") and r.get("test") == a.test
              and r.get("cmd") == suite_cmd]
    if not suites:
        print(f"suite non registrata per {a.test}: {suite_cmd!r}", file=sys.stderr)
    elif suites[-1].get("exit") != 0:
        print(f"l'ultima suite registrata fallisce (exit {suites[-1]['exit']})", file=sys.stderr)
    elif suites[-1].get("ts", "") < ultimo_verde["ts"]:
        print("la suite verde precede il GREEN mirato: l'handoff non e' provato", file=sys.stderr)
    else:
        return 0
    return 1


def _selfcheck() -> int:
    """AC1 e AC2 (firme, mutation) stanno nel selfcheck di red_signatures; le forme
    di log che verify boccia in tests/fixtures/verify_casi.json, via pytest. Qui
    AC3: il verdetto deve seguire la shell MISURATA, mai il dialetto ipotizzato."""
    import shlex
    import tempfile
    ok = red_signatures._selfcheck() == 0
    with tempfile.TemporaryDirectory() as d:
        # `cd` esplicito invece di os.chdir: il selfcheck non deve lasciare il processo
        # dentro una directory temporanea che sta per sparire.
        (Path(d) / "t.py").write_text("def test_a():\n    assert False\n", encoding="utf-8")
        log = Path(d) / "o.jsonl"
        for shell in [x for x in ("bash", "dash", "sh") if shutil.which(x)]:
            for forma in _FORME:
                cmd = f"{shell} -c {shlex.quote(f'cd {shlex.quote(d)} && ' + forma)}"
                vero = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                partito = "test session starts" in vero.stdout + vero.stderr
                log.unlink(missing_ok=True)
                rc = cmd_record(argparse.Namespace(test=f"{d}/t.py::a", cmd=cmd, out=str(log)))
                esito = (rc == 0) is partito and log.is_file() is partito
                ok = ok and esito
                print(("ok   " if esito else "FAIL ") + f"{shell}: {forma[:36]} -> "
                      + ("ROSSO" if partito else "blocco"))
    print("SELFCHECK OK" if ok else "SELFCHECK ROSSO")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="red_check.py")
    ap.add_argument("--selfcheck", action="store_true")
    # dest="cmd" collideva con l'opzione --cmd di record (B1): stesso attributo, CLI inagibile
    sub = ap.add_subparsers(dest="azione")
    for nome, aiuto in (("record", "esegue il test e registra l'esito"),
                        ("suite", "esegue e registra la suite rilevante per l'handoff")):
        p = sub.add_parser(nome, help=aiuto)
        p.add_argument("--test", required=True, help="node id, es. tests/test_x.py::test_y")
        p.add_argument("--cmd", required=True)
        p.add_argument("--out", required=True)
    v = sub.add_parser("verify", help="il test e' stato rosso, poi verde, senza essere riscritto?")
    v.add_argument("--log", required=True)
    v.add_argument("--test", required=True)
    v.add_argument("--suite-cmd", help="richiede una suite verde registrata dopo il GREEN")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    azioni = {"record": cmd_record, "suite": cmd_suite, "verify": cmd_verify}
    if a.azione in azioni:
        return azioni[a.azione](a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
