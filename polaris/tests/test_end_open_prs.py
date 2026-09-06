"""A PR left open at session end collides with the next lane — so /end says so, and stops there.

The rule is «whoever opens it, merges it». What it needs at session end is not a gate: it is the
list. A session that ends with three open PRs and no line saying WHY is the state nobody can
resume from, and the founder's call is explicit — this is a reminder, never a wall. So the
contract under test has two halves that pull against each other:

  1. it must name every open PR of this author, and say which ones already carry their reason
     in the cockpit;
  2. it must exit 0 in every branch — PRs open, no PRs, `gh` absent, `gh` refusing.

Every block is read out of the shipped `end/SKILL.md` with `skill_block` and run verbatim, so a
skill body that stops calling the command fails here instead of passing a grep.

    python3 -m pytest polaris/tests/test_end_open_prs.py -q
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from host_repo import PKG, host_repo, run_block, seed_state, skill_block, written

NEEDLE = "open-prs"


def tracker(repo: Path, scenario: dict) -> dict:
    """A `gh` on PATH that answers from a fixture instead of the network."""
    shim = repo.parent / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "gh").write_text(f'#!/bin/sh\nexec python3 "{PKG / "tests" / "fake_gh.py"}" "$@"\n')
    (shim / "gh").chmod(0o755)
    return {"PATH": f"{shim}:{os.environ['PATH']}", "POLARIS_FAKE_GH": json.dumps(scenario)}


def no_gh(_: Path) -> dict:
    """A PATH that still has a shell, a git and a python but no `gh` — the machine that
    never installed it. Emptying PATH entirely would only prove that `bash` was missing."""
    return {"PATH": "/usr/bin:/bin"}


def listing(*prs: tuple[int, str, str]) -> dict:
    return {"pr_list": [{"number": n, "headRefName": b, "title": t} for n, b, t in prs]}


TWO = listing((41, "feat/a", "il primo giro"), (42, "feat/b", "l altra lane"))


class ItListsAndNeverRefuses(unittest.TestCase):
    def prepared(self, rows: tuple[str, ...] = ()) -> Path:
        repo = host_repo()
        cockpit = seed_state(repo, "current.md")
        for row in rows:
            written(cockpit, row)
        return repo

    def test_every_open_pr_is_named_and_the_command_exits_zero(self):
        repo = self.prepared()
        done = run_block("end", NEEDLE, repo, **tracker(repo, TWO))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("#41", done.stdout)
        self.assertIn("#42", done.stdout)

    def test_a_pr_without_its_reason_is_flagged_as_missing(self):
        repo = self.prepared()
        done = run_block("end", NEEDLE, repo, **tracker(repo, TWO))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for line in done.stdout.splitlines():
            if line.startswith("OPEN_PR=#4"):
                self.assertIn("MANCA", line)

    def test_a_pr_already_carrying_its_reason_is_not_flagged(self):
        repo = self.prepared(("- `feat/a` — aperta apposta: aspetta la firma · #41 · since 2026-09-05",))
        done = run_block("end", NEEDLE, repo, **tracker(repo, TWO))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        named = {line.split()[0]: line for line in done.stdout.splitlines()
                 if line.startswith("OPEN_PR=#")}
        self.assertIn("PRESENTE", named["OPEN_PR=#41"])
        self.assertIn("MANCA", named["OPEN_PR=#42"])

    def test_a_number_inside_a_longer_one_is_not_a_reason(self):
        """`#412` in the cockpit does not excuse `#41` — the cheap grep this replaces."""
        repo = self.prepared(("- `feat/z` — tocca #412 · since 2026-09-05",))
        done = run_block("end", NEEDLE, repo, **tracker(repo, TWO))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        named = {line.split()[0]: line for line in done.stdout.splitlines()
                 if line.startswith("OPEN_PR=#")}
        self.assertIn("MANCA", named["OPEN_PR=#41"])

    def test_no_open_pr_says_zero_and_exits_zero(self):
        repo = self.prepared()
        done = run_block("end", NEEDLE, repo, **tracker(repo, listing()))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("OPEN_PRS=0", done.stdout)


class ItDegradesInsteadOfBlocking(unittest.TestCase):
    def test_a_machine_without_gh_gets_one_line_and_exit_zero(self):
        repo = host_repo()
        seed_state(repo, "current.md")
        done = run_block("end", NEEDLE, repo, **no_gh(repo))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("OPEN_PRS=unknown", done.stdout)

    def test_a_tracker_that_refuses_gets_one_line_and_exit_zero(self):
        repo = host_repo()
        seed_state(repo, "current.md")
        done = run_block("end", NEEDLE, repo, **tracker(repo, {"pr_list": "__error__"}))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("OPEN_PRS=unknown", done.stdout)


class TheSkillReallyNamesIt(unittest.TestCase):
    def test_the_shipped_end_body_carries_exactly_one_such_block(self):
        """`skill_block` raises when the skill names the command zero times or twice."""
        self.assertIn(NEEDLE, skill_block("end", NEEDLE))

    def test_the_cockpit_path_the_reminder_points_at_is_the_resolved_one(self):
        repo = host_repo()
        seed_state(repo, "current.md")
        done = run_block("end", NEEDLE, repo, **tracker(repo, TWO))
        self.assertIn(str(repo / "_polaris" / "state" / "current.md"), done.stdout)


if __name__ == "__main__":
    unittest.main()
