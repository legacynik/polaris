"""polaris-os#155 — `/start` OPENS the session, `/update` checkpoints it, `/end` closes it.

Everything downstream already waits for an open session: the pack receipt (`area-<slug>.json`)
and the reinsertion after a compaction both print `NO_OPEN_SESSION` / `RECEIPT: none` because
no skill ever called the engine's `start`. These cases run the SHIPPED bash blocks of the three
skills, so a skill that stops calling the door fails here instead of passing a grep.

What is under test is the WIRING the package owns: one deterministic sid across the three
doors, the resolver found in the host and then in the declared vault, silence where no engine
exists, one line where the pack refuses, and the legacy `polaris.vault-root` still read once
with a warning. The engine itself is the vault's (`scripts/session_continuity.py`) and is
proven by its own `selfcheck` and fixtures — here it is a stub that holds the same contract:
`start.json` with a `pack_seal`, `SESSION_EXISTS` on the second start, an event chained to the
start receipt, an `end.json` that names it.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from host_repo import LOGIN, git, host_repo, run_block

ENGINE = r'''import json, sys
from pathlib import Path
argv = sys.argv[1:]
def flag(name, default=""):
    return argv[argv.index(name) + 1] if name in argv else default
cmd, root, sid = argv[0], Path(flag("--root")), flag("--sid")
seat = root / "state" / "session" / sid
start = seat / "start.json"
if cmd == "start":
    if start.is_file():
        sys.stderr.write("SESSION_EXISTS: sid %s already has a start receipt\n" % sid)
        sys.exit(2)
    seat.mkdir(parents=True, exist_ok=True)
    start.write_text(json.dumps({"phase": "start", "sid": sid, "pack_seal": "seal-" + sid,
                                 "receipt_hash": "rh-" + sid,
                                 "work_item": flag("--work-item")}))
    print(start.read_text())
    sys.exit(0)
if not start.is_file():
    sys.stderr.write("SESSION_UNKNOWN: %s\n" % sid)
    sys.exit(2)
rec = json.loads(start.read_text())
if cmd == "update":
    with (seat / "events.jsonl").open("a") as fh:
        fh.write(json.dumps({"phase": "update", "sid": sid, "prev": rec["receipt_hash"],
                             "note": flag("--note")}) + "\n")
    sys.exit(0)
if cmd == "end":
    if not flag("--handoff"):
        sys.stderr.write("HANDOFF_MISSING: no session log passed\n")
        sys.exit(2)
    if not Path(flag("--handoff")).is_file():
        sys.stderr.write("HANDOFF_UNREADABLE: %s\n" % flag("--handoff"))
        sys.exit(2)
    (seat / "end.json").write_text(json.dumps(
        {"phase": "end", "sid": sid, "chain": {"start_receipt": rec["receipt_hash"]}}))
    sys.exit(0)
sys.exit(2)
'''

REFUSES = ('import sys\nsys.stderr.write("CONTEXTPACK_INVALID: DECISION_SCOPE_STALE: x.md\\n")\n'
           'sys.exit(2)\n')


def vault(body: str = ENGINE) -> Path:
    """A throwaway vault carrying `scripts/session_continuity.py` and nothing else."""
    home = Path(tempfile.mkdtemp(prefix="pm-sc-")).resolve()
    (home / "scripts").mkdir()
    (home / "scripts" / "session_continuity.py").write_text(body)
    return home


def declaring(body: str = ENGINE, key: str = "polaris.vault"):
    """A host repo that declares a vault holding the engine under `key`."""
    repo = host_repo()
    git(repo, "config", key, str(vault(body)))
    return repo


def block(skill: str, needle: str, repo: Path, **extra: str):
    """One shipped bash block, run with the founder's own `$POLARIS_VAULT` neutralised."""
    return run_block(skill, needle, repo, POLARIS_VAULT="", **extra)


OPEN = 'session_gate.py" open'    # the shipped blocks quote the path
CLOSE = 'session_gate.py" close'


def seat(repo: Path, sid: str) -> Path:
    return repo / "state" / "session" / sid


def sid_of(out: str) -> str:
    """The sid the brief announced, from `SESSION: opened|resumed <sid>`."""
    line = [ln for ln in out.splitlines() if ln.startswith("SESSION: ")]
    assert len(line) == 1, f"the brief must carry exactly one SESSION line, got: {out!r}"
    return line[0].split()[-1]


def handoff(repo: Path) -> Path:
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / f"{date.today()}-@{LOGIN}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("## 18:30 — fixture\n- Done: nothing\n")
    return path


class StartOpensTheSession(unittest.TestCase):
    """(a)-(d), (g) — what `/start` adds to the brief, and what it must never add."""

    def test_a_the_session_opens_and_the_brief_names_it(self):
        repo = declaring()
        done = block("start", OPEN, repo)
        self.assertEqual(done.returncode, 0, done.stderr)
        sid = sid_of(done.stdout)
        self.assertIn("SESSION: opened", done.stdout)
        self.assertTrue(sid.startswith(f"s-{LOGIN}-{date.today():%Y%m%d}-"), sid)
        record = json.loads((seat(repo, sid) / "start.json").read_text())
        self.assertTrue(record["pack_seal"], "a start receipt without a pack seal is not one")

    def test_b_a_second_start_the_same_day_resumes_the_same_session(self):
        repo = declaring()
        first = sid_of(block("start", OPEN, repo).stdout)
        again = block("start", OPEN, repo)
        self.assertIn("SESSION: resumed", again.stdout)
        self.assertEqual(again.returncode, 0, "SESSION_EXISTS is a resume, never a failure")
        self.assertEqual(sid_of(again.stdout), first, "the sid is the checkout, the day, the login")
        self.assertEqual(len(list((repo / "state" / "session").glob("*/start.json"))), 1)

    def test_c_a_repo_with_no_engine_prints_nothing_and_writes_nothing(self):
        repo = host_repo()
        done = block("start", OPEN, repo)
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.stdout.strip(), "", "a repo with no engine must not learn it exists")
        self.assertEqual(list(repo.glob("state/session/*/start.json")), [],
                         "no engine, no receipt — the seat directory itself proves nothing")

    def test_d_a_refused_pack_is_one_line_and_the_brief_goes_on(self):
        repo = declaring(REFUSES)
        done = block("start", OPEN, repo)
        self.assertEqual(done.returncode, 0, "a blocked session must not abort /start")
        self.assertIn("SESSION: blocked — CONTEXTPACK_INVALID", done.stdout)
        self.assertEqual(list(repo.glob("state/session/*/start.json")), [],
                         "a refusal leaves no receipt; the real engine still makes the seat")

    def test_g_the_legacy_vault_root_key_is_still_read_once_with_a_warning(self):
        repo = declaring(key="polaris.vault-root")
        done = block("start", OPEN, repo)
        self.assertIn("SESSION: opened", done.stdout)
        self.assertIn("polaris.vault-root", done.stderr)
        self.assertIn("polaris.vault", done.stderr, "the warning must name the key that replaces it")


class TheCheckpointAndTheClose(unittest.TestCase):
    """(e)-(f) — the other two doors reach the SAME session, or the receipt is a stump."""

    def test_e_update_writes_an_event_chained_to_the_start_receipt(self):
        repo = declaring()
        sid = sid_of(block("start", OPEN, repo).stdout)
        done = block("update", "session_gate.py", repo, ROOT=str(repo / "_polaris"))
        self.assertEqual(done.returncode, 0, done.stderr)
        rows = [json.loads(l) for l in (seat(repo, sid) / "events.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 1, "one checkpoint, one event")
        self.assertEqual(rows[0]["prev"], f"rh-{sid}", "the event must name the start receipt")

    def test_e2_a_checkpoint_with_no_open_session_is_silent(self):
        repo = declaring()
        done = block("update", "session_gate.py", repo, ROOT=str(repo / "_polaris"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "")

    def test_f_end_closes_the_same_session_with_a_linked_receipt(self):
        repo = declaring()
        sid = sid_of(block("start", OPEN, repo).stdout)
        handoff(repo)
        done = block("end", CLOSE, repo)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        record = json.loads((seat(repo, sid) / "end.json").read_text())
        self.assertEqual(record["chain"]["start_receipt"], f"rh-{sid}")

    def test_f2_a_refusal_of_the_gate_stops_end(self):
        repo = declaring()
        sid_of(block("start", OPEN, repo).stdout)
        done = block("end", CLOSE, repo)  # no handoff on disk: refused before the engine
        self.assertNotEqual(done.returncode, 0, "a refused close must stop /end, not warn")
        self.assertIn("HANDOFF_UNREADABLE", done.stdout + done.stderr)

    def test_f3_end_without_an_engine_degrades_and_does_not_block(self):
        repo = host_repo()
        handoff(repo)
        done = block("end", CLOSE, repo)
        self.assertEqual(done.returncode, 0, "the absence of the engine is the only soft case")


if __name__ == "__main__":
    unittest.main()
