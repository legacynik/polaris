#!/usr/bin/env python3
"""How a pack is closed, and whether there is a backbone to close it around (#402).

Two steps every pack takes, kept in one place so neither branch grows a second seal:

- `model_or_none` validates the backbone and answers None when there is nothing typed to
  validate. Only ABSENCE routes to the UNKNOWN layer; a backbone that exists and is
  broken — a foreign workspace, a decision record with no frontmatter — still raises,
  because a refusal must not degrade into a shrug. The one exception is a cited path that
  is gone, in a pack a human reads (`degrade`), which becomes a STALE row.
- `seal` closes either pack identically: budget, `pack_seal`, addressable id. The sealed
  branch and the unknown branch therefore agree by construction on what a seal IS, and
  the sealed pack is byte-identical to the one the resolver emitted before this layer.

It lives outside `contextpack.py` because that file is grandfathered above the 200-line
ceiling and may only shrink; `scripts/test/test_contextpack_row_contract.py` ratchets it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import check_context_backbone as cbb
import contextpack_unknown as unknown_layer

BUDGET = 4000


def model_or_none(root: Path, degrade: bool = False) -> dict[str, Any] | None:
    """The validated backbone, or None when there is none to validate — for a guided caller.

    Off by default, and then a cited path that is gone refuses: a caller that never chose —
    a compaction hook, a library call, an autonomous loop — fails closed. `degrade=True` is the
    guided pack a human or a lane reads: a gone path becomes a STALE row and a missing
    authority routes to the UNKNOWN layer; every other breach still refuses."""
    try:
        return cbb.validate(root, at_head=True, degrade=degrade)
    except cbb.ContractError as exc:
        if not degrade or not unknown_layer.absent(root, exc):
            raise
        return None


def _gone(model: dict[str, Any], path: str) -> dict[str, Any]:
    """A path a record cites or governs that is not there: an `absent` STALE row."""
    missing = model.get("stale_missing", {}).get(path)
    return {} if not missing else {
        "freshness": "STALE", "path": path, "current_hash": "absent",
        "missing": f"{missing['code']}: named by {missing['detail']}, gone; restore it or fix the record"}


def document_rows(model: dict[str, Any]) -> list[dict[str, Any]]:
    """The three live authorities, then one row per cited or governed path that is gone."""
    rows = [{"source_id": name, "source_hash": model["source_hashes"][name], "freshness": "CURRENT",
             "reason": "live technical authority (always in scope)"} for name in sorted(cbb.LIVE_DOCS)]
    held = {*cbb.LIVE_DOCS, *(item["path"] for item in model["decisions"])}
    return rows + [{"source_id": path, "source_hash": "absent", "reason": "named by a record"} | _gone(model, path)
                   for path in sorted(set(model.get("stale_missing", {})) - held)]


def area_row(root: Path, module: dict[str, Any], rel: str) -> dict[str, Any]:
    """A module doc's row: its committed hash, or `absent` with the drift when it is gone."""
    drift = module.get("stale_docs", {}).get(rel, {})
    found = "absent" if drift else cbb._source_hash(root, root / rel, at_head=True)
    return {"source_id": rel, "source_hash": found, "freshness": "CURRENT",
            "reason": f"active set of {module['module_id']} via module-context.json (work item in active_work)",
            } | drift


def area_estimate(root: Path, rows: list[dict[str, Any]]) -> int:
    """Tokens of the content the agent opens; a gone doc opens nothing."""
    return sum((len(cbb._source_bytes(root, root / row["source_id"], at_head=True)) + 3) // 4
               for row in rows if row.get("source_hash") != "absent")


def stale_rows(pack: dict[str, Any]) -> list[dict[str, str]]:
    """What a session receipt keeps of a pack's STALE rows: where, and that it is stale.

    Area rows count too — a module doc that moved is its own STALE row (W3c) — and a path
    counts once: an area doc of the active work item is also a `documents` row."""
    rows = [row for key in ("documents", "decisions") for row in pack.get(key) or []]
    rows += [row for area in pack.get("areas") or [] for row in area.get("documents") or []]
    paths = dict.fromkeys(row.get("path") or row["source_id"] for row in rows
                          if row.get("freshness") == "STALE")
    return [{"path": path, "freshness": "STALE"} for path in paths]


def seal(root: Path, pack: dict[str, Any]) -> dict[str, Any]:
    """The same closing for both branches: budget, seal, addressable id."""
    pack["sealed_commit"] = cbb._head_commit(root)
    pack["token_estimate"] = (len(json.dumps(pack, ensure_ascii=False)) + 3) // 4
    if pack["token_estimate"] > BUDGET:
        raise cbb.ContractError("CONTEXT_OVERFLOW", f"{pack['token_estimate']}>{BUDGET}")
    pack["pack_seal"] = cbb._json_hash(pack)
    pack["context_pack_id"] = f"CTX-{pack['workspace']}-{pack['pack_seal'][:12]}"
    return pack
