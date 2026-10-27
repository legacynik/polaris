#!/usr/bin/env python3
"""L2-T5 (#404) — reading a week of pack receipts, and refusing to vouch for a bad one.

The audit is why receipts are written at all: a week later, what did each session actually
have in front of it. That makes every line a claim about the past, and such a claim is
worth exactly what its weakest input is worth. Three inputs were weaker than the claim.

**The window read the filesystem, not the receipt.** `st_mtime` is a property of the copy,
not of the session: a `cp -r`, an `rsync`, a restore from backup rewrites every stamp at
once, so a six-month-old receipt walks into `--since 7d` and one written this morning but
restored from an old archive walks out. The window now reads the `ts` the receipt carries,
and a file whose `ts` is not a timestamp is not a receipt.

**The order was the order of the paths.** `sorted(glob(...))` sorts by session id, so an
audit meant to be read as a history came out alphabetical. Oldest first now.

**`pack_seal` was printed as truth.** Anyone could type `deadbeef` over a seal and the
audit would repeat it. `rows_hash` covers everything the receipt claims, so an edited field
shows as `SEAL_MISMATCH` rather than being echoed. It is tamper-EVIDENCE, not a signature:
it catches a field edited in place, not a forger who rewrote the whole file — against that
the only proof is re-resolving the pack at `sealed_commit` and comparing seals. `sid` and
`ts` sit deliberately outside it, so two receipts of the same pack at a still HEAD still
differ in exactly the two lines the acceptance asks for.

It lives beside `contextpack_receipt.py` rather than inside it because writing one receipt
and reading a week of them are two jobs, and the file limits are what say so out loud.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

WINDOW = {"d": 86400, "h": 3600, "m": 60}
# Everything the receipt CLAIMS, minus who wrote it and when.
SIGNED = ("work_item", "sealed_commit", "context_pack_id", "pack_seal", "budget",
          "included", "dropped", "unknown", "cuts")


def rows_hash(rec: dict[str, Any]) -> str:
    """Tamper-evidence over a receipt's claims, stable across `sid` and `ts`."""
    body = json.dumps({key: rec.get(key) for key in SIGNED}, sort_keys=True, ensure_ascii=False)
    return sha256(body.encode()).hexdigest()


def _entry(path: Path) -> tuple[float, str]:
    """One receipt as (when it was written, the line that reports it).

    Raises when the file is not a receipt: a missing key, a stamp that is not a stamp,
    bytes that are not JSON. The caller counts those, never prints them as sessions."""
    rec = json.loads(path.read_text(encoding="utf-8"))
    stamp = datetime.fromisoformat(rec["ts"]).timestamp()
    mark = "" if rows_hash(rec) == rec["rows_hash"] else "  SEAL_MISMATCH"
    return stamp, (f"{rec['ts']}  {rec['sid']}  {rec['area']}  {rec['pack_seal'][:12]}  "
                   f"included={len(rec['included'])} unknown={len(rec['unknown'])} "
                   f"dropped={len(rec['dropped'])} cuts={len(rec['cuts'])}{mark}")


def _cutoff(since: str) -> float:
    if len(since) < 2 or since[-1] not in WINDOW or not since[:-1].isdigit():
        raise ValueError(f"{since!r} — use 7d, 24h or 30m")
    return datetime.now().timestamp() - int(since[:-1]) * WINDOW[since[-1]]


def audit(root: Path, since: str) -> int:
    """One line per receipt in the window, oldest first; exit 2 on anything unreadable."""
    try:
        cutoff = _cutoff(since)
    except ValueError as exc:
        print(f"SINCE_INVALID: {exc}", file=sys.stderr)
        return 2
    rows, broken = [], []
    for path in sorted((root / "state" / "session").glob("*/area-*.json")):
        try:
            entry = _entry(path)
        except (ValueError, KeyError, TypeError, OSError):
            broken.append(path)
            continue
        if entry[0] >= cutoff:
            rows.append(entry)
    for _, line in sorted(rows):
        print(line)
    for path in broken:
        print(f"RECEIPT_INVALID: {path}", file=sys.stderr)
    return 2 if broken else 0
