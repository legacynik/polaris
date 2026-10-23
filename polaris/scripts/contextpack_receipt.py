#!/usr/bin/env python3
"""L2-T5 (#404) — the receipt a pack leaves behind, and the audit that reads a week of them.

A pack is emitted, read once, and gone. A week later nobody can say what the agent had in
front of it. This module answers that for every pack the CLI emits: one JSON file per area
per session under `state/session/<sid>/area-<slug>.json` with the rows that went in, those
dropped as superseded, the authorities missing, the budget burned and what it cut.

**A receipt is a side effect, so it is opt-in.** `resolve` is a library function called by
`session_continuity` and by five test modules, so `close` writes only when `--sid` named
the session — a default id made every CLI resolve write, and the golden suites started
dropping `state/session/` trees inside tracked fixtures.

**The cut order belongs to the accepted Decision, not to a slice plan.**
`DEC-polaris-contextpack-flight-layer-001` says twice that the budget cuts flight first and
never a sealed row, so `CUT_ORDER` is flight then declared and §8 of the lifecycle plan,
which had declared first, was corrected (PR #419) rather than followed. `sealed` and
`unknown` are absent from `CUT_ORDER` entirely, so no loop can reach them: the first is
the Decision's own words, the second its `contract:pack-never-silent`, since dropping the
row that says a source is missing IS the silence it exists to end. A pack over its ceiling
after every permitted cut refuses. `test_contextpack_budget.py` holds all of it.

**The seal is frozen before anything is attached, and nothing here recomputes it.**
`resolve` ends as `close(root, flight_layer.attach(root, seal(root, pack), domains))`
(coordinator, after the #420 breaker), so this runs last and touches none of the four
fields `seal` wrote; the fit is always active, and what it measures is `_estimate`.
`test_contextpack_flight_handoff.py` holds the whole handoff down, with the numbers.

It lives outside `contextpack.py`, which is grandfathered above the 200-line ceiling and
may only shrink; it ships with the resolver (`sync_scripts.py`)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import check_context_backbone as cbb
import contextpack_seal as sealer
from contextpack_audit import audit, rows_hash  # noqa: F401 — `audit` is re-exported here

# DEC-polaris-contextpack-flight-layer-001: flight first, never a sealed row. `sealed`
# and `unknown` are absent on purpose — see the module docstring.
CUT_ORDER = ("flight", "declared")
# The layer a pack key holds. A cut row is labelled with its LAYER, never with the key it
# came from: a guard that asks "was a sealed row cut?" must be able to see one.
LAYER = {"decisions": "sealed", "documents": "sealed", "areas": "sealed",
         "declared": "declared", "flight": "flight", "unknown": "unknown"}
# `unknown` is reported on its own in the receipt, so it is not part of `included`.
INCLUDED = ("decisions", "documents", "declared", "flight")
# Every row list the emitted pack hands over: what the ceiling binds on. `dropped` is
# here although the contract's list omitted it — a superseded Decision IS emitted, so it
# costs context. `flight_budget` is absent because `close` removes it from the pack.
DELIVERED = ("decisions", "documents", "dropped", "declared", "flight", "unknown")
_CFG: dict[str, Any] = {"sid": None, "area": "all", "budget": sealer.BUDGET}


def _slug(value: str, field: str) -> str:
    """A receipt names a directory and a file, so it may not name a path.

    `.` passed the first version and wrote `state/session/area-all.json`, one level above
    where `glob("*/area-*.json")` looks: invisible to the audit forever while it still
    reports success. The cap is the same — 300 characters made the filesystem raise and
    the CLI die with a traceback, where a violation owes a code."""
    if (not value or value in {".", ".."} or len(value) > 64 or ".." in value
            or not all(char.isalnum() or char in "-_." for char in value)):
        raise cbb.ContractError("RECEIPT_NAME_INVALID", f"{field}: {value!r}")
    return value


def selected_domains(root: Path, area: str, labels: list[str]) -> list[str]:
    """The domains the CLI asked for, with `--area` actually selecting something.

    `--area` used to reach only the receipt's filename, so `--area memoria` and `--area
    does-not-exist` gave the same seal and the same 21 rows. The one area vocabulary on
    origin/main is the repository's own issue labels (`.github/DOMAINS.yml`), which
    `contextpack` maps to domain ids for `--repo-domain`; a repository with no typed
    `DOMAIN.md` has none at all and refuses — L1 gives it one."""
    import contextpack  # deferred: contextpack imports this module at load time
    chosen = contextpack.repo_domains_to_polaris(root, labels) if labels else []
    if not area or area == "all":  # `all` is every declared domain, never a label (W3c)
        return chosen
    try:
        return chosen + contextpack.repo_domains_to_polaris(root, [area])
    except cbb.ContractError as exc:
        raise cbb.ContractError("AREA_UNKNOWN", f"{area}: {exc.detail}") from exc
    except OSError:
        return chosen   # no map to select WITH: see `areas` for what the slug still selects


def areas(domains: list[str]) -> list[str]:
    """The vocabulary the DECLARED layer filters on: the selected domains, plus the RAW
    `--area` slug.

    A repository with NO `DOMAIN.md` has no area->domain map, so `selected_domains` returns
    the sealed layer whole instead of refusing. It used to raise `AREA_UNRESOLVABLE`, which
    made `--area` unusable in every product repository — exactly the ones L2-T4 exists for,
    where an area IS a prose section of `CONTEXT.md`. The raw slug carried here is what the
    name still selects there, and the unknown layer already says `DOMAIN.md` is missing.

    `selected_domains` answers in `polaris.*` domain ids, which is the sealed layer's
    vocabulary and matches no `## ` section of a prose authority and no `Area:` of a lesson.
    So `--area gates` reached the seal and the receipt's filename and stopped there: the area
    map and the lessons of the area were unreachable from the CLI (residue 1 of the #423
    gate). `all` and the empty default carry nothing: an inert label is what #419 removed."""
    area = named_area()
    return domains + ([area] if area else [])


def named_area() -> str:
    """The area a CALLER NAMED, as `configure` recorded it — `""` when nobody did.

    The one channel that separates «somebody asked for this area» from «a list of names
    reached the resolver positionally», which no reader of `resolve(root, work, domains)`
    can tell apart: a test passing `["pricing"]` as a domain named no area. `all` and the
    empty default are the inert label #419 removed, so they name nothing either.

    **Armed for ONE emission, and spent by it** (`close` resets it). Without that, `resolve`
    stopped being a function of its arguments: `contextpack_declared` reads this, so an area
    configured for one pack reached the NEXT `resolve` — of another repository, which had
    asked for nothing — and only `addCleanup` kept it out of the suite's own packs. A caller
    that wants an area on two emissions arms it twice, which is what `configure` is for."""
    area = _CFG["area"]
    return "" if area in ("", "all") else area


def configure(sid: str | None, area: str, budget: int) -> None:
    """Arm the receipt for one emission: who it is for, which area, which ceiling.

    Public on purpose. `parse` calls it for the CLI, and a library caller that already
    owns a session id — `session_continuity.cmd_start`, once L2-T6 knows which area the
    session chose — calls it to get a pack receipt beside its own start receipt without
    changing `resolve`'s signature."""
    _CFG.update(cut={}, sid=None if sid is None else _slug(sid, "sid"),
                area=_slug(area or "all", "area"), budget=min(budget, sealer.BUDGET))


def parse(ap: argparse.ArgumentParser) -> argparse.Namespace:
    """Register the receipt's flags on the resolver's parser, parse, and configure."""
    ap.add_argument("--sid", default="", help="session the receipt is written for; no --sid, no receipt")
    ap.add_argument("--area", default="", help="area whose domains the pack is resolved for")
    ap.add_argument("--budget", type=int, default=sealer.BUDGET)
    ap.add_argument("--since", default="7d", help="audit window, e.g. 7d, 24h, 30m")
    args = ap.parse_args()
    if args.command == "resolve":
        try:
            configure(args.sid or None, args.area, args.budget)
        except cbb.ContractError as exc:
            ap.error(f"{exc.code}: {exc.detail}")
    return args


def _estimate(pack: dict[str, Any]) -> int:
    """The size of the ROWS the agent is handed, and of nothing else.

    Measured with L2-T3 in: 51,242 of the vault pack's 64,245 bytes were
    `flight_budget.cut`, so measuring the whole dict read 16,126 tokens against 4,000 and
    the vault stopped emitting — counting the record of what was removed against the
    ceiling that removed it. The envelope goes too: a seal and an id are identity."""
    rows = [row for key in DELIVERED for row in pack.get(key) or []]
    rows += [row for area in pack.get("areas") or [] for row in area.get("documents") or []]
    return (len(json.dumps(rows, ensure_ascii=False)) + 3) // 4


def fit(pack: dict[str, Any], budget: int) -> list[dict[str, Any]]:
    """Trim the pack to `budget` from the bottom of the priority order; say what fell.

    L2-T3 sorts flight newest-first with a `ts`, so popping the tail IS "volo dal più
    vecchio"; `test_contextpack_flight_handoff` goes red if either side flips."""
    cuts: list[dict[str, Any]] = []
    for layer in CUT_ORDER:
        rows = pack.get(layer) or []
        while rows and _estimate(pack) > budget:
            cuts.append(dict(rows.pop(), layer=LAYER.get(layer, layer),
                             cut=f"budget: {budget} tokens"))
    return cuts


def _refs(rows: list[dict[str, Any]], layer: str) -> list[dict[str, Any]]:
    """What a receipt keeps of a row: enough to re-verify it, never a second copy of it."""
    return [{"source_id": row.get("source_id", ""), "layer": row.get("layer", layer),
             "source_hash": row.get("source_hash", "")}
            | ({"freshness": "STALE"} if row.get("freshness") == "STALE" else {})
            for row in rows]


def _receipt(pack: dict[str, Any], cuts: list[dict[str, Any]],
             unknown: list[dict[str, Any]]) -> dict[str, Any]:
    """The six keys of the acceptance, plus the address the pack can be found at again."""
    return {"sid": _CFG["sid"], "area": _CFG["area"], "ts": datetime.now().astimezone().isoformat(),
            "work_item": pack["work_item"], "sealed_commit": pack["sealed_commit"],
            "context_pack_id": pack["context_pack_id"], "pack_seal": pack["pack_seal"],
            "budget": {"limit": _CFG["budget"], "used": _estimate(pack)},
            "included": [ref for key in INCLUDED
                         for ref in _refs(pack.get(key) or [], LAYER[key])],
            "dropped": _refs(pack.get("dropped") or [], "sealed"),
            "unknown": _refs(unknown, "unknown"), "cuts": cuts}


def _read(path: Path) -> dict[str, Any] | None:
    """A receipt already on disk, or None when there is none that can be read.

    A JSON value that is not an object (`"guided"`, `42`, a list) is not a receipt either:
    every caller reads it with `.get`, and one that got a string crashed (breaker, #493)."""
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def _generations(path: Path) -> list[Path]:
    """Every receipt this area already has: `area-<slug>.json` and its numbered successors."""
    return [one for one in [path, *sorted(path.parent.glob(f"{path.stem}.*.json"))]
            if one.is_file()]


def _free(path: Path) -> Path:
    index = 2
    while path.with_name(f"{path.stem}.{index}.json").exists():
        index += 1
    return path.with_name(f"{path.stem}.{index}.json")


def _place(path: Path, digest: str) -> tuple[Path, str]:
    """Where this receipt goes, and the hash of the receipt it follows (L2-T7, #406).

    **A receipt never overwrites a DIFFERENT claim, nor one it cannot read.** One file per
    area per session was the T5 rule while a pack could only be emitted once; after a
    compaction at a moved `HEAD` the resolver emits a second one, and a write that
    replaced the first would destroy the only record of what the agent had BEFORE the
    compaction. An unchanged pack still rewrites its own file, so a replay stays
    idempotent — which is what the T5 acceptance holds down — and only a changed one takes
    `area-<slug>.<n>.json` beside it. A generation that no longer parses counts as a
    different claim and not as free space: it used to be invisible to `_read`, so the next
    emission took its filename and the corruption became unrecoverable rather than
    auditable. The reuse test RECOMPUTES the hash instead of believing the one the file
    carries, because a tamperer leaves that field intact: refusing to REUSE a tampered
    receipt and then writing over it is not a refusal, and the only copy of what the agent
    was nearly handed used to disappear inside the repair for it.

    **`prev` is the chain the #404 debt left open**: the first receipt of a session names
    the `start.json` that opened it, each later one the receipt it superseded. It sits
    OUTSIDE `rows_hash` on purpose, beside `sid` and `ts`: those three say where a receipt
    sits, not what its pack claims, and the audit promises two emissions of an unchanged
    pack differ in exactly them. Inside the hash, `prev` would change the digest it is
    derived from, and no unchanged re-emission could ever match its own file again."""
    present = _generations(path)
    found = {one: rec for one in present if (rec := _read(one))}
    if not present:
        return path, (_read(path.parent / "start.json") or {}).get("receipt_hash", "")
    newest = max(found, key=lambda one: found[one].get("ts", "")) if found else None
    if newest is None or len(found) < len(present):
        return _free(path), (found[newest].get("rows_hash", "") if newest else "")
    if rows_hash(found[newest]) == found[newest].get("rows_hash") == digest:
        return newest, found[newest].get("prev", "")
    return _free(path), found[newest].get("rows_hash", "")


def _write(root: Path, rec: dict[str, Any]) -> None:
    """Atomic, so a receipt is never half a receipt: temp file beside it, then `os.replace`.

    A crash mid-write used to leave a truncated file that every later audit counted as
    corrupt and exited 2 over: one failed write turning every future audit red. The `.tmp`
    suffix keeps it out of the audit's glob, and an unwritable directory is a violation."""
    rec["rows_hash"] = rows_hash(rec)
    base = root / "state" / "session" / rec["sid"] / f"area-{rec['area']}.json"
    path, rec["prev"] = _place(base, rec["rows_hash"])
    tmp = path.with_suffix(".json.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise cbb.ContractError("RECEIPT_UNWRITABLE", f"{path}: {exc.strerror or exc}") from exc


def last_cut() -> dict[str, int]:
    """Rows the last `close` cut by budget, per layer — what the brief says aloud."""
    return dict(_CFG.get("cut") or {})


def close(root: Path, pack: dict[str, Any]) -> dict[str, Any]:
    """Fit an already-sealed pack to the ceiling; leave a receipt when a session asked.

    A cut the flight layer already made on its own per-kind cap is carried into the
    receipt so no cut is silent, and then `flight_budget` is POPPED: the record of what
    was removed belongs in the receipt, not in front of the agent."""
    unknown = list(pack.get("unknown") or [])  # counted before the cut, never after
    cuts = fit(pack, _CFG["budget"])
    cuts += [dict(row, layer="flight", cut="per-kind cap")
             for row in (pack.pop("flight_budget", None) or {}).get("cut") or []]
    # #457: the brief owes the count even when no session keeps a receipt. Kept OUT of
    # the pack: the pack is sealed, and a count is not content.
    budget_cut = [row["layer"] for row in cuts if row["cut"].startswith("budget")]
    _CFG["cut"] = {layer: budget_cut.count(layer) for layer in dict.fromkeys(budget_cut)}
    used = _estimate(pack)
    if used > _CFG["budget"]:
        raise cbb.ContractError("CONTEXT_OVERFLOW",
                                f"{used}>{_CFG['budget']} after {len(cuts)} cut(s)")
    if _CFG["sid"] is not None:
        _write(root, _receipt(pack, cuts, unknown))
    _CFG["area"] = "all"   # spent: see `named_area`
    return pack
