#!/usr/bin/env python3
"""L2-T4 (#403) — how prose is READ, for the declared layer of the ContextPack.

`contextpack_declared.py` decides WHICH prose carries authority; this decides what a line of
it says. The split keeps that file under the 200-line ceiling and puts every claim about the
shape of a human-written record in one place, where the corpus can argue with it.

The corpus is the authority on the shape, not a style guide. Across the 27 prose ADRs of one
product repository, one field is written four ways — `**Status:** Accepted`, `Status:
**Approved (founder go-ahead 2026-07-24), piloted …**`, `status: superseded` inside
frontmatter, and `- Status: accepted` — while 14 of the 27 state no date at all. `FIELD` reads
every form and `word` takes the first word undecorated; a record that states nothing gets
`UNKNOWN`, never a guess. `_` is never stripped: it is inside a field name
(`verified_against`).

Three things a round of breaking taught this file:

- **A fenced line states nothing** (R6 of the #423 breaker). `Status: accepted` inside a
  fenced example beat `**Status:** rejected` in the prose below it, so a rejected record
  entered the pack as accepted. `fields` tracks the fence and skips what is inside it; an
  unclosed fence swallows the rest of the document, which is what a Markdown reader does too.
- **One colon is required** (round 1's own defect). The optional colons let the value capture
  the separator: `Status:` with the value on the next line answered `":"`, so a record that
  states nothing was read as stating something — exactly the false claim L2-T2 spent a round
  removing. A value that strips to nothing is also not a value, so a blank line does not
  shadow the real one further down.
- **A count nobody wrote is not zero** (R8). `Recurrence: many` answered `0`; `count` now
  answers `None`, and the caller omits the field rather than inventing a number.

Every read goes through `committed`, so a row is about the bytes at HEAD and a worktree five
panels share cannot move the answer (#199). It swallows `ValueError` as well as
`ContractError` and `OSError`: `cbb._source_bytes` RESOLVES a path before taking it relative
to the root, so a committed symlink pointing out of the tree raised `ValueError` and killed
the CLI with a traceback (R2). `is_prose` asks the VALIDATOR whether a document has
frontmatter rather than forming a second opinion: `invalid` is a refusal the declared layer
must not overrule, and only `FRONTMATTER_MISSING` is prose.

It ships with the resolver (`_standard/sync_scripts.py`).
"""
from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

import check_context_backbone as cbb

TITLE_MAX = 80       # a title is an address, not the document
CODED = re.compile(r"`([^`\s]+)`")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
FENCE = re.compile(r"^(```|~~~)")
FIELD = re.compile(r"^[-*>\s]*(status|date|area|recurrence|verified_against)"
                   r"\**\s*:\**\s*(.+)$", re.I)
# The states the lifecycle uses. Anything else is UNKNOWN: `**Status:** No new contract
# introduced by the Fase-1 refactor` used to answer `no`, an authority nobody wrote (S2).
STATES = frozenset({"accepted", "proposed", "superseded", "rejected", "draft", "approved",
                    "active", "deprecated"})


def _unfenced(text: str) -> list[str]:
    """The lines a reader would take as prose: outside a code fence AND outside a comment.

    A fenced block is an EXAMPLE. Round 1 read it as a statement, so `Status: accepted`
    inside one decided a record whose prose said `rejected` (R6) — and round 2 left the
    other syntax Markdown hides text in wide open, so an HTML comment did it again (S4).
    A comment that opens and closes on one line is skipped without changing the state; an
    unclosed one swallows the rest, which is what a Markdown reader does too."""
    lines, fenced, hidden = [], False, False
    for line in text.splitlines():
        bare = line.strip()
        if FENCE.match(bare):
            fenced = not fenced
        elif "-->" in bare:
            hidden = False
        elif "<!--" in bare:
            hidden = True
        elif not fenced and not hidden:
            lines.append(line)
    return lines


def fields(text: str) -> dict[str, str]:
    """The `name: value` lines a prose record states; the first STATED value wins."""
    found: dict[str, str] = {}
    for line in _unfenced(text):
        hit = FIELD.match(line.strip())
        if hit and hit.group(2).strip():
            found.setdefault(hit.group(1).lower(), hit.group(2).strip())
    return found


def word(value: str) -> str:
    """The state a value STATES, or `UNKNOWN`.

    The first word of a status line is not a status (S2): the corpus writes whole sentences
    there, and `No new contract introduced by the Fase-1 refactor` answered `no`. Only a
    state the lifecycle uses is read; `**Approved (go-ahead)**` is `approved`, a sentence is
    `UNKNOWN`, and a row that says UNKNOWN sends the reader to the document."""
    head = value.strip().split()
    first = head[0].strip(".,;:()[]*_\"'").lower() if head else ""
    return first if first in STATES else "UNKNOWN"


def count(value: str) -> int | None:
    """`Recurrence: 3 (acme-api, slice 1).` is a number followed by prose; `many` is not one."""
    hit = re.match(r"\d+", value.strip())
    return int(hit.group()) if hit else None


def slug(heading: str) -> str:
    """An area is a label slug (plan section 2), so a section heading becomes one."""
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def title(text: str, rel: str) -> str:
    """The H1 the record carries, or its filename when it carries none."""
    for line in _unfenced(text):
        if line.startswith("# "):
            return line[2:].strip()[:TITLE_MAX]
    return PurePosixPath(rel).stem


def committed(root: Path, rel: str) -> bytes:
    """The committed bytes of a path, or none at all: the pack vouches for HEAD (#199).

    `ValueError` is caught with the rest because `cbb._source_bytes` resolves before it
    takes a path relative to the root — a symlink out of the tree used to end the CLI in a
    traceback where the contract says exit 2 or a row (R2)."""
    try:
        return cbb._source_bytes(root, root / rel, at_head=True)
    except (cbb.ContractError, OSError, ValueError):
        return b""


def row(rel: str, raw: bytes, more: dict[str, Any]) -> dict[str, Any]:
    """Section 4's vocabulary, plus only the fields the caller can actually claim."""
    return {"source_id": rel, "layer": "declared", "kind": "document", "path": rel,
            "source_hash": sha256(raw).hexdigest(), "freshness": "UNKNOWN",
            "landed": True, "reason": "", **more}


def is_prose(raw: bytes, path: Path) -> bool:
    """True for a document with nothing typed to seal, by the VALIDATOR's own opinion.

    A second opinion about what frontmatter is would let the declared layer carry a record
    the validator called broken — `invalid` is a refusal, not prose."""
    try:
        cbb._parse_frontmatter(raw.decode("utf-8", "replace"), path)
    except cbb.ContractError as exc:
        return exc.code == "FRONTMATTER_MISSING"
    except (UnicodeDecodeError, ValueError):
        return False
    return False


def is_readable_prose(root: Path, rel: str) -> bool:
    """The ONE question the unknown and declared layers must answer identically: does HEAD
    carry this path as a non-empty document with nothing typed to seal?

    S7 of the #423 breaker: `contextpack_unknown` read the `no_frontmatter` token out of a
    reason STRING while `contextpack_declared` took its own second read, so two modules
    were coupled by a piece of prose and could drift into a gap — with the declared layer
    inert, `CONTEXT.md` would have vanished from both. One predicate, two callers."""
    raw = committed(root, rel)
    return bool(raw.strip()) and is_prose(raw, root / rel)


def blocks(text: str) -> list[str]:
    """One string per `## ` block: the shape `lessons.md` has had since it was written.

    The leading newline is not cosmetic. Splitting on `"\\n## "` alone loses a block that
    starts on line 1, and one of the three ledgers of 2026-09-19 opens on its first lesson
    with no frontmatter above it — so its most recent lesson could never be a pack row, in
    silence (#156). Prepending the separator makes the first block the same shape as the
    rest without changing any other case."""
    return ["## " + part for part in ("\n" + text).split("\n## ")[1:]]


def sections(text: str) -> list[tuple[str, list[str]]]:
    """(area slug, documents named) for every `## ` section of a prose authority.

    A prose triad has no `areas:` key; what it has is sections a human wrote, each naming
    the documents that govern it. That IS the repository's area map, and reading it is what
    lets the pack place a row in an area instead of inventing one."""
    found: list[tuple[str, list[str]]] = []
    for line in _unfenced(text):
        if line.startswith("## "):
            found.append((slug(line[3:]), []))
        elif found:
            found[-1][1].extend(ref for ref in CODED.findall(line) if ref.endswith(".md"))
    return found
