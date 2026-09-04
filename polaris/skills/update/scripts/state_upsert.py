#!/usr/bin/env python3
"""T6 — a thread line is UPDATED in place, never appended a second time.

Founder, 2026-09-03: *«Non è che dentro current fa un'altra riga, ma va semplicemente ad
aggiornare l'update precedente. Invece all'interno della session mette sempre un'altra riga.»*
The session log is the ledger; the cockpit is state, and state is overwritten. The weekly plan is
the same operation in another section: merging `Active` must keep the week an item was FIRST added
in, bullet form or the donor's table form alike, or every carried item reads as this week's news.

One upsert, two doors: replace the line whose key matches, carry its first-seen stamp forward,
append only what is genuinely new — and with `--no-add`, refuse even that: `/update` refreshes a row
the thread cites, only `plan-week` reconciles the section (polaris-os#240). The key is
`state_staleness._lane_id`, the identity the vault already uses, so a line reads the same to both
tools; two sharing one refuse rather than guess. Writes are serialised and atomic — six panels on
six lanes lost 7 of 60 updates, each reporting success, having read before the previous write.
ponytail: a lock FILE with a stale-age escape, not fcntl — the cockpit is also written by shell and
by hand; move to flock if this ever guards more than markdown.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import drop_placeholder, kinds, lane_id, read, section, table_row, write  # noqa
from state_sections import heading  # noqa: E402
from state_lock import LockError, locked, still_mine, write_atomic  # noqa: E402

ADDED = re.compile(r"·?\s*Added:\s*(W\d+)", re.I)
FOOTER = "<!-- pol:state-contract -->"  # the file's own contract closes it; nothing goes below
# One registry (`state_sections`): no door here compiles a heading of its own. The week door means
# the todos file's own `## Active`, which the qualifier rule keeps apart from `## Active Priorities`
# in a cockpit. NO_ADD: the writer may refresh a row, never create one (--no-add).
SECTIONS = {"thread": heading("## Open"), "week": heading("## Active")}
NO_ADD = False


class UpsertError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


def _section(lines: list[str], door: str) -> tuple[int, int]:
    """The section body, via the shared fence-aware model. Refuses rather than guessing."""
    if (span := section(lines, SECTIONS[door])) is None:
        want = "## Open" if door == "thread" else "## Active"
        raise UpsertError("NO_OPEN_SECTION", f"no `{want}` section here — refusing to invent a "
                          f"place. Add `{want}` (a heading may qualify it after a dash, a colon or "
                          "a parenthesis), then re-run.")
    return span


def _carry_cell(cells: list[str], old: str, week: str) -> str:
    """The donor's table form: `Added` is the SECOND cell, carried, never re-stamped."""
    was = table_row(old) or []
    cells = cells + [""] * (3 - len(cells))
    cells[1] = was[1] if len(was) > 1 and was[1] else week
    return "| " + " | ".join(cells) + " |"


def _carry_stamp(old: str, new: str, week: str) -> str:
    """The stamp says when work FIRST appeared; carrying it is the whole point of the merge."""
    cells = table_row(new)
    if cells is not None:
        return _carry_cell(cells, old, week)
    was = ADDED.search(old or "")
    stamped = ADDED.sub("", new).rstrip(" ·\t")
    return f"{stamped} · Added: {was.group(1) if was else week}"


def _place(lines: list[str], span: tuple[int, int], tags: list[str]) -> int:
    """Where a NEW row goes: among the rows, never merely inside the section. The live cockpit
    closes its threads with an `Owner:` line and the new lane landed under it (polaris#11). An
    empty section takes the row under its intro — never above a table's header."""
    anchors = [i for i in range(*span)
               if tags[i] == "thread" or lines[i].lstrip().startswith(("|", "<!--"))]
    if anchors:
        return anchors[-1] + 1
    at = span[0]
    while at < span[1] and not lines[at].strip():
        at += 1
    return at


def _replace(lines: list[str], span: tuple[int, int], line: str) -> tuple[str, int]:
    """Overwrite the line with the same key, else append. Two matches refuse: see the module."""
    key, tags = lane_id(line), kinds(lines)
    hits = [i for i in range(*span) if tags[i] == "thread" and lane_id(lines[i]) == key]
    if len(hits) > 1:
        raise UpsertError("AMBIGUOUS_KEY", f"{len(hits)} lines share the key {key!r} (lines "
                          f"{', '.join(str(i + 1) for i in hits)}) — refusing to guess. "
                          "Make the lane ids distinct, then re-run.")
    if hits:
        lines[hits[0]] = line
        return "replaced", hits[0]
    if NO_ADD:
        raise UpsertError("NO_SUCH_ROW", f"no row keyed {key!r}, and --no-add may not create one: "
                          "plan-week reconciles the section, /update refreshes (polaris-os#240)")
    at = _place(lines, span, tags)
    lines.insert(at, line)
    return "appended", at


def _stamp_updated(lines: list[str], owner: str, now: str) -> None:
    """ONE `Updated:` line, overwritten. The history lives in the session log."""
    keep = [i for i, t in enumerate(kinds(lines)) if t == "updated"]
    fresh = f"Updated: {now} — @{owner}"
    if not keep:
        lines.insert(0, fresh)
        return
    lines[keep[0]] = fresh
    for i in reversed(keep[1:]):
        del lines[i]


def upsert(path: Path, line: str, opts: argparse.Namespace) -> dict:
    """Read, place the line by key, write back. Every other byte comes back untouched."""
    still_mine(path)                  # the lock may have been stolen while we stalled
    lines, newline, bom = read(path)
    span = _section(lines, opts.door)
    if opts.door == "thread":
        span = drop_placeholder(lines, span)   # the contract's example is not a lane (PM-C, D3)
    if opts.door == "week":
        key = lane_id(line)
        old = next((lines[i] for i in range(*span) if lines[i].strip()
                    and lane_id(lines[i]) == key), "")
        line = _carry_stamp(old, line, opts.week)
    action, at = _replace(lines, span, line)
    if opts.door == "thread":
        _stamp_updated(lines, opts.owner, opts.now)
    still_mine(path)                  # and again immediately before the write
    write_atomic(path, write(lines, newline, bom))
    return {"action": action, "key": lane_id(line), "line": at + 1, "path": str(path)}


def cmd_selfcheck() -> int:
    """One fixture per branch that would silently corrupt a cockpit or a plan. The fixtures live
    next door, like `session_commit_selfcheck.sh`: this file carries the guard, not its proof."""
    from state_upsert_selfcheck import run
    return run()


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="upsert one line into a state or plan section")
    ap.add_argument("door", nargs="?", choices=["thread", "week"],
                    help="thread: a lane in current.md `Open`; week: an item in `Active`")
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--owner", default="", help="thread: login on the `Updated:` line")
    ap.add_argument("--now", default="", help="thread: ISO date for `Updated:`; --week: the stamp")
    ap.add_argument("--week", default="")
    ap.add_argument("--no-add", action="store_true", help="only replace a row that exists")
    ap.add_argument("--selfcheck", action="store_true")
    return ap


def main() -> int:
    global NO_ADD
    opts = _parser().parse_args()
    if opts.selfcheck:
        return cmd_selfcheck()
    NO_ADD = opts.no_add
    if not (line := sys.stdin.read().strip()):
        print("state_upsert: nothing on stdin — a line to place is required", file=sys.stderr)
        return 2
    try:
        with locked(opts.path):
            print(json.dumps(upsert(opts.path, line, opts), indent=2))
    except (UpsertError, LockError, OSError) as exc:
        code = getattr(exc, "code", "UNREADABLE")
        print(f"{code}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
