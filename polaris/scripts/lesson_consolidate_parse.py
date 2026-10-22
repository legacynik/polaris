#!/usr/bin/env python3
"""#156 (L4) — how a lessons ledger is READ, and what each block is proposed for.

`lesson_consolidate.py` is the door; this decides what one `## ` block says and where the
lifecycle would put it. The split is the one the `contextpack_*` family already uses: the
claims about the shape of a human-written pile live in one file the corpus can argue with.

The corpus is the authority on the shape. Across the three ledgers of 2026-09-19 — 170
blocks here, 130 in one product repository, 175 in another — the metadata is written in
five shapes, and in one of the three repositories in none at all. So the parser that
already knows those shapes is reused (`lesson_recurrence._meta`), the field reader the pack
already uses is reused (`contextpack_prose.fields`), and a block neither of them can read
is a row with tier `UNPARSED`. **`rows == blocks`, always**: a consolidator that skips what
it cannot parse reads a 130-block ledger as an empty one, which is the biased sample
`lesson_recurrence` was rewritten to stop producing.

**Two lessons are the same lesson when their titles are** — 0.85 of the terms shared, the
date, the login and the tags removed first, because `(@<login>)` is in every title and
the date is in every title. The older one is the duplicate: the newer statement is the one
somebody wrote last, and the id carries the date that decides which is which.

The proposal rule is stated on `proposal` and nowhere else, so there is one place to argue
with it. Nothing here writes, and nothing here promotes.
"""
from __future__ import annotations

import re

import contextpack_prose as prose
import lesson_recurrence as recurrence

ACTIVE = ("keep", "context", "gate-candidate")
UNPARSED = "UNPARSED"
GATE_AT = 3          # the recurrence #156 makes a CANDIDATE, never a gate
DUP_OVERLAP = 0.85   # the declared threshold: |A & B| / |A | B| over the title's terms
SUPERSEDES = re.compile(r"(?mi)^[-*>\s]*\**(?:Supersedes|Supera)\**\s*:\s*(\S+)")
ARCHIVED = re.compile(r"(?mi)^[-*>\s]*\**Archived\**\s*:\s*\S+\s+superseded by\s+(\S+)")
NOISE = re.compile(r"\(@[\w-]+\)|#[\w/-]+|\d{4}-\d{2}-\d{2}|[—–]")
# A count with no cause is a number nobody can act on: 130 of one repository's blocks are
# `unparsed`, and what they need is one line of metadata, not a reader's guess.
UNPARSED_WHY = ("  unparsed: no tier/recurrence field; blocks are dated prose. "
                "Migration: add `- tier: note|context|gate` and `- recurrence: N` to the "
                "block, or one `Enforcement: <tier>. Recurrence: <n>` line under its title.")


def bare(title: str) -> str:
    """The title without its date, its login and its tags: what two blocks share, or not."""
    return NOISE.sub(" ", title)


def _ident(title: str, used: dict[str, int]) -> str:
    """`<date>-<slug>`, plus an ordinal when two blocks would share one address."""
    stamp = prose.DATE.search(title)
    base = f"{stamp.group() if stamp else 'undated'}-{prose.slug(bare(title))[:40]}".strip("-")
    used[base] = used.get(base, 0) + 1
    return base if used[base] == 1 else f"{base}-{used[base]}"


def _row(block: dict, used: dict[str, int]) -> dict:
    """One block, parsed or NAMED. `tier: UNPARSED` is a verdict, not a silence."""
    form, tier, times = recurrence._meta(block["text"])
    stated = prose.fields(block["text"])
    return {"id": _ident(block["title"], used), "line": block["line"],
            "title": block["title"], "tier": tier if form else UNPARSED,
            "recurrence": times if form else (prose.count(stated.get("recurrence", "")) or 0),
            "verified_against": stated.get("verified_against", ""),
            "area": stated.get("area", ""),
            "terms": recurrence._terms(bare(block["title"])), "text": block["text"]}


def read(raw: str) -> list[dict]:
    """Every `## ` block of the ledger, in file order, one row each."""
    used: dict[str, int] = {}
    return [_row(block, used) for block in recurrence._split_blocks(raw)]


def _overlap(one: set[str], two: set[str]) -> float:
    return len(one & two) / len(one | two) if one and two else 0.0


def _older(one: dict, two: dict) -> tuple[dict, dict]:
    """(older, newer): by date when both are dated, by POSITION otherwise.

    An `undated-` id compared as a string sorts by its slug, so the alphabet decided which
    of two undated blocks was the duplicate (breaker round 1). The ledger is newest-on-top,
    so further down the file is older."""
    dated = one["id"][:4].isdigit() and two["id"][:4].isdigit()
    key = (lambda row: row["id"][:10]) if dated else (lambda row: -row["line"])
    return (one, two) if key(one) < key(two) else (two, one)


def dupes(rows: list[dict]) -> dict[str, str]:
    """Older id -> the newer block that already says it, by title-term overlap."""
    found: dict[str, str] = {}
    for index, one in enumerate(rows):
        for two in rows[index + 1:]:
            if _overlap(one["terms"], two["terms"]) >= DUP_OVERLAP:
                older, newer = _older(one, two)
                found.setdefault(older["id"], newer["id"])
    return found


def claims(rows: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    """(everything retired, only what a live `Supersedes:` CLAIMS).

    The two are not the same question. A `Supersedes:` is a claim another block makes now,
    and a claim naming a lesson nobody carries is a contradiction the run must stop on. An
    `Archived: <date> superseded by <id>` marker is the RECORD of a completed archival: the
    lesson that replaced it may well have been pruned since, and re-reading that history as
    a conflict would block every ledger that was ever tidied."""
    retired: dict[str, str] = {}
    stated: dict[str, str] = {}
    for row in rows:
        for target in SUPERSEDES.findall(row["text"]):
            stated[target] = row["id"]
        mark = ARCHIVED.search(row["text"])
        if mark:
            retired[row["id"]] = mark.group(1)
    return {**retired, **stated}, stated


def _ring(stated: dict[str, str], start: str) -> bool:
    """Whether following `Supersedes:` from `start` comes back to `start`, at any length.

    Round 1 caught the two-block ring by comparing the pair and missed `A -> B -> C -> A`
    entirely: three blocks archived each other and the run exited 0. A chain that ENDS is
    a history and stays valid; a chain that closes is a claim that resolves to nothing."""
    seen: set[str] = set()
    node = start
    while node in stated and node not in seen:
        seen.add(node)
        node = stated[node]
    return node == start


def conflicts(rows: list[dict], stated: dict[str, str]) -> list[str]:
    """A claim that does not resolve: a name nobody carries, or a ring of any length."""
    known = {row["id"] for row in rows}
    found = [f"LESSON_CONFLICT {old}: superseded by {by}, which this ledger does not carry"
             for old, by in stated.items() if by not in known or old not in known]
    return found + [f"LESSON_CONFLICT {old}: the supersessions from {old} come back to it"
                    for old in stated if _ring(stated, old)]


def proposal(row: dict, duplicate: dict[str, str], retired: dict[str, str]) -> str:
    """Where the lifecycle would put this block. In order, first hit wins:

    `archive` when something retired it · `duplicate-of:<id>` when a newer block already
    says it · `unparsed` when no shape states a tier · `gate-candidate` ONLY at recurrence
    >= 3 with nothing superseding it and no gate already granted · `context` for a note
    seen twice · `keep` otherwise. A candidate is a proposal: `gate` is written by
    pol-apex and the founder, never from here.
    """
    if row["id"] in retired:
        return "archive"
    if row["id"] in duplicate:
        return f"duplicate-of:{duplicate[row['id']]}"
    if row["tier"] == UNPARSED:
        return "unparsed"
    if row["recurrence"] >= GATE_AT and row["tier"] != "gate":
        return "gate-candidate"
    return "context" if row["tier"] == "note" and row["recurrence"] >= 2 else "keep"


def duplicate_actives(rows: list[dict]) -> int:
    """How many ACTIVE lessons say what another active lesson already says. Must be 0."""
    return len(dupes([row for row in rows if row["proposal"] in ACTIVE]))


def table(rows: list[dict]) -> str:
    """The census, one row per block, in file order."""
    head = ("| id | tier | recurrence | superseded_by | verified | proposal |\n"
            "|---|---|---|---|---|---|")
    return "\n".join([head, *(
        f"| `{row['id']}` | {row['tier']} | {row['recurrence']} | "
        f"{row['superseded_by'] or '—'} | {row['verified'] or '—'} | {row['proposal']} |"
        for row in rows)])


def counts(rows: list[dict]) -> str:
    """One line a test and a PR body can both read: what the ledger proposes, in totals."""
    kinds: dict[str, int] = {"gate-candidate": 0}
    for row in rows:
        key = row["proposal"].split(":")[0]
        kinds[key] = kinds.get(key, 0) + 1
    tally = " ".join(f"{key}={kinds[key]}" for key in sorted(kinds))
    line = (f"blocks={len(rows)} {tally} duplicates={duplicate_actives(rows)} "
            f"markers={sum(1 for row in rows if ARCHIVED.search(row['text']))}")
    return line if not kinds.get("unparsed") else f"{line}\n{UNPARSED_WHY}"
