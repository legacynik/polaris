"""wt_sweep.sh — the report mode's selfcheck can fail, and a kept branch is named.

    python3 -m pytest skills-suite/end/tests/test_wt_sweep.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wt_sweep.sh"
REPORT_BRANCH = 'if [ "$mode" = "--report" ]; then'


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def test_selfcheck_goes_red_when_report_mode_removes_a_worktree(tmp_path):
    """A report mode that removes is the defect the selfcheck exists for: it must exit 1."""
    src = SCRIPT.read_text()
    assert REPORT_BRANCH in src, "the report branch moved: update the mutation"
    broken = tmp_path / "wt_sweep.sh"
    broken.write_text(src.replace(REPORT_BRANCH, REPORT_BRANCH + ' git worktree remove "$wt";', 1))
    done = subprocess.run(["bash", str(broken), "--selfcheck"], capture_output=True, text=True)
    assert done.returncode == 1, f"a removing report mode passed the selfcheck:\n{done.stdout}"


def test_a_branch_git_refuses_to_delete_is_reported(tmp_path):
    """Merged into origin/main but not into local HEAD: `git branch -d` refuses, and says so."""
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-qb", "main")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "base")
    _git(repo, "worktree", "add", "-q", "../wt-rem", "-b", "rem")
    _git(tmp_path / "wt-rem", "commit", "-q", "--allow-empty", "-m", "work")
    _git(repo, "update-ref", "refs/remotes/origin/main", _git(tmp_path / "wt-rem", "rev-parse", "HEAD"))
    done = subprocess.run(["bash", str(SCRIPT)], cwd=repo, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "rem" in _git(repo, "branch", "--list", "rem"), "fixture: the branch was deleted"
    out = done.stdout + done.stderr
    assert "branch rem kept" in out, f"a branch git refused to delete went unreported:\n{out}"
