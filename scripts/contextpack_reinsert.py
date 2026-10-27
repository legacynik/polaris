#!/usr/bin/env python3
"""L2-T7 (#406) — the pack, put back in front of the agent after a compaction.

A compaction takes the pack out of the context window and leaves the receipt on disk. The
naive repair is to resolve again, and it is wrong twice: it walks the tracker over the
network for every area, and at a still `HEAD` the sealed and declared layers it rebuilds
are the ones already recorded — `pack_seal` is a function of the commit. The flight layer
is not: it reads the worktree and the tracker, so a second resolution can legitimately
differ there, which is a reason to pay for it on purpose and not by accident. So the contract is `HEAD`-bound, and it is the plan's own words
(section 3, «Dopo una compaction»): **the same pack is reinserted from the receipt, without
recomputing, if `HEAD` has not changed; otherwise it is re-emitted and the receipt records
it.**

What that buys, and what it costs:

- **A still `HEAD` costs zero tracker calls.** The rows come back from
  `state/session/<sid>/area-<slug>.json`, which already carries `source_id`, `layer` and
  `source_hash` per row — enough to put the pack back and to re-verify any row the agent
  opens. It does NOT carry the row's prose, which the receipt never kept: a reinserted row
  is an address, which is what progressive delivery hands over anyway.
- **A moved `HEAD` costs one emission, and never the previous receipt.** The second
  receipt lands beside the first (`contextpack_receipt._place`) and names it in `prev`, so
  the audit can still say what the agent had BEFORE the compaction. That chain is the debt
  #404 left open: its first link is the session's own `start.json`.
- **Two things are re-emissions rather than refusals.** No receipt at all (`RECEIPT_MISSING`)
  and a receipt of a different area (`AREA_MISMATCH`) are reported on their own line and
  then resolved properly. Refusing would leave the agent with nothing after a compaction,
  which is the failure this exists to prevent; reusing the neighbour's pack would be worse
  than nothing. Either way the command exits 0 — a reinsertion that had to resolve is a
  success with a cost, not an error.

`chain` is the other half of `prev`: a link that nobody verifies is decoration. It reports
a receipt whose `prev` names a hash no receipt of the session can show, which is what a
deleted or replaced receipt looks like from the outside.

It ships with the resolver (`_standard/sync_scripts.py`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as cbb  # noqa: E402
import contextpack  # noqa: E402
import contextpack_receipt as receipt  # noqa: E402
import contextpack_seal as sealer  # noqa: E402

ROW = "{layer:9} {source_id}  {source_hash}"


def _dir(root: Path, sid: str) -> Path:
    """The session folder, with the id validated as a NAME and never as a path.

    The WRITE path has validated it since #404 (`_slug`); this one did not, so
    `--sid ../session/victim` walked out of its own folder and reinserted another
    session's pack with exit 0. One door, so no reader can forget it."""
    return root / "state" / "session" / receipt._slug(sid, "sid")


def _receipts(root: Path, sid: str) -> list[tuple[dict[str, Any], Path]]:
    """Every READABLE pack receipt of one session, newest first by its OWN timestamp.

    Its own, not the file's: a copied or restored tree rewrites every `st_mtime` at once,
    which is the same reason the audit stopped reading them (#404, round 1)."""
    found = [(rec, path) for path in _dir(root, sid).glob("area-*.json")
             if (rec := receipt._read(path)) is not None]
    return sorted(found, key=lambda pair: pair[0].get("ts", ""), reverse=True)


def _absent(root: Path, sid: str) -> str:
    """Why this session has no receipt to reuse — and unreadable is not missing.

    `_read` collapsed the two, so a corrupt receipt was reported as RECEIPT_MISSING, which
    is a different and false claim about the session, and the re-emission then took its
    filename (`contextpack_receipt._place` now refuses that)."""
    broken = [one for one in _dir(root, sid).glob("area-*.json") if receipt._read(one) is None]
    if broken:
        return (f"RECEIPT_UNREADABLE: {len(broken)} receipt(s) under state/session/{sid} "
                f"could not be parsed — kept, re-emitting beside them")
    return f"RECEIPT_MISSING: no pack receipt under state/session/{sid} — re-emitting"


def _fault(rec: dict[str, Any], path: Path, sid: str) -> str:
    """Why this receipt may not be reused — asked BEFORE a single row is reprinted.

    Both are cheap and neither was asked. The receipt carries its own `sid`, so another
    session's receipt dropped into this folder under the same name was reinserted here;
    and `rows_hash` is the tamper-evidence the audit already computes, so a `source_id`
    rewritten in place came back as a real row of a real pack."""
    if rec.get("sid") != sid:
        return (f"SID_MISMATCH: {path.name} was written for session {rec.get('sid')!r}, "
                f"not {sid!r} — not reused, re-emitting")
    if receipt.rows_hash(rec) != rec.get("rows_hash"):
        return (f"RECEIPT_TAMPERED: {path.name} does not hash to its own claims "
                f"— not reused, re-emitting")
    return ""


def _latest(root: Path, sid: str, area: str) -> tuple[tuple[dict, Path] | None, str]:
    """(the receipt of THIS AREA to reinsert, or None and the reason it may not be).

    Of this area. It used to take the newest receipt of the SESSION and then compare its
    area, so any second area emitted afterwards turned a still HEAD into an AREA_MISMATCH
    and a full re-emission — on the most ordinary path there is, a session that looked at
    two areas."""
    found = _receipts(root, sid)
    mine = [pair for pair in found if not area or pair[0].get("area") == area]
    if not found:
        return None, _absent(root, sid)
    if not mine:
        return None, (f"AREA_MISMATCH: no receipt for area {area!r} in state/session/{sid} "
                      f"(found {sorted({rec.get('area') for rec, _ in found})}) — re-emitting")
    fault = _fault(*mine[0], sid)
    return (None, fault) if fault else (mine[0], "")


def _rows(rec: dict[str, Any]) -> list[str]:
    """The pack as the agent gets it back: one addressable line per row, layer first."""
    return [ROW.format(layer=ref.get("layer") or "?", source_id=ref.get("source_id") or "?",
                       source_hash=(ref.get("source_hash") or "-")[:12])
            for ref in (rec.get("included") or []) + (rec.get("unknown") or [])]


def _printed(rec: dict[str, Any], path: Path | None) -> list[str]:
    """Identity, chain link, rows — the same shape whether it was reused or re-emitted."""
    where = f"reused from {path.name}" if path else "re-emitted"
    return [f"PACK: {rec.get('context_pack_id', '?')} seal={rec.get('pack_seal', '')[:12]}"
            f" ({where})",
            f"CHAIN: prev={(rec.get('prev') or '-')[:12]}"] + _rows(rec)


def _reemit(root: Path, sid: str, area: str) -> dict[str, Any]:
    """Resolve once, then hand back the RECEIPT it wrote, never the pack in memory.

    The receipt is what a later reinsertion will read, so printing anything else would let
    the two paths drift: a row that reached the agent now and no receipt after a compaction
    is exactly the silence the pack contract forbids."""
    receipt.configure(sid, area, sealer.BUDGET)
    guided = _opened_guided(root, sid)
    contextpack.resolve(root, "", receipt.selected_domains(root, area, []), degrade=guided)
    found = _receipts(root, sid)
    if not found:
        raise cbb.ContractError("RECEIPT_UNWRITTEN", f"resolve left no receipt for sid {sid}")
    return found[0][0]


def _opened_guided(root: Path, sid: str) -> bool:
    """Was this session opened guided? The re-emission keeps the mode it was opened in.

    Compaction fires in autonomous sessions too (`claude -p` in an AFK loop), so a
    reinsertion that was always guided would be a fail-open there. `start.json` records
    `mode`. A receipt WITHOUT the field predates it (W3b, 2026-09-30): until then only a
    human's /start opened sessions, so it is guided. A session with NO start receipt was
    never opened, or its autonomous open refused: SESSION_NOT_OPEN, never guided (W3c). A receipt that exists and is not a record refuses (START_RECEIPT_UNREADABLE); one
    naming a mode nobody defined re-emits strict (DEC-polaris-contextpack-stale-degrades-001).
    Known limit: `receipt_hash` is not verified here, so an edit that removes `mode` makes the
    reinsertion guided."""
    return _start_record(root, sid, required=True).get("mode", "guided") == "guided"


def _start_record(root: Path, sid: str, required: bool = False) -> dict[str, Any]:
    """The session's start receipt; a refusal when it is no record, and — when a mode must be
    read from it — when there is none. `chain` only reports an unanchored chain (#406)."""
    path = _dir(root, sid) / "start.json"
    if not path.exists() and not required:
        return {}
    if not path.exists():  # never opened, or an autonomous open that refused: never guided
        raise cbb.ContractError("SESSION_NOT_OPEN", f"{path}: no start receipt — run /start")
    start = receipt._read(path)
    if start is None:
        raise cbb.ContractError("START_RECEIPT_UNREADABLE", f"{path}: not a start record")
    return start


def _why_not(found: tuple[dict, Path], faults: list[str], head: str) -> str:
    """Why a receipt that passed every check still may not simply be reprinted.

    A chain whose links do not resolve is not a chain, and reprinting from it would put
    a pack in front of the agent that the session cannot account for. UNANCHORED is NOT
    a break: the links are all there and nothing ties them to a start receipt, which is
    every session opened before `/start` wrote one (#155)."""
    broken = [one for one in faults if one.startswith("CHAIN_BROKEN")]
    if broken:
        return (f"CHAIN_BROKEN: {len(broken)} link(s) of this session do not resolve "
                f"— not reused, re-emitting")
    if found[0].get("sealed_commit") != head:
        return f"REINSERT: HEAD moved {found[0].get('sealed_commit', '')[:12]} -> {head[:12]}"
    return ""


def reinsert(root: Path, sid: str, area: str = "") -> list[str]:
    """The pack back in front of the agent: from the receipt at a still `HEAD`, else remade.

    The chain is asked about THIS receipt's area and no other: a break under a neighbour
    is not a reason to re-resolve this one, and charging it here made the cost permanent."""
    found, why = _latest(root, sid, area)
    head = cbb._head_commit(root) or ""
    faults = chain(root, sid, _area_of(found)) if found else []
    notes = [one for one in faults if one.startswith("CHAIN_UNANCHORED")]
    why = why or _why_not(found, faults, head)
    if not why:
        return [f"REINSERT: HEAD unchanged at {head[:12]} — 0 tracker calls"] + notes \
            + _printed(*found)
    return [why] + notes + _printed(_reemit(root, sid, area or _area_of(found)), None)


def _area_of(found: tuple[dict, Path] | None) -> str:
    return found[0].get("area", "all") if found else "all"


def _dangling(found: list[tuple[dict, Path]], known: set[str], sid: str) -> list[str]:
    """Links naming a predecessor no receipt of the session can show: a deletion."""
    return [f"CHAIN_BROKEN: {path.name} follows {rec['prev'][:12]}, which no receipt"
            f" of session {sid} can show"
            for rec, path in found if rec.get("prev") and rec["prev"] not in known]


def _ring(rec: dict[str, Any], by_hash: dict[str, dict]) -> bool:
    """Does walking `prev` from here come back to somewhere it has already been?

    A sound chain walks strictly backwards and leaves the set of this session's receipts
    at its first link — into the start receipt, or into nothing. A walk that stays inside
    the set forever is a ring: `prev` naming its OWN `rows_hash` is the one-element case,
    and two receipts naming each other is the two-element case. Both make every link
    resolve, which is exactly why `_dangling` cannot see either."""
    seen, cursor = {rec.get("rows_hash", "")}, rec.get("prev") or ""
    while cursor in by_hash:
        if cursor in seen:
            return True
        seen.add(cursor)
        cursor = by_hash[cursor].get("prev") or ""
    return False


def _unanchored(found: list[tuple[dict, Path]]) -> list[str]:
    """One line per AREA whose oldest receipt names no predecessor.

    Per area, because the chains are: `_place` looks only at the generations of the area
    it is writing, so each area's oldest link reaches the start receipt on its own. Asking
    it of the session's globally oldest receipt answered for one area and covered for
    every other."""
    groups: dict[str, list[tuple[dict, Path]]] = {}
    for rec, path in found:
        groups.setdefault(rec.get("area", ""), []).append((rec, path))
    oldest = [min(rows, key=lambda pair: pair[0].get("ts", "")) for rows in groups.values()]
    return [f"CHAIN_UNANCHORED: {path.name} names no predecessor — nothing ties this"
            f" area's packs to a start receipt" for rec, path in oldest if not rec.get("prev")]


def chain(root: Path, sid: str, area: str = "") -> list[str]:
    """The faults in one session's receipt chain; empty when every link resolves.

    Scoped to `area` when one is named, because a chain is per area and a break under
    `gates` is not a reason to distrust `memoria` — it used to be, and it made every later
    reinsertion of every other area pay the tracker at a still HEAD, permanently.

    Three kinds, and only the first two are breaks. A `prev` that names nothing the
    session can show is a receipt deleted or replaced. A `prev` walk that loops is a
    forged terminator — the chain was deletion-evident and nothing more until round 2.
    CHAIN_UNANCHORED is the third: every link is there and the oldest names no
    predecessor, so nothing ties that area's packs to the `start.json` that opened the
    session. It is reported, and it blocks nothing and fails nothing, because it is also
    what every session looks like until `/start` itself opens one (#155)."""
    found = [pair for pair in _receipts(root, sid)
             if not area or pair[0].get("area") == area]
    if not found:
        return []
    start = _start_record(root, sid)
    by_hash = {rec.get("rows_hash", ""): rec for rec, _ in found}
    faults = _dangling(found, set(by_hash) | {start.get("receipt_hash", "")}, sid)
    faults += [f"CHAIN_BROKEN: {path.name} sits on a ring of receipts naming each other"
               for rec, path in found if _ring(rec, by_hash)]
    return faults + _unanchored(found)


def _open_session(root: Path) -> str:
    """The session a compaction hook belongs to, since a hook is told nothing else.

    The host knows a compaction happened and nothing more — no `sid`, no area — so a
    command that demanded one would be wired to a flag nobody can fill and would report
    success while reinserting nothing. `_sid` is the dashboard's own answer to the same
    question (open today, not abandoned, not closed) and having two would be having two
    definitions of which session a receipt belongs to. Imported here, not at load time:
    the dashboard imports this module's dependencies and the CLI is the only caller."""
    import contextpack_dashboard as dash
    return dash._sid(root, "")


def main() -> int:
    ap = argparse.ArgumentParser(description="#406 — reinsert the pack after a compaction")
    ap.add_argument("command", choices=["reinsert", "chain"])
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--sid", default="")
    ap.add_argument("--area", default="")
    opts = ap.parse_args()
    root = opts.root.resolve()
    sid = opts.sid or _open_session(root)
    if not sid:
        print("NO_OPEN_SESSION: nothing was reinserted — run /start to open one")
        return 0
    try:
        lines = (reinsert(root, sid, opts.area) if opts.command == "reinsert"
                 else chain(root, sid, opts.area))
    except cbb.ContractError as exc:
        print(f"{exc.code}: {exc.detail}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    # A break fails; a report does not. `chain` exited 1 on CHAIN_UNANCHORED, which its own
    # docstring calls «not a break» — and which every session has until `/start` opens one,
    # so the gate was red on the normal case. A gate red on the normal case gets ignored on
    # the day it means something.
    # The code belongs to `chain` alone: a reinsertion that had to resolve is a success
    # with a cost, which is the whole contract of RECEIPT_MISSING and its four siblings.
    return 1 if opts.command == "chain" and any(
        one.startswith("CHAIN_BROKEN") for one in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
