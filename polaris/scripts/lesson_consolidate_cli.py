#!/usr/bin/env python3
"""#156 (L4) — the verbs of the consolidator, and the four ways it refuses.

`lesson_consolidate` and its parser answer what a block says and where the lifecycle would
put it; `lesson_consolidate_verify` answers which commit verifies it. This file only
ARRANGES those answers — a table, a JSON document, a refusal, or the two lines a signature
writes — and owns the shape of a refusal. There are four, each writing nothing at all: a
ledger outside `--root` (one repository's lessons verified against another's history), an
`--area` the vocabulary does not carry, an `--area` claimed for more than one lesson at
once, and an id nobody proposed a commit for.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import lesson_consolidate as core
import lesson_consolidate_verify as verify
from lesson_consolidate_parse import UNPARSED, counts, table

_TWIN = "A rule stated once and restated later"
FOUR = (
    "## 2026-01-02 — A note nobody has seen twice (@x)\n\n- rule: one.\n"
    "- tier: note\n- recurrence: 1\n\n"
    "## 2026-01-03 — Read the log before the model's story (@x)\n\n- rule: two.\n"
    "- tier: note\n- recurrence: 2\n\n"
    "## 2026-01-04 — Assert the branch before every commit (@x)\n\n- rule: three.\n"
    "- tier: context\n- recurrence: 4\n\n"
    f"## 2026-01-05 — {_TWIN} (@x)\n\n- rule: first.\n- tier: note\n- recurrence: 1\n\n"
    f"## 2026-01-06 — {_TWIN} (@x)\n\n- rule: second.\n- tier: note\n- recurrence: 1\n"
    "- Supersedes: 2026-01-05-a-rule-stated-once-and-restated-later\n")
CRASH = FOUR.replace("- rule: first.\n", "- rule: first.\n- Archived: 2026-01-06 "
                     "superseded by 2026-01-06-a-rule-stated-once-and-restated-later\n")
_PAIR = ("## 2026-02-0{a} — {n} of a mutual pair (@x)\n\n- rule: {a}.\n- tier: note\n"
         "- recurrence: 3\n- Supersedes: 2026-02-0{b}-{m}-of-a-mutual-pair\n")
CONFLICT = (_PAIR.format(a=1, b=2, n="First", m="second") + "\n"
            + _PAIR.format(a=2, b=1, n="Second", m="first"))
FIXTURES = {"crash-after-archive": CRASH, "conflicting-supersession": CONFLICT}


def _report(rows: list[dict], faults: list[str], as_json: bool) -> int:
    # A conflict on stdout made `--json` unparseable, which is the same defect as the
    # totals line: in JSON mode stdout carries the document and nothing else.
    for line in faults:
        print(line, file=sys.stderr if as_json else sys.stdout)
    if as_json:
        print(json.dumps([{key: value for key, value in row.items()
                           if key not in ("text", "terms")} for row in rows],
                         indent=2, ensure_ascii=False))
    else:
        print(table(rows))
    # `--json` must be PARSEABLE: the totals go to stderr, or stdout is JSON plus a line.
    print(counts(rows), file=sys.stderr if as_json else sys.stdout)
    return 2 if faults else 0


def _chosen(rows: list[dict], made: dict, wanted: list[str]) -> tuple[list, list[str]]:
    """(the rows to sign with their proposal, the ids nobody proposed a commit for)."""
    by_id = {row["id"]: row for row in rows}
    return ([(by_id[one], made[one]) for one in wanted if one in made and one in by_id],
            [one for one in wanted if one not in made or one not in by_id])


def _area_fault(root: Path, area: str, chosen: list) -> str:
    """Why this `--area` may not be written, or `""`.

    Two faults, both from round 1. The value reached the ledger verbatim, `../../etc; rm`
    included (F5), so it must be a name the resolver's vocabulary carries; and it is ONE
    claim about ONE lesson, not a constant for the run."""
    if not area:
        return ""
    import contextpack  # deferred: the vocabulary lives with the resolver, not here
    try:
        known = set(contextpack._repo_domain_map(root))
    except Exception:  # a repository with no typed DOMAIN.md still has the label names
        known = set()
    if area not in known:
        return f"not an area of this repository: {area!r}"
    owed = [row for row, _ in chosen if not row["area"]]
    return "" if len(owed) < 2 else (
        f"--area is one claim about one lesson, and {len(owed)} of the signed blocks "
        f"declare none: sign them one at a time")


def _sign(a: argparse.Namespace, rows: list[dict], made: dict) -> int:
    """Write the fields into the named blocks, or refuse and write nothing at all."""
    wanted = [one.strip() for one in a.sign.split(",") if one.strip()]
    chosen, missing = _chosen(rows, made, wanted)
    if missing or not chosen:
        print(f"no resolvable proposal for: {', '.join(missing) or '(nothing named)'}",
              file=sys.stderr)
        return 2
    fault = _area_fault(a.root, a.area, chosen)
    if fault:
        print(fault, file=sys.stderr)
        return 2
    verify.apply(Path(a.ledger), chosen, a.area)
    for row, made_for in chosen:
        print(f"signed {row['id']} verified_against: {made_for[0]} ({made_for[2]})")
    return 0


def _proposals(made: dict) -> str:
    return "\n".join(f"- `{one}` → `verified_against: {sha}` — {why}"
                     for one, (sha, why, _) in sorted(made.items())) or "no proposal"


def _cmd_verify(a: argparse.Namespace) -> int:
    """Propose, and sign only what `--sign` names. A conflict stops both."""
    rows, faults = core.classify(a.root, Path(a.ledger).read_text(encoding="utf-8"))
    if faults:
        return _report(rows, faults, a.json)
    made = verify.propose(a.root, rows, _relative(a))
    if not a.apply:
        print(_proposals(made))
        print(f"proposed={len(made)} of {sum(1 for r in rows if not r['verified_against'])}"
              f" unverified")
        return 0
    return _sign(a, rows, made)


def _relative(a: argparse.Namespace) -> str:
    """The ledger's path INSIDE the root, which is the only place it may be."""
    return str(Path(a.ledger).resolve().relative_to(Path(a.root).resolve()))


def _outside(a: argparse.Namespace) -> bool:
    """A ledger of one repository verified against the history of another (breaker 6)."""
    try:
        _relative(a)
    except ValueError:
        return True
    return False


def _fixture(name: str) -> int:
    """A synthetic ledger in a temp directory: the ledger on disk is never the subject."""
    root = Path(tempfile.mkdtemp(prefix=f"lesson-{name}-"))
    (root / "lessons.md").write_text(FIXTURES[name], encoding="utf-8")
    rows, faults = core.classify(root, FIXTURES[name])
    return _report(rows, faults, False)


def _selfcheck() -> int:
    """The four outcomes, the threshold, the two adversarial fixtures. Nothing written."""
    root = Path(tempfile.mkdtemp(prefix="lesson-selfcheck-"))
    rows, faults = core.classify(root, FOUR)
    assert not faults, faults
    assert {row["proposal"] for row in rows} == {"keep", "context", "gate-candidate",
                                                 "archive"}, [r["proposal"] for r in rows]
    assert sum(1 for row in rows if row["proposal"] == "gate-candidate") == 1, rows
    assert core.duplicate_actives(rows) == 0, rows
    assert all(row["tier"] != UNPARSED for row in rows), rows
    assert _fixture("crash-after-archive") == 0
    assert _fixture("conflicting-supersession") == 2
    print("SELFCHECK OK — 4 lifecycle outcomes, 1 gate candidate, 0 duplicate actives, "
          "2 fixtures, 0 writes")
    return 0


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="#156 typed lesson consolidator (proposes)")
    ap.add_argument("command", nargs="?", choices=["classify", "propose-verification"])
    ap.add_argument("--ledger", default="lessons.md")
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--apply", action="store_true", help="write the signed field")
    ap.add_argument("--sign", default="", help="comma-separated lesson ids to sign")
    ap.add_argument("--area", default="", help="area to write when the block states none")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--fixture", choices=sorted(FIXTURES))
    return ap


def dispatch(argv: list[str] | None = None) -> int:
    ap = _parser()
    a = ap.parse_args(argv)
    if a.selfcheck:
        return _selfcheck()
    if a.fixture:
        return _fixture(a.fixture)
    if not Path(a.ledger).is_file():
        print(f"ledger not found: {a.ledger}", file=sys.stderr)
        return 2
    if _outside(a):
        print(f"the ledger is outside --root: {a.ledger} is not under {a.root}",
              file=sys.stderr)
        return 2
    if a.command == "propose-verification":
        return _cmd_verify(a)
    if a.command == "classify":
        return _report(*core.classify(a.root, Path(a.ledger).read_text(encoding="utf-8")),
                       a.json)
    ap.error("command required: classify | propose-verification")
    return 2

