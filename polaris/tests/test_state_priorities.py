"""`## Active Priorities` lives in the cockpit and one door writes it: /end, through one script.

Founder, 2026-09-23: «voglio current.md vivo — uso solo current, goals e todo», no external
pointer. Before this no door owned the section (/update wrote `## Open`, /end `## Recent Context`),
so on a product repository the priorities stayed at 13/09 for ten days. That day's hand edit also
found the heading with an unanchored `s.index`, matched a backtick MENTION of it in the prose, and
fused the new heading into the sentence. Break (each test names its own): write by string index,
touch anything outside the section, skip the date stamp.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from host_repo import run_script

MENTION = "Nota: il vecchio cockpit (`## Active Priorities` assente) è in archivio."
OPEN = "- `main` (acme-api) — lane viva · since 2026-09-20"
COCKPIT = f"""Updated: 2026-09-23 — @acme-dev

{MENTION}

## Active Priorities

1. vecchia priorità del 13/09

## Open — thread vivi

{OPEN}

<!-- pol:state-contract -->
"""


def cockpit(body: str = COCKPIT) -> Path:
    path = Path(tempfile.mkdtemp(prefix="prio-")) / "current.md"
    path.write_text(body)
    return path


def put(path: Path, *items: str, now: str = "2026-09-23"):
    return run_script("end", "state_priorities.py", "set", str(path), "--now", now,
                      input="\n".join(items) + "\n")


def check(path: Path, now: str):
    return run_script("end", "state_priorities.py", "check", str(path), "--now", now)


class EndWritesThePriorities(unittest.TestCase):
    def test_the_real_heading_is_rewritten_and_a_backtick_mention_is_left_alone(self):
        path = cockpit()
        done = put(path, "#11 domande → prod", "#12 step 1 pareti")
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = path.read_text().splitlines()
        self.assertIn(MENTION, lines)
        self.assertEqual([ln for ln in lines if ln.startswith("## Active Priorities")],
                         ["## Active Priorities"])
        body = lines[lines.index("## Active Priorities") + 1:lines.index("## Open — thread vivi")]
        self.assertEqual([ln for ln in body if ln[:1].isdigit()],
                         ["1. #11 domande → prod", "2. #12 step 1 pareti"])

    def test_everything_outside_the_section_is_byte_identical_and_a_rerun_changes_nothing(self):
        path = cockpit()
        put(path, "#11 domande → prod")
        once = path.read_text()
        put(path, "#11 domande → prod")
        self.assertEqual(path.read_text(), once)
        self.assertIn("\n1. #11 domande → prod\n", once)  # it wrote, or identity proves nothing
        self.assertTrue(once.startswith(f"Updated: 2026-09-23 — @acme-dev\n\n{MENTION}\n"), once)
        self.assertIn(f"## Open — thread vivi\n\n{OPEN}\n\n<!-- pol:state-contract -->", once)

    def test_a_cockpit_without_the_heading_gets_it_before_open(self):
        path = cockpit(COCKPIT.replace("## Active Priorities\n\n1. vecchia priorità del 13/09\n\n", ""))
        put(path, "#11 domande → prod")
        lines = path.read_text().splitlines()
        self.assertLess(lines.index("## Active Priorities"), lines.index("## Open — thread vivi"))

    def test_check_names_priorities_older_than_seven_days_and_is_silent_otherwise(self):
        path = cockpit()
        put(path, "#11 domande → prod", now="2026-09-13")
        fresh, stale = check(path, "2026-09-19"), check(path, "2026-09-23")
        self.assertEqual((fresh.returncode, fresh.stdout.strip()), (0, ""), fresh.stderr)
        self.assertIn("PRIORITIES_STALE=10d", stale.stdout)


if __name__ == "__main__":
    unittest.main()
