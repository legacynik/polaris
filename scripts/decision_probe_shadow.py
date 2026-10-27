#!/usr/bin/env python3
"""decision_probe_shadow — whether a decision's probe can falsify the decision at all.

A probe is a falsifier or it is decoration. Three ways it stops being one, each found by a critic
on a version that had already closed the one before it:

`probe: true` fills the field and reads nothing. So a passing probe is re-run against a shadow tree
missing one call site the record itself declares, in `probe_kills`. Still passing means it was
never reading it.

A selfcheck over synthetic fixtures survives that too — it reads the repository, just never the
governed part. So `probe_kills` must be a call site of that very record, and must be at HEAD: a
victim that does not exist is nothing to remove, and skipping the shadow was how `true` with a
bogus victim scored a pass.

Then the shadow itself. Symlinks are not a copy: a probe resolving `__file__` follows the link and
reads the real tree, so `check_absorption.py` exited 0 with its own victim missing. The shadow is
now `git archive HEAD | tar -x` — a materialised copy, ~0.4s — and the probe runs with cwd there
and PYTHONPATH unset. HEAD, not the working tree, is also the right question: the register makes a
claim about what is committed.

Two things a probe may not do, because either lets its own text decide the verdict: name as victim
the script it executes (removing that breaks the command, not the claim), and hold an absolute path
or `~` (which reads past the shadow entirely).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

RUNS = re.compile(r"\b(?:python3?|sh|bash|perl|ruby|node)\b\s+(?:-\S+\s+)*$")
REACHES_OUT = re.compile(r"(?:^|[\s=:'\"(])(?:~|/(?!/))")


def at_head(root: Path) -> set[str]:
    """Every path tracked at HEAD. A victim absent from it is nothing to remove."""
    done = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD"],
                          cwd=root, capture_output=True, text=True)
    return set(done.stdout.split()) if done.returncode == 0 else set()


def run_probe(probe: str, root: Path, timeout: int) -> tuple[bool, str]:
    """(passed, note). A probe that hangs is a probe that failed, and says so."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    try:
        done = subprocess.run(probe, shell=True, cwd=root, timeout=timeout, env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s"
    tail = (done.stderr or done.stdout or "").strip().splitlines()
    return done.returncode == 0, f"exit {done.returncode}" + (f" — {tail[-1][:90]}" if tail else "")


def invalid(record: dict, probe: str, tracked: set[str]) -> str:
    """Why this record cannot falsify itself, or "" when it can."""
    victim = (record.get("probe_kills") or "").strip()
    if victim not in (record.get("call_sites") or []):
        return f"`probe_kills` names {victim or 'nothing'}, not one of its call_sites"
    if not any(f == victim or f.startswith(victim.rstrip("/") + "/") for f in tracked):
        return f"`probe_kills` names {victim}, which is not at HEAD — nothing to remove"
    if victim in probe and RUNS.search(probe[:probe.index(victim)]):
        return f"`probe_kills` names {victim}, which the probe executes — that breaks the command"
    if REACHES_OUT.search(probe):
        return "the probe holds an absolute path or ~; it must address the repository relatively"
    return ""


def _without(root: Path, victim: str, tmp: Path) -> Path:
    """HEAD materialised into `tmp`, minus `victim`. A copy, never symlinks."""
    archive = subprocess.run(["git", "archive", "HEAD"], cwd=root, check=True, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(tmp)], input=archive.stdout, check=True)
    gone = tmp / victim
    if gone.is_dir():
        shutil.rmtree(gone)
    elif gone.exists():
        gone.unlink()
    return tmp


def survives(probe: str, target: tuple[Path, str], timeout: int) -> bool:
    """True when the probe still passes with the call site it names removed."""
    root, victim = target
    with tempfile.TemporaryDirectory() as tmp:
        return run_probe(probe, _without(root, victim, Path(tmp)), timeout)[0]
