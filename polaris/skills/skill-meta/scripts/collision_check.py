#!/usr/bin/env python3
"""T2a — collisione di description contro il catalogo, TF-IDF stdlib puro.

Risponde alla discovery rotta (review -> 15 candidati, triage -> 2, baseline B0): una
description quasi-duplicata di un'altra fa perdere il trigger a entrambe. Doppia soglia,
non una sola: WARN a 0.50, BLOCK a 0.75 (algoritmo standard, reimplementato da zero — zero
testo preso dalle fonti minate). Collidere con la propria donatrice durante ADATTA/FONDE e'
atteso: --donor la declassa da BLOCK a BLOCK-atteso senza fermare il gate.

    collision_check.py --desc "..." --catalog-dir DIR [--donor SLUG ...]
    collision_check.py --skill DIR --catalog-dir DIR [--donor SLUG ...]
    collision_check.py --selfcheck
"""
from __future__ import annotations
import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import frontmatter  # noqa: E402 — one frontmatter parser, block-bounded

WARN, BLOCK = 0.50, 0.75
# One tokenizer for the whole suite: _standard/collision_check.py owns it (stems plurals,
# strips stopwords). Two tokenizers gave the same description different verdicts.
def _standard_module():
    import importlib.util
    path = Path(__file__).resolve().parents[2] / "_standard" / "collision_check.py"
    spec = importlib.util.spec_from_file_location("std_collision", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_STD = _standard_module()


def tokenize(text: str) -> list[str]:
    return _STD.tokens(text)


def read_description(skill_md: Path) -> str:
    # Block-bounded via _lib: a body table containing `description:` must not shadow the
    # real trigger text (the old whole-file regex did exactly that).
    return frontmatter(skill_md.read_text(errors="replace")).get("description", "")


def scan_catalog(catalog_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in catalog_dir.glob("*/SKILL.md"):
        desc = read_description(f)
        if desc:
            out[f.parent.name] = desc
    return out


def tfidf_vectors(docs: dict[str, str]) -> dict[str, Counter]:
    """Smooth-idf (formula sklearn `smooth_idf=True`: log((n+1)/(df+1)) + 1), non la
    variante grezza: senza il '+1' un termine presente in TUTTI i documenti del corpus
    prende peso esattamente zero — a catalogo piccolo (bootstrap della suite, poche
    decine di skill) questo azzera anche i termini che DISTINGUONO due description quasi
    identiche, perche' compaiono in entrambe = 'ovunque' quando n e' piccolo. Bug reale,
    trovato eseguendo il bypass-test #2 (references/bypass-test.md), non solo letto."""
    tokenized = {k: tokenize(v) for k, v in docs.items()}
    df: Counter = Counter()
    for toks in tokenized.values():
        df.update(set(toks))
    n = max(len(tokenized), 1)
    vecs = {}
    for k, toks in tokenized.items():
        tf = Counter(toks)
        vecs[k] = Counter({t: c * (math.log((n + 1) / (df[t] + 1)) + 1.0) for t, c in tf.items()})
    return vecs


def cosine(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    da = math.sqrt(sum(v * v for v in a.values())) or 1.0
    db = math.sqrt(sum(v * v for v in b.values())) or 1.0
    return num / (da * db)


def check(candidate: str, catalog: dict[str, str], donors: set[str]) -> tuple[int, list[str]]:
    """Ritorna (exit_code, righe). BLOCK -> 1, a meno che il match non sia un donatore
    dichiarato (collidere con la propria donatrice durante ADATTA/FONDE e' atteso)."""
    docs = dict(catalog)
    docs["__candidate__"] = candidate
    vecs = tfidf_vectors(docs)
    cand_vec = vecs["__candidate__"]
    rows: list[str] = []
    hard_fail = False
    for slug, vec in vecs.items():
        if slug == "__candidate__":
            continue
        sim = cosine(cand_vec, vec)
        if sim >= BLOCK:
            if slug in donors:
                rows.append(f"BLOCK-atteso (donatore dichiarato): {slug} {sim:.0%}")
            else:
                rows.append(f"BLOCK: {slug} {sim:.0%} — due skill non discriminano, "
                            "una delle due description deve cambiare")
                hard_fail = True
        elif sim >= WARN:
            rows.append(f"WARN: {slug} {sim:.0%} — vicino, non ancora un blocco")
    return (1 if hard_fail else 0), rows


def selfcheck() -> int:
    catalog = {
        "review": "Use when reviewing a pull request for correctness before merge",
        "plan-review": "Use when reviewing a written plan before execution starts",
        "triage": "Use when a new bug report or feature request needs prioritization",
    }
    rc, rows = check("Use when reviewing a pull request for correctness before merge, twin",
                      catalog, donors=set())
    assert rc == 1, f"quasi-identica a 'review' deve bloccare: {rows}"
    rc2, rows2 = check("Use when reviewing a pull request for correctness before merge, twin",
                        catalog, donors={"review"})
    assert rc2 == 0, f"collisione con un donatore dichiarato non deve bloccare: {rows2}"
    rc3, rows3 = check("Use when host disk usage crosses 90 percent", catalog, donors=set())
    assert rc3 == 0 and not rows3, f"description distinta non deve dare match: {rows3}"
    print("SELFCHECK OK — 3 rami provati: blocco, donatore esente, nessun match")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--desc")
    p.add_argument("--skill", type=Path)
    p.add_argument("--catalog-dir", type=Path)
    p.add_argument("--donor", action="append", default=[])
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not a.catalog_dir:
        p.error("serve --catalog-dir (o --selfcheck)")
    candidate = a.desc or (read_description(a.skill / "SKILL.md") if a.skill else "")
    if not candidate:
        p.error("serve --desc o --skill con una description non vuota")
    catalog = scan_catalog(a.catalog_dir)
    # A skill living inside the catalog it is checked against matched ITSELF at 100% and
    # blocked every time, so the documented form was unusable and got skipped (bypass B7).
    if a.skill:
        catalog.pop(a.skill.resolve().name, None)
    if not catalog:
        print("nessuna skill con cui collidere nel catalogo: T2a non e' eseguibile qui "
              "(catalogo vuoto o solo la skill stessa) — exit 2, non un verde")
        return 2
    rc, rows = check(candidate, catalog, donors=set(a.donor))
    for r in rows:
        print(r)
    if not rows:
        print(f"nessuna collisione su {len(catalog)} skill del catalogo")
    return rc


if __name__ == "__main__":
    sys.exit(main())
