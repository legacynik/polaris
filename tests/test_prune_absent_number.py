"""A number this repository does not have is an answer, not silence.

A lane written about work in another repository often cites that tracker's numbers bare (`#1104`).
`gh` answers those definitely — «Could not resolve to …» — and that used to be folded into the
same BLOCKED as a rate limit, so one such lane stopped the prune for every other lane, every
session. The lane stays, since nothing here proves its work landed; the run goes on.
"""
from __future__ import annotations

import unittest

from host_repo import host_repo, written
from prune_fixture import cockpit, prune


def scenario(answer: str) -> dict:
    return {"pr": {"1104": answer},
            "issue": {"1104": answer, "77": {"state": "CLOSED", "stateReason": "NOT_PLANNED"}}}


def pruned(answer: str):
    repo = host_repo()
    written(cockpit(repo), "- `feat/z` (acme-web) — mappa #1104 chiusa · since 2026-09-02")
    out = prune(repo, scenario(answer), "--apply")
    return out, (repo / "_polaris" / "state" / "current.md").read_text()


class AbsentNumberKeepsTheThreadAndTheRun(unittest.TestCase):
    def test_a_number_the_tracker_says_does_not_exist_lets_the_run_go_on(self):
        out, text = pruned("__missing__")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("feat/z", text)        # nothing proves it landed: it stays
        self.assertNotIn("feat/b", text)     # and the lane beside it is still pruned

    def test_a_tracker_that_does_not_answer_still_stops_the_run(self):
        out, text = pruned("__error__")
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("feat/z", text)
        self.assertIn("feat/b", text)        # fail-closed: nothing was removed


if __name__ == "__main__":
    unittest.main()
