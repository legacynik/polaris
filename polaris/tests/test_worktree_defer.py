"""polaris#12 — WHERE a checkpoint lands when no checkout sits on the default branch.

Live proof, 2026-09-04: a panel in a linked worktree ran `/update`. `checkpoint.sh commit` cds into
the MAIN worktree first, that checkout was parked on another panel's branch, `_wt_on_default` found
no sibling on the default and the script concluded «this repo has one checkout» — with a second
checkout right there. It committed on the foreign branch and swept a spooled log from another day
along with it.

Two checkouts and none on the default is not one checkout: it is a repo where nothing may land
today, which is what the spool is for. One checkout on a feature branch still commits here, because
there is no next default-branch session to wait for.
"""
from __future__ import annotations

import subprocess
import unittest
from datetime import date
from pathlib import Path

from host_repo import LOGIN, git, host_repo, run_script, skill_block

STRAY = "2026-09-02-@acme-dev.md"


def sessions(repo: Path) -> Path:
    return repo / "_polaris" / "team" / LOGIN / "sessions"


def session_log(repo: Path) -> Path:
    """Today's log, the one file this run writes."""
    log = sessions(repo) / f"{date.today().isoformat()}-@{LOGIN}.md"
    log.write_text("## 10:00 — checkpoint\n- Key context: x\n- Files: y\n")
    return log


def stray_log(repo: Path) -> Path:
    """Another day's log, never committed: present in the directory, not part of this run."""
    path = sessions(repo) / STRAY
    path.write_text("## 09:00 — an older session, still untracked\n")
    return path


def parked(repo: Path) -> Path:
    """Main checkout on `feat/other` with a foreign edit; a linked worktree on a merged branch."""
    git(repo, "checkout", "-q", "-b", "feat/other")
    (repo / "_polaris" / "config.yml").write_text("root: _polaris\n# another panel's edit\n")
    wt = repo.parent / "wt-merged"
    git(repo, "branch", "-q", "feat/merged")
    git(repo, "worktree", "add", "-q", str(wt), "feat/merged")
    return wt


def commit_from(cwd: Path) -> subprocess.CompletedProcess:
    """`checkpoint.sh commit`, the command the shipped `/update` Landing block names."""
    return run_script("update", "checkpoint.sh", "commit", cwd=str(cwd))


def spooled(repo: Path) -> list[Path]:
    common = git(repo, "rev-parse", "--git-common-dir").stdout.strip()
    spool = Path(common if Path(common).is_absolute() else repo / common) / "polaris-deferred"
    return [p for p in spool.rglob("*") if p.is_file()] if spool.is_dir() else []


class NoCheckoutOnDefault(unittest.TestCase):
    """AC1 and AC3 — two checkouts, neither on the default: a declared deferral, zero commits."""

    def test_the_shipped_landing_block_names_the_command_under_test(self):
        self.assertIn("commit", skill_block("update", '"$CHECKPOINT" commit'))

    def test_a_parked_main_checkout_defers_and_names_its_branch(self):
        repo = host_repo()
        wt = parked(repo)
        session_log(repo)
        head = git(repo, "rev-parse", "HEAD").stdout.strip()
        out = commit_from(wt)
        body = out.stdout + out.stderr
        self.assertNotIn("one checkout", body, body)
        self.assertIn("deferred", body, body)
        self.assertIn("feat/other", body, body)
        self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), head, body)
        self.assertGreaterEqual(len(spooled(repo)), 1, "the entry left no trace in the spool")

    def test_the_deferral_touches_nobody_elses_file(self):
        repo = host_repo()
        wt = parked(repo)
        session_log(repo)
        stray = stray_log(repo)
        commit_from(wt)
        status = git(repo, "status", "--porcelain", "-uall").stdout
        self.assertIn(f" M _polaris/config.yml", status, status)
        self.assertIn(STRAY, status, "the stray log was swept out of the working tree")
        self.assertEqual(git(repo, "log", "--oneline").stdout.count("\n"), 1, "it committed")
        self.assertTrue(stray.is_file())


class OneCheckoutOffDefault(unittest.TestCase):
    """AC2 — a single checkout still lands here, with exactly the file this run wrote."""

    def test_it_commits_on_the_current_branch_with_only_this_runs_file(self):
        repo = host_repo()
        git(repo, "checkout", "-q", "-b", "feat/x")
        log = session_log(repo)
        stray = stray_log(repo)
        out = commit_from(repo)
        self.assertIn("committing here", out.stdout, out.stdout + out.stderr)
        names = git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
        self.assertEqual(names, [str(log.relative_to(repo))], names)
        status = git(repo, "status", "--porcelain", "-uall").stdout
        self.assertIn(f"?? {stray.relative_to(repo)}", status, status)


class MainCheckoutOnDefault(unittest.TestCase):
    """The unchanged case — the default branch is available, so the spool drains into it."""

    def test_a_sibling_on_the_default_takes_the_commit_and_drains_the_spool(self):
        repo = host_repo()
        wt = repo.parent / "wt-feat"
        git(repo, "branch", "-q", "feat/z")
        git(repo, "worktree", "add", "-q", str(wt), "feat/z")
        log = session_log(repo)
        self.assertEqual(commit_from(wt).returncode, 0)
        landed = git(repo, "show", f"HEAD:{log.relative_to(repo)}").stdout
        self.assertIn("10:00", landed)
        self.assertEqual(spooled(repo), [], "the spool kept an entry that already landed")


if __name__ == "__main__":
    unittest.main()
