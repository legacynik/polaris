"""Gate round 2, F1/F2/F5 — the registry applies to EVERY script, or it applies to nothing.

F1: `state_upsert` read the registry while `state_close`, `todos_roll` and `prune_threads` kept
their own regexes, so the four disagreed about the same file. On a `todos.md` headed
`## Active — settimana 36` — the qualified form the template's own contract invites — `/update`
wrote, `/start` counted, `plan-week` promoted nothing with rc 0 and no message, and `/end` refused
everything with `NO_SECTION`. The inverse on a cockpit headed `## Open threads`: `/update` refused
while `state_close` happily removed the line. Either all four act, or all four refuse.

F5: the qualifier accepted a separator glued to the name, so `## Open-source backlog` read as the
open-threads section. A qualifier now starts with whitespace.

F2: a section whose only content is a multi-line HTML comment took the new row INSIDE the comment,
because only the opening line was recognised as intro.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from host_repo import LOGIN, PKG, host_repo, run_script, seed_state, written

DUE = "| `feat/old` — dormant | 2026-01-01 | ctx |"
ROW = "| `feat/lane` — in volo | W36 | ctx |"


def todos_headed(repo: Path, active: str) -> Path:
    """The SHIPPED template with its `## Active` heading qualified the way a host heads it,
    one live row, and one follow-up whose Review Date has long passed."""
    path = seed_state(repo, "todos.md")
    body = (path.read_text().replace("## Active\n", f"{active}\n")
            .replace("| | | |\n\n---\n\n## Completed", f"{ROW}\n\n---\n\n## Completed")
            .replace("| Item | Review Date | Note |\n|------|-------------|------|\n| | | |",
                     "| Item | Review Date | Note |\n|------|-------------|------|\n" + DUE))
    path.write_text(body)
    return path


def cockpit_headed(repo: Path, open_heading: str) -> Path:
    """The SHIPPED cockpit template with its open-threads heading replaced."""
    path = seed_state(repo, "current.md")
    path.write_text(path.read_text().replace("## Open\n", f"{open_heading}\n")
                    .replace("`<branch>` (<repo>)", "`feat/lane` (acme-api)"))
    return path


def upsert_week(todos: Path) -> subprocess.CompletedProcess:
    return run_script("end", "state_upsert.py", "week", str(todos), "--week", "W36",
                      "--no-add", input=ROW + "\n")


def brief(repo: Path) -> subprocess.CompletedProcess:
    return run_script("start", "brief_signals.py", "--root", str(repo / "_polaris"),
                      "--current", str(repo / "_polaris" / "state" / "current.md"),
                      "--login", LOGIN, "--main-wt", str(repo), "--now", "2026-09-04")


def close(cockpit: Path, todos: Path | None) -> subprocess.CompletedProcess:
    args = ["close", str(cockpit), "--key", "feat/lane", "--owner", LOGIN, "--now", "2026-09-04"]
    return run_script("end", "state_close.py", *args, *(["--todos", str(todos)] if todos else []))


class FourScriptsOneRegistry(unittest.TestCase):
    """F1 — the same file reads the same way to `/update`, `/start`, `plan-week` and `/end`."""

    def test_a_qualified_active_heading_is_acted_on_by_all_four(self):
        repo = host_repo()
        todos = todos_headed(repo, "## Active — settimana 36")
        written(seed_state(repo, "current.md"), "- `feat/lane` (acme-api) — viva · since 2026-09-04")
        self.assertEqual(upsert_week(todos).returncode, 0, "/update refused the qualified section")
        self.assertIn("TODOS_ACTIVE=1", brief(repo).stdout, brief(repo).stdout)
        rolled = run_script("end", "todos_roll.py", str(todos), "--now", "2026-09-04")
        self.assertEqual(rolled.returncode, 0, rolled.stderr)
        self.assertIn("feat/old", todos.read_text().split("## Completed")[0],
                      "plan-week promoted the due follow-up nowhere")
        done = close(repo / "_polaris" / "state" / "current.md", todos)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_an_unrecognised_open_heading_is_refused_by_all_four(self):
        repo = host_repo()
        cockpit = cockpit_headed(repo, "## Open threads")
        before = cockpit.read_bytes()
        written = run_script("end", "state_upsert.py", "thread", str(cockpit),
                             "--owner", LOGIN, "--now", "2026-09-04", input="- `feat/x` — y\n")
        self.assertEqual(written.returncode, 2, written.stdout)
        removed = close(cockpit, None)
        self.assertEqual(removed.returncode, 2, removed.stdout)
        self.assertEqual(cockpit.read_bytes(), before, "a refusal still rewrote the cockpit")
        seen = run_script("end", "prune_threads.py", str(cockpit))
        self.assertNotIn("feat/lane", seen.stdout, "prune_threads read a section the writer cannot")

class QualifierNeedsWhitespace(unittest.TestCase):
    """F5 — a separator glued to the name is a different word, not a qualifier."""

    def test_a_glued_separator_is_not_a_qualified_name(self):
        import sys
        sys.path.insert(0, str(PKG / "skills" / "end" / "scripts"))
        from state_sections import heading
        for other in ("## Open-source backlog", "## Opened tickets", "## Open_threads"):
            self.assertIsNone(heading("## Open").match(other), other)
        for same in ("## Open", "## Open — thread vivi", "## Open (acme-api)", "## Open · lane"):
            self.assertTrue(heading("## Open").match(same), same)


class CommentOnlySection(unittest.TestCase):
    """F2 — the intro of a section is its whole comment block, not its first line."""

    def test_the_row_lands_after_the_closing_marker(self):
        repo = host_repo()
        cockpit = seed_state(repo, "current.md")
        cockpit.write_text("Updated: 2026-09-01 — @x\n\n## Open\n\n<!-- one lane per branch,\n"
                           "     closed only by /end -->\n\n## Recent Context\n")
        out = run_script("end", "state_upsert.py", "thread", str(cockpit), "--owner", LOGIN,
                         "--now", "2026-09-04", input="- `feat/lane` — viva\n")
        self.assertEqual(out.returncode, 0, out.stderr)
        body = cockpit.read_text()
        self.assertLess(body.index("-->"), body.index("- `feat/lane`"), body)


if __name__ == "__main__":
    unittest.main()
