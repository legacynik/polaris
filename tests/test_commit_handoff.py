"""L'handoff e' la cosa piu' preziosa della sessione, e `/update` non lo committava.

DB-FR-07 lo vieta esplicitamente: *«no durable information may depend on `/end`, because the
founder does not reliably end sessions»*. Misurato il 2026-09-05 su una sessione reale: l'handoff
prioritario scritto da `/update` e' rimasto untracked, e senza un commit a mano sarebbe morto li'.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from commit_fixture import checkpoint_commit, landed_names, session_log
from host_repo import LOGIN, host_repo

TODAY = date.today().isoformat()


def handoff(repo: Path, text: str = "# Handoff\nNext: lancia il workflow\n") -> Path:
    p = repo / "_polaris" / "team" / LOGIN / "handoff" / f"{TODAY}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


class TheHandoffLandsWithTheLog(unittest.TestCase):

    def test_todays_handoff_is_committed_by_a_plain_checkpoint(self):
        repo = host_repo()
        session_log(repo)
        handoff(repo)
        done = checkpoint_commit(repo)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertIn(f"{TODAY}.md",
                      " ".join(n for n in landed_names(repo) if "handoff" in n),
                      "l'handoff di oggi non e' atterrato: dipende ancora da /end")

    def test_an_absent_handoff_is_not_an_error(self):
        repo = host_repo()
        session_log(repo)
        done = checkpoint_commit(repo)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertTrue(any("sessions" in n for n in landed_names(repo)))

    def test_yesterdays_handoff_is_not_dragged_in(self):
        """Un handoff vecchio appartiene alla sessione che lo ha scritto, non a questa."""
        repo = host_repo()
        session_log(repo)
        old = repo / "_polaris" / "team" / LOGIN / "handoff" / "2026-01-01.md"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("# vecchio\n")
        checkpoint_commit(repo)
        self.assertNotIn("2026-01-01.md", " ".join(landed_names(repo)))


if __name__ == "__main__":
    unittest.main()
