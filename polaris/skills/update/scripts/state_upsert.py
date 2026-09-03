#!/usr/bin/env python3
"""T6 — a thread line is UPDATED in place, never appended a second time.

Founder, 2026-09-03: *«Non è che dentro current fa un'altra riga, ma va semplicemente ad
aggiornare l'update precedente. Invece all'interno della session mette sempre un'altra
riga.»* `/update`'s own heading said the opposite («i thread si aggiungono»), so two
sessions on one lane left two lines in the cockpit and the older one never died. The
session log is the ledger; the cockpit is state, and state is overwritten.

The weekly plan is the same operation with a different section: merging `Active` must keep
the week an item was FIRST added in, or every carried item reads as this week's news.

One upsert, two doors: replace the line whose key matches, carry its first-seen stamp
forward, append only what is genuinely new. The key is `state_staleness._lane_id` — the
identity the vault already uses for a lane, so a line reads the same to both tools. Two
existing lines sharing a key refuse rather than guess: the key falls back to a 60-character
lead, and overwriting the wrong lane is worse than a re-run.

Writes are serialised and atomic. Six panels updating six different lanes lost 7 of 60
updates, each reporting success, because every one read the file before the previous write
landed. ponytail: a lock FILE with a stale-age escape rather than fcntl, because the cockpit
is also written by shell and by hand; move to flock if this ever guards more than markdown.

Reads the new line on stdin, prints a JSON receipt. Exit 2 rather than guessing a place.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import kinds, read, section, write  # noqa: E402
from state_lock import LockError, locked, still_mine, write_atomic  # noqa: E402
from state_staleness import _lane_id  # noqa: E402  (sibling script, no package on disk)

HEADING = re.compile(r"^#{1,6}\s")
ADDED = re.compile(r"·?\s*Added:\s*(W\d+)", re.I)
UPDATED = re.compile(r"^Updated:", re.I)
FOOTER = "<!-- pol:state-contract -->"  # the file's own contract closes it; nothing goes below
SECTIONS = {"thread": re.compile(r"^#{1,6}\s+open\b", re.I),
            "week": re.compile(r"^#{1,6}\s+active\b", re.I)}


class UpsertError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


def _section(lines: list[str], door: str) -> tuple[int, int]:
    """The section body, via the shared fence-aware model. Refuses rather than guessing."""
    span = section(lines, SECTIONS[door])
    if span is None:
        raise UpsertError("NO_OPEN_SECTION",
                          f"no `{door}` section in this file — refusing to invent a place for "
                          "the line. Add the heading the contract expects, then re-run.")
    return span


def _carry_stamp(old: str, new: str, week: str) -> str:
    """The stamp says when work FIRST appeared. Carrying it is the whole point of the merge."""
    was = ADDED.search(old or "")
    stamped = ADDED.sub("", new).rstrip(" ·\t")
    return f"{stamped} · Added: {was.group(1) if was else week}"


def _replace(lines: list[str], span: tuple[int, int], line: str) -> tuple[str, int]:
    """Overwrite the line with the same key, else append. Two matches refuse: see the module."""
    key, tags = _lane_id(line), kinds(lines)
    hits = [i for i in range(*span) if tags[i] == "thread" and _lane_id(lines[i]) == key]
    if len(hits) > 1:
        raise UpsertError("AMBIGUOUS_KEY",
                          f"{len(hits)} lines share the key {key!r} (lines "
                          f"{', '.join(str(i + 1) for i in hits)}) — refusing to guess which "
                          "one this update replaces. Make the lane ids distinct, then re-run.")
    if hits:
        lines[hits[0]] = line
        return "replaced", hits[0]
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
        key = _lane_id(line)
        old = next((lines[i] for i in range(*span) if lines[i].strip()
                    and _lane_id(lines[i]) == key), "")
        line = _carry_stamp(old, line, opts.week)
    action, at = _replace(lines, span, line)
    if opts.door == "thread":
        _stamp_updated(lines, opts.owner, opts.now)
    still_mine(path)                  # and again immediately before the write
    write_atomic(path, write(path, lines, newline, bom))
    return {"action": action, "key": _lane_id(line), "line": at + 1, "path": str(path)}


def _selfcheck_thread(f: Path) -> list[bool]:
    """Replace, append above the contract footer, one `Updated:` line, and a loud refusal."""
    opts = argparse.Namespace(door="thread", owner="ada", now="2026-09-03", week="")
    f.write_text(f"Updated: 2026-09-01 — @ada\n\n## Open\n\n- `a` — uno · since 2026-09-01\n\n{FOOTER}\n")
    ok = []
    with locked(f):
        ok.append(upsert(f, "- `a` — due · since 2026-09-01", opts)["action"] == "replaced")
        ok.append(f.read_text().count("`a`") == 1 and "due" in f.read_text())
        ok.append(upsert(f, "- `b` — nuova · since 2026-09-03", opts)["action"] == "appended")
    body = f.read_text()
    ok.append(body.index("- `b`") < body.index(FOOTER))     # never under the file's contract
    ok.append(body.count("Updated:") == 1 and "@ada" in body)
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
        f = Path(d) / "current.md"
        ok = _selfcheck_thread(f)
        f.write_text("## Active\n\n- #1 — x · Added: W32\n")
        with locked(f):
            upsert(f, "- #1 — y", argparse.Namespace(door="week", owner="", now="", week="W34"))
        ok.append("Added: W32" in f.read_text())            # the stamp is carried, not reset
    print(f"state_upsert selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="upsert one line into a state or plan section")
    ap.add_argument("door", nargs="?", choices=["thread", "week"],
                    help="thread: a lane in current.md's `Open`. week: an item in `Active`.")
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--owner", default="", help="thread: the login for the `Updated:` line")
    ap.add_argument("--now", default="", help="thread: ISO date for the `Updated:` line")
    ap.add_argument("--week", default="", help="week: the stamp for a genuinely new item")
    ap.add_argument("--selfcheck", action="store_true")
    return ap


def main() -> int:
    opts = _parser().parse_args()
    if opts.selfcheck:
        return cmd_selfcheck()
    line = sys.stdin.read().strip()
    if not line:
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
