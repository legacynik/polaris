"""Gate round 2, F3 — a worktree whose directory is gone is not a checkout.

`git worktree list --porcelain` keeps reporting an entry until someone prunes it, flagged
`prunable`. Counting those made a repo with ONE real checkout look like two, so every single run
deferred forever and the session log never landed — the deferral turning into the data loss it
exists to prevent. A `bare` entry is not a checkout either: nothing can be committed from it.
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from datetime import date
from pathlib import Path

from host_repo import LOGIN, git, host_repo, run_script


def session_log(repo: Path) -> Path:
    log = repo / "_polaris" / "team" / LOGIN / "sessions" / f"{date.today().isoformat()}-@{LOGIN}.md"
    log.write_text("## 10:00 — checkpoint\n- Key context: x\n- Files: y\n")
    return log


def stale_worktree(repo: Path) -> Path:
    """A linked worktree whose directory somebody deleted with `rm -rf` — the everyday case."""
    path = repo.parent / "wt-gone"
    git(repo, "branch", "-q", "feat/gone")
    git(repo, "worktree", "add", "-q", str(path), "feat/gone")
    shutil.rmtree(path)
    return path


def commit_from(cwd: Path) -> subprocess.CompletedProcess:
    return run_script("update", "checkpoint.sh", "commit", cwd=str(cwd))


class PrunableIsNotACheckout(unittest.TestCase):

    def test_a_deleted_worktree_directory_does_not_force_a_deferral(self):
        repo = host_repo()
        git(repo, "checkout", "-q", "-b", "feat/x")
        stale_worktree(repo)
        log = session_log(repo)
        out = commit_from(repo)
        body = out.stdout + out.stderr
        self.assertIn("committing here", body, body)
        self.assertNotIn("deferred", body, body)
        names = git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
        self.assertEqual(names, [str(log.relative_to(repo))], names)

    def test_a_real_second_checkout_still_defers(self):
        repo = host_repo()
        git(repo, "checkout", "-q", "-b", "feat/other")
        stale_worktree(repo)
        git(repo, "branch", "-q", "feat/live")
        git(repo, "worktree", "add", "-q", str(repo.parent / "wt-live"), "feat/live")
        session_log(repo)
        head = git(repo, "rev-parse", "HEAD").stdout.strip()
        out = commit_from(repo.parent / "wt-live")
        body = out.stdout + out.stderr
        self.assertIn("deferred", body, body)
        self.assertIn("2 checkouts", body, "the stale entry was counted as a checkout")
        self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), head, body)


if __name__ == "__main__":
    unittest.main()
