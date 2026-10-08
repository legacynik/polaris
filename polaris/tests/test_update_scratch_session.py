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
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path

from host_repo import LOGIN, env_for, host_repo, run_script

MINE, OTHER = "aaaa1111-000", "bbbb2222-999"
FULL_UUID = "aaaa1111-0000-4000-8000-000000000000"   # what a harness hands over; the file keeps 12


def lane(repo: Path) -> Path:
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / "scratch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def at_noon(path: Path, seconds: int = 0, days: int = 0) -> Path:
    """Pin the mtime to today's noon (+seconds, -days): never `now`, which crosses midnight."""
    stamp = (datetime.combine(date.today(), time(12)) + timedelta(seconds=seconds, days=-days)).timestamp()
    os.utime(path, (stamp, stamp))
    return path


def scratch(repo: Path, sid: str, text: str, days_ago: int = 0, where: Path | None = None) -> Path:
    day = (date.today() - timedelta(days=days_ago)).isoformat()
    path = (where or lane(repo)) / f"{day}-{sid}.md"
    path.write_text(f"## 10:00 [{sid}]\n- {text}\n", encoding="utf-8")
    return at_noon(path, days=days_ago)


def legacy(repo: Path) -> Path:
    path = repo / "_polaris" / "sessions" / "scratch" / LOGIN
    path.mkdir(parents=True, exist_ok=True)
    return path


def two_panels(repo: Path) -> tuple[Path, Path]:
    """Mine first, the other panel's after: the foreign file is the newest one on disk."""
    mine = scratch(repo, MINE, "MINE own line")
    other = at_noon(scratch(repo, OTHER, "OTHER foreign line"), seconds=5)
    return mine, other


def marks(path: Path) -> int:
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("<!-- harvested: "))


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
        self.assertEqual(marks(mine), 1, "exactly one watermark, in the session's own file")
        self.assertEqual(marks(other), 0, "the watermark moved in a file this session does not own")

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
        at_noon(other, seconds=9)
        out = checkpoint(repo, "verify", sid=MINE)
        self.assertIn("scratch not harvested today", out.stdout + out.stderr,
                      "verify passed the harvest check on another session's watermark")


class ASessionCanOwnSeveralFiles(unittest.TestCase):
    """The hook names a file by the day it writes: a session alive across midnight has two, and the
    legacy lane can hold a third. All of them are this session's; none of their lines may be lost."""

    def spanning(self, repo: Path) -> tuple[Path, Path]:
        old = scratch(repo, MINE, "DAY1 harvested", days_ago=1)
        old.write_text(old.read_text() + "<!-- harvested: 2026-01-01 22:00 -->\n- DAY1 TAIL unharvested\n")
        at_noon(old, days=1)
        return old, scratch(repo, MINE, "DAY2 line")

    def test_the_tail_of_yesterdays_file_is_harvested_with_todays(self):
        repo = host_repo()
        self.spanning(repo)
        out = checkpoint(repo, "harvest-slice", MINE).stdout
        self.assertIn("DAY1 TAIL unharvested", out, "lines written before midnight were lost")
        self.assertIn("DAY2 line", out)
        self.assertNotIn("DAY1 harvested", out, "a line before the watermark was read twice")
        self.assertLess(out.index("DAY1 TAIL"), out.index("DAY2 line"), "the older file comes first")

    def test_after_done_nothing_of_the_session_is_left_unread(self):
        repo = host_repo()
        old, new = self.spanning(repo)
        checkpoint(repo, "harvest-done", sid=MINE)
        self.assertEqual((marks(old), marks(new)), (2, 1))
        self.assertEqual(checkpoint(repo, "harvest-slice", MINE).stdout.strip(), "")

    def test_the_older_file_touched_last_does_not_hide_todays(self):
        repo = host_repo()
        old, _ = self.spanning(repo)
        at_noon(old, seconds=30)
        self.assertIn("DAY2 line", checkpoint(repo, "harvest-slice", MINE).stdout)

    def test_the_legacy_lane_is_part_of_the_session(self):
        repo = host_repo()
        scratch(repo, MINE, "TEAM lane line")
        scratch(repo, MINE, "LEGACY lane line", where=legacy(repo))
        out = checkpoint(repo, "harvest-slice", MINE).stdout
        self.assertIn("TEAM lane line", out)
        self.assertIn("LEGACY lane line", out)

    def test_verify_fails_while_an_older_file_of_the_session_has_unread_lines(self):
        repo = host_repo()
        old, new = self.spanning(repo)
        new.write_text(new.read_text() + f"<!-- harvested: {date.today().isoformat()} 10:10 -->\n")
        out = checkpoint(repo, "verify", sid=MINE)
        self.assertIn("scratch not harvested today", out.stdout + out.stderr)

    def test_a_watermark_of_another_day_does_not_pass_verify(self):
        repo = host_repo()
        mine = scratch(repo, MINE, "riga")
        mine.write_text(mine.read_text() + "<!-- harvested: 2026-01-01 10:10 -->\n")
        out = checkpoint(repo, "verify", sid=MINE)
        self.assertIn("scratch not harvested today", out.stdout + out.stderr)


class OnlyTheHooksFilesCount(unittest.TestCase):

    def test_a_note_in_the_lane_is_not_a_candidate(self):
        """Real lanes hold `DISTILL-PROPOSAL-….md`: it must not block the single-file path."""
        repo = host_repo()
        only = scratch(repo, MINE, "MINE own line")
        note = lane(repo) / "DISTILL-PROPOSAL.md"
        note.write_text("una nota, non uno scratch\n")
        at_noon(note, seconds=9)
        self.assertIn("MINE own line", checkpoint(repo, "harvest-slice").stdout)
        checkpoint(repo, "harvest-done")
        self.assertEqual((marks(only), marks(note)), (1, 0))

    def test_a_name_that_only_ends_like_the_id_is_not_the_sessions_file(self):
        repo = host_repo()
        fake = lane(repo) / f"DISTILL-NOTE{MINE}.md"      # eleven characters, then the id
        fake.write_text("- FAKE\n")
        longer = lane(repo) / f"{date.today().isoformat()}-{MINE}-2.md"
        longer.write_text("- LONGER\n")
        out = checkpoint(repo, "harvest-slice", MINE).stdout
        self.assertNotIn("FAKE", out)
        self.assertNotIn("LONGER", out)

    def test_an_old_file_of_another_session_is_not_a_candidate_today(self):
        repo = host_repo()
        scratch(repo, OTHER, "OTHER yesterday", days_ago=1)
        only = scratch(repo, MINE, "MINE own line")
        self.assertIn("MINE own line", checkpoint(repo, "harvest-slice").stdout)
        checkpoint(repo, "harvest-done")
        self.assertEqual(marks(only), 1)

    def test_an_unknown_id_never_takes_the_only_file_of_today(self):
        repo = host_repo()
        other = scratch(repo, OTHER, "OTHER foreign line")
        out = checkpoint(repo, "harvest-slice", "cccc3333-777")
        checkpoint(repo, "harvest-done", sid="cccc3333-777")
        self.assertNotIn("OTHER", out.stdout)
        self.assertEqual(marks(other), 0)
        self.assertIn("cccc3333-777", out.stdout + out.stderr, "the refusal must name the id it was given")

    def test_a_line_that_quotes_the_marker_is_not_a_watermark(self):
        repo = host_repo()
        mine = scratch(repo, MINE, "IMPORTANT early line")
        mine.write_text(mine.read_text() + "- abbiamo discusso il bug di `<!-- harvested` ieri\n- later line\n")
        out = checkpoint(repo, "harvest-slice", MINE).stdout
        self.assertIn("IMPORTANT early line", out, "prose quoting the marker was read as a watermark")

    def test_verify_without_an_id_names_the_candidates_instead_of_passing_in_silence(self):
        repo = host_repo()
        mine, other = two_panels(repo)
        out = checkpoint(repo, "verify")
        self.assertIn(mine.name, out.stdout + out.stderr)

    def test_a_watermark_that_could_not_be_written_is_not_reported_as_moved(self):
        repo = host_repo()
        mine = scratch(repo, MINE, "riga")
        mine.chmod(0o444)
        try:
            out = checkpoint(repo, "harvest-done", sid=MINE)
        finally:
            mine.chmod(0o644)
        self.assertNotIn("watermark moved", out.stdout)
        self.assertEqual(out.returncode, 0, "a missing optional input never breaks a checkpoint")


if __name__ == "__main__":
    unittest.main()
