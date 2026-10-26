"""PM-E — the three declared refusals, and what is left of the spool.

C2: the only runs that do NOT commit are a detached HEAD and a repo that declares
`polaris.commit-policy no-direct-default` while sitting on its default branch. Each exits 2 with
one line naming itself; the files stay where the session wrote them and are copied nowhere. A repo
with no commit at all is NOT one of them — its first checkpoint lands like any other.
C3: the word "spool" survives only as the legacy counter.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from commit_fixture import TODAY, dirt, landed_names, session_log, spool_files
from host_repo import LOGIN, PKG, git, host_repo, run_script

SKILLS = PKG / "skills"


def refusal(repo: Path, cwd: Path | None = None) -> tuple[int, str]:
    out = run_script("end", "session_commit.sh",
                     f"_polaris/team/{LOGIN}/sessions/{TODAY}-@{LOGIN}.md", cwd=str(cwd or repo))
    return out.returncode, out.stdout + out.stderr


class TheThreeDeclaredRefusals(unittest.TestCase):
    """(d) (e) — exit 2, one line, the file untouched in the working tree. (f) commits."""

    def test_d_a_declared_policy_on_the_default_branch_refuses(self):
        repo = host_repo()
        git(repo, "config", "polaris.commit-policy", "no-direct-default")
        log = session_log(repo)
        head = git(repo, "rev-parse", "HEAD").stdout.strip()
        code, body = refusal(repo)
        self.assertEqual(code, 2, body)
        self.assertIn("polaris.commit-policy", body)
        self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), head, "0 commits")
        self.assertIn(f"?? {log.relative_to(repo)}", "\n".join(dirt(repo)))
        self.assertEqual(spool_files(repo), [], "no copy is made anywhere")

    def test_d_the_same_policy_on_a_feature_branch_does_not_stop_the_commit(self):
        repo = host_repo()
        git(repo, "config", "polaris.commit-policy", "no-direct-default")
        git(repo, "switch", "-qc", "feat/x")
        session_log(repo)
        code, body = refusal(repo)
        self.assertEqual(code, 0, body)
        self.assertEqual(dirt(repo), [], body)

    def test_e_a_detached_head_refuses_and_says_so(self):
        repo = host_repo()
        git(repo, "checkout", "-q", "--detach", "HEAD")
        log = session_log(repo)
        code, body = refusal(repo)
        self.assertEqual(code, 2, body)
        self.assertIn("detached", body)
        self.assertIn(f"?? {log.relative_to(repo)}", "\n".join(dirt(repo)))

    def test_f_a_repo_with_no_commit_lands_its_first_checkpoint(self):
        """NOT an exception: an unborn branch takes `git commit -- <path>` like any other."""
        repo = Path(tempfile.mkdtemp()) / "acme-api"
        (repo / "_polaris" / "team" / LOGIN / "sessions").mkdir(parents=True)
        git(repo, "init", "-q", "-b", "main")
        for key, value in (("user.email", "t@t"), ("user.name", "T")):
            git(repo, "config", key, value)
        log = session_log(repo)
        code, body = refusal(repo)
        self.assertEqual(code, 0, body)
        self.assertEqual(git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split(),
                         [str(log.relative_to(repo))], body)


class GitRefusesAPath(unittest.TestCase):
    """G2 — a path on disk that git will not take: declared, exit 2, the rest still lands."""

    def test_a_gitignored_session_log_is_named_and_the_others_land(self):
        repo = host_repo()
        (repo / ".gitignore").write_text("_polaris/team/*/sessions/\n")
        git(repo, "add", ".gitignore")
        git(repo, "commit", "-qm", "ignore sessions")
        log = session_log(repo)
        (repo / "_polaris" / "decisions.md").write_text("## decision\n")
        out = run_script("end", "session_commit.sh", "--end",
                         str(log), str(repo / "_polaris" / "decisions.md"), cwd=str(repo))
        body = out.stdout + out.stderr
        self.assertEqual(out.returncode, 2, body)
        self.assertIn("git refuses", body)
        self.assertIn("ignored", body)
        self.assertEqual(landed_names(repo), ["_polaris/decisions.md"], body)

    def test_a_journal_inside_a_nested_repo_is_named_and_the_others_land(self):
        repo = host_repo()
        journal = repo / ".wiki" / "journal"
        journal.mkdir(parents=True)
        git(repo / ".wiki", "init", "-q", "-b", "main")
        (journal / "2026-09-04.md").write_text("session line\n")
        log = session_log(repo)
        out = run_script("end", "session_commit.sh", "--end",
                         str(log), str(journal / "2026-09-04.md"), cwd=str(repo))
        body = out.stdout + out.stderr
        self.assertEqual(out.returncode, 2, body)
        self.assertIn("git refuses", body)
        self.assertEqual(landed_names(repo), [str(log.relative_to(repo))], body)


class TheSpoolIsOnlyALegacyCounter(unittest.TestCase):
    """(j) — an old spool is reported once, by name, and never touched."""

    def spooled(self) -> Path:
        repo = host_repo()
        spool = repo / ".git" / "polaris-deferred" / "_polaris"
        spool.mkdir(parents=True)
        (spool / "old-one.md").write_text("left by v0.23.0\n")
        (spool / "old-two.md").write_text("and another\n")
        return repo

    def test_prepare_counts_it_and_leaves_it_alone(self):
        repo = self.spooled()
        out = run_script("end", "checkpoint.sh", "prepare", cwd=str(repo))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("SPOOL_LEGACY=2", out.stdout)
        self.assertIn("git add", out.stdout, "it must say what to do with them")
        self.assertEqual(len(spool_files(repo)), 2, "prepare must not touch the legacy spool")

    def test_start_shows_it_under_the_new_name(self):
        repo = self.spooled()
        root = repo / "_polaris"
        out = run_script("start", "brief_signals.py", "--root", str(root), "--current",
                         str(root / "state" / "current.md"), "--main-wt", str(repo), cwd=str(repo))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("SPOOL_LEGACY=2", out.stdout)
        self.assertNotIn("DEFERRED=", out.stdout)

    def test_an_empty_spool_says_nothing(self):
        repo = host_repo()
        out = run_script("end", "checkpoint.sh", "prepare", cwd=str(repo))
        self.assertNotIn("SPOOL_LEGACY", out.stdout)


class TheScriptChecksItself(unittest.TestCase):
    def test_the_selfcheck_passes(self):
        out = run_script("end", "session_commit.sh", "--selfcheck")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_the_real_test_passes(self):
        out = subprocess.run(["bash", str(PKG / "tests" / "real_session_commit.sh")],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
