"""GitHub holds few, human-ready deliveries; everything operational is a bead (model §4).

Observed: the loop and the gates filed every finding, follow-up and spike as a GitHub issue, and
the queue reached 419 open issues nobody could schedule. The filter: a GitHub issue only if a
human must schedule or approve it, it will not be done inside the current PR or phase, it carries
a "Come si prova" section and an `area:`, and it duplicates no open issue. These tests drive the
public CLI with the facts the agent holds; nothing is mocked and `bd` is never called.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "route.py"
DELIVERY = ["--human", "yes", "--in-current-work", "no", "--test-section", "yes",
            "--area", "pricing", "--dup", "none", "--src", "loop", "--kind", "finding"]


def run(*overrides, base=DELIVERY):
    """Run route.py on the delivery facts with `overrides` replacing single flags."""
    args = list(base)
    for flag, value in zip(overrides[::2], overrides[1::2]):
        if flag in args:
            args[args.index(flag) + 1] = value
        else:
            args += [flag, value]
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def route(*overrides):
    r = run(*overrides)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class Filter(unittest.TestCase):
    def test_a_delivery_meeting_all_four_conditions_is_a_github_issue(self):
        self.assertEqual(route()["route"], "github")

    def test_work_no_human_must_schedule_is_a_bead(self):
        out = route("--human", "no")
        self.assertEqual(out["route"], "beads")
        self.assertIn("no human", out["reason"])

    def test_work_done_inside_the_current_pr_or_phase_is_a_bead(self):
        out = route("--in-current-work", "yes")
        self.assertEqual(out["route"], "beads")
        self.assertIn("current PR or phase", out["reason"])

    def test_work_without_a_come_si_prova_section_is_a_bead(self):
        out = route("--test-section", "no")
        self.assertEqual(out["route"], "beads")
        self.assertIn("Come si prova", out["reason"])

    def test_work_without_an_area_is_a_bead(self):
        out = route("--area", "")
        self.assertEqual(out["route"], "beads")
        self.assertIn("area:", out["reason"])

    def test_a_duplicate_of_an_open_issue_is_not_filed_again(self):
        out = route("--dup", "812")
        self.assertEqual(out["route"], "beads")
        self.assertIn("#812", out["reason"])

    def test_every_failed_condition_is_named_on_one_line(self):
        out = route("--human", "no", "--area", "")
        self.assertIn("no human", out["reason"])
        self.assertIn("area:", out["reason"])
        self.assertNotIn("\n", out["reason"])

    def test_a_bead_carries_type_and_the_three_labels(self):
        out = route("--human", "no", "--type", "bug", "--src", "real-test", "--kind", "finding")
        self.assertEqual(out["next"],
                         "bd create '<title>' -t bug -l src:real-test,kind:finding,area:pricing")

    def test_a_bead_found_while_working_links_where_it_came_from(self):
        out = route("--in-current-work", "yes", "--from", "pol-41")
        self.assertIn("--deps discovered-from:pol-41", out["next"])


class Refusal(unittest.TestCase):
    """A fact the agent did not establish never counts as satisfied."""

    def test_a_duplicate_search_left_blank_is_refused_not_read_as_no_twin(self):
        for blank in ("", "#", "None", "?"):
            self.assertEqual(run("--dup", blank).returncode, 2, blank)

    def test_a_bead_without_src_and_kind_is_refused(self):
        r = run("--human", "no", base=DELIVERY[:-4])
        self.assertEqual(r.returncode, 2)
        self.assertIn("--src", r.stderr)


class Promotion(unittest.TestCase):
    def test_a_bead_that_meets_the_filter_is_promoted_and_linked_back(self):
        out = route("--bead", "pol-7")
        self.assertEqual(out["route"], "github")
        self.assertEqual(out["next"], "bd update pol-7 --external-ref 'gh#<N>'")

    def test_a_bead_that_fails_the_filter_stays_a_bead(self):
        out = route("--bead", "pol-7", "--test-section", "no")
        self.assertEqual(out["route"], "beads")
        self.assertIn("stays bead pol-7", out["reason"])
        self.assertNotIn("bd create", out["next"])


if __name__ == "__main__":
    unittest.main()
