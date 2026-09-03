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

from host_repo import host_repo, run_script, seed_state

COCKPIT = ("Updated: 2026-09-01 — @acme-dev: ho fatto molte cose e le racconto qui in "
           "cinquanta parole, che e' esattamente il difetto\n\n"
           "## Active Priorities\n\n1. lane A\n\n## Open\n\n"
           "- `feat/a` (acme-api) — primo giro · since 2026-09-01\n"
           "- `feat/b` (acme-api) — chiude #77 · since 2026-09-02\n\n"
           "## Recent Context\n\n<!-- Last 5 session summaries, newest first -->\n")

TODOS = ("## Active\n\n- `feat/a` — primo giro · Added: W32\n"
         "- `feat/b` — chiude #77 · Added: W36\n\n"
         "## Completed\n\n## Follow-ups\n\n- riprendi #9 · Review: 2026-10-01\n")


def cockpit_of(repo):
    path = repo / "_polaris" / "state" / "current.md"
    path.write_text(COCKPIT)
    return path


def todos_of(repo):
    path = seed_state(repo, "todos.md")
    path.write_text(TODOS)
    return path


def close(repo, key: str, *args: str):
    path, todos = cockpit_of(repo), todos_of(repo)
    return run_script("update", "state_close.py", "close", str(path), "--key", key,
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
        self.assertIn("Completed: 2026-09-03", todos)
        self.assertIn("- `feat/a`", todos.split("## Completed")[1])

    def test_active_is_never_zeroed_and_added_is_never_restamped(self):
        repo = host_repo()
        close(repo, "feat/a")
        active = (repo / "_polaris" / "state" / "todos.md").read_text().split("## Completed")[0]
        self.assertIn("- `feat/b` — chiude #77 · Added: W36", active,
                      "the surviving row must come back byte-identical, stamp included")

    def test_updated_collapses_to_date_and_owner(self):
        repo = host_repo()
        close(repo, "feat/a")
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertEqual(body.count("Updated:"), 1)
        self.assertIn("Updated: 2026-09-03 — @acme-dev", body)
        self.assertNotIn("cinquanta parole", body,
                         "the session summary belongs to Recent Context, not to Updated:")

    def test_an_unknown_key_refuses_instead_of_removing_something_else(self):
        repo = host_repo()
        out = close(repo, "feat/does-not-exist")
        self.assertEqual(out.returncode, 2)
        self.assertIn("feat/a", (repo / "_polaris" / "state" / "current.md").read_text())


class TheParkedRemovalIsDeclared(unittest.TestCase):
    """polaris-os#268 — until merge truth survives a deleted branch, `/end` only lists."""

    def test_candidates_names_threads_citing_an_issue_and_removes_nothing(self):
        repo = host_repo()
        path = cockpit_of(repo)
        before = path.read_text()
        out = run_script("update", "state_close.py", "candidates", str(path))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("feat/b", out.stdout)
        self.assertNotIn("feat/a", out.stdout, "a thread citing nothing is not a candidate")
        self.assertIn("268", out.stdout, "the brief must say why removal is manual")
        self.assertEqual(path.read_text(), before, "candidates is read-only")

    def test_end_declares_the_manual_removal_in_its_body(self):
        from host_repo import PKG
        body = (PKG / "skills" / "end" / "SKILL.md").read_text()
        self.assertIn("268", body)
        self.assertIn("state_close.py", body)


class RecentContextIsARing(unittest.TestCase):
    def test_five_newest_first_and_the_sixth_evicts_the_oldest(self):
        repo = host_repo()
        path = cockpit_of(repo)
        for n in range(1, 7):
            out = run_script("update", "recent_context.py", str(path),
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
            run_script("update", "recent_context.py", str(path), "--entry", "### 2026-09-03 — una")
        self.assertEqual(path.read_text().count("sessione") + path.read_text().count("— una"), 1)

    def test_everything_outside_the_section_comes_back_byte_identical(self):
        repo = host_repo()
        path = cockpit_of(repo)
        head = COCKPIT.split("## Recent Context")[0]
        run_script("update", "recent_context.py", str(path), "--entry", "### 2026-09-03 — una")
        self.assertTrue(path.read_text().startswith(head))


class TheWeekRolls(unittest.TestCase):
    """D6 — Completed is the current week only; Follow-ups are what crosses weeks."""

    def test_last_weeks_completed_is_dropped_and_followups_survive(self):
        repo = host_repo()
        path = todos_of(repo)
        path.write_text(TODOS.replace("## Completed\n\n",
                                      "## Completed\n\n- `old` — vecchia · Completed: 2026-08-10\n"
                                      "- `new` — fresca · Completed: 2026-09-03\n"))
        out = run_script("update", "state_close.py", "week-roll", str(path), "--now", "2026-09-03")
        self.assertEqual(out.returncode, 0, out.stderr)
        body = path.read_text()
        self.assertNotIn("vecchia", body)
        self.assertIn("fresca", body)
        self.assertIn("riprendi #9", body, "Follow-ups are the only section crossing weeks")
        self.assertIn("Added: W32", body, "Active is untouched by the roll")
        self.assertEqual(json.loads(out.stdout)["dropped"], 1)

    def test_selfcheck_is_a_real_check(self):
        for name in ("state_close.py", "recent_context.py"):
            with self.subTest(script=name):
                out = run_script("update", name, "--selfcheck")
                self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
