#!/usr/bin/env python3
"""The adversarial fixtures for `state_upsert`, next door to the guard they check.

Same split as `session_commit_selfcheck.sh`: the writer carries the rule, this file carries the
proof, and neither grows past the size where a reader stops reading. Imported lazily by
`state_upsert.cmd_selfcheck`, so the two modules do not import each other at load time.
"""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from state_lock import locked
from state_upsert import FOOTER, UpsertError, upsert

def _selfcheck_thread(f: Path) -> list[bool]:
    """Replace, append above the footer, one `Updated:` line, a loud refusal."""
    opts = argparse.Namespace(door="thread", owner="ada", now="2026-09-03", week="")
    f.write_text(f"Updated: 2026-09-01 — @ada\n\n## Open\n\n- `a` — uno · since 2026-09-01\n\n{FOOTER}\n")
    ok = []
    with locked(f):
        ok.append(upsert(f, "- `a` — due · since 2026-09-01", opts)["action"] == "replaced")
        ok.append(f.read_text().count("`a`") == 1 and "due" in f.read_text())
        ok.append(upsert(f, "- `b` — nuova · since 2026-09-03", opts)["action"] == "appended")
    body = f.read_text()
    ok += [body.index("- `b`") < body.index(FOOTER),        # never under the file's contract
           body.count("Updated:") == 1 and "@ada" in body]
    f.write_text("# nothing\n")
    try:
        with locked(f):
            upsert(f, "- `z` — x", opts)
        ok.append(False)                                    # must have refused
    except UpsertError as exc:
        ok.append(exc.code == "NO_OPEN_SECTION")
    return ok


def _selfcheck_week(f: Path) -> list[bool]:
    """Bullet form and the donor's TABLE form: the `Added` stamp is carried, never re-stamped."""
    week = argparse.Namespace(door="week", owner="", now="", week="W34")
    f.write_text("## Active\n\n- #1 — x · Added: W32\n")
    with locked(f):
        upsert(f, "- #1 — y", week)
    ok = ["Added: W32" in f.read_text()]
    f.write_text("## Active\n\n| Task | Added | Context |\n|---|---|---|\n"
                 "| #1 — x | W32 | ctx |\n")     # the donor's TABLE form, what the vault uses
    with locked(f):
        ok.append(upsert(f, "| #1 — y | | |", week)["action"] == "replaced")
    body = f.read_text()
    return ok + [body.count("#1") == 1, "| W32 |" in body, "W34" not in body]


def _selfcheck_qualified(f: Path) -> list[bool]:
    """polaris#11 — a host heading that qualifies `## Open` IS the section, and the new lane
    lands among the threads, never under the `Owner:` line that closes them."""
    f.write_text("Updated: 2026-09-01 — @ada\n\n## Open — thread vivi\n\n"
                 "- `a` — uno · since 2026-09-01\n\nOwner: @ada\n\n" + FOOTER + "\n")
    opts = argparse.Namespace(door="thread", owner="ada", now="2026-09-03", week="")
    with locked(f):
        upsert(f, "- `b` — nuova · since 2026-09-03", opts)
    body = f.read_text()
    return [body.index("- `b`") < body.index("Owner:")]


def run() -> int:
    """Every branch that would silently corrupt a cockpit or a plan, one fixture each."""
    with tempfile.TemporaryDirectory() as d:   # every write below is thrown away with it
        f = Path(d) / "current.md"
        ok = _selfcheck_thread(f) + _selfcheck_week(f) + _selfcheck_qualified(f)
    print(f"state_upsert selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    import sys
    if sys.argv[1:] not in ([], ["--selfcheck"]):   # no argument kept working: CI runs it bare
        print("usage: state_upsert_selfcheck.py [--selfcheck]", file=sys.stderr)
        sys.exit(2)
    sys.exit(run())
