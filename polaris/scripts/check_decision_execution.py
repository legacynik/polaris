#!/usr/bin/env python3
"""check_decision_execution — `accepted` is an agreement. `executed` is a fact. They are not one state.

Measured 2026-09-05. `DEC-polaris-retrieval-rebuild-001` has been `accepted` since 2026-08-24, and
its own closure_check says "no operating rule names polaris_query_index.py as a mandatory move".
Thirteen days on, both CLAUDE.md files name it twice each as a first move declared not optional.
Every session executes a rule an accepted decision retired, and nothing notices — because
`accepted` was the terminal state, so there was no place for the difference to show.

The lifecycle therefore gains one value, `executed`, and the record one field, `probe`: the exact
command, no prose. `closure_check` stays the human sentence. That split is deliberate: the thirteen
closure_checks in this register are shell commands with English tails ("exits 0", "on all five
predicates in Consequences") and one is pure prose, so none is runnable as written — and a gate
that guessed which half to cut would be the same class of defect it is here to catch.

GATED (non-zero exit): a record claiming `executed` whose probe fails; any judged record with no
probe at all; and any probe that asserts nothing. The last two were reported and not fatal for one
day only, because thirteen of the fifteen judged records had no probe, and a gate that paints the
register red on its first run teaches people to route around it. Those thirteen now carry one, so
the count is at zero and the ratchet holds it there.

`NO_ASSERTION` closes the way around that ratchet, and `decision_probe_shadow` owns how: each
record names one of its own `call_sites` in `probe_kills`, and a passing probe is re-run against a
shadow of HEAD with that call site gone. That module carries the three ways this was gamed before
it held.

REPORTED, never fatal on its own: `NOT_DONE` (accepted, probe fails — decided and not done) and
`EXECUTED_IN_FACT` (accepted, probe passes — a promotion owed). Both are honest states with a
falsifier attached; naming them every run is what makes the difference visible.

Probes run through a shell because that is the form they are written in, bounded by --timeout and
never inheriting stdin. They come from files in this repository, under review like any other code.

Usage:  check_decision_execution.py [--root DIR] [--timeout SEC] | --selfcheck
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from decision_probe_shadow import at_head, invalid, run_probe, survives

JUDGED = ("accepted", "executed")
FRONTMATTER = re.compile(r"^---\n(\{.*?\n\})\n---", re.S)


def _records(root: Path) -> list[dict]:
    """Every decision record that carries JSON frontmatter, in id order."""
    out = []
    for path in sorted((root / "decisions").glob("DEC-*.md")) if (root / "decisions").is_dir() else []:
        match = FRONTMATTER.match(path.read_text(errors="replace"))
        if match:
            out.append(json.loads(match.group(1)))
    return out


def _verdict(record: dict, root: Path, timeout: int) -> tuple[str, str]:
    """(verdict, note) for one judged record."""
    silent = "CLAIMED_WITHOUT_PROBE" if record["status"] == "executed" else "UNVERIFIABLE"
    probe = (record.get("probe") or "").strip()
    if not probe:
        return silent, "no `probe` field — the closure_check is prose, not a check"
    why = invalid(record, probe, at_head(root))
    if why:
        return silent, why
    victim = record["probe_kills"].strip()
    passed, note = run_probe(probe, root, timeout)
    if passed and survives(probe, (root, victim), timeout):
        return "NO_ASSERTION", f"still passes without {victim} — it does not read what it governs"
    if record["status"] == "executed":
        return ("EXECUTED" if passed else "BROKEN_CLAIM"), note
    return ("EXECUTED_IN_FACT" if passed else "NOT_DONE"), note


def check(root: Path, timeout: int) -> tuple[list[str], list[str]]:
    """(errors, report). Errors are fatal; the report is printed whatever happens."""
    judged = [r for r in _records(root) if r.get("status") in JUDGED]
    rows, errors = [], []
    for record in judged:
        verdict, note = _verdict(record, root, timeout)
        rows.append(f"  {verdict:22} {record['decision_id']} — {note}")
        if verdict in ("BROKEN_CLAIM", "CLAIMED_WITHOUT_PROBE", "UNVERIFIABLE", "NO_ASSERTION"):
            errors.append(f"{record['decision_id']} {verdict}: {note}")
    counts = {}
    for row in rows:
        counts[row.split()[0]] = counts.get(row.split()[0], 0) + 1
    summary = " · ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "nothing to judge"
    head = [f"decisions: {len(judged)} accepted or executed · {summary}"]
    return errors, head + rows


def _fixture(tmp: Path, records: list[dict]) -> Path:
    root = Path(tempfile.mkdtemp(dir=tmp))
    (root / "decisions").mkdir()
    (root / "marker").write_text("the call site these probes govern\n")
    for rec in records:
        text = f"---\n{json.dumps(rec, indent=2)}\n---\n\n# {rec['decision_id']}\n"
        (root / "decisions" / f"{rec['decision_id']}.md").write_text(text)
    for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t",
                                                "commit", "-qm", "fixture"]):
        subprocess.run(["git", *cmd], cwd=root, check=True, capture_output=True)
    return root


def _rec(slug: str, status: str, probe: str | None = None) -> dict:
    out = {"decision_id": slug, "status": status, "closure_check": "prose",
           "call_sites": ["marker"], "probe_kills": "marker"}
    return {**out, "probe": probe} if probe else out


# slug, status, probe, timeout, breaks the build, token the row must carry (None = not judged).
CASES = [
    ("DEC-liar", "executed", "exit 3", 5, True, "BROKEN_CLAIM"),
    ("DEC-bare", "executed", None, 5, True, "CLAIMED_WITHOUT_PROBE"),
    ("DEC-mute", "accepted", None, 5, True, "UNVERIFIABLE"),
    ("DEC-fake", "accepted", "true", 5, True, "NO_ASSERTION"),
    ("DEC-ok", "executed", "test -f marker", 5, False, "EXECUTED"),
    ("DEC-pend", "accepted", "exit 1", 5, False, "NOT_DONE"),
    ("DEC-ready", "accepted", "test -f marker", 5, False, "EXECUTED_IN_FACT"),
    ("DEC-slow", "accepted", "sleep 30", 1, False, "TIMEOUT"),
    ("DEC-old", "superseded", "exit 1", 5, False, None),
]


def _selfcheck() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        for slug, status, probe, timeout, fatal, token in CASES:
            errors, report = check(_fixture(t, [_rec(slug, status, probe)]), timeout)
            assert bool(errors) is fatal and (not fatal or slug in errors[0]), (slug, errors)
            assert (token in report[1]) if token else len(report) == 1, (slug, report)
        assert check(_fixture(t, []), 5)[0] == [], "an empty register is not a failure"
        assert "0 accepted" in check(_fixture(t, []), 5)[1][0], "empty must say so"
    print(f"SELF-CHECK OK: empty register and {len(CASES)} verdicts — "
          + ", ".join(c[5] or "superseded ignored" for c in CASES))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    if args.selfcheck:
        _selfcheck()
        return 0
    errors, report = check(args.root.resolve(), args.timeout)
    print("\n".join(report))
    for line in errors:
        print(f"ERROR: {line}", file=sys.stderr)
    print("FAIL: a decision states more than its probe can show" if errors
          else "OK: every judged decision carries a probe, and no claim outruns it", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
