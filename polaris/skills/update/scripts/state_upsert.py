#!/usr/bin/env python3
"""T6 — a thread line is UPDATED in place, never appended a second time.

Founder, 2026-09-03: *«Non è che dentro current fa un'altra riga, ma va semplicemente ad
aggiornare l'update precedente. Invece all'interno della session mette sempre un'altra riga.»*
The session log is the ledger; the cockpit is state, and state is overwritten. The weekly plan is
the same operation in another section: merging `Active` must keep the week an item was FIRST added
in, bullet form or the donor's table form alike, or every carried item reads as this week's news.

One upsert, two doors: replace the line whose key matches, carry its first-seen stamp forward,
append only what is genuinely new — and with `--no-add`, refuse even that: `/update` refreshes a
row the thread cites, only `plan-week` reconciles the section (polaris-os#240). The key is `state_staleness._lane_id`, the identity the vault already uses, so a line reads the
same to both tools. Two lines sharing a key refuse rather than guess: overwriting the wrong lane is
worse than a re-run. Writes are serialised and atomic — six panels on six lanes lost 7 of 60
updates, each reporting success, because every one read the file before the previous write landed.
ponytail: a lock FILE with a stale-age escape, not fcntl — the cockpit is also written by shell
and by hand; move to flock if this ever guards more than markdown.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import kinds, lane_id, read, section, table_row, write  # noqa: E402
from state_lock import LockError, locked, still_mine, write_atomic  # noqa: E402

ADDED = re.compile(r"·?\s*Added:\s*(W\d+)", re.I)
FOOTER = "<!-- pol:state-contract -->"  # the file's own contract closes it; nothing goes below
SECTIONS = {"thread": re.compile(r"^#{1,6}\s+open\b", re.I),
            "week": re.compile(r"^#{1,6}\s+active\s*$", re.I)}
# `## Active Priorities` in a cockpit also starts with "active": the week door means the todos
# file's own `## Active`. NO_ADD: the writer may refresh a row, never create one (--no-add).
NO_ADD = False


class UpsertError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


def _section(lines: list[str], door: str) -> tuple[int, int]:
    """The section body, via the shared fence-aware model. Refuses rather than guessing."""
    if (span := section(lines, SECTIONS[door])) is None:
        raise UpsertError("NO_OPEN_SECTION", f"no `{door}` section here — refusing to invent a "
                          "place. Add the heading the contract expects, then re-run.")
    return span


def _carry_cell(cells: list[str], old: str, week: str) -> str:
    """The donor's table form: `Added` is the SECOND cell, and it is carried, never re-stamped."""
    was = table_row(old) or []
    cells = cells + [""] * (3 - len(cells))
    cells[1] = was[1] if len(was) > 1 and was[1] else week
    return "| " + " | ".join(cells) + " |"


def _carry_stamp(old: str, new: str, week: str) -> str:
    """The stamp says when work FIRST appeared. Carrying it is the whole point of the merge."""
    cells = table_row(new)
    if cells is not None:
        return _carry_cell(cells, old, week)
    was = ADDED.search(old or "")
    stamped = ADDED.sub("", new).rstrip(" ·\t")
    return f"{stamped} · Added: {was.group(1) if was else week}"


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
    at = span[1]
    while at > span[0] and not lines[at - 1].strip():  # keep the blank line before what follows
        at -= 1
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
    if opts.door == "week":
        key = lane_id(line)
        old = next((lines[i] for i in range(*span) if lines[i].strip()
                    and lane_id(lines[i]) == key), "")
        line = _carry_stamp(old, line, opts.week)
    action, at = _replace(lines, span, line)
    if opts.door == "thread":
        _stamp_updated(lines, opts.owner, opts.now)
    still_mine(path)                  # and again immediately before the write
    write_atomic(path, write(path, lines, newline, bom))
    return {"action": action, "key": lane_id(line), "line": at + 1, "path": str(path)}


def _selfcheck_thread(f: Path) -> list[bool]:
    """Replace, append above the footer, one `Updated:` line, a loud refusal."""
    opts = argparse.Namespace(door="thread", owner="ada", now="2026-09-03", week="")
    f.write_text(f"Updated: 2026-09-01 — @ada\n\n## Open\n\n- `a` — uno · since 2026-09-01\n\n{FOOTER}\n")
    ok = []
    with locked(f):
        ok.append(upsert(f, "- `a` — due · since 2026-09-01", opts)["action"] == "replaced")
        ok.append(f.read_text().count("`a`") == 1 and "due" in f.read_text())
        ok.append(upsert(f, "- `b` — nuova · since 2026-09-03", opts)["action"] == "appended")
    body = f.read_text()
    ok += [body.index("- `b`") < body.index(FOOTER),        # never under the file's contract
           body.count("Updated:") == 1 and "@ada" in body]
    f.write_text("# nothing\n")
    try:
        with locked(f):
            upsert(f, "- `z` — x", opts)
        ok.append(False)                                    # must have refused
    except UpsertError as exc:
        ok.append(exc.code == "NO_OPEN_SECTION")
    return ok


def cmd_selfcheck() -> int:
    """One fixture per branch that would silently corrupt a cockpit or a plan."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "current.md"; ok = _selfcheck_thread(f)
        f.write_text("## Active\n\n- #1 — x · Added: W32\n")
        week = argparse.Namespace(door="week", owner="", now="", week="W34")
        with locked(f):
            upsert(f, "- #1 — y", week)
        ok.append("Added: W32" in f.read_text())            # the stamp is carried, not reset
        # The donor's TABLE form, which is what the vault and the shipped template really use.
        f.write_text("## Active\n\n| Task | Added | Context |\n|---|---|---|\n"
                     "| #1 — x | W32 | ctx |\n")
        with locked(f):
            ok.append(upsert(f, "| #1 — y | | |", week)["action"] == "replaced")
        body = f.read_text()
        ok += [body.count("#1") == 1, "| W32 |" in body, "W34" not in body]
    print(f"state_upsert selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="upsert one line into a state or plan section")
    ap.add_argument("door", nargs="?", choices=["thread", "week"],
                    help="thread: a lane in current.md's `Open`. week: an item in `Active`.")
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--owner", default="", help="thread: login for the `Updated:` line")
    ap.add_argument("--now", default="", help="thread: ISO date for `Updated:`")
    ap.add_argument("--week", default="", help="week: the stamp for a genuinely new item")
    ap.add_argument("--no-add", action="store_true",
                    help="refuse to append: only replace a row that already exists")
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
