"""D5-D6 — `/end` is the only command that closes, and closing means REMOVING.

`polaris-os#202`: after `/end` the cockpit holds no closed thread and the working tree is clean.
`#240`: the session summary lives in `## Recent Context` (cap 5, newest first), `Updated:` carries
date and owner only, `Active` is never zeroed and `Added:` is never re-stamped.

Automatic removal of threads citing a merged PR stays PARKED (`polaris-os#268`): the merge truth
does not survive a branch deleted at merge. So `/end` lists candidates and removes nothing by
itself — that is asserted here, not assumed.
"""
from __future__ import annotations

import json
import unittest

from host_repo import host_repo, run_script, seed_state, written


def cockpit_of(repo):
    """The SHIPPED template, with two lanes placed by the SHIPPED writer."""
    path = seed_state(repo, "current.md")
    written(path, "- `feat/a` (acme-api) — primo giro · since 2026-09-01")
    written(path, "- `feat/b` (acme-api) — chiude #77 · since 2026-09-02")
    return path


def todos_of(repo):
    path = seed_state(repo, "todos.md")
    written(path, "| `feat/a` — primo giro | | x |", "W32")
    written(path, "| `feat/b` — chiude #77 | | y |", "W36")
    return path


def close(repo, key: str, *args: str):
    path, todos = cockpit_of(repo), todos_of(repo)
    return run_script("end", "state_close.py", "close", str(path), "--key", key,
                      "--todos", str(todos), "--owner", "acme-dev", "--now", "2026-09-03", *args)


class ClosingRemoves(unittest.TestCase):
    def test_a_closed_thread_leaves_open_and_lands_in_completed(self):
        repo = host_repo()
        out = close(repo, "feat/a")
        self.assertEqual(out.returncode, 0, out.stderr)
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        todos = (repo / "_polaris" / "state" / "todos.md").read_text()
        self.assertNotIn("feat/a", body, "closing means removing, not striking through")
        self.assertIn("feat/b", body, "another panel's live lane is untouched")
        done = todos.split("## Completed")[1]
        self.assertIn("| `feat/a` — primo giro | 2026-09-03 | x |", done)
        self.assertLess(done.index("| `feat/a`"), done.index("<!-- pol:state-contract -->"),
                        "the row must land INSIDE the Completed table, not below the rule")

    def test_active_is_never_zeroed_and_added_is_never_restamped(self):
        repo = host_repo()
        close(repo, "feat/a")
        active = (repo / "_polaris" / "state" / "todos.md").read_text().split("## Completed")[0]
        self.assertIn("| `feat/b` — chiude #77 | W36 | y |", active,
                      "the surviving row must come back byte-identical, stamp included")
        self.assertIn("| Task | Added | Context |", active, "the table survives the removal")

    def test_updated_collapses_to_date_and_owner(self):
        repo = host_repo()
        close(repo, "feat/a")
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        stamps = [ln for ln in body.splitlines() if ln.startswith("Updated:")]
        self.assertEqual(stamps, ["Updated: 2026-09-03 — @acme-dev"],
                         "one state line, date and owner only — the prose contract is not one")
        self.assertNotIn("YYYY-MM-DD", body.splitlines()[0],
                         "the template's placeholder stamp must be replaced, not kept")

    def test_an_unknown_key_refuses_instead_of_removing_something_else(self):
        repo = host_repo()
        out = close(repo, "feat/does-not-exist")
        self.assertEqual(out.returncode, 2)
        self.assertIn("feat/a", (repo / "_polaris" / "state" / "current.md").read_text())


class CandidatesStillOnlyLists(unittest.TestCase):
    """`candidates` stays read-only: the verdict is `prune_threads.py`'s job, not this one's."""

    def test_candidates_names_threads_citing_an_issue_and_removes_nothing(self):
        repo = host_repo()
        path = cockpit_of(repo)
        before = path.read_text()
        out = run_script("end", "state_close.py", "candidates", str(path))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("feat/b", out.stdout)
        self.assertNotIn("feat/a", out.stdout, "a thread citing nothing is not a candidate")
        self.assertEqual(path.read_text(), before, "candidates is read-only")

class RecentContextIsARing(unittest.TestCase):
    def test_five_newest_first_and_the_sixth_evicts_the_oldest(self):
        repo = host_repo()
        path = cockpit_of(repo)
        for n in range(1, 7):
            out = run_script("end", "recent_context.py", str(path),
                             "--entry", f"### 2026-09-0{n} — sessione {n}")
            self.assertEqual(out.returncode, 0, out.stderr)
        body = path.read_text()
        self.assertEqual(body.count("### 2026-09-0"), 5)
        self.assertNotIn("sessione 1", body, "the ring is capped at five")
        self.assertLess(body.index("sessione 6"), body.index("sessione 5"), "newest first")

    def test_the_same_entry_twice_does_not_grow_the_ring(self):
        repo = host_repo()
        path = cockpit_of(repo)
        for _ in range(2):
            run_script("end", "recent_context.py", str(path), "--entry", "### 2026-09-03 — una")
        self.assertEqual(path.read_text().count("sessione") + path.read_text().count("— una"), 1)

    def test_everything_outside_the_section_comes_back_byte_identical(self):
        repo = host_repo()
        path = cockpit_of(repo)
        head, tail = path.read_text().split("## Recent Context")
        run_script("end", "recent_context.py", str(path), "--entry", "### 2026-09-03 — una")
        after = path.read_text()
        self.assertTrue(after.startswith(head), "the head of the file was re-rendered")
        self.assertTrue(after.rstrip().endswith(tail.split("---", 1)[1].rstrip()),
                        "the contract below the rule was re-rendered")


class TheWeekRolls(unittest.TestCase):
    """D6 — Completed is the current week only; Follow-ups are what crosses weeks."""

    def rolled(self, repo):
        """A template todos file with two Completed rows and two follow-ups, one of them due."""
        path = todos_of(repo)
        body = path.read_text().replace("| *None* | | |",
                                        "| `old` — vecchia | 2026-08-10 | |\n"
                                        "| `new` — fresca | 2026-09-03 | |")
        path.write_text(body.replace("|------|-------------|------|\n| | | |",
                                     "|------|-------------|------|\n"
                                     "| riprendi #9 | 2026-08-24 | nota |\n"
                                     "| dopo | 2999-01-01 | |"))
        return path, run_script("end", "todos_roll.py", str(path), "--now", "2026-09-03")

    def test_last_weeks_completed_is_dropped_and_followups_survive(self):
        path, out = self.rolled(host_repo())
        self.assertEqual(out.returncode, 0, out.stderr)
        body = path.read_text()
        self.assertNotIn("vecchia", body)
        self.assertIn("fresca", body)
        self.assertIn("| W32 |", body, "Active is untouched by the roll")
        self.assertEqual(json.loads(out.stdout)["dropped"], 1)

    def test_a_followup_that_came_due_returns_to_active_with_the_week_it_came_due(self):
        """The template promises this and nothing implemented it (breaker F9)."""
        path, out = self.rolled(host_repo())
        body = path.read_text()
        active, later = body.split("## Completed")[0], body.split("## Follow-ups")[1]
        self.assertEqual(json.loads(out.stdout)["promoted"], 1)
        self.assertIn("| riprendi #9 | W35 | nota |", active, "stamped with the week it came due")
        self.assertNotIn("riprendi #9", later)
        self.assertIn("dopo", later, "a follow-up not yet due does not move")

    def test_selfcheck_is_a_real_check(self):
        for name in ("state_close.py", "recent_context.py", "todos_roll.py"):
            with self.subTest(script=name):
                out = run_script("end", name, "--selfcheck")
                self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
