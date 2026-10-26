"""avvisi_pr — what a careful PR writer fixes but nobody is stopped for (used by controlla_pr)."""
from __future__ import annotations

import re

SEZIONI = (("## Cosa cambia", "## What changes"), ("## Decisioni", "## Decisions"),
           ("## Prove", "## Proof"), ("## Cosa resta aperto", "## Still open"),
           ("## Rischio del merge", "## Merge risk"))
SU_RAMO = re.compile(r"(?:github\.com/[\w.-]+/[\w.-]+/(?:blob|raw)|raw\.githubusercontent\.com/[\w.-]+/[\w.-]+)"
                     r"/(?![0-9a-f]{7,40}/)[^/\s]+/")
MERMAID_RISCHIO = re.compile(r"(\[[^\"\]][^\]]*[(){}:«»][^\]]*\]|\|[^\"|][^|]*[(){}:«»][^|]*\|)")


def senza_codice(corpo: str) -> str:
    return re.sub(r"```.*?```", "", corpo, flags=re.S)


def avvisi(corpo: str, visuale: bool | None = None) -> list[str]:
    """Warnings, shown and never blocking."""
    vivo = senza_codice(corpo)
    titoli = {s.splitlines()[0].strip(): s for s in re.split(r"(?m)^(?=## )", vivo) if s.startswith("## ")}
    out = [f"sezione «{n[0]}» mancante o vuota" for n in SEZIONI
           if not any(t in titoli and "".join(titoli[t].splitlines()[1:]).strip() for t in n)]
    if visuale is None and "<img" not in vivo and "![" not in vivo:
        out.append("non so se il cambio si vede: se sì, servono le foto")
    if any(MERMAID_RISCHIO.search(b) for b in re.findall(r"```mermaid\n(.*?)```", corpo, re.S)):
        out.append("Mermaid: etichetta con ( ) { } : o «» senza virgolette, GitHub può non disegnarla")
    if SU_RAMO.search(vivo):
        out.append("immagine legata a un ramo: si sposta col ramo, legala a un commit (blob/<sha>/...)")
    if "—" in corpo:
        out.append("trattino lungo (em dash): meglio una virgola, i due punti o una frase nuova")
    return out


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:
        ok = bool(avvisi("## In breve\nx\nuno — due\n")) and avvisi(
            "## In breve\nx\n## Cosa cambia\nx\n## Decisioni\nx\n## Prove\n![a](u)\n"
            "## Cosa resta aperto\nx\n## Rischio del merge\nx\n", False) == []
        print(f"avvisi_pr selfcheck: {'ok' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)
