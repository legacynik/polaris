#!/usr/bin/env python3
"""worktree_verdict — pure verdict logic imported by cantiere.py's census (#252, child of #130).

No I/O here (no subprocess, no filesystem): every function takes data already
gathered by the caller and returns a decision. Kept separate so the decision
table is testable without a real git repo.

Verdict vocabulary (exactly these eight, no others):
  MAIN                  the primary worktree itself — never a removal candidate.
  PRUNABLE              `git worktree list --porcelain` marks it prunable (dir gone).
  IN_USE                a live process has its cwd inside the worktree — never removed.
  DIRTY                 `git status --short` is non-empty — never removed.
  "?"                   a per-row error (gh/git failed for THIS worktree only).
  CLOSABLE              a merged PR's headRefOid equals the local branch tip, tree clean.
  COMMITS_AFTER_MERGE   a merged PR exists but the local tip has since moved past it.
  ACTIVE                no merged PR found for the branch (or branch is unborn/detached).

`git branch --merged` is deliberately never used: it is squash-merge-blind (a
squash-merged branch is never an ancestor of the base), which is exactly the
gap #252 exists to close. Ground truth is `gh pr list --state merged --head
<branch>` compared against the LOCAL branch tip, never a local ref walk.
"""
from __future__ import annotations

from dataclasses import dataclass

APPLY_REMOVABLE = frozenset({"CLOSABLE", "PRUNABLE"})


@dataclass(frozen=True)
class PRInfo:
    number: int
    head_ref_oid: str


@dataclass(frozen=True)
class WorktreeInfo:
    path: str
    branch: str | None
    is_main: bool = False
    prunable: bool = False
    dirty: bool = False
    in_use: bool = False
    error: str | None = None
    local_tip: str | None = None
    pr: PRInfo | None = None


def verdict(info: WorktreeInfo) -> str:
    """One row in, one verdict out. Order is precedence, not chronology:
    a worktree that is both IN_USE and DIRTY is reported IN_USE — either
    way it is never removed, but IN_USE explains WHY more usefully."""
    if info.is_main:
        return "MAIN"
    if info.prunable:
        return "PRUNABLE"
    if info.error:
        return "?"
    if info.in_use:
        return "IN_USE"
    if info.dirty:
        return "DIRTY"
    if info.pr is None:
        return "ACTIVE"
    if info.local_tip == info.pr.head_ref_oid:
        return "CLOSABLE"
    return "COMMITS_AFTER_MERGE"


def removable(verdict_value: str) -> bool:
    """--apply touches only these two verdicts. DIRTY/IN_USE/ACTIVE/
    COMMITS_AFTER_MERGE/MAIN/"?" are never in the removal set."""
    return verdict_value in APPLY_REMOVABLE


def gate_decision(closable_count: int, threshold: int | None) -> tuple[bool, str]:
    """No threshold declared (None) => always 'propone', never blocks — the
    house rule when #130 has not fixed a number (never invent one here).
    With a threshold: blocks at count >= threshold, never before it."""
    if threshold is None:
        return False, f"no threshold declared (#130) — {closable_count} CLOSABLE, gate propone only"
    if closable_count >= threshold:
        return True, f"{closable_count} CLOSABLE >= threshold {threshold} — new worktree refused"
    return False, f"{closable_count} CLOSABLE < threshold {threshold} — gate open"


def selfcheck() -> int:
    """Every skills-suite script self-checks. This one has no git/gh/fs to
    fixture (see module docstring) — the real adversarial coverage is
    scripts/test/test_worktree_verdict.py; this is the fast, dependency-free
    floor a `--selfcheck` sweep can still run standalone."""
    assert verdict(WorktreeInfo(path="x", branch="b", is_main=True)) == "MAIN"
    assert verdict(WorktreeInfo(path="x", branch="b", in_use=True, dirty=True)) == "IN_USE"
    pr = PRInfo(number=1, head_ref_oid="a")
    assert verdict(WorktreeInfo(path="x", branch="b", local_tip="a", pr=pr)) == "CLOSABLE"
    assert verdict(WorktreeInfo(path="x", branch="b", local_tip="z", pr=pr)) == "COMMITS_AFTER_MERGE"
    assert removable("CLOSABLE") and removable("PRUNABLE") and not removable("DIRTY")
    assert gate_decision(999, None) == (False, gate_decision(999, None)[1])
    assert gate_decision(5, 5)[0] and not gate_decision(4, 5)[0]
    print("SELFCHECK OK — verdict/removable/gate_decision covered")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(selfcheck() if "--selfcheck" in sys.argv else 0)
