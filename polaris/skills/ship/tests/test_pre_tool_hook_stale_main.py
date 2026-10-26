"""A PR is judged on its own diff against the remote default branch, not a stale local copy.

2026-10-26 (a product repository): the main checkout's local `main` sat 61 commits behind origin/main.
`git diff main...HEAD` then carried weeks of other people's commits, the redaction scan found a
HIGH finding in one of them, and every `gh pr create` from a fresh branch was refused.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pre_tool_hook as hook  # noqa: E402

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t.t", "PATH": "/usr/bin:/bin"}
# Fake scanner input, assembled at run time like the hook's own selfcheck: no key shape in this file.
KEY_BODY = "ABCDEFGHIJKLMNOP"
SECRET = 'AWS_KEY="AKIA' + KEY_BODY + '"\n'


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=ENV)


def test_a_stale_local_main_does_not_put_other_commits_in_the_diff(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "commit", "-q", "--allow-empty", "-m", "base")       # local main stays here
    git(root, "checkout", "-q", "-b", "upstream")
    (root / "old.py").write_text(SECRET)                           # someone else's commit, already on origin
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "theirs")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    git(root, "checkout", "-q", "-b", "feat/x", "origin/main")      # the branch starts from origin
    (root / "notes.txt").write_text("x\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "mine")
    monkeypatch.chdir(root)
    ok, why = hook.phase_a_check(root, draft=True)
    assert ok, why
