#!/usr/bin/env python3
"""mutation.py — rimette il bug e pretende che i test tornino rossi.

Se col difetto reintrodotto la suite resta verde, quei test non provano niente:
sono uno specchio dell'implementazione, non una rete.

Exit: 0 la suite e' tornata rossa (i test valgono) · 1 e' restata verde (non
valgono) · 2 errore d'uso. Il repo viene SEMPRE ripristinato, anche in errore.
"""
import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _git(args: list, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _dirty(cwd: str) -> bool:
    return bool(_git(["status", "--porcelain"], cwd).stdout.strip())


# Senza questo la mutazione puo' misurare il codice VECCHIO: la cache .pyc si
# invalida su (mtime, dimensione) del sorgente, e un revert che cambia una riga
# di pari lunghezza nello stesso secondo la lascia valida. Trovato sul campo il
# 2026-08-11: il file diceva `return 0` e il processo eseguiva `return 1`.
_ENV_NO_CACHE = {"PYTHONDONTWRITEBYTECODE": "1"}


def _purge_bytecode(repo: str) -> None:
    root = Path(repo)
    for d in root.rglob("__pycache__"):
        if ".git" not in d.parts:
            for f in d.glob("*.pyc"):
                f.unlink(missing_ok=True)
            try:
                d.rmdir()
            except OSError:
                pass
    for f in root.rglob("*.pyc"):
        if ".git" not in f.parts:
            f.unlink(missing_ok=True)


def _run_suite(suite: str, repo: str) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(shlex.split(suite), cwd=repo, capture_output=True,
                          text=True, timeout=3600, env={**os.environ, **_ENV_NO_CACHE})


def cmd_run(a) -> int:
    repo = str(a.repo)
    if not (Path(repo) / ".git").exists():
        print(f"non e' un repo git: {repo}", file=sys.stderr)
        return 2
    if _dirty(repo):
        print("working tree sporco: la mutazione richiede un albero pulito, "
              "altrimenti il ripristino non e' sicuro", file=sys.stderr)
        return 2
    if _git(["cat-file", "-e", f"{a.fix_sha}^{{commit}}"], repo).returncode != 0:
        print(f"sha non trovato: {a.fix_sha}", file=sys.stderr)
        return 2
    suite = str(a.suite).strip()
    if not suite:
        print("--suite vuoto: senza comando non si misura niente", file=sys.stderr)
        return 2

    # Prima di mutare: la suite DEVE essere verde. Se parte rossa, qualunque
    # rosso dopo il revert non e' attribuibile alla mutazione.
    _purge_bytecode(repo)
    try:
        pre = _run_suite(suite, repo)
    except FileNotFoundError:
        print(f"comando della suite inesistente: {suite!r}", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired:
        print(f"suite oltre 3600s: {suite!r}", file=sys.stderr)
        return 2
    if pre.returncode != 0:
        print(f"la suite non e' verde PRIMA della mutazione (exit {pre.returncode}): "
              f"un rosso dopo il revert non sarebbe attribuibile. "
              f"{(pre.stdout + pre.stderr).strip()[-300:]}", file=sys.stderr)
        return 2

    rev = _git(["revert", "--no-commit", "--no-edit", a.fix_sha], repo)
    # Caso comune: fix e test vivono nello stesso commit, quindi il revert
    # cancella anche il test e non resta niente da eseguire. `--keep` rimette
    # i path del test come stanno in HEAD: si muta solo il codice di prodotto.
    if rev.returncode == 0 and getattr(a, "keep", None):
        for path in [p.strip() for p in str(a.keep).split(",") if p.strip()]:
            _git(["checkout", "HEAD", "--", path], repo)
    if rev.returncode != 0:
        _git(["revert", "--abort"], repo)
        _git(["checkout", "--", "."], repo)
        print(f"revert non applicabile: {rev.stderr.strip()[:200]}", file=sys.stderr)
        return 2
    try:
        try:
            # dopo il revert la cache va buttata: altrimenti si misura il codice pre-revert
            _purge_bytecode(repo)
            res = _run_suite(suite, repo)
            exit_con_bug, tail = res.returncode, ((res.stdout or "") + (res.stderr or ""))[-1200:]
        except FileNotFoundError:
            print(f"comando della suite inesistente: {suite!r}", file=sys.stderr)
            return 2
        except subprocess.TimeoutExpired:
            print(f"suite oltre 3600s: {suite!r}", file=sys.stderr)
            return 2
    finally:
        _git(["revert", "--abort"], repo)
        _git(["checkout", "--", "."], repo)
        _git(["clean", "-fd"], repo)

    if _dirty(repo):
        print("ATTENZIONE: il ripristino non ha pulito tutto — controlla a mano",
              file=sys.stderr)

    # Un exit != 0 NON basta: pytest esce 4 per errore d'uso e 5 se non ha
    # raccolto test — e il revert puo' benissimo aver cancellato il file di test.
    # Quel caso e' «non lo so», e non lo so si dichiara, non si spaccia per rosso.
    # (Difetto reale trovato sul campo il 2026-08-11: exit 4 «no tests ran»
    # registrato come tornato_rosso=true.)
    NON_CONCLUSIVI = {2, 3, 4, 5}
    segnali_vuoti = ("no tests ran", "file or directory not found",
                     "ERROR: not found", "collected 0 items")
    inconcludente = (exit_con_bug in NON_CONCLUSIVI
                     or any(s in tail for s in segnali_vuoti))
    if inconcludente:
        print(f"la suite NON ha eseguito test col bug rimesso (exit {exit_con_bug}): "
              f"non e' un rosso, e' un'assenza di misura. "
              f"Probabile causa: il revert ha rimosso anche il file di test — "
              f"escludilo dalla mutazione o applica il revert solo al codice di prodotto. "
              f"{tail.strip()[-300:]}", file=sys.stderr)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(), "fix_sha": a.fix_sha,
            "suite": suite, "exit_con_bug": exit_con_bug,
            "tornato_rosso": None, "inconcludente": True, "tail": tail,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2

    tornato_rosso = exit_con_bug != 0
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "fix_sha": a.fix_sha,
        "suite": suite,
        "exit_con_bug": exit_con_bug,
        "tornato_rosso": tornato_rosso,
        "tail": tail,
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not tornato_rosso:
        print("i test restano VERDI col bug rimesso: non provano niente, riscrivili",
              file=sys.stderr)
        return 1
    print(f"ok: col bug rimesso la suite torna rossa (exit {exit_con_bug}) -> {out}")
    return 0


def _selfcheck() -> int:
    import tempfile
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + msg)
        ok = ok and cond

    def g(args, cwd):
        return _git(["-c", "user.email=s@s", "-c", "user.name=s", *args], cwd)

    with tempfile.TemporaryDirectory() as d:
        check(cmd_run(argparse.Namespace(repo=d, fix_sha="x", suite="true",
                                         out=str(Path(d) / "m.json"), keep=None)) == 2,
              "non e' un repo git -> errore d'uso, mai 0")
        repo = Path(d) / "r"
        repo.mkdir()
        g(["init", "-q"], str(repo))
        # il "prodotto": una funzione col bug, e un test che lo esercita
        (repo / "app.py").write_text("def f():\n    return 0\n", encoding="utf-8")
        (repo / "check.py").write_text(
            "import app, sys\nsys.exit(0 if app.f() == 1 else 1)\n", encoding="utf-8")
        g(["add", "app.py", "check.py"], str(repo))
        g(["commit", "-qm", "bug"], str(repo))
        (repo / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        g(["add", "app.py"], str(repo))
        g(["commit", "-qm", "fix"], str(repo))
        fix_sha = g(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        out = repo.parent / "m.json"
        suite = f"{sys.executable} check.py"

        check(cmd_run(argparse.Namespace(repo=str(repo), fix_sha="deadbeef",
                                         suite=suite, out=str(out))) == 2,
              "sha inesistente -> errore d'uso, mai 0")
        check(cmd_run(argparse.Namespace(repo=str(repo), fix_sha=fix_sha,
                                         suite="", out=str(out))) == 2,
              "suite vuota -> errore d'uso, mai 0")
        check(cmd_run(argparse.Namespace(repo=str(repo), fix_sha=fix_sha,
                                         suite="/bin/nonesiste-mai", out=str(out))) == 2,
              "comando della suite inesistente -> errore d'uso, mai 0")
        check(cmd_run(argparse.Namespace(repo=str(repo), fix_sha=fix_sha,
                                         suite=suite, out=str(out))) == 0,
              "il test COPRE il bug: col bug rimesso torna rosso -> PASS")
        check(not _dirty(str(repo)), "il repo e' stato ripristinato dopo la mutazione")
        log = json.loads(out.read_text(encoding="utf-8"))
        check(log["tornato_rosso"] is True and log["fix_sha"] == fix_sha,
              "il mutation-log registra sha e esito reali")
        # un test che NON copre il bug: deve risultare inutile
        (repo / "check.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        g(["add", "check.py"], str(repo))
        g(["commit", "-qm", "test cieco"], str(repo))
        check(cmd_run(argparse.Namespace(repo=str(repo), fix_sha=fix_sha,
                                         suite=suite, out=str(out))) == 1,
              "il test NON copre il bug: resta verde -> FAIL, i test non valgono")
        check(not _dirty(str(repo)), "il repo e' pulito anche dopo il caso rosso")

        # Il difetto trovato sul campo il 2026-08-11, riprodotto fedelmente: il fix
        # e il suo test sono nello STESSO commit, quindi il revert cancella anche il
        # test. La suite non gira, esce 4/5 «no tests ran», e senza questo controllo
        # verrebbe scambiata per un rosso.
        repo2 = Path(d) / "r2"
        repo2.mkdir()
        g(["init", "-q"], str(repo2))
        (repo2 / "app.py").write_text("def f():\n    return 0\n", encoding="utf-8")
        g(["add", "app.py"], str(repo2))
        g(["commit", "-qm", "bug"], str(repo2))
        (repo2 / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (repo2 / "runner.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            "t = Path('test_f.py')\n"
            "if not t.is_file():\n"
            "    print('no tests ran'); sys.exit(5)\n"
            "import app\nsys.exit(0 if app.f() == 1 else 1)\n", encoding="utf-8")
        (repo2 / "test_f.py").write_text("# il test vive nello stesso commit del fix\n",
                                         encoding="utf-8")
        g(["add", "app.py", "runner.py", "test_f.py"], str(repo2))
        g(["commit", "-qm", "fix + test insieme"], str(repo2))
        sha2 = g(["rev-parse", "HEAD"], str(repo2)).stdout.strip()
        out2 = Path(d) / "m2.json"
        check(cmd_run(argparse.Namespace(repo=str(repo2), fix_sha=sha2,
                                         suite=f"{sys.executable} runner.py",
                                         out=str(out2), keep=None)) == 2,
              "il revert cancella il file di test: nessun test gira -> inconcludente, mai rosso")
        log2 = json.loads(out2.read_text(encoding="utf-8"))
        check(log2.get("tornato_rosso") is None and log2.get("inconcludente") is True,
              "il log dichiara 'inconcludente', non un rosso finto")
        check(not _dirty(str(repo2)), "anche il caso inconcludente ripristina l'albero")
        # e la suite rossa PRIMA della mutazione non e' attribuibile
        (repo / "check.py").write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
        g(["add", "check.py"], str(repo))
        g(["commit", "-qm", "test gia rosso"], str(repo))
        check(cmd_run(argparse.Namespace(repo=str(repo), fix_sha=fix_sha,
                                         suite=suite, out=str(out))) == 2,
              "suite gia rossa prima della mutazione -> errore d'uso, non attribuibile")
        # albero sporco: non si mutila un albero con lavoro dentro
        (repo / "sporco.txt").write_text("x", encoding="utf-8")
        check(cmd_run(argparse.Namespace(repo=str(repo), fix_sha=fix_sha,
                                         suite=suite, out=str(out))) == 2,
              "working tree sporco -> errore d'uso, mai toccare lavoro altrui")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="mutation.py")
    ap.add_argument("--selfcheck", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="rimette il bug e rilancia la suite")
    r.add_argument("--repo", required=True)
    r.add_argument("--fix-sha", required=True, dest="fix_sha")
    r.add_argument("--suite", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--keep", help="path (separati da virgola) da NON revertire — "
                                  "tipicamente i file di test che vivono nello "
                                  "stesso commit del fix")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
