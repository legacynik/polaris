#!/usr/bin/env python3
"""sweep_gate.py — decide se una PR puo' fondersi DA SOLA.

La revisione la scrive il modello; l'auto-merge lo decide questo script.
Un verdetto e' prosa: qui diventa un exit code.

Exit: 0 auto-merge consentito · 1 negato (su stderr il perche') · 2 errore
d'uso. Fail-closed: record assente, campo vuoto, SHA diversa da HEAD,
file-list mancante non producono MAI 0.
"""
import argparse
import fnmatch
import re
import sys
from pathlib import Path

VUOTI = {"", ".", "-", "--", "?", "tbd", "todo", "n/a", "na", "none", "null", "<>"}
APPROVE = {"approve", "approve-with-minor"}
ATTESTAZIONI_OK = {"attestata", "non-deployabile"}
# Chi cambia il gate non puo' essere approvato dal gate che sta cambiando:
# una PR che tocca la pipeline si fonde solo con un umano.
PIPELINE = re.compile(
    r"(^|/)\.github/workflows/|(^|/)\.fix/contract\.yml$|(^|/)sweep_gate\.py$"
    r"|(^|/)fix_gate\.py$|(^|/)red_check\.py$")


def read_frontmatter(path: Path) -> dict:
    """Frontmatter YAML piatto -> dict. Stesso parser di fix_gate: niente dipendenze."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
    out = {}
    for line in (m.group(1) if m else text).splitlines():
        mm = re.match(r"^([a-z_][a-z0-9_-]*):\s*(.*)$", line)
        if mm:
            out[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
    return out


def _has(rec: dict, key: str) -> bool:
    v = rec.get(key)
    return v is not None and str(v).strip().lower() not in VUOTI


def _check_record(rec: dict, pr_head: str) -> list:
    errs = []
    for k in ("verdict", "head_sha", "attestazione", "risk"):
        if not _has(rec, k):
            errs.append(f"campo '{k}' assente o vuoto nel run-state: senza, il verdetto "
                        "non e' legato a niente")
    if errs:
        return errs
    if rec["verdict"] not in APPROVE:
        errs.append(f"verdetto '{rec['verdict']}': solo approve/approve-with-minor si fondono")
    if rec["head_sha"] != pr_head:
        errs.append(f"verdetto emesso su {rec['head_sha'][:8]} ma la PR e' a {pr_head[:8]}: "
                    "STALE — la revisione ha letto un codice che non esiste piu'")
    return errs


def _check_prod(rec: dict, files: list, deployabili) -> list:
    """Fuori dal perimetro prod dichiarato l'auto-merge e' il default (founder
    2026-08-17). Dentro — o senza perimetro dichiarato — resta la via stretta."""
    if deployabili is not None:
        prod = [f for f in files
                if any(fnmatch.fnmatch(f, p) or f.startswith(p.rstrip("*").rstrip("/") + "/")
                       for p in deployabili)]
        if not prod:
            return []   # doc, test, tooling: si fonde con approve + SHA fresca
        ragione = f"tocca il perimetro prod ({', '.join(prod[:3])})"
    else:
        ragione = "perimetro 'deployabili' NON dichiarato nel contratto: non si indovina cosa e' prod"
    errs = []
    if rec["risk"] != "trivial":
        errs.append(f"{ragione} e risk '{rec['risk']}': solo risk:trivial si fonde da solo")
    if rec["attestazione"] not in ATTESTAZIONI_OK:
        errs.append(f"{ragione} e attestazione '{rec['attestazione']}': questo codice non e' "
                    "mai stato eseguito da nessuna parte — real test prima del merge")
    return errs


def _read_files(files_path: Path):
    """(files, errs). File assente o vuoto -> mai PASS al buio."""
    if not files_path.is_file():
        return [], [f"file-list inesistente: {files_path} (gh pr diff --name-only > file)"]
    files = [f.strip() for f in files_path.read_text(encoding="utf-8").splitlines() if f.strip()]
    if not files:
        return [], ["file-list vuota: una PR senza file non e' una PR — mai PASS al buio"]
    toccati = [f for f in files if PIPELINE.search(f)]
    if toccati:
        return files, [f"la PR tocca la pipeline ({', '.join(toccati[:3])}): il gate non "
                       "approva chi modifica il gate — merge umano"]
    return files, []


def _load_deployabili(repo):
    """Lista `deployabili` da <repo>/.fix/contract.yml, o None se non dichiarata."""
    if not repo:
        return None
    c = read_frontmatter(Path(repo) / ".fix" / "contract.yml") \
        if (Path(repo) / ".fix" / "contract.yml").is_file() else {}
    v = c.get("deployabili", "")
    if not v or v in ("[]",):
        return None
    return [x.strip().strip('"').strip("'") for x in v.strip("[]").split(",") if x.strip()]


def cmd_automerge(a) -> int:
    run = Path(a.run)
    if not run.is_file():
        print(f"run-state inesistente: {run}", file=sys.stderr)
        return 2
    rec = read_frontmatter(run)
    if not rec:
        print(f"run-state vuoto o senza frontmatter leggibile: {run}", file=sys.stderr)
        return 2
    errs = _check_record(rec, a.pr_head)
    files, file_errs = _read_files(Path(a.files))
    errs += file_errs
    if not errs:
        errs += _check_prod(rec, files, _load_deployabili(a.repo))
    for e in errs:
        print(f"NEGATO: {e}", file=sys.stderr)
    return 1 if errs else 0


def _selfcheck() -> int:
    import tempfile
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + msg)
        ok = ok and cond

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        files = d / "files.txt"
        files.write_text("src/app.py\ntests/test_app.py\n", encoding="utf-8")

        def run(fm, files_path=files, head="aaa111", repo=None):
            p = d / "run.md"
            p.write_text(f"---\n{fm}---\n", encoding="utf-8")
            return cmd_automerge(argparse.Namespace(
                run=str(p), pr_head=head, files=str(files_path), repo=repo))

        buono = ("verdict: approve\nhead_sha: aaa111\nattestazione: attestata\n"
                 "risk: trivial\n")
        check(run(buono) == 0, "verdetto completo, SHA giusta, attestata -> PASS")
        check(cmd_automerge(argparse.Namespace(
            run=str(d / "nope.md"), pr_head="aaa111", files=str(files))) == 2,
            "run-state assente -> errore d'uso, mai 0")
        (d / "vuoto.md").write_text("", encoding="utf-8")
        check(cmd_automerge(argparse.Namespace(
            run=str(d / "vuoto.md"), pr_head="aaa111", files=str(files))) == 2,
            "run-state vuoto -> errore d'uso, mai 0")
        check(run(buono.replace("head_sha: aaa111\n", "")) == 1,
              "head_sha assente -> NEGATO (B3: il verdetto non e' legato al codice)")
        check(run(buono, head="bbb222") == 1,
              "SHA diversa da HEAD -> NEGATO (B3: verdetto stale)")
        check(run(buono.replace("attestazione: attestata", "attestazione: non-attestata")) == 1,
              "non attestata -> NEGATO (B1: mai eseguito da nessuno)")
        check(run(buono.replace("attestazione: attestata", "attestazione: .")) == 1,
              "attestazione placeholder '.' -> NEGATO")
        check(run(buono.replace("attestazione: attestata",
                                "attestazione: non-deployabile")) == 0,
              "non-deployabile (solo doc) -> PASS: attestazione non richiesta")
        check(run(buono.replace("risk: trivial", "risk: medium")) == 1,
              "risk:medium -> NEGATO")
        check(run(buono.replace("verdict: approve", "verdict: request-changes")) == 1,
              "request-changes -> NEGATO")
        pipe = d / "pipe.txt"
        pipe.write_text("src/app.py\n.github/workflows/ci.yml\n", encoding="utf-8")
        check(run(buono, files_path=pipe) == 1,
              "la PR tocca .github/workflows -> NEGATO (B2: il gate non approva chi lo modifica)")
        check(run(buono, files_path=d / "niente.txt") == 1,
              "file-list inesistente -> NEGATO, mai PASS al buio")
        (d / "empty.txt").write_text("", encoding="utf-8")
        check(run(buono, files_path=d / "empty.txt") == 1, "file-list vuota -> NEGATO")

        # B4: fuori dal perimetro prod dichiarato l'auto-merge e' il default
        repo = d / "repo"
        (repo / ".fix").mkdir(parents=True)
        (repo / ".fix" / "contract.yml").write_text(
            "deployabili: [src/*, app/*]\n", encoding="utf-8")
        docs = d / "docs.txt"
        docs.write_text("docs/README.md\ntests/test_x.py\n", encoding="utf-8")
        medio = buono.replace("risk: trivial", "risk: medium") \
                     .replace("attestazione: attestata", "attestazione: non-attestata")
        check(run(medio, files_path=docs, repo=str(repo)) == 0,
              "B4: fuori dal perimetro prod -> PASS anche con risk:medium non attestata")
        check(run(medio, repo=str(repo)) == 1,
              "dentro il perimetro prod (src/) + risk:medium -> NEGATO")
        check(run(buono, repo=str(repo)) == 0,
              "dentro il perimetro prod + risk:trivial attestata -> PASS")
        check(run(medio, files_path=docs, repo=None) == 1,
              "perimetro NON dichiarato -> via stretta: risk:medium NEGATO, mai indovinare")
        pipedocs = d / "pipedocs.txt"
        pipedocs.write_text("docs/README.md\n.github/workflows/ci.yml\n", encoding="utf-8")
        check(run(medio, files_path=pipedocs, repo=str(repo)) == 1,
              "pipeline batte perimetro: NEGATO anche se fuori da deployabili")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="sweep_gate.py")
    ap.add_argument("--selfcheck", action="store_true")
    sub = ap.add_subparsers(dest="azione")   # mai dest="cmd": collisione B1 di tdd-red
    m = sub.add_parser("automerge", help="questa PR puo' fondersi da sola?")
    m.add_argument("--run", required=True, help="run-state della sweep (frontmatter)")
    m.add_argument("--pr-head", required=True, help="SHA di testa VIVA della PR (da gh)")
    m.add_argument("--files", required=True, help="file coi path toccati, uno per riga")
    m.add_argument("--repo", default=None,
                   help="checkout del repo: legge 'deployabili' da .fix/contract.yml — "
                        "fuori da quel perimetro l'auto-merge e' il default")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    if a.azione == "automerge":
        return cmd_automerge(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
