"""polaris#40 round 1 — WHERE the seat is, and what the three doors do when it is not there.

The seat is the one thing every reader agrees on or nothing works: the pack is compiled
against the checkout (`emit_pack` hands the compiler `git rev-parse --show-toplevel`), the
receipt is written beside the pack, and the dashboard looks for the session under the same
root it was given. A session written anywhere else is invisible to all three — the brief keeps
saying `RECEIPT: none` and the reinsertion keeps saying `NO_OPEN_SESSION`. So the invariant is
tested directly: the root the PACK sees must be a root where the session is.

The rest is what a deterministic sid does on a real day. Midnight rolls the sid over while the
session is still open; a panel closes without ever having opened; `/end` runs twice. None of
those may cost the handoff commit, and none may overwrite a receipt that already exists.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from host_repo import LOGIN, PKG, env_for, git, host_repo, run_script, skill_block
from test_start_opens_session import (CLOSE, ENGINE, OPEN, block, declaring,  # noqa: E501
                                      handoff, seat, sid_of, vault)

ECHO = "import sys\nprint('ROOT_SEEN: ' + sys.argv[sys.argv.index('--root') + 1])\n"


def with_echo(name: str):
    """A host repo whose declared vault answers the engine AND echoes another script's root."""
    repo = host_repo()
    home = vault(ENGINE)
    (home / "scripts" / name).write_text(ECHO)
    git(repo, "config", "polaris.vault", str(home))
    return repo


def root_seen(out: str) -> Path:
    rows = [line.split(": ", 1)[1] for line in out.splitlines() if line.startswith("ROOT_SEEN")]
    assert len(rows) == 1, f"expected exactly one ROOT_SEEN, got {rows}"
    return Path(rows[0])


def opened(repo: Path) -> str:
    return sid_of(block("start", OPEN, repo).stdout)


def close(repo: Path, **extra: str):
    return block("end", CLOSE, repo, **extra)


class TheSeatIsWhereEveryReaderLooks(unittest.TestCase):
    """F1 — one root for the pack, the receipt and the session, or the feature is invisible."""

    def test_the_pack_is_compiled_against_a_root_that_holds_the_session(self):
        repo = with_echo("contextpack_dashboard.py")   # $ROOT is _polaris/, the checkout is not
        sid = opened(repo)
        root = repo / "_polaris"
        signals = run_script("start", "brief_signals.py", "--root", str(root),
                             "--current", str(root / "state" / "current.md"),
                             cwd=str(repo), env={**env_for(repo), "POLARIS_VAULT": ""})
        home = root_seen(signals.stdout)
        self.assertTrue((home / "state" / "session" / sid / "start.json").is_file(),
                        f"the pack sees {home}, and the session is not there: the receipt of "
                        "the pack lands in a seat the dashboard will never read")

    def test_the_reinsertion_the_package_ships_reaches_that_same_seat(self):
        repo = with_echo("contextpack_reinsert.py")
        sid = opened(repo)
        done = subprocess.run(["bash", "-c", skill_block("start", "reinsert --root")],
                              cwd=str(repo), env={**env_for(repo), "POLARIS_VAULT": ""},
                              capture_output=True, text=True)
        self.assertTrue((root_seen(done.stdout) / "state" / "session" / sid / "start.json").is_file(),
                        "Step 3b asks for the pack back from a root with no session in it")

    def test_the_compaction_hook_reaches_it_too(self):
        """The hook is the only path that runs by itself, so a wrong root there is silent."""
        repo = with_echo("contextpack_reinsert.py")
        sid = opened(repo)
        template = json.loads((PKG / "skills" / "start" / "templates" / "settings.team.json")
                              .read_text())
        command = template["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        done = subprocess.run(["bash", "-c", command], cwd=str(repo), capture_output=True,
                              text=True, env={**env_for(repo), "POLARIS_VAULT": "",
                                              "CLAUDE_PROJECT_DIR": str(repo)})
        self.assertTrue((root_seen(done.stdout) / "state" / "session" / sid / "start.json").is_file(),
                        "after a compaction the hook asks the wrong root and reinserts nothing")

    def test_the_seat_never_shows_up_in_git_status(self):
        """F4 — receipts are ephemeral; a tree the session dirties blocks the commit gates."""
        repo = declaring()
        opened(repo)
        done = git(repo, "status", "--porcelain")
        self.assertEqual(done.stdout.strip(), "", "the session seat must ignore itself")


class TheDoorsSurviveARealDay(unittest.TestCase):
    """B1, F3 — midnight, a panel that never opened, and `/end` run twice."""

    def test_end_closes_the_session_that_is_open_when_the_sid_has_rolled_over(self):
        repo = declaring()
        sid = opened(repo)
        rolled = repo / "state" / "session" / f"{sid[:-7]}-ffffff"  # yesterday's derived seat
        (seat(repo, sid)).rename(rolled)
        handoff(repo)
        done = close(repo)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue((rolled / "end.json").is_file(),
                        "midnight rolled the sid and /end refused to close the open session")

    def test_end_with_nothing_open_says_so_and_lets_the_handoff_land(self):
        repo = declaring()
        handoff(repo)
        done = close(repo)
        self.assertEqual(done.returncode, 0, "no session is not a refusal — /end must go on")
        self.assertIn("SESSION: none open", done.stdout)

    def test_a_second_end_never_overwrites_the_receipt_it_already_wrote(self):
        repo = declaring()
        sid = opened(repo)
        handoff(repo)
        close(repo)
        before = (seat(repo, sid) / "end.json").stat().st_mtime_ns
        done = close(repo)
        self.assertEqual(done.returncode, 0)
        self.assertIn("SESSION: none open", done.stdout, "the second close must say what it did")
        self.assertEqual((seat(repo, sid) / "end.json").stat().st_mtime_ns, before,
                         "the close receipt was silently rewritten")

    def test_a_checkpoint_after_the_close_records_nothing(self):
        repo = declaring()
        sid = opened(repo)
        handoff(repo)
        close(repo)
        done = block("update", "session_gate.py", repo, ROOT=str(repo / "_polaris"))
        self.assertEqual(done.returncode, 0)
        self.assertFalse((seat(repo, sid) / "events.jsonl").is_file(),
                         "a closed session still collected a checkpoint")

    def test_a_start_after_the_close_opens_a_new_seat_instead_of_resuming_a_closed_one(self):
        repo = declaring()
        first = opened(repo)
        handoff(repo)
        close(repo)
        again = block("start", OPEN, repo)
        self.assertIn("SESSION: opened", again.stdout, "a closed session cannot be resumed")
        self.assertNotEqual(sid_of(again.stdout), first)


class TheHandoffIsReadBeforeAnythingElse(unittest.TestCase):
    """C1 — with no session open NONE of the seven refusals runs, so the one that does not
    need a session has to run here: a log that is not on disk is not a closed boundary."""

    def test_a_close_with_no_log_on_disk_refuses_even_with_no_session_open(self):
        repo = declaring()                      # no handoff(), so today's log does not exist
        done = close(repo)
        self.assertEqual(done.returncode, 1, "a missing log must stop /end, session or not")
        self.assertIn("HANDOFF_UNREADABLE", done.stdout + done.stderr)

    def test_a_close_whose_log_path_is_a_directory_refuses_too(self):
        repo = declaring()
        opened(repo)
        log = handoff(repo)
        log.unlink()
        log.mkdir()
        done = close(repo)
        self.assertEqual(done.returncode, 1)
        self.assertIn("HANDOFF_UNREADABLE", done.stdout + done.stderr)


class TheChainQuestionReachesTheSeat(unittest.TestCase):
    """C2 — `chain` had the root the reinsertion had: `$ROOT`, where no session ever is."""

    def test_the_chain_command_the_package_ships_asks_about_the_checkout(self):
        repo = with_echo("contextpack_reinsert.py")
        sid = opened(repo)
        done = subprocess.run(["bash", "-c", skill_block("start", "chain --root")],
                              cwd=str(repo), env={**env_for(repo), "POLARIS_VAULT": ""},
                              capture_output=True, text=True)
        self.assertTrue((root_seen(done.stdout) / "state" / "session" / sid).is_dir(),
                        "the chain is verified against a root with no session in it")


CRASHES = "import sys\nraise SystemError('EPERM: state/session is not writable')\n"


class TheCauseIsTheCause(unittest.TestCase):
    """B2 — `Traceback (most recent call last):` is not a cause, it is the word before one."""

    def test_a_crashing_engine_reports_what_it_said_not_the_traceback_header(self):
        repo = declaring(CRASHES)
        done = block("start", OPEN, repo)
        self.assertEqual(done.returncode, 0)
        self.assertIn("SESSION: blocked", done.stdout)
        self.assertNotIn("Traceback", done.stdout)
        self.assertIn("EPERM", done.stdout)


if __name__ == "__main__":
    unittest.main()
