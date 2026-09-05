"""What a REMOVAL touches in `## Open` — and what it must never touch.

Two findings with one root: a writer that scans `range(*span)` by hand instead of asking
`state_lines.kinds()` what each line is. `drop_placeholder` deleted a placeholder-shaped line
sitting inside a code fence (F6), and a closed thread left its indented child lines and its whole
fenced block orphaned under `## Open` (F5). `state_lines` states the invariant this file defends:
inside a fence NOTHING is structure, and a lane is the bullet plus what hangs under it.
"""
from __future__ import annotations

import unittest

from host_repo import host_repo, run_script, seed_state, written

PLACEHOLDER = "- `<branch>` (<repo>) — <state in one line> · since YYYY-MM-DD"


class TheTemplatePlaceholderLeaves(unittest.TestCase):
    """D3 — the example line the contract ships is scaffolding, not a live lane."""

    def test_one_upsert_leaves_one_thread_and_no_placeholder(self):
        repo = host_repo()
        path = seed_state(repo, "current.md")
        self.assertIn("`<branch>`", path.read_text(), "the template ships the example")
        written(path, "- `feat/a` (acme-api) — primo giro · since 2026-09-01")
        body = path.read_text()
        self.assertNotIn("`<branch>`", body, "the example must go on the first real write")
        threads = [ln for ln in body.split("## Recent Context")[0].splitlines()
                   if ln.startswith("- `")]
        self.assertEqual(threads, ["- `feat/a` (acme-api) — primo giro · since 2026-09-01"])

    def test_only_that_exact_line_goes(self):
        repo = host_repo()
        path = seed_state(repo, "current.md")
        path.write_text(path.read_text().replace(
            PLACEHOLDER, PLACEHOLDER + "\n- `<altro>` (<repo>) — quasi uguale · since 2026-09-01"))
        written(path, "- `feat/a` (acme-api) — primo giro · since 2026-09-01")
        after = path.read_text()
        self.assertNotIn("`<branch>`", after)
        self.assertIn("`<altro>`", after, "only the line the contract ships is recognised")

    def test_a_placeholder_inside_a_code_fence_is_documentation(self):
        """F6 — `state_lines` says nothing inside a fence is structure. This writer agreed once."""
        repo = host_repo()
        path = seed_state(repo, "current.md")
        path.write_text(path.read_text().replace(
            PLACEHOLDER, f"- `vivo` (acme-api) — lane viva · since 2026-09-01\n\n"
                         f"```md\n{PLACEHOLDER}\n```"))
        written(path, "- `feat/a` (acme-api) — primo giro · since 2026-09-01")
        after = path.read_text()
        self.assertIn(PLACEHOLDER, after, "a sample in a code block is documentation, not a lane")
        self.assertIn("- `vivo`", after)


class ClosingTakesTheWholeLane(unittest.TestCase):
    """F5 — «closing means REMOVING» is not «removing the first line»."""

    def cockpit(self, repo):
        path = seed_state(repo, "current.md")
        written(path, "- `feat/a` (acme-api) — da chiudere · since 2026-09-01")
        written(path, "- `feat/b` (acme-api) — viva · since 2026-09-02")
        body = path.read_text().replace(
            "- `feat/a` (acme-api) — da chiudere · since 2026-09-01",
            "- `feat/a` (acme-api) — da chiudere · since 2026-09-01\n"
            "  - sub: ripartire da tests/x.py\n"
            "```bash\npytest tests/x.py\n```")
        path.write_text(body)
        return path

    def test_the_child_lines_and_the_fence_go_with_the_thread(self):
        repo = host_repo()
        path = self.cockpit(repo)
        out = run_script("update", "state_close.py", "close", str(path), "--key", "feat/a",
                         "--owner", "acme-dev", "--now", "2026-09-03")
        self.assertEqual(out.returncode, 0, out.stderr)
        after = path.read_text()
        for residue in ("sub: ripartire", "pytest tests/x.py", "```bash"):
            self.assertNotIn(residue, after, f"{residue!r} orphaned under ## Open")
        self.assertIn("- `feat/b`", after, "the next lane is untouched")

    def test_the_lane_below_keeps_its_own_children(self):
        repo = host_repo()
        path = seed_state(repo, "current.md")
        written(path, "- `feat/a` (acme-api) — da chiudere · since 2026-09-01")
        written(path, "- `feat/b` (acme-api) — viva · since 2026-09-02")
        path.write_text(path.read_text().replace(
            "- `feat/b` (acme-api) — viva · since 2026-09-02",
            "- `feat/b` (acme-api) — viva · since 2026-09-02\n  - sub: non mia"))
        run_script("update", "state_close.py", "close", str(path), "--key", "feat/a",
                   "--owner", "acme-dev", "--now", "2026-09-03")
        self.assertIn("  - sub: non mia", path.read_text())


if __name__ == "__main__":
    unittest.main()
