"""A citation qualified with ANOTHER repository's name is not this repository's issue.

`acme-web#77` used to be read as this repository's `#77`: whatever that number happened to be
here decided the lane. A lane tracking work in another repository was closed as DEAD because an
unrelated local issue was closed as not planned, and a number that did not exist here came back
BLOCKED and stopped the whole prune. This checkout cannot read the other tracker, so the only
honest answer is that the lane stays.
"""
from __future__ import annotations

import unittest

from host_repo import host_repo, written
from prune_fixture import cockpit, prune

NOT_PLANNED = {"issue": {"77": {"state": "CLOSED", "stateReason": "NOT_PLANNED"}}}


def with_foreign_lane(number: str):
    repo = host_repo()
    written(cockpit(repo), f"- `feat/x` (acme-web) — segue acme-web#{number} · since 2026-09-02")
    return repo


class ForeignCitationKeepsTheThread(unittest.TestCase):
    def test_a_local_issue_of_the_same_number_never_closes_it(self):
        repo = with_foreign_lane("77")
        out = prune(repo, NOT_PLANNED, "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        text = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertIn("feat/x", text)        # the other repository's lane stays
        self.assertNotIn("feat/b", text)     # this repository's `#77` lane still closes

    def test_a_number_unknown_here_does_not_block_the_run(self):
        repo = with_foreign_lane("1123")
        out = prune(repo, NOT_PLANNED, "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        text = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertIn("feat/x", text)
        self.assertNotIn("feat/b", text)


if __name__ == "__main__":
    unittest.main()
