#!/usr/bin/env python3
"""`/end` is the only command with closing authority, and closing means REMOVING.

A `~~struck~~` line that stays is still tokens the next session reads and reconciles
(polaris-os#202). So a closed thread leaves `## Open`, its todo row leaves `## Active` and
lands in `## Completed`, and the `Updated:` line collapses to date and owner — the session
summary belongs to `## Recent Context` and the full handoff to the session log (#240).

What this deliberately does NOT do is decide WHICH thread is closed. Automatic removal of
threads citing a merged PR is parked on polaris-os#268: `merge_truth` returns `None` when
the branch ref is gone, which is the normal case after `--delete-branch`, so a remover would
report success and remove nothing. `candidates` lists them and a human closes them. A
declared manual step beats a remover that silently no-ops.

Every write goes through the same lock and the same fence-aware line model as `/update`:
two notions of "what a line is" is the root cause the package already paid for once.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import kinds, lane_id, read, section, write  # noqa: E402
from state_lock import LockError, locked, write_atomic  # noqa: E402
from state_upsert import UpsertError, _stamp_updated  # noqa: E402

OPEN = re.compile(r"^#{1,6}\s+open\b", re.I)
ACTIVE = re.compile(r"^#{1,6}\s+active\s*$", re.I)
COMPLETED = re.compile(r"^#{1,6}\s+completed\s*$", re.I)
CITES = re.compile(r"#\d+|\bPR\s*\d+", re.I)
STAMP = re.compile(r"·?\s*Added:\s*W\d+", re.I)
DONE_ON = re.compile(r"Completed:\s*(\d{4}-\d{2}-\d{2})")
PARKED = ("removal stays MANUAL until polaris-os#268 lands a merge truth that survives a "
          "branch deleted at merge — verify each candidate on GitHub, then close by hand")


def find(lines: list[str], span: tuple[int, int], key: str) -> int:
    """The one line in `span` whose lane id is `key`, or -1."""
    tags = kinds(lines)
    hits = [i for i in range(*span) if tags[i] == "thread" and lane_id(lines[i]) == key]
    return hits[0] if len(hits) == 1 else -1


def take(lines: list[str], name: re.Pattern, key: str) -> str:
    """Remove that line from the named section and hand it back. "" when it is not there."""
    span = section(lines, name)
    if span is None:
        return ""
    at = find(lines, span, key)
    return lines.pop(at) if at >= 0 else ""


def put(lines: list[str], name: re.Pattern, line: str) -> None:
    """Append a line to the end of the named section, above whatever follows it."""
    span = section(lines, name)
    if span is None:
        raise UpsertError("NO_SECTION", f"no section matching {name.pattern!r} — refusing to "
                                        "invent a place for a closed row")
    at = span[1]
    while at > span[0] and not lines[at - 1].strip():
        at -= 1
    lines.insert(at, line)


def close_todo(path: Path, key: str, now: str) -> str:
    """Move the row out of `Active` and into `Completed`, stamped with the day it landed."""
    lines, newline, bom = read(path)
    row = take(lines, ACTIVE, key)
    if not row:
        return "absent"
    put(lines, COMPLETED, f"{STAMP.sub('', row).rstrip(' ·')} · Completed: {now}")
    write_atomic(path, write(path, lines, newline, bom))
    return "moved"


def cmd_close(opts: argparse.Namespace) -> int:
    """Remove the thread, move its todo, collapse `Updated:`. Refuses an unknown key."""
    path = Path(opts.path)
    lines, newline, bom = read(path)
    if not take(lines, OPEN, opts.key):
        print(f"UNKNOWN_THREAD: no single `{opts.key}` under `## Open` in {path} — refusing to "
              "remove a line this key does not name", file=sys.stderr)
        return 2
    _stamp_updated(lines, opts.owner, opts.now)
    write_atomic(path, write(path, lines, newline, bom))
    todo = close_todo(Path(opts.todos), opts.key, opts.now) if opts.todos else "skipped"
    print(json.dumps({"closed": opts.key, "todo": todo, "path": str(path)}))
    return 0


def cmd_candidates(opts: argparse.Namespace) -> int:
    """List the open threads citing an issue or a PR. Read-only, by design (#268)."""
    lines, _, _ = read(Path(opts.path))
    span = section(lines, OPEN)
    tags = kinds(lines)
    rows = [lines[i] for i in range(*(span or (0, 0)))
            if tags[i] == "thread" and CITES.search(lines[i])]
    for row in rows:
        print(f"CANDIDATE={row.strip()}")
    print(f"NOTE={PARKED}" if rows else "NOTE=no open thread cites an issue or a PR")
    return 0


def cmd_week_roll(opts: argparse.Namespace) -> int:
    """`Completed` is the current week only; `Active` and `Follow-ups` are never touched."""
    path = Path(opts.path)
    lines, newline, bom = read(path)
    span, tags = section(lines, COMPLETED), kinds(lines)
    week = date.fromisoformat(opts.now).isocalendar()[:2]
    drop = [i for i in range(*(span or (0, 0))) if tags[i] == "thread"
            and _week_of(lines[i]) not in (week, None)]
    for i in reversed(drop):
        del lines[i]
    write_atomic(path, write(path, lines, newline, bom))
    print(json.dumps({"dropped": len(drop), "path": str(path)}))
    return 0


def _week_of(line: str):
    """The ISO (year, week) a completed row belongs to; None when it carries no date."""
    found = DONE_ON.search(line)
    return date.fromisoformat(found.group(1)).isocalendar()[:2] if found else None


def _fixture(path: Path, todos: Path) -> None:
    path.write_text("Updated: 2026-09-01 — @ada: cinquanta parole di riassunto\n\n## Open\n\n"
                    "- `feat/a` (acme) — uno · since 2026-09-01\n"
                    "- `feat/b` (acme) — chiude #77 · since 2026-09-02\n")
    todos.write_text("## Active\n\n- `feat/a` — uno · Added: W32\n- `feat/b` — due · Added: W36\n"
                     "\n## Completed\n\n- `old` — vecchia · Completed: 2026-08-10\n"
                     "\n## Follow-ups\n\n- riprendi · Review: 2026-10-01\n")


def cmd_selfcheck() -> int:
    """One fixture per branch that would remove the wrong line or lose a live one."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path, todos = Path(d) / "current.md", Path(d) / "todos.md"
        _fixture(path, todos)
        opts = argparse.Namespace(path=str(path), todos=str(todos), key="feat/a",
                                  owner="ada", now="2026-09-03")
        with locked(path):
            ok = [cmd_close(opts) == 0]
        body, rows = path.read_text(), todos.read_text()
        ok += ["feat/a" not in body, "feat/b" in body,
               body.count("Updated:") == 1 and "cinquanta" not in body,
               "- `feat/b` — due · Added: W36" in rows.split("## Completed")[0],
               "Completed: 2026-09-03" in rows.split("## Completed")[1]]
        opts.key = "feat/nope"
        ok.append(cmd_close(opts) == 2)
        cmd_week_roll(argparse.Namespace(path=str(todos), now="2026-09-03"))
        rows = todos.read_text()
        ok += ["vecchia" not in rows, "riprendi" in rows, "Added: W36" in rows]
    print(f"state_close selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="close a thread, list candidates, roll the week")
    ap.add_argument("mode", nargs="?", choices=["close", "candidates", "week-roll"])
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
    runner = {"close": cmd_close, "candidates": cmd_candidates, "week-roll": cmd_week_roll}
    if not opts.mode or not opts.path:
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
