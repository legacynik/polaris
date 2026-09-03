#!/usr/bin/env python3
"""T6 — is this branch merged? Ask the PR state, never ancestry.

This repository squash-merges, so a merged branch tip is on no ancestry path of `main`:
`git merge-base --is-ancestor <head> origin/main` exits 1 on every merged PR (measured
2026-09-03 on `#253`, `#255`, `#256` — 3 of 3 that GitHub reports MERGED). Anything that
removes work on ancestry therefore never fires here, which is worse than wrong: it is a
cleanup that silently does nothing while reporting success.

Split out of `state_reconcile` because "is it merged" is not state reconciliation, and
because the same answer belongs to the worktree census: when T13 lands `cantiere.py`'s own
merge truth, this module delegates to it instead of asking twice.

Fail-closed by contract: no `gh`, no auth, no answer → None, and the caller KEEPS the work.
A removal is destructive; the burden of proof is on removing.
"""
from __future__ import annotations

import json
import subprocess

def _capture(args: list[str], repo_dir: str) -> str | None:
    """stdout, or None when the binary is missing or the call failed."""
    try:
        done = subprocess.run(args, cwd=repo_dir, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def git_merged(branch: str, repo_dir: str) -> bool | None:
    """True merged, False not, None unverifiable — and None means the caller KEEPS it."""
    prs = _capture(["gh", "pr", "list", "--state", "merged", "--head", branch,
                    "--json", "headRefOid", "--limit", "5"], repo_dir)
    tip = _capture(["git", "rev-parse", branch], repo_dir)
    if prs is None or not tip:
        return None
    try:
        return any(row.get("headRefOid") == tip.strip() for row in json.loads(prs))
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None
