"""PM-C — `/end` lands the session and leaves the working tree clean.

`polaris-os#202` AC4: *«`/end` rimuove i thread chiusi e lascia il working tree pulito:
`git status --short` esce `0` righe»*. Since the founder decision of 2026-09-04 the handoff commits
on the CURRENT branch of the checkout that wrote it, in every repo shape — one checkout or five,
on the default branch or off it.

`#141`: where the repository's own policy forbids a direct commit on the default branch, the run
REFUSES with exit 2 and one line; the files stay in the working tree and are copied nowhere.

Every fixture is the shipped template or the shipped writer; every command is the shipped script.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from host_repo import LOGIN, PKG, git, host_repo, run_script

DAY = "2026-09-04"


def landed(repo: Path, login: str = LOGIN) -> list[str]:
    """The two files `/end` writes, in the contract's own paths, repo-relative."""
    root = repo / "_polaris" / "team" / login
    log = root / "sessions" / f"{DAY}-@{login}.md"
    hand = root / "handoff" / f"{DAY}.md"
    for path in (log, hand):
        path.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"## 18:00 — session end · lane chiusa · wt: main · branch: x\n- Files: y\n")
    hand.write_text(f"# Handoff {DAY} 18:00 — @{login}\n## Shipped (verified)\n- niente\n")
    return [str(p.relative_to(repo)) for p in (log, hand)]


def end(repo: Path, *paths: str) -> subprocess.CompletedProcess:
    return run_script("update", "session_commit.sh", "--end", *paths, cwd=str(repo))


def dirt(repo: Path) -> list[str]:
    """Only the Polaris paths: another panel's unrelated work is not ours to judge."""
    return [ln for ln in git(repo, "status", "--short", "-uall").stdout.splitlines()
            if "_polaris/" in ln]


def spooled(repo: Path) -> list[str]:
    """Nothing writes here since v0.24.0; the assertions below prove it stays empty."""
    root = repo / ".git" / "polaris-deferred"
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()) \
        if root.is_dir() else []


class ASingleCheckoutCommitsOnItsOwnBranch(unittest.TestCase):
    """D1b — one checkout means the current branch IS where this repo's history is written."""

    def parked(self):
        repo = host_repo()
        git(repo, "switch", "-qc", "feat/x")
        return repo, landed(repo)

    def test_the_tree_is_clean_and_the_handoff_is_committed_here(self):
        repo, paths = self.parked()
        out = end(repo, *paths)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(dirt(repo), [], "AC4: git status --short must be 0 Polaris lines")
        for path in paths:
            self.assertEqual(git(repo, "show", f"HEAD:{path}").returncode, 0, f"{path} not landed")

    def test_nothing_is_copied_anywhere_once_the_commit_landed(self):
        repo, paths = self.parked()
        end(repo, *paths)
        self.assertEqual(spooled(repo), [], "a landed handoff has nothing left to drain")

    def test_a_foreign_staged_file_is_neither_committed_nor_unstaged(self):
        repo, paths = self.parked()
        (repo / "notes.md").write_text("another panel\n")
        git(repo, "add", "notes.md")
        end(repo, *paths)
        landed_files = git(repo, "show", "--name-only", "--format=", "HEAD").stdout
        self.assertIn(paths[0], landed_files, "the handoff commit must have happened at all")
        self.assertNotIn("notes.md", landed_files)
        self.assertIn("notes.md", git(repo, "diff", "--cached", "--name-only").stdout,
                      "what the user had staged before must come back exactly as it was")


class ASiblingWorktreeOnTheDefaultChangesNothing(unittest.TestCase):
    """D1a — the log belongs to the branch the session happened on, not to whoever holds main."""

    def split(self):
        repo = host_repo()
        linked = repo.parent / "linked"
        git(repo, "worktree", "add", "-q", "-b", "feat/y", str(linked))
        return repo, linked

    def test_the_linked_tree_commits_its_own_branch_and_leaves_the_default_alone(self):
        repo, linked = self.split()
        paths = landed(linked)
        out = end(linked, *paths)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(dirt(linked), [], "the tree that wrote them must not stay dirty")
        for path in paths:
            self.assertEqual(git(linked, "show", f"HEAD:{path}").returncode, 0, f"{path} not landed")
            self.assertNotEqual(git(repo, "show", f"HEAD:{path}").returncode, 0,
                                f"{path} was written onto the default branch")

    def test_the_absolute_paths_the_skill_passes_still_resolve(self):
        """`/end` Step 5 names its files absolutely; the pathspec must survive the normalisation."""
        repo, linked = self.split()
        paths = landed(linked)
        out = end(linked, *[str(linked / p) for p in paths])
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        for path in paths:
            self.assertEqual(git(linked, "show", f"HEAD:{path}").returncode, 0, f"{path} never landed")

    def test_the_commit_drags_nothing_that_was_staged_beside_it(self):
        repo, linked = self.split()
        (linked / "notes.md").write_text("another panel\n")
        git(linked, "add", "notes.md")
        end(linked, *landed(linked))
        self.assertNotIn("notes.md", git(linked, "show", "--name-only", "--format=", "HEAD").stdout,
                         "every commit here is pathspec-only")


class ADeclaredPolicyRefusesInsteadOfForcing(unittest.TestCase):
    """D1c / `#141` — a policy that forbids the direct commit produces exit 2, never a commit."""

    def forbidden(self):
        repo = host_repo()
        git(repo, "config", "polaris.commit-policy", "no-direct-default")
        return repo, landed(repo), git(repo, "rev-parse", "HEAD").stdout.strip()

    def test_no_commit_is_made_and_the_result_names_the_policy(self):
        repo, paths, head = self.forbidden()
        out = end(repo, *paths)
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("polaris.commit-policy", out.stderr)
        self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), head, "0 commits")

    def test_the_files_stay_in_the_tree_and_are_copied_nowhere(self):
        repo, paths, _ = self.forbidden()
        end(repo, *paths)
        self.assertEqual(sorted(ln.split()[-1] for ln in dirt(repo)), sorted(paths))
        self.assertEqual(spooled(repo), [], "nothing is copied out of the working tree any more")


class OneSessionDoesNotRewriteAnother(unittest.TestCase):
    """D5 — a second contributor's commit leaves the first one's log entry byte-identical."""

    def test_bs_commit_does_not_alter_as_entry(self):
        repo = host_repo()
        a_paths = landed(repo, LOGIN)
        end(repo, *a_paths)
        a_blob = git(repo, "rev-parse", f"HEAD:{a_paths[0]}").stdout.strip()
        git(repo, "config", "polaris.login", "acme-two")
        end(repo, *landed(repo, "acme-two"))
        self.assertEqual(git(repo, "rev-parse", f"HEAD:{a_paths[0]}").stdout.strip(), a_blob,
                         "the ledger of another session is append-only and not ours to rewrite")


class PostPushWithoutARemote(unittest.TestCase):
    """D4 — «push presente ma nessuna PR verificabile» on a repo that has no remote at all."""

    def test_no_remote_says_so_and_exits_zero(self):
        repo = host_repo()
        out = run_script("end", "lane_phase.sh", cwd=str(repo))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("nessun remote: push non applicabile", out.stdout)

    def test_with_a_remote_the_verdict_is_left_to_git_power(self):
        repo = host_repo()
        git(repo, "remote", "add", "origin", str(repo.parent / "bare.git"))
        out = run_script("end", "lane_phase.sh", cwd=str(repo),
                         env={"PATH": "/usr/bin:/bin", "HOME": str(repo.parent)})
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("nessun remote", out.stdout)
        self.assertIn("git-power", out.stdout, "an absent git-power degrades, it does not crash")

    def test_the_skill_calls_the_script_instead_of_cantiere_directly(self):
        body = (PKG / "skills" / "end" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("lane_phase.sh", body)
        self.assertNotIn("phase post-push", body,
                         "the guard must live in the script, not in prose a model may skip")


class TheScriptsCheckThemselves(unittest.TestCase):
    def test_selfchecks_pass(self):
        for skill, name in (("update", "session_commit.sh"), ("end", "lane_phase.sh")):
            with self.subTest(script=name):
                out = run_script(skill, name, "--selfcheck")
                self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
