#!/usr/bin/env python3
"""#257 and #407 (X6) — what a receipt hash binds, and what a backdated clock cannot hide.

Two hashes, because one cannot do both jobs:

`receipt_hash`  the IDENTITY of the session: the payload without the clock. Two `end`
                calls a second apart produce the same value, which is what #257 is about
                — `ts` inside this hash made the idempotence of the receipt a coin toss
                (red 2/40 on `origin/main` at parity of everything else).
`file_hash`     the INTEGRITY of the written file, clock included. Without it, dropping
                `ts` out of the hash would let anyone rewrite the timestamp of a start
                receipt and still close the session: the audit trail would say whatever
                the last writer wanted. `verify_chain` checks both.

A receipt written before this module existed carries no `file_hash` and its
`receipt_hash` covers `ts`. That is not tampering, and calling it tampering would strand
every session opened before the merge, so the old form is accepted and the end receipt
says `chain_form: legacy`. New receipts are always `sealed`.

That acceptance is a downgrade path, and it is closed from the other side: dropping
`file_hash` and recomputing the old hash over a backdated record would otherwise pass as
`legacy`. A session whose own checkpoints were written against a sealed receipt cannot
have been born before the two hashes existed — the events still carry the sealed identity
in `prev`, and a `prev` that names it while the file claims the old form is the tell.
A legacy session with no checkpoint at all has nothing to compare, and is accepted: it is
exactly the session that predates this module and never reached an `update`.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as cbb  # noqa: E402

VOLATILE = ("receipt_hash", "file_hash", "receipt_path", "ts")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def payload(record: dict) -> str:
    """The identity of the record: everything but the clock and the hashes."""
    return json.dumps({k: v for k, v in record.items() if k not in VOLATILE}, sort_keys=True)


def dir_for(root: Path, sid: str) -> Path:
    d = root / "state" / "session" / sid
    d.mkdir(parents=True, exist_ok=True)
    return d


def write(path: Path, record: dict) -> dict:
    """Stamp both hashes and write. `receipt_path` is added after, never hashed."""
    body = payload(record)
    record["receipt_hash"] = sha(body)
    record["file_hash"] = sha(body + record.get("ts", ""))
    path.write_text(json.dumps(record, indent=2) + "\n")
    record["receipt_path"] = str(path)
    return record


def _legacy_hash(record: dict) -> str:
    """The pre-#257 form: everything in the file except the hash itself, `ts` included."""
    rest = {k: v for k, v in record.items() if k not in ("receipt_hash", "receipt_path")}
    return sha(json.dumps(rest, sort_keys=True))


def start_record(root: Path, sid: str) -> dict:
    """The start receipt, or SESSION_UNKNOWN — never a FileNotFoundError traceback."""
    path = dir_for(root, sid) / "start.json"
    if not path.is_file():
        raise cbb.ContractError("SESSION_UNKNOWN", f"sid {sid}: no start receipt under {path.parent} — run `start` first")
    return json.loads(path.read_text())


def _claims_sealed(root: Path, sid: str, identity: str) -> bool:
    """Does a checkpoint of this session point at the sealed identity of the receipt?"""
    path = dir_for(root, sid) / "events.jsonl"
    rows = path.read_text().splitlines() if path.is_file() else []
    return any(json.loads(line).get("prev") == identity for line in rows if line.strip())


def verify_chain(root: Path, sid: str) -> dict:
    """The start receipt with `chain_form` set, or CHAIN_BROKEN.

    A sealed receipt must match on BOTH hashes: the identity proves the payload, the file
    hash proves the clock nobody rewrote. A legacy receipt has only the old combined
    form; it is accepted as `legacy` rather than accused, unless a checkpoint of the same
    session already named the sealed identity, which no session born before the two
    hashes could have done.
    """
    start = start_record(root, sid)
    body = payload(start)
    if "file_hash" in start:
        form, intact = "sealed", (start.get("receipt_hash") == sha(body)
                                  and start["file_hash"] == sha(body + start.get("ts", "")))
    else:
        form = "legacy"
        intact = (start.get("receipt_hash") == _legacy_hash(start)
                  and not _claims_sealed(root, sid, sha(body)))
    if not intact:
        raise cbb.ContractError("CHAIN_BROKEN", f"start receipt tampered for sid {sid} ({form} form) — POISON, do not emit an end receipt")
    start["chain_form"] = form
    return start
