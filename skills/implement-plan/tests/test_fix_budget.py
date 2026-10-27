"""The fix loop stops itself before it digs (gstack /qa's self-regulation, adapted).

Observed: a fix loop that keeps reverting and keeps reaching into files the task never named is
not converging; left alone it burns the phase and hands the human a diff nobody can review. The
budget is read from git since the task base (noted on the task bead at claim), so a crashed
orchestrator resumes with the same score. These tests drive the public CLI on a throwaway
repository; nothing is mocked.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fix_budget.py"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


def commit(repo, path, text, msg):
    f = Path(repo) / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    git(repo, "add", "--", path)
    git(repo, "commit", "-q", "-m", msg)


def budget(repo, base, *scope):
    args = [sys.executable, str(SCRIPT), "--repo", str(repo), "--base", base]
    for s in scope:
        args += ["--scope", s]
    return subprocess.run(args, capture_output=True, text=True)


class FixBudget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        commit(self.repo, "src/parser.py", "v0\n", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def revert_last(self):
        git(self.repo, "revert", "--no-edit", "HEAD")

    def test_fixes_inside_the_task_scope_keep_the_loop_going(self):
        commit(self.repo, "src/parser.py", "v1\n", "fix: parser")
        commit(self.repo, "tests/test_parser.py", "t\n", "test: parser")
        r = budget(self.repo, self.base, "src/parser.py", "tests/*")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("score 0", r.stdout)

    def test_one_revert_raises_the_score_but_does_not_stop(self):
        commit(self.repo, "src/parser.py", "v1\n", "fix: parser")
        self.revert_last()
        r = budget(self.repo, self.base, "src/*")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("score 15", r.stdout)

    def test_two_reverts_stop_the_loop_and_say_why(self):
        for i in (1, 2):
            commit(self.repo, "src/parser.py", f"v{i}\n", f"fix: attempt {i}")
            self.revert_last()
        r = budget(self.repo, self.base, "src/*")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("STOP", r.stdout)
        self.assertIn("2 reverts", r.stdout)

    def test_a_file_outside_the_scope_plus_a_revert_stops_and_names_the_file(self):
        commit(self.repo, "src/parser.py", "v1\n", "fix: parser")
        self.revert_last()
        commit(self.repo, "billing/rates.py", "x\n", "fix: unrelated")
        r = budget(self.repo, self.base, "src/*")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("billing/rates.py", r.stdout)

    def test_uncommitted_edits_outside_the_scope_count_too(self):
        commit(self.repo, "src/parser.py", "v1\n", "fix: parser")
        self.revert_last()
        (Path(self.repo) / "infra").mkdir()
        (Path(self.repo) / "infra" / "deploy.sh").write_text("x\n")
        r = budget(self.repo, self.base, "src/*")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("infra/deploy.sh", r.stdout)

    def test_moving_an_out_of_scope_file_into_the_scope_is_still_seen(self):
        commit(self.repo, "billing/rates.py", "x\n", "setup")
        self.base = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "mv", "billing/rates.py", "src/rates.py")
        git(self.repo, "commit", "-q", "-m", "fix: move")
        commit(self.repo, "src/parser.py", "v1\n", "fix: parser")
        self.revert_last()
        r = budget(self.repo, self.base, "src/*")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("billing/rates.py", r.stdout)

    def test_a_non_ascii_path_inside_the_scope_is_in_scope(self):
        commit(self.repo, "src/café.py", "x\n", "fix: accent")
        r = budget(self.repo, self.base, "src/*")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("score 0", r.stdout)

    def test_no_scope_is_a_usage_error_not_a_free_pass(self):
        r = budget(self.repo, self.base)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--scope", r.stderr)

    def test_an_unknown_base_fails_closed(self):
        r = budget(self.repo, "deadbeef" * 5, "src/*")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("unknown base", r.stderr)


if __name__ == "__main__":
    unittest.main()
