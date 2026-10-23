#!/usr/bin/env python3
"""L2-T4 (#403) — which committed files are prose DECISION RECORDS, for the declared layer.

`contextpack_declared.py` owns the layer — the triad, the area map, the order of survival.
This owns one question ahead of it: given everything HEAD carries, which paths are decision
records, and what does the reader get told about the ones that are not? It moved out when
the layer passed its 200-line ceiling for the third review round, which is the right seam:
the discovery rules changed in every round while the layer's shape did not.

**A record is one by WHERE IT LIVES and by a name the corpus uses.** Plan section 5 names
`docs/architecture/ADR-*` and `docs/adr/*`. Round 1 accepted only `ADR-*.md` and dropped 38
records across two repositories in silence (R3). Round 2 accepted any four leading digits
and a date starts with four, so five design notes under `docs/architecture/` entered one
repository as decisions and broke the count in the acceptance criterion of #403 (S1). What
survives both: `ADR-*.md` wherever a record may live, and a sequence number or a date only
where the folder NAME says decisions — `architecture` holds all sorts of documents, while
`adr`, `adrs` and `decisions` are for records and are answered for in full.

**Never an authority, whoever links it.** A test input, a pinned external corpus, another
worktree, a wiki projection, an archive — `NOT_AUTHORITY` — and the root `decisions/`
register, which L2-T2 already answers for and must not be read twice.

**Three things the reader is owed rather than left to guess.** A record with no content is
an `unknown` row; a committed symlink is too, because we will not hash a target the row does
not name and following one out of the tree used to kill the CLI (R2); and a `.md` in a
decisions folder that matches no form is counted in one `unknown` row, because a cap or a
naming scheme that drops a source in silence is the silence this layer exists to end.

Ships with the resolver (`sync_scripts.py`).
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import check_context_backbone as cbb
import contextpack_prose as prose

LOCATIONS = frozenset({"adr", "adrs", "architecture", "decisions"})
RECORD_DIRS = frozenset({"adr", "adrs", "decisions"})   # here every `.md` IS a record
NOT_AUTHORITY = frozenset({"test", "tests", "fixtures", "node_modules", "_archived",
                           "references", "wiki", ".wiki", ".worktrees"})
OWNED = "decisions/"     # the root register is L2-T2's, never read twice
SEQUENCE = re.compile(r"^(?!\d{4}-\d{2}-)\d{3,4}-.*\.md$")
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-.*\.md$")
LIMIT = 256              # records read per repository: 27 in one of ours, 65 in another
# An index is not a record that got its name wrong. `adr/README.md` was counted in the
# `unnameable` row, so the MAP of an area was reported as a defect of the area (residue of
# the #423 gate, closed by L2-T6). It is still nameable BY THE AREA MAP, through
# `contextpack_declared._placed` — dropped from the count, never from the pack.
INDEX = frozenset({"README.md", "readme.md", "index.md", "INDEX.md"})


def _in(rel: str, dirs: frozenset[str]) -> bool:
    return PurePosixPath(rel).parent.name in dirs


def excluded(rel: str) -> bool:
    """A path no layer of this pack may carry, however a document links to it."""
    return bool(NOT_AUTHORITY & set(PurePosixPath(rel).parts)) or rel.startswith(OWNED)


def nameable(rel: str) -> bool:
    """`ADR-*.md` wherever a record may live; a number or a date only where the folder NAME
    says decisions — see the module docstring for the two rounds that set this boundary."""
    name = PurePosixPath(rel).name
    if name.startswith("ADR-"):
        return True
    return bool(SEQUENCE.match(name) or DATED.match(name)) and _in(rel, RECORD_DIRS)


def committed(root: Path) -> tuple[list[str], list[str]]:
    """(the paths HEAD carries, the symlinks among them), root-relative.

    The mode comes from HEAD, not from `is_symlink()` on disk: the worktree decides nothing
    here, and a link committed then replaced on disk would otherwise be read as a file."""
    if not (root / ".git").exists():
        try:
            return [p.relative_to(root).as_posix() for p in cbb._sources_at(root, ".")], []
        except (cbb.ContractError, OSError):
            return [], []
    try:
        found = cbb._head_entries(root, ["."])
    except (cbb.ContractError, OSError):
        return [], []
    return ([name for name, _, mode in found if mode != "120000"],
            [name for name, _, mode in found if mode == "120000"])


def _count_row(source_id: str, many: int, token: str, what: str) -> list[dict[str, Any]]:
    """A number the pack owes the reader, or nothing when there is none to owe."""
    if many <= 0:
        return []
    return [prose.row(source_id, b"", {"layer": "unknown", "kind": "adr", "path": None,
                                       "source_hash": "", "landed": False,
                                       "reason": f"{token}: {many} {what}"})]


def _row(root: Path, rel: str) -> dict[str, Any]:
    """One prose record: the title it carries, the status it states, the bytes at HEAD."""
    raw = prose.committed(root, rel)
    if not raw.strip():
        return prose.row(rel, raw, {"layer": "unknown", "kind": "adr", "landed": False,
                                    "reason": "empty: no content to declare"})
    text = raw.decode("utf-8", "replace")
    stated = prose.fields(text)
    return prose.row(rel, raw, {"kind": "adr", "ts": stated.get("date", ""),
                                "state": prose.word(stated.get("status", "")),
                                "reason": f"prose ADR: {prose.title(text, rel)}"})


def links(found: list[str]) -> list[dict[str, Any]]:
    """A committed symlink in a decisions folder, named rather than dropped (R2)."""
    return [prose.row(rel, b"", {"layer": "unknown", "kind": "adr", "source_hash": "",
                                 "landed": False, "reason": "symlink: not a source the pack "
                                 "can vouch for, it would hash a target it does not name"})
            for rel in found if _in(rel, LOCATIONS) and not excluded(rel)]


def _stamp(rel: str) -> str:
    """The date a dated record carries in its name, or "" (sorts after every date)."""
    name = PurePosixPath(rel).name
    return name[:10] if DATED.match(name) else ""


def _committed_on(root: Path, undated: list[str]) -> dict[str, str]:
    """Last-commit time of each undated record, as `YYYY-MM-DDTHH:MM:SS` UTC so it compares with
    a date in a name. One `git log`, newest first, paths relative to `root`; a git that fails or
    hangs yields no date — the record sorts last, never a crash and never a guess (#457 r1)."""
    if not undated:
        return {}
    try:
        done = subprocess.run(["git", "-C", str(root), "-c", "core.quotePath=false", "log",
                               "--relative", "--format=%x01%ct", "--name-only", "--", *undated],
                              capture_output=True, text=True, timeout=10)
    except (subprocess.TimeoutExpired, OSError):
        return {}
    dates: dict[str, str] = {}
    when = ""
    for line in done.stdout.splitlines():
        if line.startswith("\x01"):
            when = datetime.fromtimestamp(int(line[1:]), timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        elif line:
            dates.setdefault(line, when)
    return dates


def rows(root: Path, paths: list[str]) -> list[dict[str, Any]]:
    """Every prose decision record as a row, plus the two counts the reader is owed."""
    here = [rel for rel in paths
            if rel.endswith(".md") and _in(rel, LOCATIONS) and not excluded(rel)
            and PurePosixPath(rel).name not in INDEX]
    # #457: newest first, because `receipt.fit` pops the tail — a name sort put the
    # oldest dated record first and the budget cut the newest.
    named = sorted(rel for rel in here if nameable(rel))
    dated = _committed_on(root, [rel for rel in named if not _stamp(rel)])
    found = sorted(named, key=lambda rel: (_stamp(rel) or dated.get(rel, ""), rel), reverse=True)
    lost = [rel for rel in here if rel not in set(found) and _in(rel, RECORD_DIRS)]
    return ([_row(root, rel) for rel in found[:LIMIT]]
            + _count_row("adr:over-limit", len(found) - LIMIT, "capped",
                         "prose ADR(s) not read")
            + _count_row("adr:unnameable", len(lost), "unnameable",
                         "record(s) in a decisions folder match no known form"))
