#!/usr/bin/env python3
"""`## Recent Context` — the bounded, newest-first session ring inside the state file.

The donor keeps recent history INSIDE the state file and caps it explicitly
(`references/marvin-template-1.1.0/state/current.md`: "Last 5 session summaries, newest
first"). Polaris moved that section out into a separate dense file and dropped the cap: measured
2026-09-01, 188 KB and 93 blocks, last written nine days earlier — it had died and nobody noticed,
while `current.md` kept being updated. So the ring comes back, in the file everyone opens, capped.

Three surfaces, three jobs (#240): `Updated:` carries date and owner, THIS section carries
the session summary, and the session log carries the full handoff. Only `/end` writes here.

Everything outside the section comes back byte-identical: an entry is prepended, the ring is
trimmed to `CAP`, and the head and tail of the file are never re-rendered. The evicted entry
is not lost — its full form is the session log, which is append-only and committed.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lines import kinds, read, write  # noqa: E402
from state_lock import LockError, locked, write_atomic  # noqa: E402

CAP = 5
HEADING = re.compile(r"^##\s+Recent Context\s*$", re.I)
ENTRY = re.compile(r"^###\s+")
OUTER = re.compile(r"^#{1,2}\s")


def bounds(lines: list[str]) -> tuple[int, int] | None:
    """(first, last+1) of the section body, fence-aware. None when the section is absent.

    It ends at the next `#`/`##` heading or at the contract rule — NEVER at a `### ` line,
    which is an ENTRY of this section. Stopping at any heading collapsed the section to
    zero entries, so the cap never fired and the same entry was appended twice.
    """
    tags = kinds(lines)
    start = next((i for i, t in enumerate(tags) if t == "heading" and HEADING.match(lines[i])), None)
    if start is None:
        return None
    stop = [i for i in range(start + 1, len(lines))
            if (tags[i] == "heading" and OUTER.match(lines[i])) or lines[i].startswith("---")]
    return start + 1, stop[0] if stop else len(lines)


def split(lines: list[str], span: tuple[int, int]) -> tuple[list[str], list[list[str]]]:
    """The section's intro comment and its entries, each entry a block of lines."""
    tags = kinds(lines)
    starts = [i for i in range(*span) if tags[i] == "heading" and ENTRY.match(lines[i])]
    if not starts:
        return lines[span[0]:span[1]], []
    edges = starts + [span[1]]
    return (lines[span[0]:starts[0]],
            [lines[edges[i]:edges[i + 1]] for i in range(len(starts))])


def ring(intro: list[str], entries: list[list[str]], entry: str) -> list[str]:
    """The new body: the entry first, the ring trimmed to CAP, one blank line between."""
    fresh = [entry.strip(), ""]
    kept = [[ln for ln in block if ln.strip()] + [""] for block in entries][:CAP - 1]
    return [ln for ln in intro if ln.strip()] + [""] + fresh + [ln for b in kept for ln in b]


def append(path: Path, entry: str) -> dict:
    """Prepend one `### ` entry. Adding the same entry twice does not grow the ring."""
    if not entry.strip().startswith("### "):
        raise ValueError('a Recent Context entry must start with "### "')
    lines, newline, bom = read(path)
    span = bounds(lines)
    if span is None:
        raise ValueError(f"{path} has no `## Recent Context` section — /end writes into the "
                         "section the contract declares, it does not invent one at EOF")
    intro, entries = split(lines, span)
    head = entry.strip().splitlines()[0].strip()
    if any(block and block[0].strip() == head for block in entries):
        return {"added": False, "entries": len(entries)}   # same session, not a second one
    body = ring(intro, entries, entry)
    lines[span[0]:span[1]] = body
    write_atomic(path, write(lines, newline, bom))
    return {"added": True, "entries": min(len(entries) + 1, CAP)}


def cmd_selfcheck() -> int:
    """The cap, the order, the idempotence, and the bytes outside the section."""
    import tempfile
    from _selfcheck_parts import check_ring, score
    with tempfile.TemporaryDirectory() as d:
        return score("recent_context", check_ring(Path(d), append, locked))


def main() -> int:
    ap = argparse.ArgumentParser(description="append one capped entry to `## Recent Context`")
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--entry", default="", help='the block, starting with "### "')
    ap.add_argument("--selfcheck", action="store_true")
    opts = ap.parse_args()
    if opts.selfcheck:
        return cmd_selfcheck()
    entry = opts.entry or sys.stdin.read()
    try:
        with locked(opts.path):
            print(append(opts.path, entry))
    except (LockError, OSError, ValueError) as exc:
        print(f"RECENT_CONTEXT: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
