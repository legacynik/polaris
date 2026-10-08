#!/usr/bin/env python3
"""`## Active Priorities` — the order of the work, written by /end, read by /start.

Founder, 2026-09-23: the cockpit is the one live view («uso solo current, goals e todo»), so the
priorities live IN it and one door keeps them: /end reconciles them every session from
`goals.md`, `todos.md` and the `## Open` threads, and writes them here. No door owned the section
before, and on a product repository it sat at 13/09 for ten days; that day's hand edit found the
heading with an unanchored `s.index`, matched a backtick mention in the prose, and fused the new
heading into a sentence. So: the heading is found by the fence-aware registry (`section`,
`heading`), the write is atomic under the cockpit lock, and a date stamp lets /start say when the
order is old instead of presenting it as current.

    printf '%s\\n' "#11 domande → prod" "#12 step 1" | state_priorities.py set current.md
    state_priorities.py check current.md        # PRIORITIES_STALE=<n>d, or silence
    state_priorities.py prune current.md        # drop what the tracker has proven closed

`prune` is the one write `/update` may make here, and it decides nothing: an item leaves only when
every issue or PR it cites is PROVEN done by the same verdict `/end` uses (abandoned work, `DEAD`,
waits for `/end`), and the stamp keeps the day `/end` last ordered the work, because dropping a
finished item is not re-ordering.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import read, section, write  # noqa: E402
from state_lock import LockError, locked, still_mine, write_atomic  # noqa: E402
from state_sections import exact, heading  # noqa: E402

TITLE = "## Active Priorities"
STAMP = re.compile(r"^<!-- pol:priorities updated=(\d{4}-\d{2}-\d{2}) -->$")
NUMBERED = re.compile(r"^\s*(?:\d+[.)]|[-*])(?:\s+|$)")  # a bare `1.` is a marker, not an item
STALE_DAYS = 7
# The h2 exactly (`exact`), never the any-level `heading()`: breaker on polaris#42.
OWN = exact(TITLE)
FOOTER = "<!-- pol:state-contract -->"


def block(items: list[str], now: str) -> list[str]:
    """The section body exactly as it lands: blank, stamp, the numbered order, blank."""
    return ["", f"<!-- pol:priorities updated={now} -->",
            *[f"{n}. {item}" for n, item in enumerate(items, 1)], ""]


def placed(lines: list[str], items: list[str], now: str) -> list[str]:
    """Replace the real section's body; without one, add it before `## Open` (else the footer)."""
    span = section(lines, OWN)
    if span:
        return lines[:span[0]] + block(items, now) + lines[span[1]:]
    open_body = section(lines, heading("## Open"))
    at = open_body[0] - 1 if open_body else next(
        (i for i, ln in enumerate(lines) if ln.startswith(FOOTER)), len(lines))
    return lines[:at] + [TITLE] + block(items, now) + lines[at:]


def cmd_set(path: Path, now: str) -> int:
    items = [NUMBERED.sub("", ln).strip() for ln in sys.stdin.read().splitlines()]
    items = [item for item in items if item]
    if not items:   # an empty order is a lost order, never a reset
        print("STOP: no priorities given — nothing was written", file=sys.stderr)
        return 2
    with locked(path):
        lines, newline, bom = read(path)
        body = write(placed(lines, items, now), newline, bom)
        still_mine(path)
        write_atomic(path, body)
    print(f"PRIORITIES: {len(items)} written · updated={now}")
    return 0


def _items(lines: list[str]) -> tuple[list[str], str]:
    """(the items in order, the stamp's date) of the real section; ([], "") without one."""
    span = section(lines, OWN)
    body = lines[span[0]:span[1]] if span else []
    stamp = next((m.group(1) for ln in body if (m := STAMP.match(ln))), "")
    return [NUMBERED.sub("", ln).strip() for ln in body if NUMBERED.match(ln)], stamp


def _verdicts(items: list[str]) -> list[tuple[str, str, str]]:
    """(item, verdict, why) for each one, from the prover `/end` closes lanes with."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "end" / "scripts"))
    from merge_truth import default_branch, verdict  # noqa: E402  (one prover, never a second)
    trunk = default_branch()
    return [(item, *verdict(item, trunk)) for item in items]


def cmd_prune(path: Path, now: str) -> int:
    """Drop the items whose every citation is proven closed. One unreadable answer drops none."""
    lines, newline, bom = read(path)
    items, stamp = _items(lines)
    seen = _verdicts(items)
    if blocked := [f"{item} :: {why}" for item, kind, why in seen if kind == "BLOCKED"]:
        print("NOTE=fail-closed — no priority removed: " + "; ".join(blocked))
        return 2
    gone = [(item, why) for item, kind, why in seen if kind == "PROVEN"]
    if not gone:
        return 0
    kept = [item for item, kind, _ in seen if kind != "PROVEN"]
    with locked(path):
        lines, newline, bom = read(path)
        body = write(placed(lines, kept, stamp or now), newline, bom)
        still_mine(path)
        write_atomic(path, body)
    for item, why in gone:
        print(f"DROPPED={item} :: {why}")
    return 0


def staleness(path: Path, now: str) -> str:
    """The one line /start owes when the order is old or unstamped; "" when it is fresh."""
    lines, _, _ = read(path)
    span = section(lines, OWN)
    stamps = [m.group(1) for ln in (lines[span[0]:span[1]] if span else []) if (m := STAMP.match(ln))]
    if not stamps:
        return "PRIORITIES_STALE=unstamped — /end has never written the order"
    try:
        age = (date.fromisoformat(now) - date.fromisoformat(stamps[0])).days
    except ValueError:   # a bad date silenced /start, which reads as fresh
        return f"PRIORITIES_STALE=malformed — stamp {stamps[0]!r} is not a date"
    return f"PRIORITIES_STALE={age}d — last written {stamps[0]} by /end" if age > STALE_DAYS else ""


def cmd_check(path: Path, now: str) -> int:
    """Read-only: one line when the order is old or unstamped, silence when it is fresh."""
    line = staleness(path, now)
    if line:
        print(line)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("verb", choices=("set", "check", "prune"))
    ap.add_argument("cockpit", type=Path)
    ap.add_argument("--now", default=date.today().isoformat())
    a = ap.parse_args()
    try:
        return {"set": cmd_set, "check": cmd_check, "prune": cmd_prune}[a.verb](a.cockpit, a.now)
    except (LockError, OSError) as exc:
        print(f"STOP: {exc} — nothing was written", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
