#!/usr/bin/env python3
"""`## Completed` is the current week only — the one prune `plan-week` owns.

`polaris-os#240`: the history, with the why, already lives in `team/<login>/weeks/`, which keeps it
better. Whoever does not know the rule "helps" by dragging old rows forward, and that is exactly how
this file would become the diary three decisions had already killed.

`Active` and `Follow-ups` are never touched here: `Active` is reconciled row by row (a row leaves
only when its work landed), and `Follow-ups` is the one section that crosses weeks.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import kinds, read, section, write  # noqa: E402
from state_lock import LockError, locked, write_atomic  # noqa: E402

COMPLETED = re.compile(r"^#{1,6}\s+completed\s*$", re.I)
ON = re.compile(r"(\d{4}-\d{2}-\d{2})")


def week_of(line: str):
    """The ISO (year, week) a completed row belongs to; None when it carries no date."""
    found = ON.search(line)
    return date.fromisoformat(found.group(1)).isocalendar()[:2] if found else None


def roll(path: Path, now: str) -> dict:
    """Drop the rows completed in an earlier week. A row with no date is left alone."""
    lines, newline, bom = read(path)
    span, tags = section(lines, COMPLETED), kinds(lines)
    week = date.fromisoformat(now).isocalendar()[:2]
    drop = [i for i in range(*(span or (0, 0)))
            if tags[i] == "thread" and week_of(lines[i]) not in (week, None)]
    for i in reversed(drop):
        del lines[i]
    write_atomic(path, write(path, lines, newline, bom))
    return {"dropped": len(drop), "path": str(path)}


def cmd_selfcheck() -> int:
    """Last week's row goes, this week's stays, and the other two sections are untouched."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "todos.md"
        f.write_text("## Active\n\n| Task | Added | Context |\n|---|---|---|\n"
                     "| `a` — x | W32 | |\n\n## Completed\n\n| Task | Completed | Note |\n"
                     "|---|---|---|\n| `old` | 2026-08-10 | |\n| `new` | 2026-09-03 | |\n"
                     "| *None* | | |\n\n## Follow-ups\n\n| Item | Review Date | Note |\n"
                     "|---|---|---|\n| riprendi | 2026-10-01 | |\n")
        with locked(f):
            out = roll(f, "2026-09-03")
        body = f.read_text()
        ok = [out["dropped"] == 1, "`old`" not in body, "`new`" in body,
              "*None*" in body,                      # a row with no date is not ours to drop
              "| W32 |" in body, "riprendi" in body]
    print(f"todos_roll selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


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
