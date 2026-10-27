"""PM-C / D2 — resolving the truth: two sources must agree, and every citation must be proven.

The defect that kept removal parked was a truth built on one source. F3 showed a second shape of the
same mistake inside the fix: `cite()` resolved only the FIRST citation, so a lane citing a merged
PR and an open one closed on the merged half.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from host_repo import git, host_repo, seed_state, written
from prune_fixture import MISSING, cockpit, log_of, merged_lane, pr, prune, run_script


class UnprovenTruthKeepsTheThread(unittest.TestCase):
    def test_a_merge_this_checkout_cannot_see_is_ambiguous(self):
        repo = host_repo()
        out = prune(repo, pr({"head": MISSING, "merge": MISSING}), "--apply")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("AMBIGUOUS=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_a_branch_reused_after_the_merge_is_ambiguous(self):
        repo = host_repo()
        head, merge = merged_lane(repo, keep=True)
        git(repo, "switch", "-q", "feat/b")
        (repo / "c.md").write_text("c\n")
        git(repo, "add", "c.md")
        git(repo, "commit", "-qm", "riuso")
        git(repo, "switch", "-q", "main")
        out = prune(repo, pr({"head": head, "merge": merge}), "--apply")
        self.assertIn("AMBIGUOUS=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_an_open_pr_is_not_a_closed_thread(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        out = prune(repo, pr({"head": head, "merge": merge, "state": "OPEN"}), "--apply")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("OPEN=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())


class AClosedIssueIsNotAMergedPr(unittest.TestCase):
    def test_a_completed_issue_cited_as_an_issue_closes_the_thread(self):
        repo = host_repo()
        out = prune(repo, {"issue": {"77": {"state": "CLOSED", "stateReason": "COMPLETED"}}},
                    "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_not_planned_is_not_completed(self):
        """Superseded 2026-09-30 (founder: «/end non chiude mai»): not planned is abandoned work.
        The lane leaves `## Open`, and the log says DEAD, never PROVEN or completed."""
        repo = host_repo()
        out = prune(repo, {"issue": {"77": {"state": "CLOSED", "stateReason": "NOT_PLANNED"}}},
                    "--apply")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())
        self.assertIn("DEAD: issue #77 closed as NOT_PLANNED", log_of(repo).read_text())
        self.assertNotIn("PROVEN", log_of(repo).read_text())

    def test_a_thread_citing_a_pr_never_falls_back_to_the_issue(self):
        repo = host_repo()
        path = seed_state(repo, "current.md")
        written(path, "- `feat/b` (acme-api) — attende PR 77 · since 2026-09-02")
        out = prune(repo, {"issue": {"77": {"state": "CLOSED", "stateReason": "COMPLETED"}}},
                    "--apply")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("BLOCKED=", out.stdout, "a PR citation is resolved as a PR or not at all")
        self.assertIn("feat/b", path.read_text())


class EveryCitationHasToBeProven(unittest.TestCase):
    """F3 — a thread citing two PRs closed on the first one: `cite()` used `search`."""

    def test_a_thread_citing_a_merged_and_an_open_pr_stays(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = seed_state(repo, "current.md")
        written(path, "- `feat/b` (acme-api) — chiude #77, poi #79 · since 2026-09-02")
        scenario = pr({"head": head, "merge": merge})
        scenario["pr"]["79"] = {"state": "OPEN", "mergeCommit": None,
                                "headRefOid": None, "headRefName": None}
        out = prune(repo, scenario, "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("#79", out.stdout, "the refusal must name the citation that is still open")
        self.assertIn("feat/b", path.read_text(), "one open citation keeps the whole lane")

    def test_all_citations_proven_closes_it(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = seed_state(repo, "current.md")
        written(path, "- `feat/b` (acme-api) — chiude #77, poi #79 · since 2026-09-02")
        scenario = pr({"head": head, "merge": merge})
        scenario["issue"] = {"79": {"state": "CLOSED", "stateReason": "COMPLETED"}}
        out = prune(repo, scenario, "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("feat/b", path.read_text())

if __name__ == "__main__":
    unittest.main()
