#!/usr/bin/env python3
"""L2-T2 (#402) — the UNKNOWN layer of the ContextPack.

A repository with no typed backbone is the normal case outside the vault, and until now
the resolver answered it with an exception: the agent got nothing, and could not tell
"this repository declares no decisions" from "nobody asked". The plan's invariant is the
opposite — *una fonte mancante produce una riga UNKNOWN, mai il silenzio*.

**The invariant, in one sentence: every live document produces exactly one row — `sealed`
when the validator accepts it, `declared` when L2-T4 can read it as prose, and `unknown`
with a TRUE reason otherwise; `absent()` decides on the path relative to the root, never on
the name.**

Both halves were broken in round 1 and are what the tests in
`scripts/test/test_contextpack_breaker_r2.py` hold down:

- A `DOMAIN.md` that parsed fine produced NO row, in any list — a valid authority simply
  vanished. Emitting nothing for a document is the silence this layer exists to end, so a
  typed document the pack could not seal now gets an `unsealed` row with its real hash.
- A reason is a claim, and a false claim is worse than an exception. `missing` was reported
  for bytes `git show` returns, and `no_frontmatter: readable prose` for a file of zero
  bytes. Each state has its own word now, and every word is about the COMMITTED bytes: read
  at HEAD exactly as the sealed branch reads them, so one commit is one pack.
- Frontmatter of `: :` parses to `{'': ':'}` without raising, so broken YAML passed as a
  typed authority. The check is the validator's OWN `DOC_REQUIRED`, never a second opinion.
- `absent()` compared basenames, so a broken module dossier at
  `docs/modules/CONTEXT/CONTEXT.md` turned an exit 2 into an UNKNOWN pack. Only the three
  paths AT THE ROOT are absence.

This layer never promotes anything: it emits `layer: unknown` only, and the pack it
builds has empty `decisions`, `documents` and `areas` by construction. Carrying a prose
document as a *declared* row is L2-T4's, and since the critic of PR #423 this layer
STANDS ASIDE for one (`_declared_elsewhere`) rather than emitting a second row about it.
Every other violation still exits 2: a broken backbone is not an absent one.

**The register never claims a verdict it did not reach.** `decisions/` is reported from
HEAD — how many `DEC-*.md` are committed — and never as `invalid`. This branch runs only
because the live documents could not be read, so whether the register validates is NOT
KNOWABLE here. By
the same construction no row here can be `sealed`: the branch exists because it refused.

**Field map to section 4 of the lifecycle plan** (`2026-09-14-contextpack-lifecycle-plan`),
so the declared (L2-T4) and flight (L2-T3) layers extend one vocabulary, not a second:

| this row | section 4 | note |
|---|---|---|
| `layer` | `layer` | always `unknown` here |
| `kind` | `kind` | `context`, `architecture`, `domain` from `cbb.LIVE_DOCS`, or `decision-register` |
| `source_id` | `source_id` | the address the pack is asked about |
| `path` | `path` | the repository-relative path; never null in this layer |
| `source_hash` | `hash` | kept under the name the SEALED rows already use — one name for one thing |
| `freshness` | `freshness` | always `UNKNOWN` here |
| `reason` | `reason` | `<token>: <prose>`, the token from `WHY` |

`landed`, `verified_against` and `budget_tokens` are section-4 fields this layer does NOT
emit: claims about a tracker, a verification and a budget the other layers own — unclaimed
on purpose, not forgotten.

It lives outside `contextpack.py` because that file is grandfathered above the 200-line
ceiling and may only shrink; it ships with the resolver (`sync_scripts.py`).
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import check_context_backbone as cbb
import contextpack_prose as prose

BACKBONE_ABSENT = frozenset({"LIVE_DOC_MISSING", "FRONTMATTER_MISSING",
                             "FRONTMATTER_INVALID", "HEAD_UNREADABLE"})
REGISTER = "decisions/"
WHY = {"missing": "no committed bytes under this path",
       "empty": "no content",
       "no_frontmatter": "readable prose: nothing typed to seal",
       "invalid": "frontmatter present and not a document record",
       "unsealed": "typed and readable, but nothing sealed it"}


def _relative(root: Path, detail: str) -> str:
    """The detail of a ContractError as a path relative to the root, or "" if outside."""
    path = Path(detail.split(": ")[0].strip())
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return ""


def absent(root: Path, exc: cbb.ContractError) -> bool:
    """True when the backbone is not there to be sealed, false when it is there and broken.

    Two questions, and the second is the one round 1 got wrong: the code must be one of
    absence, AND the detail must be one of the three live documents AT THE ROOT. A
    decision record or a module dossier raises the same codes and is a BROKEN authority,
    which must still exit 2 rather than degrade into a shrug."""
    return exc.code in BACKBONE_ABSENT and _relative(root, str(exc.detail)) in cbb.LIVE_DOCS


def _committed(root: Path, path: Path) -> bytes | None:
    """The bytes the pack can vouch for, or None when there are none to vouch for."""
    try:
        return cbb._source_bytes(root, path, at_head=True)
    except (cbb.ContractError, OSError):
        return None


def _typed(raw: bytes, path: Path) -> str | None:
    """None when `raw` is a document record, else why it is not one."""
    try:
        record = cbb._parse_frontmatter(raw.decode(), path)
    except cbb.ContractError as exc:
        return "no_frontmatter" if exc.code == "FRONTMATTER_MISSING" else "invalid"
    except (UnicodeDecodeError, ValueError):
        return "invalid"
    return None if cbb.DOC_REQUIRED <= set(record) else "invalid"


def _fault(root: Path, name: str) -> tuple[str, bytes | None]:
    """Why `name` cannot be sealed, and the bytes it is answered for.

    Read at HEAD like every other source: the pack vouches for committed bytes and for
    nothing else (#199), so a worktree that diverges cannot change the answer. Nothing
    here returns None — in a pack the validator refused, even a perfectly typed document
    is `unsealed`, never silently dropped."""
    raw = _committed(root, root / name)
    if raw is None:
        return "missing", None
    if not raw.strip():
        return "empty", raw
    return _typed(raw, root / name) or "unsealed", raw


def _base(source_id: str, kind: str) -> dict[str, Any]:
    """The section-4 fields every row in this layer carries, whatever it is about."""
    return {"source_id": source_id, "layer": "unknown", "kind": kind,
            "path": source_id, "freshness": "UNKNOWN"}


def _row(root: Path, name: str) -> dict[str, Any]:
    """One row, and its hash is of the bytes the reason talks about — never invented."""
    fault, raw = _fault(root, name)
    return dict(_base(name, cbb.LIVE_DOCS[name]),
                source_hash="" if raw is None else sha256(raw).hexdigest(),
                reason=f"{fault}: {WHY[fault]}")


def _records(root: Path) -> list[Path]:
    """The decision records HEAD carries — never a draft somebody left on disk."""
    folder = root / "decisions"
    return [p for p in _committed_paths(root)
            if p.parent == folder and p.name.startswith("DEC-")]


def _committed_paths(root: Path) -> list[Path]:
    try:
        return cbb._sources_at(root, "decisions", at_head=True)
    except (cbb.ContractError, OSError):
        return []


def _register_row(root: Path) -> dict[str, Any]:
    """What HEAD says about the register — never a verdict this branch cannot reach."""
    records = _records(root)
    why = (f"{len(records)} committed record(s), unvalidated: the live documents could not be read"
           if records else "no committed decision records under this path")
    return dict(_base(REGISTER, "decision-register"), source_hash="",
                reason=f"{'missing' if not records else 'unsealed'}: {why}")


def rows(root: Path) -> list[dict[str, Any]]:
    """One row per live document the declared layer does not own, plus the register.

    One source, one row (critic of PR #423), chosen HERE — before `contextpack_seal.seal` —
    so the declared layer only ever ADDS and `pack_seal` keeps reconstructing. The question
    is asked through `prose.is_readable_prose`, the SAME predicate `contextpack_declared`
    calls: round 2 read the `no_frontmatter` token out of a reason string here while the
    other module took its own second read, two answers to one question that could drift
    into a gap (S7)."""
    return ([_row(root, name) for name in cbb.LIVE_DOCS
             if not prose.is_readable_prose(root, name)] + [_register_row(root)])


def pack(root: Path, work_item: str, domains: list[str]) -> dict[str, Any]:
    """A pack with no sealed row: what it cannot prove, named, instead of an exception."""
    root = root.resolve()
    return {"schema_version": 1, "work_item": work_item or f"foundation:{root.name}",
            "workspace": "UNKNOWN", "repo": root.name, "domains": sorted(set(domains)),
            "decisions": [], "documents": [], "areas": [], "dropped": [],
            "unknown": rows(root)}
