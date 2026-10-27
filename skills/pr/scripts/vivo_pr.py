"""vivo_pr — controlla_pr's command line: reads the PR and its issues on GitHub, then judges the body.

The visible-change rule comes from the PR's own files (`--pr`) or an explicit flag, never from the
branch checked out where the command runs. Exit 0 pass, 1 blocked, 2 cannot decide, 3 warnings.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import controlla_pr as cp
import rete_pr
import visuale_pr

SENZA_CASELLE = re.compile(r"(?i)^\s*\**issue (senza caselle|without checkboxes)")


def opzioni(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=(cp.__doc__ or "").split("\n")[0])
    for opt in ("--body", "--pr", "--head", "--verifica-pubblicato"):
        ap.add_argument(opt)
    ap.add_argument("--repo", "-R")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--visuale", action=argparse.BooleanOptionalAction, default=None)
    return ap.parse_args(argv)


def rifiuto(a: argparse.Namespace) -> str:
    """Why the command cannot judge, or empty."""
    if not a.body or not Path(a.body).is_file():
        return "--body <file> richiesto"
    if a.head and not a.pr:
        return "--head vuole --pr <n>: la head della bozza si confronta con quella della PR"
    if a.head and not re.fullmatch(r"[0-9a-f]{7,40}", a.head):
        return "--head: uno SHA di almeno 7 caratteri esadecimali"
    if a.visuale is None and not a.pr:
        return ("non so quali file tocca la PR: passa --pr <n> [-R o/r], o --visuale / --no-visuale "
                "(la cartella da cui lanci il comando non è la PR)")
    return ""


def avvisi_issue(corpo: str, n: int, testo: str) -> list[str]:
    """An issue with no checkbox is judged on its points, and the body says so under `### #n`."""
    if cp.caselle(testo):
        return []
    if not cp.punti(testo):
        return [f"#{n}: l'issue non ha caselle né punti sotto criteri o «Fix»: la colonna # non ha un confronto"]
    m = re.search(rf"(?m)^### #{n}\b.*\n+(.*)", corpo)
    if m and SENZA_CASELLE.match(m.group(1)):
        return []
    return [f"#{n}: issue senza caselle, scrivi sotto «### #{n}» «Issue senza caselle: righe = «Fix» 1-k»"]


def visuale(a: argparse.Namespace, dati: dict) -> bool:
    return cp.ui_da_file([f["path"] for f in dati["files"]]) if a.visuale is None else a.visuale


def errori_vivi(corpo: str, a: argparse.Namespace, letto: tuple[dict, dict]) -> list[str]:
    lette, dati = letto
    rif, head = cp.riferimenti(corpo)[0], dati.get("headRefOid", "")
    errori = [f"la head della PR è {head[:7]}, la bozza è scritta su {a.head}: rileggi la PR e riscrivi"
              ] if a.head and not head.startswith(a.head) else []
    errori += [f"#{n} è una pull request: Closes non la chiude, scrivi «Sostituisce #{n}» nel testo"
               for n, v in lette.items() if v["pr"] and rif[n] == "closes"]
    issues = {n: cp.criteri(v["testo"]) for n, v in lette.items() if not v["pr"]}
    return errori + cp.controlla(corpo, issues, visuale(a, dati))


def note_vive(corpo: str, a: argparse.Namespace, letto: tuple[dict, dict]) -> list[str]:
    lette, dati = letto
    rif = cp.riferimenti(corpo)[0]
    note = [f"#{n} è una pull request: nominala nel testo («Sostituisce #{n}»), non in Refs"
            for n, v in lette.items() if v["pr"] and rif[n] == "refs"]
    for n, v in lette.items():
        note += avvisi_issue(corpo, n, v["testo"]) if not v["pr"] and rif[n] == "closes" else []
    note += cp.avvisi(corpo, visuale(a, dati)) + rete_pr.immagini_mancanti(corpo) + forzato(a, dati)
    return note + (rete_pr.avviso_ricevuta(corpo, dati["headRefOid"]) if dati else [])


def forzato(a: argparse.Namespace, dati: dict) -> list[str]:
    """`--no-visuale` stays an escape hatch on a PR that touches the interface, never a silent one."""
    ui = [f["path"] for f in dati.get("files", []) if visuale_pr.UI.search(f["path"])]
    if a.visuale is not False or not ui:
        return []
    return [f"--no-visuale su una PR che tocca l'interfaccia ({', '.join(ui[:5])}): niente foto solo se nulla si vede"]


def numeri(s: set[int]) -> str:
    return " ".join(f"#{k}" for k in sorted(s)) or "nessuna"


def pubblicato(n: str, repo: str | None) -> int:
    """After `gh pr edit`: the issues GitHub will close must be the body's `Closes` lines."""
    try:
        dati = rete_pr.pr(n, repo, "body,closingIssuesReferences")
        voluti = {k for k, p in cp.riferimenti(dati["body"])[0].items() if p == "closes"}
        visti = {i["number"] for i in dati["closingIssuesReferences"]}  # ponytail: numbers only, cross-repo twins collide
    except rete_pr.LETTURA as e:
        print(f"non si verifica: PR illeggibile ({e})", file=sys.stderr)
        return 2
    if voluti == visti:
        print("✓ GitHub chiude le issue delle righe Closes")
        return 0
    print(f"✗ Closes nel corpo: {numeri(voluti)}; GitHub chiude: {numeri(visti)}. Appena pubblicato? "
          "GitHub ricalcola in pochi secondi: riprova, poi correggi le righe")
    return 1


def main(argv: list[str] | None = None) -> int:
    a = opzioni(argv)
    if a.selfcheck:
        return cp.selfcheck()
    if a.verifica_pubblicato:
        return pubblicato(a.verifica_pubblicato, a.repo)
    if perche := rifiuto(a):
        print(perche, file=sys.stderr)
        return 2
    corpo = Path(a.body).read_text(encoding="utf-8")
    try:
        lette = {n: rete_pr.issue(n, cp.repo_di(corpo, n) or a.repo) for n in cp.riferimenti(corpo)[0]}
        dati = rete_pr.pr(a.pr, a.repo, "files,headRefOid") if a.pr else {}
        errori, note = errori_vivi(corpo, a, (lette, dati)), note_vive(corpo, a, (lette, dati))
    except rete_pr.LETTURA as e:
        print(f"non si giudica: issue, PR o immagini illeggibili ({e})", file=sys.stderr)
        return 2
    print("\n".join([f"✗ {e}" for e in errori] + [f"· {n}" for n in note]) or "✓ la PR si giudica da sola")
    return 1 if errori else 3 if note else 0


if __name__ == "__main__":
    sys.exit(main())
