#!/usr/bin/env python3
"""fixtures — throwaway repos in a DECLARED state, for behavioural skill evals.

Polaris session skills are judged by what they leave on disk and in git (a session
log appended, `current.md` reconciled, a commit made or deferred), never by what
they say. That makes the assertions deterministic: no LLM grader, no prose match.
A fixture is the precondition; the eval case owns the assertion.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

LOGIN = "evaluser"


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    return r.stdout.strip()


def _init(repo: Path) -> None:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "eval@test")
    _git(repo, "config", "user.name", "eval")
    _git(repo, "config", "polaris.login", LOGIN)


def _contract(repo: Path) -> Path:
    """The `_polaris/` contract with this contributor's own team path."""
    root = repo / "_polaris"
    for sub in ("sessions", "weeks", "handoff"):
        (root / "team" / LOGIN / sub).mkdir(parents=True, exist_ok=True)
    (root / "state").mkdir(parents=True, exist_ok=True)
    (root / "config.yml").write_text("root: _polaris\n")
    (root / "decisions.md").write_text("# Decisions\n")
    (root / "lessons.md").write_text("# Lessons\n")
    (repo / ".gitignore").write_text("_polaris/state/current*.md\n")
    return root


def _thread(n: int, repo_name: str = "acme") -> str:
    return (f"- `main` ({repo_name}) — thread {n}: contesto della riga, "
            f"cosa la sblocca · since 2026-07-{10 + n % 20:02d}\n")


def build(threads: int = 3, blocks: int = 2, branch: str = "main") -> Path:
    """A repo whose state carries `threads` open threads and `blocks` cockpit blocks."""
    repo = Path(tempfile.mkdtemp(prefix="polaris-eval-"))
    _init(repo)
    root = _contract(repo)
    (root / "state" / "current.md").write_text(
        "# Current — live threads\nUpdated: 2026-08-02 by @%s — setup\n\n## Open\n%s\n## Next\n%s"
        % (LOGIN, "".join(_thread(i) for i in range(threads)),
           "".join(f"- `main`: passo {i}\n" for i in range(min(threads, 2)))))
    (root / "state" / "current-state.md").write_text(
        "".join(f"## Update: 2026-08-0{i % 9 + 1} 10:00 · acme · main\n- riga di contesto\n\n"
                for i in range(blocks)))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    if branch != "main":
        _git(repo, "checkout", "-qb", branch)
    return repo


def open_threads(repo: Path) -> int:
    text = (repo / "_polaris/state/current.md").read_text()
    body = text.split("## Open", 1)[-1].split("## Next", 1)[0]
    return sum(1 for line in body.splitlines() if line.startswith("- "))


def cockpit_blocks(repo: Path) -> int:
    p = repo / "_polaris/state/current-state.md"
    return sum(1 for line in p.read_text().splitlines() if line.startswith("## ")) if p.exists() else 0


def head_files(repo: Path) -> list[str]:
    return _git(repo, "show", "--name-only", "--format=", "HEAD").splitlines()


def commits(repo: Path) -> int:
    return len(_git(repo, "log", "--oneline").splitlines())
