#!/usr/bin/env python3
"""T6 — ONE notion of what a line is, shared by every writer of a state file.

Seven separate failures had one root: the section finder, the thread matcher, the state-line
stamper and the remover each carried their own regex, so they disagreed. A ```bash block
under a condemned thread reopened the section and promoted a line inside the fence to a live
thread. A `## Open` inside an earlier fence won the section lookup. The vault's real
`# Open — thread vivi` is an H1: one writer saw the section, the other saw no threads in it,
and `/end` reported `APPLIED` while removing nothing — a permanent no-op on the real cockpit.

So the classification happens once, here, in one pass that knows about fences, and every
writer consumes it. Reading and writing live here too, because "every other byte comes back
identical" is a property of the round trip: a CRLF file must stay CRLF, and a BOM must stay
one BOM rather than hiding the `Updated:` line behind it and growing a second.
"""
from __future__ import annotations

import re

BOM = "﻿"
FENCE = re.compile(r"^\s{0,3}(?:```|~~~)")
HEADING = re.compile(r"^#{1,6}\s")
THREAD = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
UPDATED = re.compile(r"^Updated:", re.I)


def read(path) -> tuple[list[str], str, str]:
    """(lines, newline, bom) — everything a faithful write-back needs."""
    # newline="" or Python translates CRLF to LF before we can see it, and the
    # file comes back rewritten in a terminator it never had.
    with path.open(encoding="utf-8", newline="") as fh:
        raw = fh.read()
    bom, raw = (BOM, raw[1:]) if raw.startswith(BOM) else ("", raw)
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n").split("\n"), newline, bom


def write(path, lines: list[str], newline: str, bom: str) -> str:
    """The body as it must land on disk: same terminator, same BOM, no extra blank tail."""
    body = "\n".join(lines).rstrip("\n") + "\n"
    return bom + body.replace("\n", newline)


def _kind(line: str) -> str:
    """Outside a fence: heading | updated | thread | other."""
    for tag, pat in (("heading", HEADING), ("updated", UPDATED), ("thread", THREAD)):
        if pat.match(line):
            return tag
    return "other"


def kinds(lines: list[str]) -> list[str]:
    """One fence-aware pass. Inside a fence NOTHING is structure — a sample in a code block
    is documentation, and treating it as structure is how a fenced example got overwritten
    and a fenced `## Open` stole the section."""
    out, inside = [], False
    for line in lines:
        if FENCE.match(line):
            inside = not inside
            out.append("fence")
        else:
            out.append("other" if inside else _kind(line))
    return out


def section(lines: list[str], name: re.Pattern) -> tuple[int, int] | None:
    """(first, last+1) of the body under the first REAL heading matching `name`.

    Ends at the next real heading — any level, so an H1 section is not swallowed by an H2
    inside it — or at the file's own contract footer, which nothing may land under.
    """
    tags = kinds(lines)
    start = next((i for i, t in enumerate(tags) if t == "heading" and name.match(lines[i])), None)
    if start is None:
        return None
    stop = [i for i in range(start + 1, len(lines))
            if tags[i] == "heading" or lines[i].startswith("<!-- pol:state-contract -->")]
    return start + 1, stop[0] if stop else len(lines)


def _selfcheck() -> int:
    body = ["Updated: x", "", "## Note", "~~~", "## Open", "- `finto` — y", "~~~", "",
            "# Open — veri", "", "- `vero` — z", "```", "- `esempio` — w", "```"]
    tags = kinds(body)
    ok = [tags[4] == "other", tags[5] == "other",          # inside the first fence
          tags[8] == "heading", tags[10] == "thread",      # the real H1 section and its lane
          tags[12] == "other",                             # inside the second fence
          section(body, re.compile(r"^#{1,6}\s+open\b", re.I)) == (9, 14)]
    print(f"state_lines selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selfcheck())
