"""polaris-os#538 — a checkpoint removes what the tracker already closed, and only that.

`/update` used to touch one line: its own lane. A panel that checkpoints and never reaches `/end`
therefore left the cockpit false: a lane whose pull request merged a day earlier still under
`## Open`, an issue already closed still second in `## Active Priorities`. `/end` already owns a
prover (`prune_threads`, `merge_truth`): it asks the tracker AND this checkout and removes nothing
when either is silent. `checkpoint.sh reconcile` runs that same prover at every checkpoint.

What stays with `/end` is closing by judgment. Here nothing is decided: a lane or a priority goes
only when every number it cites is proven closed, and one unreadable answer removes nothing.
"""
from __future__ import annotations

import json
import os
import unittest
from datetime import date
from pathlib import Path

from host_repo import LOGIN, PKG, env_for, git, host_repo, run_script
from prune_fixture import cockpit, merged_lane, pr, todos

STAMP = "<!-- pol:priorities updated=2026-09-01 -->"


def session_log(repo: Path) -> Path:
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / f"{date.today().isoformat()}-@{LOGIN}.md"
    path.write_text("## 10:00 — checkpoint · una voce\n- Files: x\n", encoding="utf-8")
    return path


def priorities(repo: Path, *items: str) -> Path:
    """The order as `/end` last wrote it, eight days of September ago: the stamp must survive."""
    path = cockpit(repo)
    done = run_script("update", "state_priorities.py", "set", str(path), "--now", "2026-09-01",
                      input="\n".join(items) + "\n")
    assert done.returncode == 0, done.stderr
    return path


def order(path: Path) -> list[str]:
    body = path.read_text(encoding="utf-8").split("## Active Priorities")[1].split("## Open")[0]
    return [ln.strip() for ln in body.splitlines() if ln.strip()]


def reconcile(repo: Path, scenario: dict, every: str = "0"):
    """`checkpoint.sh reconcile` with the fake tracker on PATH, as the skill body calls it.

    `every` is the throttle window in minutes; the cases that are not about it switch it off."""
    shim = repo.parent / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "gh").write_text(f'#!/bin/sh\nexec python3 "{PKG / "tests" / "fake_gh.py"}" "$@"\n')
    (shim / "gh").chmod(0o755)
    env = {**env_for(repo), "PATH": f"{shim}:{os.environ['PATH']}",
           "POLARIS_FAKE_GH": json.dumps(scenario)}
    if every:
        env["POLARIS_RECONCILE_EVERY"] = every
    else:
        env.pop("POLARIS_RECONCILE_EVERY", None)
    return run_script("update", "checkpoint.sh", "reconcile", cwd=str(repo), env=env)


class WhatTheTrackerClosedLeavesTheCockpit(unittest.TestCase):

    def proven(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        todos(repo)
        path = priorities(repo, "#77 chiudere la lane b", "scrivere la spec del modulo")
        return repo, path, session_log(repo), pr({"head": head, "merge": merge})

    def test_a_merged_lane_leaves_open_and_the_verdict_lands_in_the_log(self):
        repo, path, log, scenario = self.proven()
        out = reconcile(repo, scenario)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        body = path.read_text()
        self.assertNotIn("`feat/b`", body.split("## Open")[1], "the merged lane is still open")
        self.assertIn("`feat/a`", body, "a lane citing nothing is never a candidate")
        self.assertIn("feat/b", log.read_text(), "the verdict follows the lane into the log")

    def test_the_priority_citing_it_leaves_and_the_others_keep_text_and_order(self):
        repo, path, _, scenario = self.proven()
        out = reconcile(repo, scenario)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(order(path), [STAMP, "1. scrivere la spec del modulo"])
        self.assertIn("DROPPED=", out.stdout)

    def test_the_stamp_keeps_the_day_end_last_ordered_the_work(self):
        """Dropping a finished item is not re-ordering: /start must still call the order old."""
        repo, path, _, scenario = self.proven()
        reconcile(repo, scenario)
        check = run_script("update", "state_priorities.py", "check", str(path), "--now", "2026-09-20")
        self.assertIn("PRIORITIES_STALE=19d", check.stdout)

    def test_a_second_run_changes_nothing(self):
        repo, path, _, scenario = self.proven()
        reconcile(repo, scenario)
        before = path.read_bytes()
        reconcile(repo, scenario)
        self.assertEqual(path.read_bytes(), before)


class NothingIsRemovedOnAGuess(unittest.TestCase):

    def test_a_silent_tracker_removes_nothing_and_the_checkpoint_goes_on(self):
        repo = host_repo()
        merged_lane(repo)
        path = priorities(repo, "#77 chiudere la lane b", "scrivere la spec del modulo")
        session_log(repo)
        before = path.read_bytes()
        out = reconcile(repo, {"pr": {"77": "__error__"}, "issue": {"77": "__error__"}})
        self.assertEqual(out.returncode, 0, "a checkpoint must not die because the tracker is down")
        self.assertEqual(path.read_bytes(), before, "something was removed without proof")
        self.assertIn("nothing removed", out.stdout + out.stderr)

    def test_a_priority_citing_one_closed_and_one_open_item_stays(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = priorities(repo, "#77 e #78 vanno insieme", "scrivere la spec del modulo")
        session_log(repo)
        scenario = pr({"head": head, "merge": merge})
        scenario["issue"] = {"78": {"state": "OPEN", "stateReason": None}}   # #78 is an open issue
        reconcile(repo, scenario)
        self.assertIn("1. #77 e #78 vanno insieme", order(path))

    def test_a_priority_citing_nothing_is_never_touched(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = priorities(repo, "scrivere la spec del modulo", "parlare con il cliente")
        session_log(repo)
        reconcile(repo, pr({"head": head, "merge": merge}))
        self.assertEqual(order(path), [STAMP, "1. scrivere la spec del modulo", "2. parlare con il cliente"])

    def test_without_todays_entry_nothing_is_reconciled(self):
        """The verdicts are written to the session log; with no entry there is nowhere to put them."""
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = priorities(repo, "#77 chiudere la lane b")
        before = path.read_bytes()
        out = reconcile(repo, pr({"head": head, "merge": merge}))
        self.assertEqual(out.returncode, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_every_priority_proven_leaves_the_section_and_its_stamp(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = priorities(repo, "#77 chiudere la lane b")
        session_log(repo)
        out = reconcile(repo, pr({"head": head, "merge": merge}))
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(order(path), [STAMP])
        self.assertIn("## Open", path.read_text())


class AbandonedWorkWaitsForEnd(unittest.TestCase):
    """DEAD (closed as not planned, a PR closed unmerged) is a judgment about abandoned work. On a
    real cockpit two such lanes still carried a live warning in their prose: a checkpoint, which
    runs many times a day from every panel, removes only what is PROVEN done."""

    DEAD = {"issue": {"77": {"state": "CLOSED", "stateReason": "NOT_PLANNED"}}}

    def test_a_lane_and_a_priority_closed_as_not_planned_stay(self):
        repo = host_repo()
        path = priorities(repo, "#77 chiudere la lane b", "scrivere la spec del modulo")
        session_log(repo)
        before = path.read_bytes()
        out = reconcile(repo, self.DEAD)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(path.read_bytes(), before, "abandoned work was removed by a checkpoint")
        self.assertIn("/end", out.stdout, "the output must say who decides it")


class ACheckpointStaysCheap(unittest.TestCase):

    def test_only_removals_and_one_count_reach_the_output(self):
        """Measured on a real cockpit: 14 lanes printed in full at every checkpoint."""
        repo = host_repo()
        head, merge = merged_lane(repo)
        priorities(repo, "#77 chiudere la lane b")
        session_log(repo)
        out = reconcile(repo, pr({"head": head, "merge": merge})).stdout
        self.assertFalse([ln for ln in out.splitlines() if ln.startswith(("OPEN=", "AMBIGUOUS=", "STALE=", "NOTE="))])
        self.assertIn("1 removed", out)
        self.assertLessEqual(len(out.splitlines()), 6, out)

    def test_a_second_run_inside_the_window_asks_the_tracker_nothing(self):
        """Measured: 109 seconds for 13 lanes. Once per window is enough for every panel."""
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = priorities(repo, "#77 chiudere la lane b")
        session_log(repo)
        nothing = {"pr": {"77": {"state": "OPEN", "mergeCommit": None, "headRefOid": head, "headRefName": "feat/b"}}}
        reconcile(repo, nothing, every="")                       # the window opens here
        before = path.read_bytes()
        out = reconcile(repo, pr({"head": head, "merge": merge}), every="")
        self.assertEqual(path.read_bytes(), before, "the tracker was asked again inside the window")
        self.assertIn("skipped", out.stdout)

    def test_a_blocked_run_does_not_open_the_window(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = priorities(repo, "#77 chiudere la lane b")
        session_log(repo)
        reconcile(repo, {"pr": {"77": "__error__"}, "issue": {"77": "__error__"}}, every="")
        reconcile(repo, pr({"head": head, "merge": merge}), every="")
        self.assertNotIn("`feat/b`", path.read_text().split("## Open")[1],
                         "a run that learned nothing must not postpone the next one")


class TwoBranchesOneSessionLog(unittest.TestCase):
    """Every panel commits its log on the branch it sits on, so one day's file is born twice."""

    LOG = f"_polaris/team/{LOGIN}/sessions/2026-09-04-@{LOGIN}.md"
    RULE = "_polaris/team/*/sessions/*.md merge=union\n"

    def two_branches(self, attribute: bool) -> tuple[Path, int]:
        repo = host_repo()
        if attribute:
            (repo / ".gitattributes").write_text(self.RULE)
            git(repo, "add", ".gitattributes")
            git(repo, "commit", "-qm", "attributes")
        for branch, entry in (("lane-a", "## 10:00 — panel A\n"), ("lane-b", "## 11:00 — panel B\n")):
            git(repo, "switch", "-qc", branch, "main")
            (repo / self.LOG).parent.mkdir(parents=True, exist_ok=True)   # git drops an emptied dir
            (repo / self.LOG).write_text(entry)
            git(repo, "add", self.LOG)
            git(repo, "commit", "-qm", branch)
        git(repo, "switch", "-q", "main")
        git(repo, "merge", "-q", "--no-ff", "-m", "a", "lane-a")
        return repo, git(repo, "merge", "--no-ff", "-m", "b", "lane-b").returncode

    def test_with_the_union_attribute_both_entries_survive_and_nothing_conflicts(self):
        repo, code = self.two_branches(attribute=True)
        self.assertEqual(code, 0, "two panels' logs of one day conflicted")
        merged = (repo / self.LOG).read_text()
        self.assertIn("panel A", merged)
        self.assertIn("panel B", merged)
        self.assertNotIn("<<<<<<<", merged)

    def test_without_it_the_same_merge_conflicts(self):
        _, code = self.two_branches(attribute=False)
        self.assertNotEqual(code, 0, "the control must conflict, or the case above proves nothing")

    def test_prepare_says_when_the_repo_lacks_the_attribute_and_is_silent_when_it_has_it(self):
        repo = host_repo()
        env = env_for(repo)
        missing = run_script("update", "checkpoint.sh", "prepare", cwd=str(repo), env=env)
        self.assertIn("LOG_MERGE=missing", missing.stdout)
        self.assertIn("merge=union", missing.stdout, "the note must carry the line to add")
        (repo / ".gitattributes").write_text(self.RULE)
        present = run_script("update", "checkpoint.sh", "prepare", cwd=str(repo), env=env)
        self.assertIn("LOG_MERGE=union", present.stdout)


if __name__ == "__main__":
    unittest.main()
