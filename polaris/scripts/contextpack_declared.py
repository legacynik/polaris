#!/usr/bin/env python3
"""L2-T4 (#403) — the declared layer of the ContextPack.

The sealed layer answers what HEAD proves; the flight layer what a repository is doing.
Neither answers for what the product repositories are made of: 27 prose ADRs in one, 65 in
another, a `CONTEXT.md` a human wrote for humans (plan section 5). After L2-T2 those were
four rows saying *nothing typed to seal* — true, and not the accepted decision in front of
the agent about to re-propose it (INC-02, INC-07 of #63).

So this layer reads prose and emits what it can NAME under `layer: "declared"`, every row
`freshness: "UNKNOWN"`. That pair is the safety property, mirrored from flight: the row
carries authority nothing proved fresh, and «code, not docs, for state» is the reader's rule.
How a line of prose is read lives in `contextpack_prose.py` and the lessons in
`contextpack_lessons.py`; which prose is an authority is decided here — three sources:

- **A prose decision record**, by WHERE IT LIVES and by a name the corpus uses:
  `contextpack_records.py` owns that question, the paths no layer may carry, and the three
  things it tells the reader instead of guessing: empty, symlinked, or named like nothing.
- **Every non-empty prose triad document** (plan section 5: *finché manca, la triade entra
  come dichiarata*), unconditionally since R4 — the real prose `CONTEXT.md` of a product
  repository is 179 lines with no code span. Its `## ` sections are the area map, which is
  what the row CARRIES, not what earns it.
- **A lesson, only once somebody verified it** — founder decision 2026-09-17 question 2.

**One source, one row.** The area map STAMPS a source this layer already answered for, at
any layer, and never promotes it (R1). For a live document the choice is made UPSTREAM, by
`contextpack_prose.is_readable_prose`, which `contextpack_unknown` calls too (S7): this
layer only ever ADDS, so `pack_seal` reconstructs from the pack minus the unsealed layers.

**Per area, like the tracker.** A map entry is read only for an area `resolve` was asked for
and a lesson only when it declares one, so the areas emitted are a subset of those requested
(residual G of the #415 breaker). **The seal does not move**: `attach` runs AFTER
`contextpack_seal.seal`. **Fields are claimed**: `state` on a record, `recurrence` and
`verified_against` on a lesson, `area` where a map placed it. Ships with `sync_scripts.py`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import check_context_backbone as cbb
import contextpack_lessons as lessons
import contextpack_receipt as receipt
import contextpack_prose as prose
import contextpack_plans as plans
import contextpack_records as records

def _triad_row(name: str, raw: bytes, named: int) -> dict[str, Any]:
    """The prose authority itself, with the size of the map it carries."""
    text = raw.decode("utf-8", "replace")
    return prose.row(name, raw, {"kind": cbb.LIVE_DOCS[name], "ts": "",
                                 "reason": f"prose authority: {prose.title(text, name)}"
                                           f" — declares {named} document(s)"})


def _triad(root: Path, paths: list[str], areas: list[str]) -> tuple[list[dict], list[tuple]]:
    """A declared row for every non-empty prose live document, and the area map it carries."""
    rows, placed = [], []
    for name in (doc for doc in cbb.LIVE_DOCS if doc in paths):
        if not prose.is_readable_prose(root, name):   # S7: the one shared predicate
            continue
        raw = prose.committed(root, name)
        found = [(slug, [ref for ref in refs if ref in paths])
                 for slug, refs in prose.sections(raw.decode("utf-8", "replace"))]
        placed += [(slug, ref) for slug, refs in found if slug in areas for ref in refs]
        rows.append(_triad_row(name, raw, sum(len(refs) for _, refs in found)))
    return rows, placed


def _placed(root: Path, carried: dict[str, dict], named: list[tuple]) -> list[dict]:
    """The documents a prose section names, each in the area that named it.

    It STAMPS and never promotes (R1). A source this layer already answered for is stamped
    whatever its row's LAYER; a live document is another layer's; a path `NOT_AUTHORITY`
    covers is nobody's, however a human linked it. The FIRST section to name a document owns
    its area, so a section added later cannot move it without a word."""
    rows = []
    for area, rel in named:
        if rel in carried:
            carried[rel].setdefault("area", area)
        elif rel not in cbb.LIVE_DOCS and not records.excluded(rel):
            carried[rel] = prose.row(rel, prose.committed(root, rel),
                                     {"area": area, "ts": "",
                                      "reason": f"named by the prose triad for area {area}"})
            rows.append(carried[rel])
    return rows


def rows(root: Path, areas: list[str]) -> tuple[list[dict], list[dict]]:
    """(declared rows, sources named and not carried) — in the order of SURVIVAL.

    `receipt.fit` pops the TAIL, so this order IS the contract with the budget. Round 2 put
    the records first, so at a tight ceiling the first row to fall was `CONTEXT.md` — the
    one that closes INC-02 and INC-07 — while 26 records stayed (S5). What falls is what
    there are thirty of.

    #432: plan rows sit right after the triad, ahead of generic ADR records. INC-03's own
    motivation — "the pack must surface this file... before a new record is written next to
    it" — is undermined if the fix is the first thing a tight budget cuts; measured on this
    vault at budget=4000, putting plans at the tail of `found` (Round 2's placement) cut 6 of
    19 plan rows for one domain and 0 for another, silently. A plan is one per area; an ADR
    record folder can hold many, so this ordering protects the scarcer, higher-signal row."""
    paths, links = records.committed(root)
    triad, named = _triad(root, paths, areas)
    plan_rows = plans.rows(root, paths, areas) + plans.links(root, links)  # #432: the plans folder
    record_rows = records.rows(root, paths) + records.links(links)
    found = plan_rows + record_rows
    carried = {row["source_id"]: row for row in triad + found}
    placed = _placed(root, carried, named)
    built = triad + plan_rows + lessons.rows(root, paths, areas) + placed + record_rows
    return ([row for row in built if row["layer"] == "declared"],
            [row for row in built if row["layer"] == "unknown"])


def unvalidated(root: Path) -> bool:
    """Whether NOTHING upstream can refuse an area name before this layer is asked for it.

    A typed `DOMAIN.md` is that something: `contextpack_receipt.selected_domains` refuses an
    unknown slug with `AREA_UNKNOWN` and the pack never gets here. Where it is absent — every
    repository the prose layer exists for — the vocabulary is the `## ` sections of a prose
    authority and the `Area:` of a lesson, both written by hand, and nobody checks the name."""
    try:
        return not cbb._frontmatter(root / "DOMAIN.md").get("domains")
    except (cbb.ContractError, OSError, ValueError, TypeError, AttributeError):
        return True


def named_nothing(built: list[dict[str, Any]], area: str) -> list[dict[str, Any]]:
    """The area a caller NAMED and no source in this layer answered for, as its own row.

    `--area gates` and `--area typo-inesistente` produced byte-identical packs at exit 0 in a
    repository with no typed `DOMAIN.md`, so a typo was indistinguishable from an area with
    nothing in it (critic of PR #426).

    Two conditions, each with its own reason. **Only a NAMED area**, through
    `contextpack_receipt.named_area`: a list of names that reached `resolve` positionally
    asked nothing, and answering it puts a row outside the seal in every pack that passes a
    domain list — which is what the positive-form seal test of `test_contextpack_flight`
    catches. **Only where nothing validates the name**: with a typed vocabulary an unknown
    slug is refused upstream with `AREA_UNKNOWN`, so a row on every legitimate area of this
    vault would be noise that reads like a fault."""
    if not area or area in {row.get("area") for row in built}:
        return []
    return [prose.row(area, b"", {"layer": "unknown", "kind": "area", "path": None,
                                  "source_hash": "", "landed": False,
                                  "reason": f"AREA_NAMED_NOTHING: {area}"})]


def attach(root: Path, pack: dict[str, Any], areas: list[str]) -> dict[str, Any]:
    """The declared rows, added AFTER the seal: `pack_seal` means "what the commit carries"
    and these rows are claims the commit cannot prove fresh.

    Nothing sealed is taken back. One source, one row is settled upstream instead:
    `contextpack_unknown._declared_elsewhere` stands aside for a live document that is
    readable prose, so this layer only ever ADDS — and the positive-form seal test of
    `test_contextpack_flight.py` still reconstructs `pack_seal` exactly (R1)."""
    wanted = sorted(set(areas))
    declared, unknown = rows(root.resolve(), wanted)
    pack["declared"] = declared
    if unvalidated(root):
        unknown = unknown + named_nothing(declared + unknown, receipt.named_area())
    if unknown or "unknown" in pack:
        pack["unknown"] = list(pack.get("unknown") or []) + unknown
    return pack
