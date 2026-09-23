"""`/start` carries no pack rows — the pack loads on entering a lane (founder, 2026-09-23).

Measured that day on three repositories, six fresh agents, /start with and without the pack:
identical briefs, +15% tokens, 0 of 131 `layer:` rows changed a brief, and one repository
stopped the brief to ask "which area?" for a pack nobody read. The resolver still runs, so a
blocked emission stays loud; its rows are counted in one line, never printed.
Break: print the resolver's lines verbatim again and the rows and the question are back.
"""
from __future__ import annotations

import unittest

from host_repo import git, host_repo
from test_start_brief_signals import brief_of, stub_vault

RESOLVER = ("print('AREA: memoria  issues: 3  prs: 1  last_decision: DEC-9')\n"
            "print('QUESTION: which area? candidates: docs, memoria')\n"
            "print('layer: declared  source_id: CONTEXT.md  path: CONTEXT.md  freshness: UNKNOWN')\n"
            "print('layer: flight  source_id: b  path: -  freshness: UNKNOWN')\n")


class StartCarriesNoPackRows(unittest.TestCase):
    def test_rows_and_the_area_question_are_counted_not_printed(self):
        repo = host_repo()
        git(repo, "config", "polaris.vault", str(stub_vault(RESOLVER)))
        lines = brief_of(repo).stdout.splitlines()
        self.assertEqual([ln for ln in lines if ln.startswith(("layer: ", "QUESTION:"))], [], lines)
        self.assertIn("PACK: 2 rows held for lane entry", lines)


if __name__ == "__main__":
    unittest.main()
