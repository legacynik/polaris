"""/start keeps the founder's queue in front of him and says when the cockpit needs a rewrite.

The cockpit rots: priorities are rewritten only by /end, and the items that live ONLY in the
cockpit (an ok awaited, a key to rotate, a paused job, a deadline) are the ones a rewrite loses.
So the brief prints the top of `## Coda founder`, and one `COCKPIT_REWRITE` line when the file
has drifted. Every case runs the shipped `brief_signals.py` in a real host repo.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from host_repo import git, host_repo
from test_start_brief_signals import signals

NOW = date.today()


def day(offset: int) -> str:
    return (NOW + timedelta(days=offset)).isoformat()


def cockpit(items: list[str], *, stamp: str = "", updated: int = 1, queue: bool = True) -> str:
    """A cockpit in the shape the rewrite contract writes, fresh unless told otherwise."""
    head = "".join(f"Updated: {day(0)} — @ada\n" for _ in range(updated))
    body = (f"\n## Active Priorities\n\n<!-- pol:priorities updated={stamp or day(0)} -->\n"
            "1. #123 ship the importer\n\n")
    if queue:
        body += "## Coda founder · azioni non tracciate\n\n" + "".join(f"- {i}\n" for i in items)
    return head + body + "\n## Open\n\n- `feat/importer` (acme-api) — in review · since 2026-10-01\n"


def run(repo: Path, text: str | None = None, wt: Path | None = None, crlf: bool = False) -> list[str]:
    path = repo / "_polaris" / "state" / "current.md"
    if text is None:
        path.unlink()
    else:
        path.write_bytes(text.replace("\n", "\r\n" if crlf else "\n").encode("utf-8"))
    out = signals(repo, "--now", day(0), "--main-wt", str(wt or repo))
    return [ln for ln in out.splitlines() if ln.startswith(("QUEUE", "COCKPIT_REWRITE"))]


def queue(lines: list[str]) -> list[str]:
    return [ln for ln in lines if ln.startswith("QUEUE: ")]


NINE = [f"Firma il contratto fornitore · {day(-10)}, da handoff · tuo ok",
        f"Scegliere il piano hosting sì/no · {day(-12)}, da log · tua scelta",
        f"Ruotare la chiave API sandbox stampata in un log · {day(-5)}, da log · tuo giro",
        f"Job notturno in pausa in produzione · {day(-4)}, da log · tuo via libera",
        f"Bando regionale, consegna {day(1)} · {day(-3)}, da todos · tuo",
        f"Approva il nuovo listino · {day(-8)}, da log · tuo ok",
        f"Decidi se archiviare acme-web · {day(-9)}, da log · tua decisione",
        f"Password del pannello admin condivisa in chat · {day(-2)}, da log · cambiala",
        f"Rileggere la bozza del post · {day(-1)}, da log · tuo"]
FILLER = [f"Rileggere la nota {n} · {day(-20 + n)}, da log · tuo" for n in range(5)]


class TheQueueReachesTheBrief(unittest.TestCase):
    def test_no_cockpit_file_says_nothing(self):
        self.assertEqual(run(host_repo(), None), [])

    def test_a_cockpit_without_the_queue_asks_for_a_rewrite(self):
        lines = run(host_repo(), cockpit([], queue=False, stamp=day(-10)))
        self.assertEqual(queue(lines), [])
        rewrite = [ln for ln in lines if ln.startswith("COCKPIT_REWRITE: ")]
        self.assertEqual(len(rewrite), 1, lines)
        self.assertIn("no-queue", rewrite[0])
        self.assertIn("priorities-stale", rewrite[0])

    def test_security_and_deadlines_are_forced_and_the_rest_is_counted_by_kind(self):
        lines = run(host_repo(), cockpit(NINE))
        shown = queue(lines)
        self.assertEqual(len(shown), 5, lines)
        self.assertIn("Ruotare la chiave", shown[0])
        self.assertIn("Password del pannello", shown[1])
        self.assertIn("Bando regionale", shown[2])
        self.assertIn("Job notturno", shown[3])
        self.assertIn("piano hosting", shown[4])
        self.assertIn("QUEUE_MORE: +2 ok · +1 decisions · +1 other", lines)
        self.assertNotIn("COCKPIT_REWRITE", "\n".join(lines))

    def test_every_security_item_is_printed_even_beyond_five(self):
        keys = [f"Ruotare il token {n} del webhook · {day(-n)}, da log · tuo" for n in range(6)]
        shown = queue(run(host_repo(), cockpit(FILLER + keys)))
        self.assertEqual(len(shown), 6)
        self.assertTrue(all("token" in ln for ln in shown), shown)

    def test_a_deadline_eight_days_away_is_not_forced_but_seven_is(self):
        prod = [f"Servizio {n} bloccato in prod · {day(-n)}, da log · tuo" for n in range(5)]
        far = queue(run(host_repo(), cockpit(prod + [f"Bando, consegna {day(8)} · {day(0)}, da todos · tuo"])))
        near = queue(run(host_repo(), cockpit(prod + [f"Bando, consegna {day(7)} · {day(0)}, da todos · tuo"])))
        self.assertFalse(any("Bando" in ln for ln in far), far)
        self.assertTrue(any("Bando" in ln for ln in near), near)

    def test_keyword_markdown_and_prodotto_are_not_security_or_prod(self):
        decoy = f"Aggiornare le keyword del markdown e il download del prodotto · {day(0)}, da log · tuo"
        shown = queue(run(host_repo(), cockpit(FILLER + [decoy])))
        self.assertEqual(len(shown), 5)
        self.assertFalse(any("keyword" in ln for ln in shown), shown)

    def test_only_the_oldest_item_over_thirty_days_is_asked(self):
        old = [f"Vecchia richiesta A · {day(-40)}, da log · tuo",
               f"Vecchia richiesta B · {day(-50)}, da log · tuo"]
        asks = [ln for ln in run(host_repo(), cockpit(old + FILLER)) if ln.startswith("QUEUE_ASK")]
        self.assertEqual(len(asks), 1, asks)
        self.assertTrue(asks[0].startswith("QUEUE_ASK: keep or drop? Vecchia richiesta B"))

    def test_a_dormant_repo_costs_nothing(self):
        repo = host_repo()
        dead = Path(tempfile.mkdtemp(prefix="dead-")) / "acme-old"
        dead.mkdir()
        git(dead, "init", "-q", "-b", "main")
        env = {**os.environ, "GIT_COMMITTER_DATE": "2020-01-01T00:00:00",
               "GIT_AUTHOR_DATE": "2020-01-01T00:00:00"}
        subprocess.run(["git", "-C", str(dead), "-c", "user.email=t@t", "-c", "user.name=T",
                        "commit", "-q", "--allow-empty", "-m", "old"], env=env, check=True)
        self.assertEqual(run(repo, cockpit(NINE, updated=2, queue=True), wt=dead), [])

    def test_two_updated_lines_ask_for_a_rewrite(self):
        lines = run(host_repo(), cockpit(NINE, updated=2))
        self.assertTrue(any(ln.startswith("COCKPIT_REWRITE: ") and "updated-lines=2" in ln
                            for ln in lines), lines)

    def test_a_cockpit_over_eight_thousand_chars_asks_for_a_rewrite(self):
        lines = run(host_repo(), cockpit(NINE) + "\n" + "x" * 8000 + "\n")
        self.assertTrue(any(ln.startswith("COCKPIT_REWRITE: ") and "size=" in ln
                            for ln in lines), lines)

    def test_a_crlf_cockpit_reads_the_same_and_a_healthy_one_is_silent_on_rewrite(self):
        lines = run(host_repo(), cockpit(NINE), crlf=True)
        self.assertEqual(len(queue(lines)), 5, lines)
        self.assertFalse(any("\r" in ln for ln in lines))
        self.assertNotIn("COCKPIT_REWRITE", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
