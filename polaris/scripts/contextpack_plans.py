"""contextpack_plans — the repository's plans folder enters the declared layer (#432, INC-03).

INC-03 (2026-09-04): a canonical plan already on `origin/main` was duplicated by a record
written from a stale copy, because no /start pack carried the plan. The folder is the one the
repository DECLARES — `outputs.plan` in its Polaris contract, `<area>` read as a wildcard —
and `docs/plans/` when it declares nothing: the writer, the gate and the pack read one map.
A plan under `archive/`, `_archived/` or `done/` is counted, never carried; `status:` is
reported as stated and never promoted; a committed symlink is named, not hashed.
"""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path, PurePosixPath
from typing import Any

import contextpack_prose as prose
import contextpack_records as records

DEFAULT_DIR = "docs/plans"
ARCHIVED = frozenset({"archive", "_archived", "done"})
INDEX = records.INDEX
LIMIT = records.LIMIT
OUTPUTS = re.compile(r"^outputs:\n((?:[ \t]+.*\n?)+)", re.M)
PLAN_KEY = re.compile(r"^[ \t]+plan(?:_done)?:[ \t]*(\S+)", re.M)
CELLS = re.compile(r"^\|(.+)\|\s*$")


def plan_dirs(root: Path) -> list[str]:
    """The folder patterns `outputs.plan` and `outputs.plan_done` declare (`<area>` → `*`),
    else the default: an archive the map names beside the live folder is counted, not lost."""
    for rel in ("_polaris/config.yml", "config.yml"):
        cfg = root / rel
        if not cfg.is_file():
            continue
        block = OUTPUTS.search(cfg.read_text(errors="replace"))
        hits = PLAN_KEY.findall(block.group(1)) if block else []
        if hits:
            return sorted({PurePosixPath(h.replace("<area>", "*")).parent.as_posix() for h in hits})
    return [DEFAULT_DIR]


def _under(rel: str, patterns: list[str]) -> bool:
    parent = PurePosixPath(rel).parent.as_posix()
    return any(fnmatch.fnmatch(parent, p) or fnmatch.fnmatch(parent, p + "/*") for p in patterns)


def _dead(rel: str) -> bool:
    """A path no layer may carry — the records' boundary, minus the archives this file counts."""
    return bool((records.NOT_AUTHORITY - ARCHIVED) & set(PurePosixPath(rel).parts)) \
        or rel.startswith(records.OWNED)


def _map_area(root: Path, rel: str, paths: list[str]) -> str | None:
    """The area whose map lists the plan: a README table row naming the path, first cell
    the slug — the shape `area_map.py` generates, and the fixture's own declaration."""
    for readme in (p for p in paths if PurePosixPath(p).name in INDEX):
        for line in prose.committed(root, readme).decode("utf-8", "replace").splitlines():
            cells = [c.strip().strip("`") for c in CELLS.match(line).group(1).split("|")] \
                if CELLS.match(line) else []
            if rel in cells and cells[0] and not cells[0].startswith("-"):
                return cells[0]
    return None


def area_of(root: Path, rel: str, paths: list[str]) -> str | None:
    """`<area>` read off the declared path first, the area map that lists it second."""
    for pattern in plan_dirs(root):
        if "*" in pattern:
            for a, b in zip(pattern.split("/"), PurePosixPath(rel).parts):
                if a == "*":
                    return b
    return _map_area(root, rel, paths)


def _row(root: Path, rel: str, area: str | None) -> dict[str, Any]:
    raw = prose.committed(root, rel)
    if not raw.strip():
        return prose.row(rel, raw, {"layer": "unknown", "kind": "plan", "landed": False,
                                    "reason": "empty: no content to declare"})
    text = raw.decode("utf-8", "replace")
    stated = prose.fields(text)
    placed = {"area": area} if area else {"reason_unplaced": "no area names it"}
    return prose.row(rel, raw, {"kind": "plan", "ts": stated.get("date", ""),
                                "state": prose.word(stated.get("status", "")),
                                "reason": f"plan: {prose.title(text, rel)}", **placed})


def _count(many: int, token: str, what: str) -> list[dict[str, Any]]:
    if many <= 0:
        return []
    return [prose.row(f"plan:{token}", b"", {"layer": "unknown", "kind": "plan", "path": None,
                                             "source_hash": "", "landed": False,
                                             "reason": f"{token}: {many} {what}"})]


def links(root: Path, found: list[str]) -> list[dict[str, Any]]:
    """A committed symlink in the plans folder: named, never hashed (it would vouch for a
    target it does not name, possibly outside the root)."""
    return [prose.row(rel, b"", {"layer": "unknown", "kind": "plan", "source_hash": "",
                                 "landed": False, "reason": "symlink: not a source the pack "
                                 "can vouch for"})
            for rel in found if _under(rel, plan_dirs(root)) and not _dead(rel)]


def rows(root: Path, paths: list[str], areas: list[str] = ()) -> list[dict[str, Any]]:
    """Every live plan as a declared row placed in its area when one names it (and it is
    an area the caller asked for), the archived ones as one count the reader is owed."""
    dirs = plan_dirs(root)
    here = [rel for rel in paths if rel.endswith(".md") and _under(rel, dirs)
            and not _dead(rel) and PurePosixPath(rel).name not in INDEX]
    archived = [rel for rel in here if ARCHIVED & set(PurePosixPath(rel).parts)]
    live = sorted(rel for rel in here if rel not in set(archived))
    def placed(rel: str) -> str | None:
        area = area_of(root, rel, paths)
        return area if (area and (not areas or area in areas)) else None
    return ([_row(root, rel, placed(rel)) for rel in live[:LIMIT]]
            + _count(len(live) - LIMIT, "over-limit", "plan(s) not read")
            + _count(len(archived), "archived", "plan(s) archived, counted and not carried"))
