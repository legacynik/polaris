"""/end Step 1 — is THIS repository memory-wired, before a line is remembered.

Observed, 2026-07-15: `polmem` installed globally and wired to another repository. `remember` run
in a repo with no journal of its own did not fail; it wrote this session into the other vault.
`command -v polmem` passes in exactly that state, so the check the skill ships has to look at the
repository and not at the binary. The shipped check is run here in that state.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from host_repo import host_repo, run_block

CHECK = "test -d .wiki/journal"


def a_polmem_that_resolves(repo: Path) -> dict:
    """A `polmem` on PATH that would accept anything — the dangerous half of the state."""
    shim = repo.parent / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "polmem").write_text("#!/bin/sh\nexit 0\n")
    (shim / "polmem").chmod(0o755)
    return {"PATH": f"{shim}:{os.environ['PATH']}"}


class TheCheckLooksAtTheRepository(unittest.TestCase):

    def test_a_repo_with_no_journal_is_reported_even_when_polmem_resolves(self):
        repo = host_repo()
        out = run_block("end", CHECK, repo, **a_polmem_that_resolves(repo))
        self.assertNotEqual(out.stdout.strip(), "", "nothing told the session to skip the line")

    def test_a_repo_with_its_own_journal_is_silent(self):
        repo = host_repo()
        (repo / ".wiki" / "journal").mkdir(parents=True)
        out = run_block("end", CHECK, repo, **a_polmem_that_resolves(repo))
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
