#!/usr/bin/env python3
"""T6 — remove the settled threads from a cockpit, and nothing else.

Split out of `state_reconcile` because judging and removing are different jobs and the file
was over the repository's line limit. Everything here consumes the one line model in
`state_lines`: the fence-aware classification is what makes a removal safe, and every
disagreement between writers about what a heading or a thread is has ended as data loss.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import kinds, read, section, write  # noqa: E402  (one line model)
from state_lock import locked, write_atomic  # noqa: E402  (one lock, one writer)
from state_upsert import SECTIONS  # noqa: E402

_THREAD = re.compile(r"^-\s+`([^`]+)`(?:\s+\(([^)]+)\))?")


def _thread_key(line: str) -> tuple[str, str] | None:
    """(branch, repo) — the identity `classify` judges. The bare branch is NOT it: two repos
    can carry `feat/login`, and collapsing them deleted a live foreign thread."""
    m = _THREAD.match(line)
    return (m.group(1), m.group(2) or "") if m else None


def _survivors(lines: list[str], span: tuple[int, int], keys: set) -> list[str]:
    """Every line except the settled threads inside `span` — header and everything under it.

    Only a thread header ends a block. A blank line does not (children straddle it), and
    neither does any other column-0 line: a code fence under a condemned thread used to
    reset the flag and survive as an orphan.
    """
    keep, dropping, tags = [], False, kinds(lines)
    for i, ln in enumerate(lines):
        if not span[0] <= i < span[1]:
            keep.append(ln)                      # outside `## Open`: never ours to remove
            continue
        if tags[i] == "thread" and (key := _thread_key(ln)) is not None:
            dropping = key in keys
        elif tags[i] == "heading":
            dropping = False
        if not dropping:
            keep.append(ln)
    return keep


def apply_cleanup(state_path: Path, superseded: list[dict]) -> int:
    """Remove settled threads — header and children — by key, in `## Open`, under the lock.

    Text-matching swept `## Next` too; parse-time indices were worse, because any write
    between the read and the apply (another panel's /update, or the stamp collapsing three
    stacked `Updated:` lines) shifted them and deleted a LIVE lane. Re-resolve by key on the
    content about to be written, inside the writer's own lock, and replace atomically.
    """
    keys = {(t["branch"], t["repo"]) for t in superseded}
    if not keys:
        return 0
    return _prune(state_path, keys)


def _prune(state_path: Path, keys: set) -> int:
    """The write half, under the lock."""
    with locked(state_path):
        lines, newline, bom = read(state_path)
        span = section(lines, SECTIONS["thread"])
        if span is None:
            return 0                             # no section, nothing ours to remove
        keep = _survivors(lines, span, keys)
        if keep == lines:
            return 0                             # APPLIED over an untouched file is a bug
        write_atomic(state_path, write(state_path, keep, newline, bom))
    return len(keys)                             # threads, not lines: a thread has children
