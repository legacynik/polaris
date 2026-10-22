"""tabelle_pr — the criteria table under `### #n`, read the way GitHub renders it (used by controlla_pr)."""
from __future__ import annotations

import re

ESITI = {"✅", "❌", "🟡", "⚠", "⚠️"}
SENZA_PROVA = {"", "-", "—", "–", "n/d", "n/a", "tbd", "todo", "x", ".", "...", "…"}  # pr_status.PLACEHOLDER and more
SEP = re.compile(r":?-+:?")


def celle(riga: str) -> list[str]:
    """The cells of one row: `\\|` is a literal pipe, inside a code span too (GitHub's rule)."""
    parti = re.split(r"(?<!\\)\|", riga.strip())
    parti = parti[1:] if parti and parti[0] == "" else parti
    parti = parti[:-1] if parti and parti[-1] == "" else parti
    return [p.strip().replace("\\|", "|") for p in parti]


def tabella(corpo: str, n: int) -> tuple[list[list[str]], list[bool]]:
    """Every table row under the issue's own `### #n` heading, and which of them is a `|---|` line."""
    m = re.search(rf"(?m)^### #{n}\b.*$", corpo)
    if not m:
        return [], []
    fine = re.search(r"(?m)^##+ ", corpo[m.end():])
    blocco = corpo[m.end(): m.end() + fine.start()] if fine else corpo[m.end():]
    tutte = [celle(r) for r in blocco.splitlines() if r.startswith("|")]
    return tutte, [all(SEP.fullmatch(x) for x in c) for c in tutte]


def righe_issue(corpo: str, n: int) -> list[list[str]]:
    """The rows but the header and its `|---|` line: a row with an unknown mark or no number stays in."""
    tutte, sep = tabella(corpo, n)
    sep = sep + [False]
    return [c for i, c in enumerate(tutte) if not sep[i] and not sep[i + 1]]


def errore_larghezza(corpo: str, n: int) -> list[str]:
    """A row with more or fewer cells than its header is misread: an unescaped `|` in the text, usually."""
    tutte, sep = tabella(corpo, n)
    testa = next((len(tutte[i - 1]) for i in range(1, len(tutte)) if sep[i]), None)
    if testa is None or all(len(c) == testa for i, c in enumerate(tutte) if not sep[i]):
        return []
    return [f"#{n}: una riga ha più o meno celle dell'intestazione ({testa}): un «|» nel testo si scrive «\\|»"]


def errori_issue(corpo: str, n: int, parola: str, attesi: list[str]) -> list[str]:
    righe = righe_issue(corpo, n)
    if parola != "closes":
        return []  # only Closes does harm at merge; Refs rows are welcome, never demanded
    if not righe:
        return [f"#{n}: nessuna riga di criteri sotto «### #{n}»"]
    numeri, k = sorted(r[0] for r in righe), len(attesi) or len(righe)  # nothing to count: the rows count
    errori = [] if numeri == sorted(str(i) for i in range(1, k + 1)) else [
        f"#{n}: colonna # {numeri}, l'issue ne ha {k}: ogni numero da 1 a {k} una volta sola"]
    if any("✅" in "".join(r) and (len(r) < 4 or r[-1].lower() in SENZA_PROVA) for r in righe):
        errori.append(f"#{n}: una riga ✅ senza prova nell'ultima colonna")
    if any(len(r) < 4 or r[-2] not in ESITI for r in righe):
        errori.append(f"#{n}: una riga senza esito leggibile (✅ ❌ 🟡 ⚠)")
    if any(len(r) < 4 or r[-2] != "✅" for r in righe):  # the cell IS the tick, it does not merely hold one
        errori.append(f"#{n}: non tutti i criteri sono ✅, quindi Refs e non Closes")
    return errori


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:
        ok = celle("| 1 | `t[a\\|b]` | ✅ |") == ["1", "`t[a|b]`", "✅"] and errore_larghezza(
            "### #1 t\n| # | a |\n|---|---|\n| 1 | b | c |\n", 1) != []
        print(f"tabelle_pr selfcheck: {'ok' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)
