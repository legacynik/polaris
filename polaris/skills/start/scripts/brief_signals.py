#!/usr/bin/env python3
"""brief_signals — the read-only half of /start: what the system already knows.

Three signals exist today and nothing reads them (polaris-os#243): the deferred session-log
spool, the drift of the MAIN worktree, and the sections a state file has lost. Two more
surfaces landed with the donor's four-file form and had no reader (#240): `state/todos.md`
and `## Recent Context`. And a repo that carries the typed backbone should have its pack id
in the brief, while a repo without one must not even learn that the feature exists (#155).

Every line is emitted ONLY when it has something to say. A row that always reads zero is
noise, and noise is what teaches a reader to skip the brief. Nothing here writes; ONE signal
(divergence) reaches the network, bounded and silent on failure, because a checkout that is
behind answers "not on main" for things that are. A missing input is never an error.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _brief_parts import (emit_divergence, emit_drift, emit_pack,  # noqa: E402
                          emit_recent, emit_sections, emit_spool, emit_todos)


def report(opts: argparse.Namespace) -> list[str]:
    """Every signal, in brief order. Read-only, and a missing input is a silent line."""
    root, current = Path(opts.root), Path(opts.current)
    main_wt = Path(opts.main_wt) if opts.main_wt else root.parent
    return (emit_todos(root, opts.now) + emit_recent(current)
            + emit_spool(main_wt) + emit_drift(main_wt, opts.login)
            + emit_sections(root, current) + emit_pack(root)
            + emit_divergence(main_wt))


def cmd_selfcheck() -> int:
    """One fixture per branch that would put a wrong or a missing line in the brief."""
    import tempfile
    from _selfcheck_parts import check_brief, score

    def options(root: str, current: str, wt: str) -> argparse.Namespace:
        return argparse.Namespace(root=root, current=current, login="ada",
                                  main_wt=wt, now="2026-09-03")

    with tempfile.TemporaryDirectory() as d:
        return score("brief_signals", check_brief(Path(d), report, options))


def main() -> int:
    ap = argparse.ArgumentParser(description="read-only signals for the /start brief")
    ap.add_argument("--root", default=".", help="the Polaris root of THIS repo")
    ap.add_argument("--current", default="", help="the resolved cockpit path")
    ap.add_argument("--login", default="", help="the contributor, to tell own files from foreign")
    ap.add_argument("--main-wt", default="", help="the MAIN worktree (default: the root's parent)")
    ap.add_argument("--now", default=date.today().isoformat())
    ap.add_argument("--selfcheck", action="store_true")
    opts = ap.parse_args()
    if opts.selfcheck:
        return cmd_selfcheck()
    for line in report(opts):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
