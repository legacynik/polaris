"""`/end` closes abandoned work too, and names the uncited notes it cannot judge.

Measured on a product repo (2026-09-30): 38 lanes under `## Open`, 15 of them dead, and `/end`
closed none. A lane whose every citation is a PR closed without merge, or an issue closed as not
planned, is abandoned work: it leaves the cockpit as DEAD and lands in the session log, like a
PROVEN one. A lane citing nothing is not judged, but when it is older than 14 days `/end` prints
it as STALE so it cannot stay invisible. And `state_close --key #N` names the one lane citing #N.
"""
from __future__ import annotations

import unittest

from host_repo import LOGIN, host_repo, run_script, written
from prune_fixture import cockpit, log_of, prune


def closed_pr() -> dict:
    return {"pr": {"77": {"state": "CLOSED", "mergeCommit": None, "headRefOid": "a" * 40,
                          "headRefName": "feat/b"}}}


class AbandonedWorkLeavesTheCockpit(unittest.TestCase):
    def test_a_lane_whose_pr_closed_unmerged_is_closed_as_dead_and_logged(self):
        repo = host_repo()
        out = prune(repo, closed_pr(), "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())
        self.assertIn("DEAD", log_of(repo).read_text())

    def test_a_dead_citation_next_to_an_open_one_keeps_the_lane(self):
        repo = host_repo()
        written(cockpit(repo), "- `feat/c` (acme-api) — rifatto in #78 dopo #77 · since 2026-09-02")
        scenario = closed_pr()
        scenario["pr"]["78"] = {"state": "OPEN", "mergeCommit": None, "headRefOid": "c" * 40,
                                "headRefName": "feat/c"}
        prune(repo, scenario, "--apply")
        self.assertIn("feat/c", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_an_uncited_lane_older_than_14_days_is_named_stale(self):
        repo = host_repo()
        out = prune(repo, closed_pr(), "--now", "2026-09-30")   # feat/a is from 2026-09-01
        self.assertIn("STALE=", out.stdout)
        self.assertIn("feat/a", out.stdout.split("STALE=", 1)[1].splitlines()[0])


class StateCloseTakesAnIssueNumber(unittest.TestCase):
    def test_key_hash_n_closes_the_one_lane_citing_it(self):
        repo = host_repo()
        path = cockpit(repo)
        done = run_script("update", "state_close.py", "close", str(path), "--key", "#77",
                          "--owner", LOGIN, "--now", "2026-09-30",
                          "--todos", str(repo / "_polaris" / "state" / "absent.md"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("feat/b", path.read_text())


if __name__ == "__main__":
    unittest.main()
