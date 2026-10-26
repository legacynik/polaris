"""PM-E — the session log commits on the CURRENT branch of the checkout that wrote it, always.

Founder decision, 2026-09-04: an `/end` that postpones instead of committing is an `/end` that
did not work. The spool, the sibling-worktree hand-off and the «wait for a default-branch session»
rule are gone; what is left is a commit here, or one of three declared refusals.

Cases (a) (b) (c) (g) (h) (i) of the contract. The refusals live in `test_commit_exceptions.py`.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from commit_fixture import (checkpoint_commit, dirt, landed_names,
                            session_log, spool_files, STRAY)
from host_repo import LOGIN, git, host_repo, run_script


def stray_log(repo: Path) -> Path:
    """Another day's log, untracked: present in the directory, not part of this run."""
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / STRAY
    path.write_text("## 09:00 — an older session, still untracked\n")
    return path


class ItCommitsOnTheBranchYouAreOn(unittest.TestCase):
    """(a) (b) (c) — three repo shapes, one behaviour: the panel's own worktree and branch."""

    def assert_landed_here(self, tree: Path, branch: str):
        log = session_log(tree)
        stray = stray_log(tree)
        out = checkpoint_commit(tree)
        body = out.stdout + out.stderr
        self.assertEqual(out.returncode, 0, body)
        self.assertEqual(git(tree, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), branch)
        self.assertEqual(landed_names(tree), [str(log.relative_to(tree))], body)
        self.assertEqual(dirt(tree), [f"?? {stray.relative_to(tree)}"], "only the stray is left")
        self.assertEqual(spool_files(tree), [], "the spool is gone from the normal path")

    def test_a_a_linked_worktree_commits_its_own_log_on_its_own_branch(self):
        """G1 — the main checkout is parked on another panel's branch and stays untouched."""
        repo = host_repo()
        git(repo, "switch", "-qc", "feat/main-panel")
        for n in ("one", "two", "three"):
            git(repo, "worktree", "add", "-q", "-b", f"feat/{n}", str(repo.parent / f"wt-{n}"))
        head = git(repo, "rev-parse", "HEAD").stdout.strip()
        self.assert_landed_here(repo.parent / "wt-one", "feat/one")
        self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), head,
                         "the main checkout's branch took somebody else's session log")

    def test_b_a_single_checkout_on_a_feature_branch_commits_here(self):
        repo = host_repo()
        git(repo, "switch", "-qc", "feat/x")
        self.assert_landed_here(repo, "feat/x")

    def test_c_a_checkout_sitting_on_the_default_commits_there_too(self):
        repo = host_repo()
        self.assert_landed_here(repo, "main")

    def test_the_shared_resolver_puts_the_root_here_and_the_cockpit_at_home(self):
        """G1 — `/end` builds its paths from `resume_paths.sh`, so the split lives there too."""
        repo = host_repo()
        wt = repo.parent / "wt-mine"
        git(repo, "worktree", "add", "-q", "-b", "feat/mine", str(wt))
        out = run_script("start", "resume_paths.sh", cwd=str(wt))
        self.assertEqual(out.returncode, 0, out.stderr)
        fields = dict(ln.split("=", 1) for ln in out.stdout.splitlines() if "=" in ln)
        self.assertIn(str(wt), fields["ROOT"], fields["ROOT"])
        self.assertIn(str(repo), fields["CURRENT"], fields["CURRENT"])
        self.assertIn(str(repo), fields["MAIN_WT"], fields["MAIN_WT"])

    def test_prepare_resolves_the_log_here_and_the_cockpit_at_home(self):
        """G1 — SESSION_LOG follows the panel; CURRENT (gitignored) stays in the main worktree."""
        repo = host_repo()
        wt = repo.parent / "wt-mine"
        git(repo, "worktree", "add", "-q", "-b", "feat/mine", str(wt))
        out = run_script("end", "checkpoint.sh", "prepare", cwd=str(wt))
        self.assertEqual(out.returncode, 0, out.stderr)
        fields = dict(ln.split("=", 1) for ln in out.stdout.splitlines() if "=" in ln)
        self.assertTrue(fields["SESSION_LOG"].startswith(f"{wt}/"), fields["SESSION_LOG"])
        self.assertTrue(fields["CURRENT"].startswith(f"{repo}/"), fields["CURRENT"])

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
        scripts = Path(__file__).resolve().parents[1] / "skills" / "end" / "scripts"
        for name in ("session_commit.sh", "checkpoint.sh"):
            code = [ln for ln in (scripts / name).read_text().splitlines()
                    if not ln.lstrip().startswith("#")]
            self.assertEqual([ln for ln in code if "--no-verify" in ln], [], name)

if __name__ == "__main__":
    unittest.main()
