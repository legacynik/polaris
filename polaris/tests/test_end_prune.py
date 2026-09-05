"""PM-C / D2 — applying a proven verdict: what leaves `## Open`, and what stops the whole run.

Fail-closed on purpose: one candidate whose state cannot be read blocks every removal. A pruner that
removes four lanes and silently skips the fifth is the "success that removed nothing" this replaces,
inverted — and F4 proved the loop could do exactly that after its first failure.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from host_repo import LOGIN, git, host_repo, seed_state, written
from prune_fixture import MISSING, cockpit, log_of, merged_lane, pr, prune, run_script


class ProvenMergeRemovesTheThread(unittest.TestCase):
    def test_the_lane_leaves_open_and_its_verdict_lands_in_the_session_log(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        out = prune(repo, pr({"head": head, "merge": merge}), "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertNotIn("feat/b", body, "closing means removing")
        self.assertIn("feat/a", body, "a thread citing nothing is never a candidate")
        self.assertIn("feat/b", log_of(repo).read_text(), "the verdict follows the thread")
        self.assertIn("MERGED", log_of(repo).read_text())

    def test_the_session_log_only_grows(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        before = log_of(repo).read_text()
        prune(repo, pr({"head": head, "merge": merge}), "--apply")
        after = log_of(repo).read_text()
        self.assertTrue(after.startswith(before), "the log is append-only, never rewritten")
        self.assertGreater(len(after), len(before), "the verdict is written down, not implied")
        self.assertEqual(after.count("## "), before.count("## "), "entries never decrease")

    def test_the_todo_row_moves_to_completed(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        prune(repo, pr({"head": head, "merge": merge}), "--apply")
        done = (repo / "_polaris" / "state" / "todos.md").read_text().split("## Completed")[1]
        self.assertIn("`feat/b`", done)

    def test_without_apply_it_only_reports(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        out = prune(repo, pr({"head": head, "merge": merge}))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("PROVEN=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())


class ASilentTrackerBlocksEverything(unittest.TestCase):
    """gh absent, erroring, rate-limited or answering nothing: no removal, exit 2, named line."""

    def test_a_tracker_error_names_the_line_and_removes_nothing(self):
        repo = host_repo()
        out = prune(repo, {"pr": {"77": "__error__"}, "issue": {"77": "__error__"}}, "--apply")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("BLOCKED=", out.stdout)
        self.assertIn("feat/b", out.stdout, "the refusal must name the line it could not resolve")
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_one_blocked_candidate_blocks_the_provable_one_too(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = cockpit(repo)
        written(path, "- `feat/c` (acme-api) — chiude #79 · since 2026-09-03")
        scenario = pr({"head": head, "merge": merge})
        scenario["pr"]["79"] = "__error__"
        scenario["issue"] = {"79": "__error__"}
        out = prune(repo, scenario, "--apply")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("BLOCKED=", out.stdout)
        self.assertIn("PROVEN=", out.stdout, "the provable one is still reported, just not applied")
        self.assertIn("feat/b", path.read_text(), "fail-closed: a partial prune is not a prune")

    def test_no_gh_at_all_is_a_refusal_not_a_pass(self):
        repo = host_repo()
        out = run_script("end", "prune_threads.py", str(cockpit(repo)), "--log", str(log_of(repo)),
                         "--owner", LOGIN, "--now", "2026-09-04", "--apply",
                         cwd=str(repo), env={"PATH": "/nonexistent", "HOME": str(repo.parent)})
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("BLOCKED=", out.stdout, "an absent tracker is a refusal with a reason")
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())


class OneFailedCloseDoesNotSilenceTheRest(unittest.TestCase):
    """F4 — `bad = bad or (...)` short-circuited the loop after the first failure."""

    def test_every_proven_row_gets_its_own_outcome(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = cockpit(repo)
        # two lines share a lane id, so the closer refuses that one — and must not eat the next
        path.write_text(path.read_text().replace(
            "- `feat/b` (acme-api) — chiude #77 · since 2026-09-02",
            "- `feat/b` (acme-api) — chiude #77 · since 2026-09-02\n"
            "- `feat/b` (acme-api) — doppia · since 2026-09-02\n"
            "- `feat/c` (acme-api) — chiude #77 · since 2026-09-02"))
        out = prune(repo, pr({"head": head, "merge": merge}), "--apply")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("feat/c", out.stdout, "the last PROVEN row must be reported, not skipped")
        self.assertNotIn("feat/c", path.read_text(), "and it must actually be closed")
        self.assertIn("feat/b", path.read_text(), "the ambiguous lane stays")


class TheScriptChecksItself(unittest.TestCase):
    def test_selfcheck_is_a_real_check(self):
        out = run_script("end", "prune_threads.py", "--selfcheck")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

if __name__ == "__main__":
    unittest.main()
