#!/usr/bin/env python3
"""L2-T4 (#403) — the lessons of an area, for the declared layer of the ContextPack.

A lesson is the one source in this layer that can be WRONG. INC-14 of the corpus of #63 is
the ledger's most recurrent lesson prescribing the opposite of the right thing, which is why
the founder answered question 2 of the lifecycle plan the way he did (2026-09-17): a lesson
enters the pack only once somebody verified it still describes the code, and otherwise it is
an `unknown` row saying so — counted, never silent (plan section 6 rule 2).

Round 2 of the #423 breaker found that promise unkept in three places:

- **`verified_against` was a presence check** (R5). `deadbeefdeadbeef…`, `HEAD` and
  a bare filesystem path all counted as a verification, which inverts the founder's decision
  of implementing it. It must RESOLVE to a commit of this repository, and `HEAD` is refused
  along with the rest: a name that means a different commit tomorrow verifies nothing today.
- **two lessons with the same first sixty characters collided** (R7). One `source_id` and
  one `source_hash` — the hash was of the whole ledger — so one of the two was unreachable
  and the pack deduplicated it without a word. The id carries the block's ordinal and the
  hash is of the BLOCK, which is also what lets a receipt say which lesson was delivered.
- **`Recurrence: many` answered 0** (R8). The field is now absent unless an integer was
  stated; `contextpack_prose.count` returns `None` and this module omits it.

**A lesson of no area is not this area's lesson.** It gets neither row, exactly as the flight
layer's tracker is not asked about an area nobody named. That is also what keeps a healthy
sealed pack free of an `unknown` layer: the vault's own ledger declares no area, so resolving
the vault emits no lesson row of either kind.

It ships with the resolver (`_standard/sync_scripts.py`).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import contextpack_prose as prose

LEDGER = "lessons.md"
# An object name, and nothing else. A denylist of three moving names let `main`, an
# annotated tag and any other resolvable string through (S3); the shape is the rule, and
# `^{commit}` after it is what refuses a blob whose own sha has exactly this shape.
OBJECT = re.compile(r"[0-9a-f]{7,40}")
TIMEOUT = 30
UNVERIFIED = ("unverified", "no verified_against, so nobody has proved it still "
                            "describes the code")
UNRESOLVED = ("unresolved", "verified_against does not resolve to a commit of this "
                            "repository")


def _resolves(root: Path, value: str) -> bool:
    """Whether `value` names a COMMIT this repository carries.

    Two gates, because either alone lets a non-verification through (S3). The shape refuses
    every moving name — `HEAD`, `main`, a tag — since a name that means a different commit
    tomorrow records no verification today. `^{commit}` then refuses an object that is not
    one: a blob's sha has exactly the right shape and git resolves it happily."""
    if not OBJECT.fullmatch(value):
        return False
    try:
        done = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "cat-file",
                               "-e", f"{value}^{{commit}}"],
                              capture_output=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def _fault(root: Path, stated: dict[str, str]) -> tuple[str, str] | None:
    """Why this lesson may not be a declared row, or None when it may."""
    value = stated.get("verified_against", "")
    if not value:
        return UNVERIFIED
    return None if _resolves(root, value) else UNRESOLVED


def _row(block: str, ordinal: int, stated: dict[str, str]) -> dict[str, Any]:
    """One lesson of the ledger, addressed and hashed by its OWN block (R7)."""
    head = block.splitlines()[0][3:].strip()
    stamp = prose.DATE.search(head)
    times = prose.count(stated.get("recurrence", ""))
    built = prose.row(f"{LEDGER}#{ordinal:03d}-{prose.slug(head)[:60]}",
                      block.encode("utf-8", "replace"),
                      {"kind": "lesson", "path": LEDGER, "area": stated["area"],
                       "ts": stamp.group() if stamp else "",
                       "verified_against": stated.get("verified_against") or None,
                       "reason": f"lesson of area {stated['area']}: "
                                 f"{head[:prose.TITLE_MAX]}"})
    return built if times is None else dict(built, recurrence=times)


def rows(root: Path, paths: list[str], areas: list[str]) -> list[dict[str, Any]]:
    """The area's lessons: a declared row each when verified, an `unknown` row otherwise."""
    raw = prose.committed(root, LEDGER) if LEDGER in paths else b""
    found = []
    for ordinal, block in enumerate(prose.blocks(raw.decode("utf-8", "replace"))):
        stated = prose.fields(block)
        if stated.get("area", "") not in areas:
            continue
        row = _row(block, ordinal, stated)
        fault = _fault(root, stated)
        found.append(row if fault is None else dict(
            row, layer="unknown", landed=False, reason=f"{fault[0]}: {fault[1]}"))
    return found
