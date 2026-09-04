"""Shared fixtures for the two prune suites: a really merged branch, a cockpit, a fake tracker.

One definition, because two copies of "what a merged lane looks like" is how the two halves of a
contract start disagreeing — the same reason `state_lines` owns the one notion of a line.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from host_repo import LOGIN, PKG, git, run_script, seed_state, written

MISSING = "0" * 40


def merged_lane(repo: Path, keep: bool = False) -> tuple[str, str]:
    """A real merged branch: (head oid, merge commit oid). `keep` leaves the branch reusable."""
    git(repo, "switch", "-qc", "feat/b")
    (repo / "b.md").write_text("b\n")
    git(repo, "add", "b.md")
    git(repo, "commit", "-qm", "b")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge b", "feat/b")
    merge = git(repo, "rev-parse", "HEAD").stdout.strip()
    if not keep:
        git(repo, "branch", "-qD", "feat/b")
    return head, merge


def cockpit(repo: Path) -> Path:
    """The shipped template with two lanes placed by the shipped writer — built once per repo."""
    path = repo / "_polaris" / "state" / "current.md"
    if path.is_file() and "feat/b" in path.read_text():
        return path
    path = seed_state(repo, "current.md")
    written(path, "- `feat/b` (acme-api) — chiude #77 · since 2026-09-02")
    written(path, "- `feat/a` (acme-api) — nessuna citazione · since 2026-09-01")
    return path


def todos(repo: Path) -> Path:
    path = seed_state(repo, "todos.md")
    written(path, "| `feat/b` — chiude #77 | | y |", "W36")
    return path


def log_of(repo: Path) -> Path:
    """Today's append-only session log — seeded once, then only ever read or appended to."""
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / "2026-09-04-@acme-dev.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text("## 18:00 — session end · lane chiusa\n- Files: x\n")
    return path


def prune(repo: Path, scenario: dict, *extra: str) -> subprocess.CompletedProcess:
    """Run the shipped pruner with the fake tracker on PATH, as `/end` calls it."""
    shim = repo.parent / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "gh").write_text(f'#!/bin/sh\nexec python3 "{PKG / "tests" / "fake_gh.py"}" "$@"\n')
    (shim / "gh").chmod(0o755)
    env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}",
           "POLARIS_FAKE_GH": json.dumps(scenario)}
    return run_script("end", "prune_threads.py", str(cockpit(repo)), "--log", str(log_of(repo)),
                      "--todos", str(todos(repo)), "--owner", LOGIN, "--now", "2026-09-04",
                      *extra, cwd=str(repo), env=env)


def pr(facts: dict) -> dict:
    """One tracker answer for `#77`. A dict, not four positional arguments."""
    return {"pr": {"77": {"state": facts.get("state", "MERGED"),
                          "mergeCommit": {"oid": facts["merge"]},
                          "headRefOid": facts["head"],
                          "headRefName": facts.get("name", "feat/b")}}}


