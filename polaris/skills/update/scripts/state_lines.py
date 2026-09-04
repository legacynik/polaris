#!/usr/bin/env python3
"""T6 — ONE notion of what a line is, shared by every writer of a state file.

Seven separate failures had one root: the section finder, the thread matcher, the state-line stamper
and the remover each carried their own regex, so they disagreed. A ```bash block under a condemned
thread promoted a line inside the fence to a live thread; a `## Open` inside an earlier fence won the
section lookup; the vault's real H1 `# Open — thread vivi` made `/end` report `APPLIED` while
removing nothing. So the classification happens once, here, in one fence-aware pass, and every writer
consumes it — including `drop_placeholder`, which did not, and deleted a sample out of a code block.

Reading and writing live here too, because "every other byte comes back identical" is a property of
the round trip: a CRLF file stays CRLF, and a BOM stays one BOM.
"""
from __future__ import annotations

import re

BOM = "﻿"
FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
HEADING = re.compile(r"^#{1,6}\s")
RULE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
# The ONE predicate for "this line is a thread". Every writer asks here: two
# notions of a bullet is how `*` and `1.` threads became invisible to one side.
THREAD = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
# The donor writes state as TABLES (references/marvin-template-1.1.0/state/todos.md), and the
# vault's own `state/todos.md` follows it. A bullet-only predicate read that file as zero rows and
# then APPENDED a bullet under it — a duplicate row carrying a fresh stamp beside the real one.
# So the table row is a branch of the SAME predicate, never a second model: one `table_row`, and
# every writer keeps asking `kinds()` what a line is.
TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
# Markdown escapes a literal pipe as `\|`. Splitting on it shredded `a\|b` into two cells and
# shifted every later cell left, so the `Added` stamp was overwritten by the Context text.
CELL_SPLIT = re.compile(r"(?<!\\)\|")
# At least one dash, or the donor's empty placeholder row `| | | |` reads as a rule and
# demotes the real row above it to structure.
TABLE_RULE = re.compile(r"^\s*\|[\s:|-]*-[\s:|-]*\|\s*$")
UPDATED = re.compile(r"^Updated:", re.I)
# The contract ships ONE example thread so the section is never an empty heading. It is scaffolding,
# not a lane: left in place it survives every session, and `/end` can never close it (no branch
# called `<branch>` can be proved merged). Matched EXACTLY as the template writes it.
PLACEHOLDER = re.compile(
    r"^[-*+]\s+`<branch>`\s+\(<repo>\)\s+—\s+<state in one line>\s+·\s+since YYYY-MM-DD\s*$")
LIST_ITEM = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
LANE_BRANCH = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)`([^`]+)`")
LANE_BOLD = re.compile(r"^\*\*([^*]+)\*\*")


def read(path) -> tuple[list[str], str, str]:
    """(lines, newline, bom) — everything a faithful write-back needs."""
    # newline="" or Python translates CRLF to LF before we can see it, and the
    # file comes back rewritten in a terminator it never had.
    with path.open(encoding="utf-8", newline="") as fh:
        raw = fh.read()
    bom, raw = (BOM, raw[1:]) if raw.startswith(BOM) else ("", raw)
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n").split("\n"), newline, bom


def write(lines: list[str], newline: str, bom: str) -> str:
    """The body as it must land on disk: same terminator, same BOM, no extra blank tail."""
    body = "\n".join(lines).rstrip("\n") + "\n"
    return bom + body.replace("\n", newline)


def table_row(line: str) -> list[str] | None:
    """The cells of a data row, or None for a header rule, a header, or a non-row.

    A header (`| Task | Added |`) and its rule (`|---|---|`) are structure, not content: only the
    rows under them are state. The header is told apart by the rule that follows it, which the
    caller knows and this predicate does not — so `kinds()` owns that one bit of context and this
    function stays a pure line test.
    """
    m = TABLE_ROW.match(line)
    if not m or TABLE_RULE.match(line):
        return None
    return [c.strip() for c in CELL_SPLIT.split(m.group(1))]


def _kind(line: str) -> str:
    """Outside a fence: heading | updated | thread | other."""
    for tag, pat in (("heading", HEADING), ("updated", UPDATED), ("thread", THREAD)):
        if pat.match(line):
            return tag
    return "thread" if table_row(line) is not None else "other"


def kinds(lines: list[str]) -> list[str]:
    """One fence-aware pass. Inside a fence NOTHING is structure — a sample in a code block
    is documentation, and treating it as structure is how a fenced example got overwritten
    and a fenced `## Open` stole the section."""
    out, open_marker = [], ""
    for line in lines:
        m = FENCE.match(line)
        run = m.group(1) if m else ""
        if not open_marker and run:
            open_marker = run                      # opened
        elif open_marker and run[:1] == open_marker[:1] and len(run) >= len(open_marker):
            open_marker = ""                       # closed: same char, at least as long
        elif open_marker:
            out.append("other")                    # anything else inside is content
            continue
        out.append("fence" if run else _kind(line))
    for i, tag in enumerate(out):   # a row right above a `|---|` rule is that table's HEADER
        if tag == "thread" and i + 1 < len(lines) and TABLE_RULE.match(lines[i + 1]):
            out[i] = "other"
    return out


def drop_placeholder(lines: list[str], span: tuple[int, int]) -> tuple[int, int]:
    """Remove the contract's example thread from `span`, and hand back the span it leaves.

    Called by the writer of a REAL thread, so the section never carries both. Returns the span
    unchanged when there is nothing to drop, which is every run after the first.
    """
    tags = kinds(lines)      # inside a fence NOTHING is structure — a sample is documentation
    at = next((i for i in range(*span) if tags[i] == "thread" and PLACEHOLDER.match(lines[i])), -1)
    if at < 0:
        return span
    del lines[at]
    return span[0], span[1] - 1


def lane_id(text: str) -> str:
    """The branch in backticks if the line follows the documented format, else its bold lead, else
    the lead before the ` — ` separator. This id is what a consumer acts on, so it must never be a
    mid-token truncation of prose (real case in a product repo: current.md:48, branch not in backticks)."""
    cells = table_row(text)
    if cells:                       # a table row's identity is its FIRST cell, same rules as a lane
        m = re.match(r"^`([^`]+)`", cells[0]) or re.match(r"^\*\*([^*]+)\*\*", cells[0])
        if m:
            return m.group(1).strip()
        return re.split(r"\s+[—–-]\s+", cells[0], maxsplit=1)[0].strip()[:60]
    for pat in (LANE_BRANCH, LANE_BOLD):
        m = pat.match(text)
        if m:
            return m.group(1).strip()
    lead = LIST_ITEM.sub("", text.strip(), count=1)
    return re.split(r"\s+[—–-]\s+", lead, maxsplit=1)[0].strip()[:60]


def section(lines: list[str], name: re.Pattern) -> tuple[int, int] | None:
    """(first, last+1) of the body under the first REAL heading matching `name`.

    Ends at the next real heading — any level, so an H1 section is not swallowed by an H2
    inside it — at the file's own contract footer, or at a horizontal RULE. The donor separates
    its sections with `---` and closes with an italic contract instead of the sentinel, so a
    finder that only knew the sentinel ran the section to EOF: `/end` wrote a `Completed` row
    below the rule, outside the table, and `/update` appended a thread under the contract line.
    One rule, one place — every writer asks here.
    """
    tags = kinds(lines)
    start = next((i for i, t in enumerate(tags) if t == "heading" and name.match(lines[i])), None)
    if start is None:
        return None
    stop = [i for i in range(start + 1, len(lines))
            if tags[i] == "heading" or RULE.match(lines[i])
            or lines[i].startswith("<!-- pol:state-contract -->")]
    return start + 1, stop[0] if stop else len(lines)


EXAMPLE = "- `<branch>` (<repo>) — <state in one line> · since YYYY-MM-DD"


def _check_placeholder() -> list[bool]:
    """The contract's example goes; a look-alike is someone's lane; a fenced one is documentation."""
    live = ["## Open", "", EXAMPLE, "- `<altro>` (<repo>) — quasi uguale · since 2026-09-01"]
    fenced = ["## Open", "", "- `vivo` — lane", "```md", EXAMPLE, "```"]
    return [drop_placeholder(live, (1, 4)) == (1, 3),
            live == ["## Open", "", "- `<altro>` (<repo>) — quasi uguale · since 2026-09-01"],
            drop_placeholder(live, (1, 3)) == (1, 3),
            drop_placeholder(fenced, (1, 6)) == (1, 6), EXAMPLE in fenced]


def _selfcheck() -> int:
    """Fences, the donor's tables, an escaped pipe, and a section that ends at the rule."""
    body = ["Updated: x", "", "## Note", "~~~", "```", "## Open", "```", "~~~", "",
            "# Open — veri", "", "* `vero` — z", "```", "1. `esempio` — w", "```"]
    table = ["| Task | Added | Context |", "|------|-------|---------|",
             "| #11 — primo | W32 | x |", "| | | |"]
    donor = ["## Completed", "", "| T | C |", "|---|---|", "| x | |", "", "---", "", "## Next"]
    t, u = kinds(body), kinds(table)
    ok = [t[4] == "other", t[5] == "other", t[6] == "other",   # ``` cannot close ~~~
          t[9] == "heading", t[11] == "thread", t[13] == "other",
          section(body, re.compile(r"^#{1,6}\s+open\b", re.I)) == (10, 15),
          u[0] == "other", u[1] == "other", u[2] == "thread",  # header and rule are structure
          lane_id(table[2]) == "#11", table_row(table[1]) is None,
          lane_id("| `feat/a` | W32 | |") == "feat/a",
          # An escaped pipe is content: splitting on it shifted every later cell left.
          table_row(r"| `a\|b` — nome | W32 | ctx |") == [r"`a\|b` — nome", "W32", "ctx"],
          # A section ends at the donor's rule, not at EOF: below it lives the next table.
          section(donor, re.compile(r"^#{1,6}\s+completed\s*$", re.I)) == (1, 6)] \
        + _check_placeholder()
    print(f"state_lines selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selfcheck())
