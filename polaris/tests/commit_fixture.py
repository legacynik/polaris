"""Shared shapes for the "commit where you are" contract (PM-E).

The founder's rule of 2026-09-04: *«il log di sessione si committa dove sei, sul branch
corrente, sempre. Niente spool, niente rinvii, niente worktree principale sul default»*.

Every repo here is built by `host_repo` from the package's own templates, and every command
is a shipped script or a bash block read verbatim out of a shipped SKILL.md.
"""
from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from host_repo import LOGIN, git, run_script

TODAY = date.today().isoformat()
STRAY = "2026-09-02-@acme-dev.md"


def session_log(repo: Path, login: str = LOGIN) -> Path:
    """Today's log — the one file a checkpoint run writes."""
    log = repo / "_polaris" / "team" / login / "sessions" / f"{TODAY}-@{login}.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("## 10:00 — checkpoint\n- Key context: x\n- Files: y\n")
    return log


def end_files(repo: Path, login: str = LOGIN) -> list[str]:
    """The four paths `/end` Step 5 names and that exist on a normal run, repo-relative."""
    root = repo / "_polaris"
    log = session_log(repo, login)
    hand = root / "team" / login / "handoff" / f"{TODAY}.md"
    hand.parent.mkdir(parents=True, exist_ok=True)
    hand.write_text(f"# Handoff {TODAY} — @{login}\n## Shipped (verified)\n- niente\n")
    (root / "decisions.md").write_text(f"## {TODAY} — decision (@{login})\n")
    (root / "lessons.md").write_text(f"## {TODAY} — lesson (@{login})\n")
    return sorted(str(p.relative_to(repo)) for p in
                  (log, hand, root / "decisions.md", root / "lessons.md"))


def checkpoint_commit(cwd: Path) -> subprocess.CompletedProcess:
    """`checkpoint.sh commit` — the command the shipped `/update` Landing block names."""
    return run_script("end", "checkpoint.sh", "commit", cwd=str(cwd))


def dirt(repo: Path) -> list[str]:
    """Only the Polaris paths: another panel's unrelated work is not ours to judge."""
    return [ln for ln in git(repo, "status", "--short", "-uall").stdout.splitlines()
            if "_polaris/" in ln]


def spool_files(repo: Path) -> list[Path]:
    """Whatever sits in the legacy spool. On the normal path this must stay empty."""
    spool = repo / ".git" / "polaris-deferred"
    return sorted(p for p in spool.rglob("*") if p.is_file()) if spool.is_dir() else []


def landed_names(repo: Path) -> list[str]:
    return sorted(git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split())
