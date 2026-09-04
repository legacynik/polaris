"""D1-D3 — `/start` shows what the system already knows (polaris-os#243, #240, polaris#3).

Three signals exist today and nobody reads them: the legacy session-log spool, the drift of
the main worktree, and the sections a state file has lost. Two more surfaces landed with the
four-file donor form and no reader: `state/todos.md` and `## Recent Context`. And the typed
backbone must be used where a repo has one and be invisible where it does not.

Every case runs the shipped `start/scripts/brief_signals.py` in a real host repo.
"""
from __future__ import annotations

import json
import unittest
from datetime import date, timedelta

from host_repo import LOGIN, git, host_repo, run_script, seed_state


def signals(repo, *args: str) -> str:
    root = repo / "_polaris"
    out = run_script("start", "brief_signals.py", "--root", str(root),
                     "--current", str(root / "state" / "current.md"), *args, cwd=str(repo))
    assert out.returncode == 0, f"the brief must never fail a session:\n{out.stderr}"
    return out.stdout


class TodosReachTheBrief(unittest.TestCase):
    """D1 — `/start` reads the host repo's todos file, or says it is not there."""

    def test_active_rows_and_only_overdue_followups_are_named(self):
        repo = host_repo()
        todos = seed_state(repo, "todos.md")
        past = (date.today() - timedelta(days=2)).isoformat()
        soon = (date.today() + timedelta(days=9)).isoformat()
        todos.write_text("## Active\n\n- #11 — primo · Added: W32\n- #12 — secondo · Added: W36\n"
                         f"\n## Completed\n\n## Follow-ups\n\n- riprendi #9 · Review: {past}\n"
                         f"- non ancora · Review: {soon}\n")
        out = signals(repo)
        self.assertIn("TODOS_ACTIVE=2", out)
        self.assertIn("#11 — primo", out)
        self.assertIn("#12 — secondo", out)
        self.assertIn("FOLLOWUP_DUE=", out)
        self.assertIn("riprendi #9", out)
        self.assertNotIn("non ancora", out, "a follow-up not yet due is noise in the brief")

    def test_a_repo_without_todos_says_so_once_and_still_exits_zero(self):
        repo = host_repo()
        out = signals(repo)
        self.assertIn("TODOS=absent", out)
        self.assertNotIn("TODOS_ACTIVE=", out)

    def test_recent_context_entries_are_carried_newest_first(self):
        repo = host_repo()
        current = repo / "_polaris" / "state" / "current.md"
        current.write_text("Updated: 2026-09-03 — @acme-dev\n\n## Recent Context\n\n"
                           "### 2026-09-03 — terza\n\n### 2026-09-02 — seconda\n\n"
                           "### 2026-09-01 — prima\n")
        lines = [ln for ln in signals(repo).splitlines() if ln.startswith("RECENT=")]
        self.assertEqual([ln.split("=", 1)[1] for ln in lines][:2],
                         ["2026-09-03 — terza", "2026-09-02 — seconda"])


class TheThreeSignals(unittest.TestCase):
    """D2 — polaris-os#243: a line that always says zero teaches you to ignore it."""

    def test_a_legacy_spool_is_counted_only_when_it_holds_something(self):
        repo = host_repo()
        self.assertNotIn("SPOOL_LEGACY=", signals(repo))
        spool = repo / ".git" / "polaris-deferred"
        spool.mkdir()
        (spool / "a.md").write_text("x")
        (spool / "b.md").write_text("y")
        self.assertIn("SPOOL_LEGACY=2", signals(repo))

    def test_main_worktree_drift_is_named_off_default_and_silent_on_it(self):
        repo = host_repo()
        self.assertNotIn("DRIFT=", signals(repo), "a clean default branch has no drift to report")
        git(repo, "checkout", "-q", "-b", "reference/other-panel")
        for name in ("a.md", "b.md", "c.md"):
            (repo / name).write_text("foreign work\n")
        git(repo, "add", "-A")
        line = [ln for ln in signals(repo).splitlines() if ln.startswith("DRIFT=")]
        self.assertEqual(len(line), 1, "off the default branch the brief must name the drift")
        self.assertIn("reference/other-panel", line[0])
        self.assertIn("3", line[0])

    def test_missing_state_sections_are_named_and_a_complete_file_is_silent(self):
        repo = host_repo()
        current = repo / "_polaris" / "state" / "current.md"
        self.assertNotIn("SECTIONS_MISSING=", signals(repo), "the template is complete")
        current.write_text("Updated: 2026-09-03 — @acme-dev\n\n## Open\n\n- `a` — x\n")
        self.assertIn("Recent Context", [ln for ln in signals(repo).splitlines()
                                         if ln.startswith("SECTIONS_MISSING=")][0])

    def test_an_absent_state_file_invents_nothing(self):
        repo = host_repo()
        (repo / "_polaris" / "state" / "current.md").unlink()
        out = signals(repo)
        self.assertNotIn("SECTIONS_MISSING=", out)
        self.assertNotIn("RECENT=", out)


class TheBackboneIsFeatureDetected(unittest.TestCase):
    """D3 — with a typed backbone the brief carries the pack id; without one, nothing changes."""

    @staticmethod
    def _backbone(repo, *, emits=None, blocks=None):
        """A host repo carrying the REAL shapes: a manifest with no `pack_id` key (the live one
        has none) and a resolver that answers the declared CLI contract, not a stub file."""
        root = repo / "_polaris"
        (root / "decisions").mkdir()
        (root / "decisions" / "manifest.json").write_text(json.dumps(
            {"schema_version": 1, "repo": "host", "workspace": "w",
             "manifest_hash": "abc", "decisions": [], "live_documents": []}))
        (root / "scripts").mkdir()
        body = ("import json,sys\n"
                f"print(json.dumps({{'context_pack_id': {emits!r}}}))\n" if emits else
                f"import sys\nsys.stderr.write({blocks!r})\nsys.exit(1)\n")
        (root / "scripts" / "contextpack.py").write_text(body)
        return root

    def test_the_pack_id_comes_from_running_the_resolver_not_from_a_manifest_key(self):
        """The live manifest has NO `pack_id`: reading one means the signal is dead in every
        real repo while its fixture invents the field that makes it pass."""
        repo = host_repo()
        self._backbone(repo, emits="CTX-polaris-ee16119dd0cf")
        self.assertIn("PACK=CTX-polaris-ee16119dd0cf", signals(repo))

    def test_a_blocked_pack_is_loud_not_silent(self):
        """DB-FR-05: a blocked emission blocks. A silent empty line is indistinguishable from
        a repo that has no backbone at all."""
        repo = host_repo()
        self._backbone(repo, blocks="DECISION_SCOPE_STALE: docs/x.md\n")
        out = signals(repo)
        self.assertIn("PACK=BLOCKED", out)
        self.assertIn("DECISION_SCOPE_STALE", out)

    def test_a_repo_without_the_backbone_prints_no_pack_line_and_no_error(self):
        repo = host_repo()
        out = run_script("start", "brief_signals.py", "--root", str(repo / "_polaris"),
                         "--current", str(repo / "_polaris" / "state" / "current.md"),
                         cwd=str(repo))
        self.assertEqual(out.returncode, 0)
        self.assertNotIn("PACK=", out.stdout)
        self.assertEqual(out.stderr.strip(), "", "a missing backbone is not an error")


class TheSkillActuallyCallsIt(unittest.TestCase):
    def test_start_resolves_the_shipped_signals_script(self):
        from host_repo import skill_block
        self.assertIn("brief_signals.py", skill_block("start", "brief_signals.py"))

    def test_selfcheck_is_a_real_check(self):
        out = run_script("start", "brief_signals.py", "--selfcheck")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("OK", out.stdout)


if __name__ == "__main__":
    unittest.main()
