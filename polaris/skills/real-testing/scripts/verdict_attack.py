#!/usr/bin/env python3
"""The attack axis of the real-test matrix: HOW each changed hunk was attacked.

The matrix classes say where a change lands; these say what a hostile user, a crash or a lying
tool would do to it. Adapted from the scenario classes of oh-my-codex's `ultraqa` (MIT), rewritten.
A live row of a class that faces users, models or browsers must carry one hostile probe that ran.
"""
from __future__ import annotations

ATTACKS = {
    "malformed-input",     # invalid JSON, missing fields, huge strings, odd Unicode, traversal-like paths
    "interruption",        # repeated continue/stop, output cut mid-stream, retry after partial progress
    "prompt-injection",    # text that tries to override rules, skip verification, claim success
    "cancel-resume",       # cancel mid-run, then resume or restart from stale in-progress state
    "stale-state",         # old state files, mismatched sessions, contradictory phase metadata
    "dirty-worktree",      # pre-existing edits and untracked files must survive untouched
    "hung-command",        # a command that never returns: bounded timeout, killed child, recovery
    "flaky",               # rerun policy: one lucky pass is not green
    "misleading-success",  # success words with a non-zero exit, skipped tests, partial logs
}
PROBE_REQUIRED = {"api-cli", "llm-agent", "frontend"}


def _entry_errors(file: str, a: dict) -> list[str]:
    cls, status = a.get("class"), a.get("status")
    if cls not in ATTACKS:
        return [f"{file}: attack class '{cls}' is not one of {sorted(ATTACKS)}"]
    if status == "run" and not (a.get("probe") and a.get("result")):
        return [f"{file}: attack '{cls}' ran without probe and result"]
    if status == "n/a" and not a.get("reason"):
        return [f"{file}: attack '{cls}' is n/a without a reason"]
    if status not in {"run", "n/a"}:
        return [f"{file}: attack '{cls}' status '{status}' is not run or n/a"]
    return []


def check(v: dict) -> list[str]:
    """Every attack entry is well-formed; every live user-, model- or browser-facing row ran one."""
    errs: list[str] = []
    for row in v.get("matrix", []):
        attacks, file = row.get("attack") or [], row.get("file")
        for a in attacks:
            errs += _entry_errors(file, a)
        ran = any(a.get("status") == "run" and a.get("class") in ATTACKS for a in attacks)
        if row.get("class") in PROBE_REQUIRED and row.get("evidence") == "live" and not ran:
            errs.append(f"{file}: class '{row.get('class')}' is live but no hostile probe was run")
    return errs


def _selfcheck() -> int:
    """Each refusal branch forced once, and the accepted shapes pass."""
    ran = {"class": "flaky", "status": "run", "probe": "rerun x3", "result": "3/3 green"}
    live = {"file": "a.py", "class": "api-cli", "evidence": "live"}
    ok = [check({"matrix": [live]}) != [],
          check({"matrix": [dict(live, attack=[ran])]}) == [],
          check({"matrix": [dict(live, attack=[dict(ran, **{"class": "x"})])]}) != [],
          check({"matrix": [dict(live, attack=[{"class": "flaky", "status": "run"}])]}) != [],
          check({"matrix": [dict(live, attack=[dict(ran, status="n/a")])]}) != [],
          check({"matrix": [dict(live, attack=[dict(ran, status="skip")])]}) != [],
          check({"matrix": [dict(live, **{"class": "symbol"})]}) == []]
    print(f"verdict_attack selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selfcheck() if "--selfcheck" in sys.argv else 64)
