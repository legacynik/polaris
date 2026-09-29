"""Breaker on polaris#42 — three inputs that corrupted or silenced the order.

1. The heading matcher took ANY level: a `### Active Priorities` note inside another section was
   rewritten and its content deleted, while the real h2 kept its old order.
2. Input made only of list markers (`1.`, `2)`, `*`) passed as items and wiped the order.
3. A malformed stamp (`updated=2026-13-45`) made `/start` silent, which reads as fresh.
Break: match the shared any-level heading again, keep the whitespace-required marker regex, or
swallow the bad date.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from host_repo import run_script

H3_FIRST = """# S

## Open

- x

### Active Priorities
note under open

## Active Priorities

1. real
"""


def cockpit(body: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix="prio-b-")) / "current.md"
    path.write_text(body)
    return path


def put(path: Path, stdin: str):
    return run_script("update", "state_priorities.py", "set", str(path), "--now", "2026-09-24",
                      input=stdin)


class BreakerOnFortyTwo(unittest.TestCase):
    def test_only_the_h2_is_the_section_and_an_h3_elsewhere_is_untouched(self):
        path = cockpit(H3_FIRST)
        put(path, "#11 nuovo\n")
        text = path.read_text()
        self.assertIn("### Active Priorities\nnote under open\n", text)
        self.assertNotIn("1. real", text)
        self.assertIn("1. #11 nuovo", text)

    def test_input_made_only_of_markers_is_refused_and_nothing_is_written(self):
        path = cockpit(H3_FIRST)
        before = path.read_text()
        done = put(path, "1.\n2)\n*\n  \n")
        self.assertEqual((done.returncode, path.read_text()), (2, before), done.stdout)

    def test_a_malformed_stamp_is_named_not_silent(self):
        path = cockpit("## Active Priorities\n\n<!-- pol:priorities updated=2026-13-45 -->\n1. x\n")
        done = run_script("update", "state_priorities.py", "check", str(path), "--now", "2026-09-24")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("PRIORITIES_STALE=malformed", done.stdout)


if __name__ == "__main__":
    unittest.main()
