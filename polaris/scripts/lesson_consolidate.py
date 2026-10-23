#!/usr/bin/env python3
"""#156 (L4) — the typed lesson consolidator. It PROPOSES; the founder promotes.

Three ledgers, one pile: 170 blocks in this vault, 130 in one product repository, 175 in
another — and among the 475 not one carries `verified_against`, so the declared layer of
the ContextPack (`contextpack_lessons`, L2-T4) emits zero lesson rows. The contract holds
and nothing flows. CLAUDE.md's rule for a pile like that is a consolidator that
deduplicates, marks supersession and moves a lesson along `note -> context -> gate ->
archived` "mai aggiungere un'altra source of truth narrativa", and #156 adds the hard half:
`0 automatic promotion before deterministic approval`.

So this door does three things and nothing else:

    classify              one row per block with its proposal. Writes NOTHING.
    propose-verification  the commit that would verify each unverified lesson.
    ... --apply --sign    writes ONE field into the blocks a human named, and the diff
                          is the proof.

`gate` is never written from here. A `gate-candidate` is a line in a table that pol-apex
and the founder act on, which is what #156 means by a sink that is not a lifecycle owner.

**A supersession that does not resolve blocks the whole run** — exit 2, one
`LESSON_CONFLICT` per claim, every proposal `blocked`. A ledger whose own history
contradicts itself promotes nothing; it is fixed first.

How a block is read and what each verdict means lives in `lesson_consolidate_parse.py`;
finding and writing a `verified_against` lives in `lesson_consolidate_verify.py`. Stdlib
only, and the only write in the three files is the signed field.
"""
from __future__ import annotations

import sys
from pathlib import Path

import contextpack_lessons as lessons
from lesson_consolidate_parse import (ACTIVE, GATE_AT, UNPARSED, claims,  # noqa: F401
                                      conflicts, counts, dupes, duplicate_actives,
                                      proposal, read, table)



def _verified(root: Path, value: str) -> str:
    """The pack's OWN predicate, so this table and the pack never disagree on a word."""
    if not value:
        return ""
    return "ok" if lessons._resolves(root, value) else "unresolved"


def classify(root: Path, raw: str) -> tuple[list[dict], list[str]]:
    """Every block with its proposal, plus the supersessions that do not resolve."""
    rows = read(raw)
    retired, stated = claims(rows)
    faults = conflicts(rows, stated)
    duplicate = dupes(rows)
    for row in rows:
        row["verified"] = _verified(root, row["verified_against"])
        row["superseded_by"] = retired.get(row["id"], "")
        row["proposal"] = "blocked" if faults else proposal(row, duplicate, retired)
    return rows, faults


def main(argv: list[str] | None = None) -> int:
    """The door's verbs live in `lesson_consolidate_cli`; the reading lives here."""
    import lesson_consolidate_cli as cli   # deferred: the CLI imports this module
    return cli.dispatch(argv)


if __name__ == "__main__":
    sys.exit(main())
