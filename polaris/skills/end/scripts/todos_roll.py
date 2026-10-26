#!/usr/bin/env python3
"""`## Completed` is the current week only — the one prune `week` owns.

`polaris-os#240`: the history, with the why, already lives in `team/<login>/weeks/`, which keeps it
better. Whoever does not know the rule "helps" by dragging old rows forward, and that is exactly how
this file would become the diary three decisions had already killed.

`Follow-ups` is the one section that crosses weeks, and the reason it exists is the promotion the
contract promises: a Review Date that has arrived puts the row back in `Active`. Nothing implemented
that promise, so the template made a claim `week` then denied. It is implemented here, in the
one command that already owns this file's weekly rhythm.

A promoted row keeps its ORIGIN, not today: `Added` is the ISO week of the Review Date — the week
the item actually came due. Stamping it with the current week would erase exactly the age signal
`Added` exists to carry.

`Active` is never emptied and never reconciled here: a row leaves it only when its work landed, and
that is `/end`'s move.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import kinds, read, section, table_row, write  # noqa: E402
from state_sections import heading  # noqa: E402
from state_lock import LockError, locked, write_atomic  # noqa: E402

# The ONE registry: a host that heads `## Active — settimana 36` promoted no follow-up
# here while `/update` wrote to it happily, rc 0 and no message (gate round 2, F1).
COMPLETED, ACTIVE = heading("## Completed"), heading("## Active")
FOLLOWUPS = heading("## Follow-ups")
ON = re.compile(r"(\d{4}-\d{2}-\d{2})")
PLACEHOLDER = re.compile(r"^[\s|*]*(none|nessuno)?[\s|*]*$", re.I)


def week_of(line: str):
    """The ISO (year, week) a completed row belongs to; None when it carries no date."""
    found = ON.search(line)
    return date.fromisoformat(found.group(1)).isocalendar()[:2] if found else None


def due_rows(lines: list[str], now: str) -> list[int]:
    """The follow-ups whose Review Date has arrived, newest last. Placeholders are not rows."""
    span, tags = section(lines, FOLLOWUPS), kinds(lines)
    return [i for i in range(*(span or (0, 0)))
            if tags[i] == "thread" and not PLACEHOLDER.match(lines[i])
            and (ON.search(lines[i]) or [""]) and _on(lines[i]) and _on(lines[i]) <= now]


def _on(line: str) -> str:
    found = ON.search(line)
    return found.group(1) if found else ""


def promote(lines: list[str], now: str) -> int:
    """Move each due follow-up into `Active`, stamped with the week it came due, not today."""
    due = due_rows(lines, now)
    rows = [lines[i] for i in due]
    for i in reversed(due):
        del lines[i]
    for row in rows:
        cells = table_row(row) or []
        stamp = "W%02d" % date.fromisoformat(_on(row)).isocalendar()[1]
        moved = f"| {cells[0]} | {stamp} | {(cells + ['', '', ''])[2]} |" if cells else row
        span = section(lines, ACTIVE)
        if span is None:
            return 0
        at = span[1]
        while at > span[0] and not lines[at - 1].strip():
            at -= 1
        lines.insert(at, moved)
    return len(rows)


def roll(path: Path, now: str) -> dict:
    """Drop last week's `Completed`, then promote the follow-ups that came due."""
    lines, newline, bom = read(path)
    span, tags = section(lines, COMPLETED), kinds(lines)
    week = date.fromisoformat(now).isocalendar()[:2]
    drop = [i for i in range(*(span or (0, 0)))
            if tags[i] == "thread" and week_of(lines[i]) not in (week, None)]
    for i in reversed(drop):
        del lines[i]
    moved = promote(lines, now)
    write_atomic(path, write(lines, newline, bom))
    return {"dropped": len(drop), "promoted": moved, "path": str(path)}


def cmd_selfcheck() -> int:
    """Last week's Completed goes, a due follow-up is promoted, everything else stays put."""
    import tempfile
    from _selfcheck_parts import check_roll, score
    with tempfile.TemporaryDirectory() as d:
        return score("todos_roll", check_roll(Path(d), roll, locked))


def main() -> int:
    ap = argparse.ArgumentParser(description="drop Completed rows from an earlier week")
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--now", default=date.today().isoformat())
    ap.add_argument("--selfcheck", action="store_true")
    opts = ap.parse_args()
    if opts.selfcheck:
        return cmd_selfcheck()
    if not opts.path:
        print("todos_roll: a path is required", file=sys.stderr)
        return 64
    try:
        with locked(opts.path):
            print(json.dumps(roll(opts.path, opts.now)))
    except (LockError, OSError, ValueError) as exc:
        print(f"TODOS_ROLL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
