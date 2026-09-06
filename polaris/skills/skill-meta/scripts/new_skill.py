#!/usr/bin/env python3
"""Scaffold di una nuova skill — valida-per-costruzione, non a posteriori.

Crea <root>/<slug>/ con SKILL.md (tutte le chiavi obbligatorie presenti),
references/bypass-test.md (stub) e scripts/ vuota. Il T1 (_standard/validate_suite.py)
deve passare sullo scaffold grezzo, prima ancora che il contenuto sia scritto — è come
il gate strutturale (G2.3: gate esiste, nessun runner lo chiama) diventa un default
invece di una promessa: non reimplementa il T1, lo shella (single source of truth).

    new_skill.py <slug> [--root DIR] [--donor SLUG ...]
    new_skill.py --check <root>       # shella su _standard/validate_suite.py
    new_skill.py --selfcheck
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

TEMPLATE = '''---
name: {slug}
description: "TODO: Use when <trigger osservabile> — terza persona, niente riassunto del workflow"
version: 0.1.0
user-invocable: true
auto: false
lifecycle: "TODO: artefatti prodotti -> chi li drena, quando"
invokes: []
invoked-by: []
io: "TODO: riceve X -> produce Y"
status: draft
---

# {slug}

## Overview
TODO — un principio, non una lista di feature.

## Quando NON usarla
TODO — "sempre X" senza condizioni e' un bug (obbligatorio, non opzionale).

## Quick reference
| comando | quando | blocca? |
|---|---|---|

## Origine
{origin_line}
'''

BYPASS_STUB = """# Bypass-test — TODO

Il test che DEVE fallire se il gate viene aggirato. Comando riproducibile + esito atteso.
Non lasciare questo stub: uno stub e' "dichiarato", non "blindato" (SKILL-STANDARD.md).
"""


def find_standard(start: Path) -> Path | None:
    """Risale da `start` cercando una cartella _standard/validate_suite.py sorella.
    Non duplica il T1: lo shella. Se non lo trova, chi chiama fallisce rumoroso —
    mai passare in silenzio (vedi 'Quando NON usarla' in SKILL.md)."""
    for up in (start, *start.parents):
        cand = up / "_standard" / "validate_suite.py"
        if cand.exists():
            return cand
    return None


def scaffold(slug: str, root: Path, donors: list[str]) -> Path:
    d = root / slug
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    (d / "references").mkdir(parents=True, exist_ok=True)
    origin = (f"ADATTA/FONDE da: {', '.join(donors)} — questa skill deve pesare MENO "
              "righe (SKILL.md) della donatrice piu' pesante, mai frankenstein."
              if donors else "NUOVA — nessun donatore, costruita da evidenza diretta.")
    (d / "SKILL.md").write_text(TEMPLATE.format(slug=slug, origin_line=origin))
    (d / "references" / "bypass-test.md").write_text(BYPASS_STUB)
    return d


def check(root: Path) -> int:
    std = find_standard(root)
    if std is None:
        print("T1 non eseguibile: _standard/validate_suite.py non trovato risalendo da "
              f"{root} — skill-meta richiede un checkout di skills-suite. Non promuovere "
              "una skill senza T1 verde: fallire rumoroso, mai passare in silenzio.")
        return 2
    return subprocess.run([sys.executable, str(std), str(root)]).returncode


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        d = scaffold("demo-skill", root, donors=["skill-creator"])
        assert (d / "SKILL.md").exists() and (d / "references" / "bypass-test.md").exists()
        assert find_standard(root) is None, "un tmpdir isolato non deve trovare uno _standard estraneo"
        real_std = find_standard(Path(__file__).resolve())
        assert real_std is not None, "dal proprio bundle, _standard va trovato risalendo"
        rc = subprocess.run([sys.executable, str(real_std), str(root)]).returncode
        assert rc == 0, "lo scaffold grezzo deve passare il T1 reale, non una copia"
        broken = (d / "SKILL.md").read_text().replace("## Quando NON usarla", "## rimossa")
        (d / "SKILL.md").write_text(broken)
        rc2 = subprocess.run([sys.executable, str(real_std), str(root)]).returncode
        assert rc2 == 1, "senza 'Quando NON usarla' il T1 reale deve rifiutare"
    print("SELFCHECK OK — scaffold valido-per-costruzione, T1 reale integrato (non copiato)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("slug", nargs="?")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--donor", action="append", default=[])
    p.add_argument("--check", action="store_true")
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()
    if a.check:
        # `--check <root>` is the documented form, so the positional IS the root there.
        # Before this line it landed in `slug` and the check silently ran on the CWD —
        # a green belonging to another tree, read as a green for this skill (bypass B6).
        return check(Path(a.slug) if a.slug else a.root)
    if not a.slug:
        p.error("serve <slug> (o --check / --selfcheck)")
    d = scaffold(a.slug, a.root, a.donor)
    print(f"scaffold creato: {d}")
    return check(d.parent)


if __name__ == "__main__":
    sys.exit(main())
