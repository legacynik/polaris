#!/usr/bin/env python3
"""`/end` is the only command with closing authority, and closing means REMOVING.

A `~~struck~~` line that stays is still tokens the next session reads and reconciles
(polaris-os#202). So a closed thread leaves `## Open`, its todo row leaves `## Active` and lands in
`## Completed`, and `Updated:` collapses to date and owner — the session summary belongs to
`## Recent Context` and the full handoff to the session log (#240).

What this deliberately does NOT do is decide WHICH thread is closed — that verdict lives in
`end/scripts/merge_truth.py`, which asks the tracker AND this checkout and refuses when either is
silent. Here the job is the WRITE: `close` performs one decided removal, `candidates` lists the
threads a verdict could apply to. Keeping the two apart is why a wrong verdict can never be a
half-written pair of files.

A close touches two files, so `precheck` refuses BEFORE the first byte: the earlier version wrote
the cockpit and only then found the todos file had no `## Completed`. Both files go through the same
lock and the same fence-aware line model as `/update` — two notions of "what a line is" is the root
cause the package already paid for once.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import kinds, lane_id, read, section, table_row, write  # noqa: E402
from state_sections import heading  # noqa: E402
from state_lock import LockError, locked, write_atomic  # noqa: E402
from state_upsert import UpsertError, _stamp_updated  # noqa: E402

# The ONE registry — a heading this script recognised and `state_upsert` did not is how
# `/end` removed a thread `/update` had just refused to write (gate round 2, F1).
OPEN, ACTIVE = heading("## Open"), heading("## Active")
COMPLETED = heading("## Completed")
CITES = re.compile(r"#\d+|\bPR\s*\d+", re.I)
STAMP = re.compile(r"·?\s*Added:\s*W\d+", re.I)
LISTED = ("these are the threads a verdict can apply to — `end/scripts/prune_threads.py` resolves "
          "each one against the tracker and this checkout, and closes only what it can prove")


def find(lines: list[str], span: tuple[int, int], key: str) -> int:
    """The ONE line in `span` whose lane id is `key`, or -1. Two matches are not one."""
    tags = kinds(lines)
    hits = [i for i in range(*span) if tags[i] == "thread" and lane_id(lines[i]) == key]
    return hits[0] if len(hits) == 1 else -1


def take(lines: list[str], name: re.Pattern, key: str) -> str:
    """Remove that LANE from the named section and hand its head line back. "" when absent.

    A lane is the thread line plus what hangs under it — an indented child, a fenced command to
    resume with. Removing only the head left both orphaned under `## Open`, which the next session
    then had to reconcile: "closing means REMOVING" is not "removing the first line".
    ponytail: the run ends at the first blank line, so a fenced block with a blank line inside it
    keeps its tail; a fence-state walk is the upgrade if that ever shows up in a real cockpit.
    """
    span = section(lines, name)
    at = find(lines, span, key) if span else -1
    if at < 0:
        return ""
    head = lines[at]
    tags = kinds(lines)
    end = at + 1
    while end < (span[1] if span else len(lines)) and tags[end] not in ("thread", "heading") \
            and lines[end].strip():
        end += 1
    del lines[at:end]
    return head


def put(lines: list[str], name: re.Pattern, line: str) -> None:
    """Append a line to the end of the named section, above whatever follows it."""
    if (span := section(lines, name)) is None:
        raise UpsertError("NO_SECTION", f"no section matching {name.pattern!r}")
    at = span[1]
    while at > span[0] and not lines[at - 1].strip():
        at -= 1
    lines.insert(at, line)


def close_todo(path: Path, key: str, now: str) -> str:
    """Move the row out of `Active` into `Completed`, stamped with the day it landed.

    The donor writes state as tables, so the row is re-celled, not string-patched: the second cell
    of `Active` is `Added`, of `Completed` it is the date.
    """
    lines, newline, bom = read(path)
    row = take(lines, ACTIVE, key)
    if not row:
        return "absent"
    cells = table_row(row)
    done = f"| {cells[0]} | {now} | {(cells + ['', '', ''])[2]} |" if cells else \
        f"{STAMP.sub('', row).rstrip(' ·')} · Completed: {now}"
    put(lines, COMPLETED, done)
    write_atomic(path, write(lines, newline, bom))
    return "moved"


def precheck(opts: argparse.Namespace) -> None:
    """Every refusal happens BEFORE the first byte is written.

    The first version wrote the cockpit, then found the todos file had no `## Completed`: exit 2
    with the thread gone from `## Open` and nothing recording it. So both are validated first.
    """
    lines, _, _ = read(Path(opts.path))
    span = section(lines, OPEN) or (0, 0)
    if re.fullmatch(r"#\d+", opts.key):       # `#N` names the ONE lane citing it
        hits = [i for i in range(*span) if re.search(rf"{opts.key}\b", lines[i])]
        opts.key = lane_id(lines[hits[0]]) if len(hits) == 1 else opts.key
    if find(lines, span, opts.key) < 0:
        raise UpsertError("UNKNOWN_THREAD", f"no single `{opts.key}` under `## Open` in "
                          f"{opts.path} — refusing to remove a line this key does not name")
    if not opts.todos or not Path(opts.todos).is_file():   # todos.md is optional in the contract
        opts.todos = ""
        return
    rows, _, _ = read(Path(opts.todos))
    for name in (ACTIVE, COMPLETED):
        if section(rows, name) is None:
            raise UpsertError("NO_SECTION", f"{opts.todos} has no section matching "
                              f"{name.pattern!r} — nothing is written until it does")


def cmd_close(opts: argparse.Namespace) -> int:
    """Remove the thread, move its todo, collapse `Updated:`. Validates before it writes."""
    precheck(opts)
    path = Path(opts.path)
    lines, newline, bom = read(path)
    take(lines, OPEN, opts.key)
    _stamp_updated(lines, opts.owner, opts.now)
    write_atomic(path, write(lines, newline, bom))
    todo = "skipped"
    if opts.todos:
        with locked(Path(opts.todos)):       # its own lock: a second file, a second writer
            todo = close_todo(Path(opts.todos), opts.key, opts.now)
    print(json.dumps({"closed": opts.key, "todo": todo, "path": str(path)}))
    return 0


def cmd_candidates(opts: argparse.Namespace) -> int:
    """List the open threads citing an issue or a PR. Read-only, by design: the verdict is not ours."""
    lines, _, _ = read(Path(opts.path))
    span = section(lines, OPEN)
    tags = kinds(lines)
    rows = [lines[i] for i in range(*(span or (0, 0)))
            if tags[i] == "thread" and CITES.search(lines[i])]
    for row in rows:
        print(f"CANDIDATE={row.strip()}")
    print(f"NOTE={LISTED}" if rows else "NOTE=no open thread cites an issue or a PR")
    return 0


def cmd_selfcheck() -> int:
    """One fixture per branch that would remove the wrong line or lose a live one."""
    import tempfile
    from _selfcheck_parts import check_close, score

    def refuses(opts: argparse.Namespace) -> bool:
        try:
            return bool(cmd_close(opts)) and False
        except UpsertError:
            return True

    with tempfile.TemporaryDirectory() as d:
        return score("state_close", check_close(Path(d), cmd_close, refuses))


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="close a thread, or list the candidates")
    ap.add_argument("mode", nargs="?", choices=["close", "candidates"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--key", default="", help="the lane id to close")
    ap.add_argument("--todos", default="", help="the host repo's state/todos.md")
    ap.add_argument("--owner", default="")
    ap.add_argument("--now", default=date.today().isoformat())
    ap.add_argument("--selfcheck", action="store_true")
    return ap


def main() -> int:
    opts = _parser().parse_args()
    if opts.selfcheck:
        return cmd_selfcheck()
    runner = {"close": cmd_close, "candidates": cmd_candidates}
    if not (opts.mode and opts.path):
        print("state_close: a mode and a path are required", file=sys.stderr)
        return 64
    try:
        with locked(Path(opts.path)):
            return runner[opts.mode](opts)
    except (UpsertError, LockError, OSError, ValueError) as exc:
        print(f"{getattr(exc, 'code', 'UNWRITABLE')}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
