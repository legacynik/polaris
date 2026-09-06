#!/usr/bin/env python3
"""red_check.py — prova che un test E' STATO rosso prima del fix.

Un test mai fallito non e' un test: e' uno specchio dell'implementazione.
Registra ogni run con l'hash del FILE di test, cosi' un test riscritto fra il
rosso e il verde non puo' spacciare il rosso di un altro test per il proprio.

Exit: 0 PASS · 1 FAIL · 2 errore d'uso. Fail-closed ovunque.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else "assente"


def _test_file(nodeid: str) -> Path:
    """pytest node id: path::classe::test — il file e' la parte prima di ::"""
    return Path(nodeid.split("::")[0])


def _run(cmd: str):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired:
        print(f"comando oltre 3600s: {cmd!r}", file=sys.stderr)
        return None


def cmd_record(a) -> int:
    cmd = str(a.cmd).strip()
    if not cmd:
        print("--cmd vuoto: non c'e' niente da registrare", file=sys.stderr)
        return 2
    if not _test_file(a.test).is_file():
        # Difetto C (eval sul campo 2026-08-17): registrare con file_sha "assente"
        # degrada in silenzio e fallisce solo al verify — si fallisce QUI, forte.
        print(f"il file di test non si risolve da questa cwd: {_test_file(a.test)} — "
              "lancia record dalla directory giusta o correggi il node id", file=sys.stderr)
        return 2
    # shell=True: il contratto scrive comandi di shell ("cd x && pytest").
    # shlex.split senza shell eseguiva /usr/bin/cd, che esce 0 ignorando
    # tutto → verde farlocco (fail-open trovato dall'eval sul campo).
    r = _run(cmd)
    if r is None:
        return 2
    if r.returncode == 127:
        print(f"comando non trovato (exit 127): {cmd!r} — un rosso d'ambiente "
              "non e' un rosso", file=sys.stderr)
        return 2
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "test": a.test,
        "cmd": cmd,
        "exit": r.returncode,
        "rosso": r.returncode != 0,
        "file_sha": _sha(_test_file(a.test)),
        "tail": ((r.stdout or "") + (r.stderr or ""))[-800:],
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"{'ROSSO' if entry['rosso'] else 'verde'} exit={r.returncode} -> {out}")
    return 0


def cmd_suite(a) -> int:
    cmd = str(a.cmd).strip()
    if not cmd:
        print("--cmd vuoto: non c'e' una suite da registrare", file=sys.stderr)
        return 2
    if not _test_file(a.test).is_file():
        print(f"il file di test non si risolve da questa cwd: {_test_file(a.test)}", file=sys.stderr)
        return 2
    r = _run(cmd)
    if r is None:
        return 2
    if r.returncode == 127:
        print(f"comando suite non trovato (exit 127): {cmd!r}", file=sys.stderr)
        return 2
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "test": a.test,
        "suite": True,
        "cmd": cmd,
        "exit": r.returncode,
        "tail": ((r.stdout or "") + (r.stderr or ""))[-800:],
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"suite exit={r.returncode} -> {out}")
    return 0


def cmd_verify(a) -> int:
    log = Path(a.log)
    if not log.is_file():
        print(f"nessun log di run: {log}", file=sys.stderr)
        return 1
    runs = []
    for line in log.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"log corrotto: riga non JSON in {log}", file=sys.stderr)
                return 1
    mine = [r for r in runs if r.get("test") == a.test and not r.get("suite")]
    if not mine:
        print(f"nessun run registrato per {a.test}", file=sys.stderr)
        return 1
    rossi = [r for r in mine if r.get("rosso")]
    verdi = [r for r in mine if not r.get("rosso")]
    if not rossi:
        print(f"nessun run ROSSO per {a.test}: il test non ha mai fallito, "
              f"quindi non prova niente", file=sys.stderr)
        return 1
    if not verdi:
        print(f"{a.test} e' stato rosso ma mai verde: il fix non c'e'", file=sys.stderr)
        return 1
    ultimo_rosso, ultimo_verde = rossi[-1], verdi[-1]
    if ultimo_rosso["ts"] > ultimo_verde["ts"]:
        print(f"l'ultimo run di {a.test} e' rosso: il fix non regge", file=sys.stderr)
        return 1
    if ultimo_rosso.get("file_sha") != ultimo_verde.get("file_sha"):
        print(f"il file di test e' cambiato fra il rosso e il verde "
              f"({ultimo_rosso.get('file_sha')} -> {ultimo_verde.get('file_sha')}): "
              f"quel rosso non prova QUESTO test", file=sys.stderr)
        return 1
    if ultimo_rosso.get("file_sha") == "assente":
        print(f"il file di test non esiste: {_test_file(a.test)}", file=sys.stderr)
        return 1
    suite_cmd = getattr(a, "suite_cmd", None)
    if suite_cmd:
        suites = [r for r in runs if r.get("suite") and r.get("test") == a.test
                  and r.get("cmd") == suite_cmd]
        if not suites:
            print(f"suite non registrata per {a.test}: {suite_cmd!r}", file=sys.stderr)
            return 1
        latest = suites[-1]
        if latest.get("exit") != 0:
            print(f"l'ultima suite registrata fallisce (exit {latest.get('exit')})", file=sys.stderr)
            return 1
        if latest.get("ts", "") < ultimo_verde["ts"]:
            print("la suite verde precede il GREEN mirato: l'handoff non e' provato", file=sys.stderr)
            return 1
    return 0


def _selfcheck() -> int:
    import tempfile
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + msg)
        ok = ok and cond

    def verify(log, test="t.py::a", suite_cmd=None):
        return cmd_verify(argparse.Namespace(log=str(log), test=test, suite_cmd=suite_cmd))

    def write(log, *entries):
        log.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")

    def e(ts, rosso, sha="aaa", test="t.py::a"):
        return {"ts": ts, "test": test, "exit": 1 if rosso else 0, "rosso": rosso, "file_sha": sha}

    def s(ts, exit_code=0, cmd="python3 -m pytest", test="t.py::a"):
        return {"ts": ts, "test": test, "suite": True, "cmd": cmd, "exit": exit_code}

    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / "r.jsonl"
        check(verify(log) == 1, "log assente -> FAIL, mai PASS")
        log.write_text("", encoding="utf-8")
        check(verify(log) == 1, "log vuoto -> FAIL")
        log.write_text("non-json\n", encoding="utf-8")
        check(verify(log) == 1, "log corrotto -> FAIL")
        write(log, e("2026-01-01T00:00:00+00:00", False))
        check(verify(log) == 1, "solo verde: mai stato rosso -> FAIL")
        write(log, e("2026-01-01T00:00:00+00:00", True))
        check(verify(log) == 1, "solo rosso: il fix non c'e' -> FAIL")
        write(log, e("2026-01-02T00:00:00+00:00", False), e("2026-01-03T00:00:00+00:00", True))
        check(verify(log) == 1, "l'ultimo run e' rosso: il fix non regge -> FAIL")
        write(log, e("2026-01-01T00:00:00+00:00", True, "aaa"),
                   e("2026-01-02T00:00:00+00:00", False, "bbb"))
        check(verify(log) == 1, "test riscritto fra rosso e verde -> FAIL")
        write(log, e("2026-01-01T00:00:00+00:00", True), e("2026-01-02T00:00:00+00:00", False))
        check(verify(log) == 0, "rosso poi verde, stesso file -> PASS")
        check(verify(log, suite_cmd="python3 -m pytest") == 1,
              "handoff senza suite registrata -> FAIL")
        write(log, e("2026-01-01T00:00:00+00:00", True),
                   e("2026-01-02T00:00:00+00:00", False),
                   s("2026-01-03T00:00:00+00:00", 1))
        check(verify(log, suite_cmd="python3 -m pytest") == 1,
              "suite registrata ma rossa -> FAIL")
        write(log, s("2026-01-01T00:00:00+00:00"),
                   e("2026-01-02T00:00:00+00:00", True),
                   e("2026-01-03T00:00:00+00:00", False))
        check(verify(log, suite_cmd="python3 -m pytest") == 1,
              "suite verde prima del GREEN mirato -> FAIL")
        write(log, e("2026-01-01T00:00:00+00:00", True),
                   e("2026-01-02T00:00:00+00:00", False),
                   s("2026-01-03T00:00:00+00:00"))
        check(verify(log, suite_cmd="python3 -m unittest") == 1,
              "suite diversa da quella dichiarata -> FAIL")
        check(verify(log, suite_cmd="python3 -m pytest") == 0,
              "rosso, verde e suite successiva registrati -> PASS handoff")
        write(log, e("2026-01-01T00:00:00+00:00", True, test="altro.py::b"),
                   e("2026-01-02T00:00:00+00:00", False, test="altro.py::b"))
        check(verify(log) == 1, "il rosso e' di un ALTRO test -> FAIL")
        write(log, e("2026-01-01T00:00:00+00:00", True, "assente"),
                   e("2026-01-02T00:00:00+00:00", False, "assente"))
        check(verify(log) == 1, "il file di test non esiste -> FAIL")

        # record: il ramo dell'ignoranza
        out = Path(d) / "rec.jsonl"
        import os
        os.chdir(d)
        Path("t.py").write_text("def test_a():\n    assert False\n", encoding="utf-8")
        check(cmd_record(argparse.Namespace(test="t.py::a", cmd="", out=str(out))) == 2,
              "record con --cmd vuoto -> errore d'uso, mai 0")
        check(cmd_record(argparse.Namespace(test="manca.py::x", cmd="/usr/bin/false",
                                            out=str(out))) == 2,
              "record su file di test irrisolvibile -> errore d'uso SUBITO (difetto C)")
        check(cmd_record(argparse.Namespace(test="t.py::a", cmd="/bin/nonesiste-mai",
                                            out=str(out))) == 2,
              "record con comando inesistente (127 via shell) -> errore d'uso, mai rosso")
        cmd_record(argparse.Namespace(test="t.py::a", cmd="/usr/bin/false", out=str(out)))
        cmd_record(argparse.Namespace(test="t.py::a", cmd="/usr/bin/true", out=str(out)))
        check(verify(out) == 0, "record rosso poi verde su file reale -> verify PASS")

        # fail-open del cd (eval sul campo): comando composto che DEVE fallire
        comp = Path(d) / "comp.jsonl"
        cmd_record(argparse.Namespace(test="t.py::a", cmd=f"cd {d} && /usr/bin/false",
                                      out=str(comp)))
        last = json.loads(comp.read_text().splitlines()[-1])
        check(last["rosso"] is True,
              "comando composto 'cd x && false' -> ROSSO vero (prima: verde farlocco)")

        # B1: il path CLI vero, non il Namespace costruito a mano — è così che
        # la collisione argparse dest="cmd" è rimasta invisibile al selfcheck
        cli = subprocess.run(
            [sys.executable, __file__, "record", "--test", "t.py::a",
             "--cmd", "/usr/bin/false", "--out", str(Path(d) / "cli.jsonl")],
            capture_output=True, text=True, cwd=d)
        check(cli.returncode == 0 and (Path(d) / "cli.jsonl").is_file(),
              "CLI 'record --cmd ...' registra il run (B1: no collisione argparse)")
        suite_log = Path(d) / "suite.jsonl"
        suite_cli = subprocess.run(
            [sys.executable, __file__, "suite", "--test", "t.py::a",
             "--cmd", "/usr/bin/true", "--out", str(suite_log)],
            capture_output=True, text=True, cwd=d)
        check(suite_cli.returncode == 0 and json.loads(suite_log.read_text())["suite"] is True,
              "CLI 'suite' registra l'evidenza autoritativa")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="red_check.py")
    ap.add_argument("--selfcheck", action="store_true")
    # dest="cmd" collideva con l'opzione --cmd di record (B1): stesso attributo, CLI inagibile
    sub = ap.add_subparsers(dest="azione")
    r = sub.add_parser("record", help="esegue il test e registra l'esito")
    r.add_argument("--test", required=True, help="node id, es. tests/test_x.py::test_y")
    r.add_argument("--cmd", required=True)
    r.add_argument("--out", required=True)
    s = sub.add_parser("suite", help="esegue e registra la suite rilevante per l'handoff")
    s.add_argument("--test", required=True, help="node id a cui appartiene il ciclo")
    s.add_argument("--cmd", required=True)
    s.add_argument("--out", required=True)
    v = sub.add_parser("verify", help="il test e' stato rosso, poi verde, senza essere riscritto?")
    v.add_argument("--log", required=True)
    v.add_argument("--test", required=True)
    v.add_argument("--suite-cmd", help="richiede una suite verde registrata dopo il GREEN")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    if a.azione == "record":
        return cmd_record(a)
    if a.azione == "suite":
        return cmd_suite(a)
    if a.azione == "verify":
        return cmd_verify(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
