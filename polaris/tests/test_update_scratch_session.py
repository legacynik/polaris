"""polaris-os#536 — a checkpoint reads and stamps only ITS OWN session's scratch.

The stop hook writes one scratch file per session (`<date>-<sid12>.md`). The checkpoint script
used to take the newest file of the login, so on a machine with several panels it printed another
session's lines as this one's and moved the watermark in a file it did not own. `#89` capped the
foreign prefix of a then-shared file; it never selected a file, and its tests model one file.

Every case here builds the layout the hook really writes: several files, one per session, and the
foreign one modified LAST, which is the only order in which "the newest" is the wrong answer.
"""
from __future__ import annotations

import os
import time
import unittest
from datetime import date
from pathlib import Path

from host_repo import LOGIN, env_for, host_repo, run_script

MINE, OTHER = "aaaa1111-000", "bbbb2222-999"
FULL_UUID = "aaaa1111-0000-4000-8000-000000000000"   # what a harness hands over; the file keeps 12


def lane(repo: Path) -> Path:
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / "scratch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def scratch(repo: Path, sid: str, text: str) -> Path:
    path = lane(repo) / f"{date.today().isoformat()}-{sid}.md"
    path.write_text(f"## 10:00 [{sid}]\n- {text}\n", encoding="utf-8")
    return path


def two_panels(repo: Path) -> tuple[Path, Path]:
    """Mine first, the other panel's after: the foreign file is the newest one on disk."""
    mine = scratch(repo, MINE, "MINE own line")
    other = scratch(repo, OTHER, "OTHER foreign line")
    later = time.time() + 5
    os.utime(other, (later, later))
    return mine, other


def checkpoint(repo: Path, *args: str, sid: str = ""):
    env = {**env_for(repo), "POLARIS_SID": sid}
    return run_script("update", "checkpoint.sh", *args, cwd=str(repo), env=env)


def stamped(path: Path) -> bool:
    return "<!-- harvested" in path.read_text(encoding="utf-8")


class TheSessionOwnsItsScratch(unittest.TestCase):

    def test_the_slice_is_this_sessions_lines_even_when_another_panel_wrote_last(self):
        repo = host_repo()
        two_panels(repo)
        out = checkpoint(repo, "harvest-slice", MINE)
        self.assertIn("MINE own line", out.stdout)
        self.assertNotIn("OTHER", out.stdout, "another panel's text was returned as this session's")

    def test_the_watermark_lands_in_this_sessions_file_only(self):
        repo = host_repo()
        mine, other = two_panels(repo)
        out = checkpoint(repo, "harvest-done", sid=MINE)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(stamped(mine), "the session's own scratch was left unstamped")
        self.assertFalse(stamped(other), "the watermark moved in a file this session does not own")

    def test_a_full_session_uuid_finds_the_twelve_character_file(self):
        repo = host_repo()
        mine, other = two_panels(repo)
        checkpoint(repo, "harvest-done", sid=FULL_UUID)
        self.assertTrue(stamped(mine))
        self.assertFalse(stamped(other))

    def test_the_newest_line_of_a_long_session_is_never_cut_by_a_cap(self):
        """The cap of #89 skipped a foreign prefix. In a file that is all this session's, a cap by
        position drops the NEWEST lines, and harvest-done then marks them as read."""
        repo = host_repo()
        mine, _ = two_panels(repo)
        mine.write_text("\n".join([f"- riga {i}" for i in range(200)] + ["- ULTIMA riga"]) + "\n")
        out = checkpoint(repo, "harvest-slice", MINE)
        self.assertIn("ULTIMA riga", out.stdout)
        self.assertEqual(len(out.stdout.splitlines()), 201, "lines of this session were dropped")

    def test_prepare_names_this_sessions_file(self):
        repo = host_repo()
        mine, _ = two_panels(repo)
        out = checkpoint(repo, "prepare", sid=MINE)
        self.assertIn(f"SCRATCH={mine}", out.stdout)


class NoSessionIdNeverGuesses(unittest.TestCase):

    def test_several_candidates_and_no_id_read_nothing_and_stamp_nothing(self):
        repo = host_repo()
        mine, other = two_panels(repo)
        sliced = checkpoint(repo, "harvest-slice")
        done = checkpoint(repo, "harvest-done")
        self.assertEqual((sliced.returncode, done.returncode), (0, 0))
        self.assertNotIn("own line", sliced.stdout)
        self.assertNotIn("foreign line", sliced.stdout)
        self.assertFalse(stamped(mine) or stamped(other), "a file was stamped on a guess")
        said = sliced.stdout + sliced.stderr
        self.assertIn(mine.name, said, "the refusal must name the candidates")
        self.assertIn(other.name, said)

    def test_one_candidate_and_no_id_is_that_sessions_file(self):
        repo = host_repo()
        only = scratch(repo, MINE, "MINE own line")
        self.assertIn("MINE own line", checkpoint(repo, "harvest-slice").stdout)
        checkpoint(repo, "harvest-done")
        self.assertTrue(stamped(only))

    def test_an_id_that_names_no_file_does_not_fall_back_to_the_newest(self):
        repo = host_repo()
        mine, other = two_panels(repo)
        checkpoint(repo, "harvest-done", sid="cccc3333-777")
        self.assertFalse(stamped(mine) or stamped(other))

    def test_a_shorter_id_is_not_a_prefix_match(self):
        repo = host_repo()
        mine, other = two_panels(repo)
        checkpoint(repo, "harvest-done", sid="aaaa")
        self.assertFalse(stamped(mine) or stamped(other), "'aaaa' matched 'aaaa1111-000' by prefix")


class VerifyReadsTheSessionsWatermark(unittest.TestCase):

    def test_a_foreign_watermark_does_not_satisfy_this_sessions_harvest(self):
        repo = host_repo()
        _, other = two_panels(repo)
        other.write_text(other.read_text() + f"\n<!-- harvested: {date.today().isoformat()} 10:10 -->\n")
        later = time.time() + 9
        os.utime(other, (later, later))
        out = checkpoint(repo, "verify", sid=MINE)
        self.assertIn("scratch not harvested today", out.stdout + out.stderr,
                      "verify passed the harvest check on another session's watermark")


if __name__ == "__main__":
    unittest.main()
