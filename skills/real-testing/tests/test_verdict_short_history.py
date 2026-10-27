"""A repository too young for the requested base gets a plain refusal, not a traceback.

On a repository with one commit, `--base HEAD~1` names nothing; on a repository with no commit,
HEAD itself names nothing. Either way the verdict cannot be computed: exit 2 (usage error, the
suite convention) with the git reference that failed.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

VERDICT = Path(__file__).resolve().parents[1] / "scripts" / "verdict.py"


def _repo(tmp_path: Path, commits: int) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for n in range(commits):
        (tmp_path / "f.txt").write_text(f"{n}\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
        subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", f"c{n}"], check=True)
    return tmp_path


def _new(repo: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(VERDICT), "new", "--repo", str(repo), *extra],
                          capture_output=True, text=True)


def test_one_commit_with_a_base_before_it_is_refused_plainly(tmp_path: Path) -> None:
    done = _new(_repo(tmp_path, 1), "--base", "HEAD~1")
    assert "Traceback" not in done.stderr, done.stderr
    assert done.returncode == 2, (done.returncode, done.stderr)
    assert "HEAD~1" in done.stderr


def test_no_commit_is_refused_plainly(tmp_path: Path) -> None:
    done = _new(_repo(tmp_path, 0))
    assert "Traceback" not in done.stderr, done.stderr
    assert done.returncode == 2, (done.returncode, done.stderr)
