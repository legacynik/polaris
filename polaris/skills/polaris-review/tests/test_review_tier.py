"""The reviewer tier is read from the diff: size, file count and risk paths.

Each test builds a throwaway git repository, commits a base, changes files on top, and runs the
public CLI against `--base`. The tier line and its reason are the contract the skill routes on.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_tier.py"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


class Repo:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp())
        git(self.dir, "init", "-q", "-b", "main")
        git(self.dir, "config", "user.email", "t@example.invalid")
        git(self.dir, "config", "user.name", "t")
        (self.dir / "README.md").write_text("base\n")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "base")
        git(self.dir, "tag", "base")

    def change(self, files):
        for rel, lines in files.items():
            p = self.dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("".join(f"line {i}\n" for i in range(lines)))
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "change")
        return self

    def tier(self, path_dirs=(), extra=()):
        env = {**os.environ, "PATH": os.pathsep.join([*map(str, path_dirs), "/usr/bin", "/bin"])}
        return subprocess.run([sys.executable, str(SCRIPT), "--base", "base", "--cwd", str(self.dir), *extra],
                              capture_output=True, text=True, timeout=60, env=env)


def first_line(done):
    return done.stdout.splitlines()[0] if done.stdout else ""


class TierFromTheDiff(unittest.TestCase):
    def test_a_small_mechanical_diff_is_tier_1(self):
        done = Repo().change({"docs/guide.md": 12}).tier()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(first_line(done).startswith("TIER 1"), done.stdout)

    def test_a_normal_code_change_is_tier_2(self):
        done = Repo().change({"app/a.py": 60, "app/b.py": 40, "app/c.py": 30, "tests/t.py": 20}).tier()
        self.assertTrue(first_line(done).startswith("TIER 2"), done.stdout)

    def test_a_small_change_on_a_money_path_is_tier_3_and_names_the_file(self):
        done = Repo().change({"app/billing/invoice.py": 5}).tier()
        self.assertTrue(first_line(done).startswith("TIER 3"), done.stdout)
        self.assertIn("app/billing/invoice.py", done.stdout)
        self.assertIn("money", done.stdout)

    def test_a_migration_is_tier_3(self):
        done = Repo().change({"db/migrations/0007_add_column.sql": 4}).tier()
        self.assertTrue(first_line(done).startswith("TIER 3"), done.stdout)
        self.assertIn("data", done.stdout)

    def test_an_auth_change_is_tier_3(self):
        done = Repo().change({"src/auth/session.ts": 8}).tier()
        self.assertTrue(first_line(done).startswith("TIER 3"), done.stdout)

    def test_a_very_large_diff_is_tier_3_even_without_a_risk_path(self):
        done = Repo().change({f"app/m{i}.py": 40 for i in range(30)}).tier()
        self.assertTrue(first_line(done).startswith("TIER 3"), done.stdout)

    def test_the_repository_config_adds_its_own_risk_paths(self):
        repo = Repo()
        (repo.dir / "_polaris").mkdir()
        (repo.dir / "_polaris" / "config.yml").write_text('review:\n  risk_paths: "^infra/"\n')
        done = repo.change({"infra/main.tf": 3}).tier()
        self.assertTrue(first_line(done).startswith("TIER 3"), done.stdout)
        self.assertIn("infra/main.tf", done.stdout)


class CrossModelAvailability(unittest.TestCase):
    def test_codex_on_path_is_reported_available(self):
        bindir = Path(tempfile.mkdtemp())
        (bindir / "codex").write_text("#!/bin/sh\nexit 0\n")
        (bindir / "codex").chmod(0o755)
        done = Repo().change({"app/billing/x.py": 3}).tier(path_dirs=[bindir])
        self.assertIn("codex: available", done.stdout)

    def test_codex_absent_is_reported_missing(self):
        done = Repo().change({"app/billing/x.py": 3}).tier()
        self.assertIn("codex: missing", done.stdout)


class UnusableInput(unittest.TestCase):
    def test_a_directory_that_is_not_a_repository_is_exit_2(self):
        done = subprocess.run([sys.executable, str(SCRIPT), "--cwd", tempfile.mkdtemp()],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertEqual(done.stdout, "")


if __name__ == "__main__":
    unittest.main()
