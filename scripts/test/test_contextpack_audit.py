"""L2-T5 (#404) — reading a week of pack receipts, and refusing to vouch for a bad one.

The audit is the whole point of writing receipts: a week later, what did each session
actually have in front of it. That makes it a claim about the past, and a claim about the
past is only worth what its weakest input is worth. Three inputs were weaker than the
claim:

- **The window read the filesystem, not the receipt.** `st_mtime` is a property of the
  copy, not of the session: a `cp -r`, an `rsync`, a restore from backup rewrites every
  timestamp, and a six-month-old receipt walks into `--since 7d` while a receipt written
  this morning and restored from an old archive walks out. The window now reads the `ts`
  the receipt itself carries, and a receipt whose `ts` is not a timestamp is not a receipt.
- **The order was the order of the paths.** `sorted(glob(...))` sorts by session id, so an
  audit meant to be read as a history came out alphabetical. It is now oldest first.
- **`pack_seal` was printed as truth.** Anyone could open a receipt, type `deadbeef` over
  the seal, and the audit would repeat it. `rows_hash` covers everything the receipt
  claims, so an edited field shows as `SEAL_MISMATCH` instead of being echoed. It is
  tamper-EVIDENCE, not a signature: it catches a field edited in place, not a forger who
  rewrote the file. `sid` and `ts` are deliberately outside it, so two receipts of the same
  pack at a still HEAD still differ in exactly two lines.

RED-first: `scripts/contextpack_audit.py` does not exist yet.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import contextpack_audit as auditor  # noqa: E402

PROSE = {"CONTEXT.md": "# prose, nothing typed here\n", "source.txt": "x\n"}


def cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / "contextpack.py"), *args],
                          cwd=root, capture_output=True, text=True)


class Audited(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="audit-")).resolve()
        for name, body in PROSE.items():
            (self.root / name).write_text(body, encoding="utf-8")
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "under test"]):
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                           cwd=self.root, check=True, capture_output=True)
        self.addCleanup(shutil.rmtree, self.root, True)

    def emit(self, sid: str) -> Path:
        done = cli(self.root, "resolve", "--root", ".", "--sid", sid)
        self.assertEqual(done.returncode, 0, done.stderr)
        return self.root / "state" / "session" / sid / "area-all.json"

    def edit(self, path: Path, **fields) -> None:
        rec = json.loads(path.read_text(encoding="utf-8"))
        rec.update(fields)
        path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")

    def run_audit(self, since: str = "7d") -> tuple[int, list[str], str]:
        done = cli(self.root, "audit", "--root", ".", "--since", since)
        return done.returncode, [x for x in done.stdout.splitlines() if x.strip()], done.stderr


class TheWindowIsTheReceiptsOwnTimestamp(Audited):
    def test_an_old_receipt_with_a_fresh_mtime_is_outside_the_window(self) -> None:
        """The disease: `cp -r state/ backup/` used to make every receipt seven days young."""
        path = self.emit("s-old")
        self.edit(path, ts=(datetime.now().astimezone() - timedelta(days=30)).isoformat())
        self.assertGreater(path.stat().st_mtime, datetime.now().timestamp() - 60,
                           "the file was just written: mtime says fresh, the receipt says old")
        code, lines, err = self.run_audit("7d")
        self.assertEqual((code, lines), (0, []), err)
        self.assertEqual(self.run_audit("60d")[1] and len(self.run_audit("60d")[1]), 1)

    def test_a_malformed_timestamp_makes_it_an_invalid_receipt(self) -> None:
        path = self.emit("s-bad")
        self.edit(path, ts="last tuesday")
        code, lines, err = self.run_audit()
        self.assertEqual((code, lines), (2, []))
        self.assertIn("RECEIPT_INVALID", err)

    def test_the_audit_is_ordered_oldest_first_not_alphabetically(self) -> None:
        older, newer = self.emit("zzz-first"), self.emit("aaa-second")
        self.edit(older, ts=(datetime.now().astimezone() - timedelta(hours=2)).isoformat())
        code, lines, err = self.run_audit()
        self.assertEqual(code, 0, err)
        self.assertEqual([x.split()[1] for x in lines], ["zzz-first", "aaa-second"])
        self.assertTrue(newer.exists())


class TheAuditDoesNotRepeatAClaimItCannotCheck(Audited):
    def test_a_falsified_pack_seal_is_marked_not_echoed(self) -> None:
        path = self.emit("s-forged")
        self.edit(path, pack_seal="deadbeef" * 8)
        code, lines, err = self.run_audit()
        self.assertEqual(code, 0, err)
        self.assertEqual(len(lines), 1)
        self.assertIn("SEAL_MISMATCH", lines[0])

    def test_an_untouched_receipt_carries_no_mark(self) -> None:
        self.emit("s-honest")
        code, lines, err = self.run_audit()
        self.assertEqual(code, 0, err)
        self.assertNotIn("SEAL_MISMATCH", lines[0])

    def test_the_hash_ignores_who_wrote_it_and_when(self) -> None:
        """Otherwise the acceptance's two-line diff between two receipts becomes three."""
        rec = json.loads(self.emit("s-a").read_text(encoding="utf-8"))
        moved = dict(rec, sid="s-b", ts="2020-01-01T00:00:00+00:00")
        self.assertEqual(auditor.rows_hash(rec), auditor.rows_hash(moved))
        self.assertNotEqual(auditor.rows_hash(rec), auditor.rows_hash(dict(rec, pack_seal="x")))


class TheAuditReadsAWeekOfThem(Audited):
    def test_one_line_per_session(self) -> None:
        root = self.root
        for sid in ("s1", "s2"):
            self.emit(sid)
        done = cli(root, "audit", "--root", ".", "--since", "7d")
        lines = [line for line in done.stdout.splitlines() if line.strip()]
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(lines), 2, done.stdout)
        self.assertEqual(sorted(line.split()[1] for line in lines), ["s1", "s2"])
        self.assertTrue(all(" all " in line for line in lines), done.stdout)

    def test_no_receipts_is_zero_lines_and_exit_zero(self) -> None:
        root = self.root
        done = cli(root, "audit", "--root", ".", "--since", "7d")
        self.assertEqual((done.returncode, done.stdout.strip()), (0, ""), done.stderr)

    def test_a_truncated_receipt_exits_two_and_is_counted_zero_times(self) -> None:
        root = self.root
        self.emit("s1")
        good = (root / "state/session/s1/area-all.json").read_text()
        bad = root / "state" / "session" / "s2" / "area-all.json"
        bad.parent.mkdir(parents=True)
        bad.write_text(good[: len(good) // 2], encoding="utf-8")
        done = cli(root, "audit", "--root", ".", "--since", "7d")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("RECEIPT_INVALID", done.stderr)
        self.assertEqual([line.split()[1] for line in done.stdout.splitlines() if line.strip()],
                         ["s1"], done.stdout)


if __name__ == "__main__":
    unittest.main()
