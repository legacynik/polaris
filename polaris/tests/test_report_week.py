"""/report Step 0 — which week gets reported, computed by the block the skill ships.

The block is read out of `report/SKILL.md` with `skill_block` and run verbatim. What is asserted
is what it resolves for a given `WEEK_START`, never how the skill words the rule: the reason this
file exists is that a filename convention changed (ISO week to the week's Sunday) and the only
test of it was a substring that kept naming the old one.
"""
from __future__ import annotations

import datetime
import os
import subprocess
import unittest

from host_repo import skill_block

SHOW = '\nprintf "%s|%s|%s|%s\\n" "$WEEK" "$SINCE" "$UNTIL" "$PLANWEEK"\n'
NOTHING = "|||"


def run(script: str, week_start: str) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ["PATH"], "WEEK_START": week_start}
    return subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)


def resolved(week_start: str = "") -> str:
    """`WEEK|SINCE|UNTIL|PLANWEEK` as the shipped block leaves them in the shell."""
    return run(skill_block("week", "read WEEK SINCE UNTIL PLANWEEK") + SHOW, week_start).stdout.strip()


class AFinishedWeekIsResolved(unittest.TestCase):

    def test_a_sunday_names_the_report_its_window_and_the_plan_it_measures(self):
        # Sunday 19 July 2026: the window ends on Saturday 25, and the Monday inside it (20 July)
        # is in ISO week 30 — the label the plan was filed under.
        self.assertEqual(resolved("2026-07-19"), "2026-07-19|2026-07-19|2026-07-25|2026-W30")

    def test_a_week_across_new_year_measures_the_plan_of_the_year_its_monday_is_in(self):
        # Sunday 28 December 2025 starts a week whose Monday opens ISO 2026-W01: the report is
        # dated in 2025 and the plan it reads is filed under 2026.
        self.assertEqual(resolved("2025-12-28"), "2025-12-28|2025-12-28|2026-01-03|2026-W01")

    def test_with_no_argument_it_is_the_last_sunday_to_saturday_already_over(self):
        before = datetime.date.today()
        week, since, until, _plan = resolved().split("|")
        after = datetime.date.today()
        start, end = datetime.date.fromisoformat(since), datetime.date.fromisoformat(until)
        self.assertEqual(week, since)
        self.assertEqual(start.weekday(), 6, "the window opens on a Sunday")
        self.assertEqual((end - start).days, 6, "and closes on the Saturday after")
        # Over, and the most recent one that is: its Saturday is 1 to 7 days back. Both sides of
        # the call are accepted so a run across midnight cannot fail on the clock.
        self.assertTrue(any(1 <= (day - end).days <= 7 for day in (before, after)), until)


class AnythingElseIsRefused(unittest.TestCase):

    def test_a_start_that_is_not_a_sunday_resolves_nothing(self):
        self.assertEqual(resolved("2026-07-20"), NOTHING)       # a Monday

    def test_a_week_that_has_not_ended_resolves_nothing(self):
        today = datetime.date.today()
        ahead = today + datetime.timedelta(days=(6 - today.weekday()) % 7 + 7)   # a Sunday, 7+ days out
        self.assertEqual(ahead.weekday(), 6)
        self.assertEqual(resolved(ahead.isoformat()), NOTHING)

    def test_the_block_itself_fails_so_no_query_runs_on_an_empty_window(self):
        refused = run(skill_block("week", "read WEEK SINCE UNTIL PLANWEEK"), "2026-07-20")
        self.assertNotEqual(refused.returncode, 0, refused.stdout + refused.stderr)


if __name__ == "__main__":
    unittest.main()
