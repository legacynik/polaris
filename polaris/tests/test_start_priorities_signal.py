"""/start says when the priorities in the cockpit are old — it never presents them as current.

The cockpit is the one view the founder reads, so an order ten days old (a product repository,
13/09 → 23/09) must reach the brief as a signal, not as today's priorities. Break: drop the
check from `brief_signals` and the brief is silent about an order nobody has written since.
"""
from __future__ import annotations

import unittest

from host_repo import host_repo, run_script, seed_state
from test_start_brief_signals import signals


class TheBriefNamesOldPriorities(unittest.TestCase):
    def test_an_order_written_ten_days_ago_is_named_and_a_fresh_one_is_silent(self):
        repo = host_repo()
        cockpit = seed_state(repo, "current.md")
        run_script("update", "state_priorities.py", "set", str(cockpit), "--now", "2026-09-13",
                   input="#11 domande → prod\n")
        self.assertIn("PRIORITIES_STALE=10d", signals(repo, "--now", "2026-09-23"))
        self.assertNotIn("PRIORITIES_STALE", signals(repo, "--now", "2026-09-15"))


if __name__ == "__main__":
    unittest.main()
