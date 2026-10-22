#!/usr/bin/env python3
"""controlla_pr — is this PR body something the owner can merge from without reading code?

Blocks only what does harm: no decision on top, `Closes` on an issue whose criteria are not all ✅ or
answered, an unfilled placeholder, several issues behind one keyword, no screenshot when the change
surely touches the interface, an empty body or an unreadable issue. The rest only warns.

    controlla_pr.py --body body.md (--pr <n> [-R owner/name] [--head <sha>] | --visuale | --no-visuale)
    controlla_pr.py --verifica-pubblicato <n> [-R owner/name]  |  --selfcheck
The command line lives in vivo_pr. Exit 0 pass, 1 blocked, 2 cannot decide, 3 warnings.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rete_pr  # noqa: E402  every GitHub read, through one runner
from avvisi_pr import avvisi  # noqa: E402  the warnings, never blocking
from tabelle_pr import errore_larghezza, errori_issue, righe_issue  # noqa: E402,F401  the criteria table
from visuale_pr import NonSo, tocca_ui, ui_da_file  # noqa: E402,F401  re-exported to the hook and babysit

TESTA = ("## In breve", "## In short")
DECISIONE = re.compile(r"(?i)\*\*(decisione richiesta|decision)\s*(?::\*\*|\*\*\s*:)[ \t]*[^\s<]")
CRIT_TITOLO = re.compile(r"(?i)^#+ .*(acceptance|criteri|adversarial|verifica|definition of done|\bdod\b|"
                         r"requisit|requirement|done when|exit criteri)")
CASELLA = re.compile(r"^\s*[-*] \[[ xX]\] +(.+?)\s*$")
PUNTO = re.compile(r"^(?:\d+[.)]|[-*+])\s+(?!\[[ xX]\])(.+?)\s*$")  # top level only, never a nested point
FIX_TITOLO = re.compile(r"(?i)^#+ .*\bfix\b")
TITOLO = re.compile(r"^#{1,6}\s")  # an ATX heading at column 0; `#1700 broke it` or `   # comment` is not one
RECINTO = re.compile(r"^\s*(```|~~~)")
CHIUDE = re.compile(r"(?i)\b(close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b:?\s+"
                    r"(?:https://github\.com/[\w.-]+/[\w.-]+/issues/|[\w.-]+/[\w.-]+#|#)(\d+)")
ELENCO = re.compile(r"#\d+\s*(?:,|\band\b|\be\b|&)\s*(?:[\w.-]+/[\w.-]+)?#\d+")
RIF = re.compile(r"(?im)^\s*(refs?|references?)\b:?\s+(.*)$")
FINTO = re.compile(r"(?im)^\W*(chiud|risolv|sistem)\w*\s+#\d+")
SEGNAPOSTO = re.compile(r"<(?!/?(?:img|br|details|summary|sub|sup|kbd|a|p|b|i|table|thead|tbody|tr|td|th|video|"
                        r"source|div|span|picture|code|em|strong|ul|ol|li|hr|h\d)\b)(?!!--)(?!https?:)(?![\d\s=/])"
                        r"[^<>\n]{1,80}>")


def senza_codice(corpo: str) -> str:
    return re.sub(r"`[^`\n]+`", "", re.sub(r"```.*?```", "", corpo, flags=re.S))


def fuori_codice(testo: str) -> list[str]:
    """The lines outside fenced code blocks (``` or ~~~): a `#` or a checkbox in code is not the issue's."""
    out, recinto = [], ""
    for riga in testo.splitlines():
        m = RECINTO.match(riga)
        if m and (not recinto or m.group(1) == recinto):
            recinto = "" if recinto else m.group(1)
        elif not recinto:
            out.append(riga)
    return out


def caselle(testo: str) -> list[str]:
    """Checkboxes under a criteria heading, once each; if none is under one, every checkbox counts."""
    sotto, tutte, dentro = [], [], False
    for riga in fuori_codice(testo):
        if TITOLO.match(riga):
            dentro = bool(CRIT_TITOLO.match(riga.strip()))
            continue
        m = CASELLA.match(riga)
        if m and m.group(1) not in tutte:
            tutte.append(m.group(1))
        if m and dentro and m.group(1) not in sotto:
            sotto.append(m.group(1))
    return sotto or tutte


def punti(testo: str) -> list[str]:
    """The top-level numbered or bulleted points under a criteria or «Fix» heading, once each, in order."""
    out, dentro = [], False
    for riga in fuori_codice(testo):
        if TITOLO.match(riga):
            dentro = bool(CRIT_TITOLO.match(riga.strip()) or FIX_TITOLO.match(riga.strip()))
            continue
        m = PUNTO.match(riga) if dentro else None
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def criteri(testo: str) -> list[str]:
    """What the `#` column numbers: the checkboxes; an issue with none, its points (the skill's contract)."""
    return caselle(testo) or punti(testo)


def riferimenti(corpo: str) -> tuple[dict[int, str], list[str]]:
    """`{issue: keyword}` from closing words anywhere and `Refs` lines, and every conflict."""
    vivo, trovati, errori = senza_codice(corpo), {}, []
    for m in RIF.finditer(vivo):
        numeri = re.findall(r"#(\d+)", m.group(2))
        if len(numeri) > 1:
            errori.append(f"«{m.group(0).strip()}»: una riga per issue")
        trovati.update({int(n): "refs" for n in numeri})
    for riga in vivo.splitlines():
        chiusi = CHIUDE.findall(riga)
        if chiusi and ELENCO.search(riga):
            errori.append(f"«{riga.strip()}»: una riga per issue, GitHub chiude solo la prima")
        for _, n in chiusi:
            if trovati.get(int(n)) == "refs":
                errori.append(f"#{n} sotto due parole chiave (Closes e Refs): GitHub la chiude comunque")
            trovati[int(n)] = "closes"
    return trovati, errori


def repo_di(corpo: str, n: int) -> str | None:
    """`owner/repo` written with `#n` or in its issue URL; None for an issue of the PR's own repo.
    ponytail: the first match wins, so one body closing #n in two repositories reads the first."""
    m = re.search(rf"github\.com/([\w.-]+/[\w.-]+)/issues/{n}\b|([\w.-]+/[\w.-]+)#{n}\b", senza_codice(corpo))
    return (m.group(1) or m.group(2)) if m else None


def errori_testa(vivo: str) -> list[str]:
    prima = next((s for s in re.split(r"(?m)^(?=## )", vivo) if s.startswith("## ")), "")
    errori = [] if prima.startswith(TESTA) else ["la prima sezione deve essere «## In breve»"]
    if not DECISIONE.search(prima):
        errori.append("manca «**Decisione richiesta:**» con la decisione, in «In breve»")
    if posti := SEGNAPOSTO.findall(vivo):
        errori.append(f"segnaposto non compilati: {', '.join(sorted(set(posti))[:5])}")
    return errori


def controlla(corpo: str, issues: dict[int, list[str]], visuale: bool | None) -> list[str]:
    """Every reason the owner could not merge from this body; empty list = it stands."""
    if not corpo.strip():
        return ["corpo vuoto"]
    rif, errori = riferimenti(corpo)
    vivo = senza_codice(corpo)
    errori += [f"«{m.group(0).strip()}» non chiude niente su GitHub: una riga «Closes #n» per issue"
               for m in FINTO.finditer(vivo)]
    in_breve = re.split(r"(?m)^## (?!In breve|In short)", vivo)[0]
    if not rif and not re.search(r"(?i)nessuna issue|no linked issue", in_breve):
        errori.append("nessuna issue collegata: righe Closes/Refs con i criteri, o «Nessuna issue» in «In breve»")
    errori += errori_testa(vivo)
    if visuale and "<img" not in vivo and "![" not in vivo:
        errori.append("il cambio tocca l'interfaccia: servono le foto, un passo per titolo")
    for n, parola in rif.items():
        errori += errore_larghezza(corpo, n) + errori_issue(corpo, n, parola, issues.get(n, []))
    return errori


def leggi_issue(n: int, repo: str | None) -> list[str]:
    return criteri(rete_pr.issue(n, repo)["testo"])


def selfcheck() -> int:
    buono = ("## In breve\nx\n\n**Decisione richiesta:** merge sì\n\nCloses #1\n\n## Criteri delle issue\n"
             "### #1 x\n| 1 | a | ✅ | test t |\n## Cosa cambia\nx\n## Decisioni\nx\n## Prove\n![a](u)\n"
             "## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")
    casi = [controlla(buono, {1: ["a"]}, True) == [], bool(controlla("", {}, False)),
            bool(controlla(buono.replace("✅", "🟡"), {1: ["a"]}, True)),
            bool(controlla(buono, {1: ["a", "b"]}, True)),
            bool(controlla(buono.replace("Closes #1", "Closes #1, #2"), {1: ["a"]}, True)),
            controlla(buono.replace("![a](u)", ""), {1: ["a"]}, None) == [],
            bool(controlla(buono.replace("merge sì", "<merge sì>"), {1: ["a"]}, True)),
            bool(avvisi(buono + "uno — due")) and not controlla(buono + "uno — due", {1: ["a"]}, True),
            criteri("## Acceptance criteria\n- [ ] a\n## Altro\n- [ ] b\n## Adversarial\n- [ ] a\n") == ["a"]]
    print(f"controlla_pr selfcheck: {sum(casi)}/{len(casi)}")
    return 0 if all(casi) else 1


def main(argv: list[str] | None = None) -> int:
    import vivo_pr  # the command line, a sibling that imports this module: loaded late, never at import
    return vivo_pr.main(argv)


if __name__ == "__main__":
    sys.exit(main())
