"""PM-E — the session log commits on the CURRENT branch of the checkout that wrote it, always.

Founder decision, 2026-09-04: an `/end` that postpones instead of committing is an `/end` that
did not work. The spool, the sibling-worktree hand-off and the «wait for a default-branch session»
rule are gone; what is left is a commit here, or one of three declared refusals.

Cases (a) (b) (c) (g) (h) (i) of the contract. The refusals live in `test_commit_exceptions.py`.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from commit_fixture import (checkpoint_commit, dirt, end_files, landed_names,
                            session_log, spool_files, STRAY)
from host_repo import LOGIN, git, host_repo, run_block, skill_block


def stray_log(repo: Path) -> Path:
    """Another day's log, untracked: present in the directory, not part of this run."""
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / STRAY
    path.write_text("## 09:00 — an older session, still untracked\n")
    return path


class ItCommitsOnTheBranchYouAreOn(unittest.TestCase):
    """(a) (b) (c) — three repo shapes, one behaviour."""

    def assert_landed_here(self, repo: Path, run_cwd: Path, branch: str):
        log = session_log(repo)
        stray = stray_log(repo)
        out = checkpoint_commit(run_cwd)
        body = out.stdout + out.stderr
        self.assertEqual(out.returncode, 0, body)
        self.assertEqual(git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), branch)
        self.assertEqual(landed_names(repo), [str(log.relative_to(repo))], body)
        self.assertEqual(dirt(repo), [f"?? {stray.relative_to(repo)}"], "only the stray is left")
        self.assertEqual(spool_files(repo), [], "the spool is gone from the normal path")

    def test_a_main_checkout_off_the_default_with_three_worktrees_commits_here(self):
        repo = host_repo()
        git(repo, "switch", "-qc", "feat/main-panel")
        linked = []
        for n in ("one", "two", "three"):
            path = repo.parent / f"wt-{n}"
            git(repo, "worktree", "add", "-q", "-b", f"feat/{n}", str(path))
            linked.append(path)
        self.assert_landed_here(repo, linked[0], "feat/main-panel")

    def test_b_a_single_checkout_on_a_feature_branch_commits_here(self):
        repo = host_repo()
        git(repo, "switch", "-qc", "feat/x")
        self.assert_landed_here(repo, repo, "feat/x")

    def test_c_a_checkout_sitting_on_the_default_commits_there_too(self):
        repo = host_repo()
        self.assert_landed_here(repo, repo, "main")

    def test_the_shipped_landing_block_still_names_this_command(self):
        self.assertIn("commit", skill_block("update", '"$CHECKPOINT" commit'))


class NobodyElsesWorkRidesAlong(unittest.TestCase):
    """(g) — a file another panel staged is neither committed nor unstaged."""

    def test_a_foreign_staged_file_stays_staged_and_out_of_the_commit(self):
        repo = host_repo()
        git(repo, "switch", "-qc", "feat/x")
        log = session_log(repo)
        (repo / "notes.md").write_text("another panel\n")
        git(repo, "add", "notes.md")
        self.assertEqual(checkpoint_commit(repo).returncode, 0)
        self.assertEqual(landed_names(repo), [str(log.relative_to(repo))])
        self.assertIn("notes.md", git(repo, "diff", "--cached", "--name-only").stdout,
                      "what the user had staged before must come back exactly as it was")


class AHookThatRefusesIsAFailure(unittest.TestCase):
    """(h) — exit 1, the index cleared of OUR paths only, and never a forced commit."""

    def refused(self):
        repo = host_repo()
        git(repo, "switch", "-qc", "feat/x")
        hook = repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho 'the hook says no' >&2\nexit 1\n")
        hook.chmod(0o755)
        return repo, session_log(repo)

    def test_it_exits_one_names_the_hook_and_leaves_the_file_in_the_tree(self):
        repo, log = self.refused()
        out = checkpoint_commit(repo)
        body = out.stdout + out.stderr
        self.assertEqual(out.returncode, 1, body)
        self.assertIn("the hook says no", body, "the hook's own line must reach the session")
        self.assertEqual(git(repo, "diff", "--cached", "--name-only").stdout.strip(), "",
                         "a staged handoff is swallowed by the next commit without a pathspec")
        self.assertIn(f"?? {log.relative_to(repo)}", "\n".join(dirt(repo)))
        self.assertEqual(spool_files(repo), [], "nothing is copied anywhere on a refusal")

    def test_the_scripts_never_pass_no_verify(self):
        """Comments may name the rule; no executable line may carry the flag."""
        scripts = Path(__file__).resolve().parents[1] / "skills" / "update" / "scripts"
        for name in ("session_commit.sh", "checkpoint.sh"):
            code = [ln for ln in (scripts / name).read_text().splitlines()
                    if not ln.lstrip().startswith("#")]
            self.assertEqual([ln for ln in code if "--no-verify" in ln], [], name)


class EndLandsTheWholeHandoff(unittest.TestCase):
    """(i) — the shipped Step 5 block commits the four files that exist, and the tree is clean."""

    def test_the_shipped_end_block_lands_log_handoff_and_both_ledgers(self):
        repo = host_repo()
        git(repo, "switch", "-qc", "feat/x")
        paths = end_files(repo)
        out = run_block("end", '"$SC" --end', repo)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(landed_names(repo), paths, out.stdout + out.stderr)
        self.assertEqual(dirt(repo), [], "C5: /end leaves the Polaris paths clean")
        self.assertEqual(spool_files(repo), [])


if __name__ == "__main__":
    unittest.main()
