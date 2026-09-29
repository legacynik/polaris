"""A qualified h2 IS the section — `## Active Priorities — l'ordine del lavoro`.

polaris#43 narrowed the heading to the whole-line h2 so an `### Active Priorities` elsewhere could
not be taken for the order. It narrowed too far: the vault's own cockpit heads the section with a
qualifier, the script did not recognise it, and on its first real run it ADDED a second section
before `## Open` (2026-09-24). The level stays exact; the qualifier the registry allows everywhere
else is allowed here too. Break: require the bare heading again.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from host_repo import run_script

VAULT = """Updated: 2026-09-24 — @acme-dev

## Active Priorities — l'ordine del lavoro

1. vecchio ordine

## Open — thread vivi

- `main` — lane
"""


class AQualifiedHeadingIsTheSection(unittest.TestCase):
    def test_the_qualified_h2_is_rewritten_and_no_second_section_is_added(self):
        path = Path(tempfile.mkdtemp(prefix="prio-q-")) / "current.md"
        path.write_text(VAULT)
        done = run_script("update", "state_priorities.py", "set", str(path), "--now", "2026-09-24",
                          input="#11 nuovo\n")
        text = path.read_text()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(text.count("Active Priorities"), 1, text)
        self.assertNotIn("vecchio ordine", text)
        self.assertIn("## Active Priorities — l'ordine del lavoro\n\n<!-- pol:priorities", text)


if __name__ == "__main__":
    unittest.main()
