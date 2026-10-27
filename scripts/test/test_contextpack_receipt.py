"""L2-T5 (#404) — the receipt a pack leaves behind: what it carries, and what it costs.

A pack is emitted, read once, and gone. A week later nobody can say what the agent had in
front of it: which rows went in, which were dropped as superseded, which authorities were
missing, how much of the budget it burned, what the budget cut. The receipt is that
record. The budget and its cut order are `test_contextpack_budget.py`, what the receipt
refuses is `test_contextpack_refusals.py`, and reading a week of them back is
`test_contextpack_audit.py`.

- **A receipt is a side effect, so it is opt-in twice over.** `resolve` is a library
  function: `session_continuity.cmd_start` and `cmd_end` call it, and five test modules
  call it to compare `pack_seal` across mutations. Only the CLI writes one, and only when
  `--sid` named the session — minting a default id instead made every golden suite that
  shells out to the resolver drop a `state/session/` tree inside a tracked fixture.
- **Two resolves at a still HEAD produce the same pack.** The receipts may differ in who
  wrote them and when, and in nothing else.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import contextpack  # noqa: E402
import contextpack_receipt as receipt  # noqa: E402
import contextpack_unknown  # noqa: E402
import check_context_backbone as cbb  # noqa: E402


def _raises(*_args, **_kwargs):
    raise OSError(28, "No space left on device")

KEYS = ("included", "dropped", "unknown", "budget", "cuts", "pack_seal")
# Prose where the resolver wants a typed authority: the UNKNOWN branch of L2-T2, which is
# the only branch that carries cuttable rows until T3 and T4 land.
PROSE = {"CONTEXT.md": "# prose, nothing typed here\n", "source.txt": "x\n"}


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   cwd=root, check=True, capture_output=True)


def cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / "contextpack.py"), *args],
                          cwd=root, capture_output=True, text=True)


class Built(unittest.TestCase):
    def build(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="receipt-")).resolve()
        for name, body in PROSE.items():
            (root / name).write_text(body, encoding="utf-8")
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the repository under test")
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def emit(self, root: Path, sid: str, *extra: str) -> dict:
        done = cli(root, "resolve", "--root", ".", "--sid", sid, *extra)
        self.assertEqual(done.returncode, 0, done.stderr)
        path = root / "state" / "session" / sid / "area-all.json"
        return json.loads(path.read_text(encoding="utf-8"))


class TheResolveLeavesAReceipt(Built):
    def test_the_receipt_is_valid_json_carrying_the_six_keys_of_the_acceptance(self) -> None:
        root = self.build()
        rec = self.emit(root, "s1")
        self.assertEqual([k for k in KEYS if k not in rec], [], sorted(rec))
        # L2-T4 round 2 promotes the prose `CONTEXT.md` out of the unknown layer: one
        # source, one row, and the row belongs to the layer that could read the document.
        self.assertEqual(len(rec["unknown"]), 3, rec["unknown"])
        self.assertEqual(rec["budget"]["limit"], 4000)

    def test_the_receipt_seal_is_the_seal_of_the_pack_that_was_printed(self) -> None:
        root = self.build()
        done = cli(root, "resolve", "--root", ".", "--sid", "s1")
        rec = json.loads((root / "state/session/s1/area-all.json").read_text())
        self.assertEqual(rec["pack_seal"], json.loads(done.stdout)["pack_seal"])

    def test_resolve_without_a_sid_writes_nothing(self) -> None:
        """A receipt belongs to a session, and a session has a name the caller gives.

        Minting one instead was tried and reverted: every CLI resolve then wrote, and the
        golden suites that shell out to the resolver started dropping `state/session/`
        trees inside tracked fixture directories (`scripts/test/fixtures/no-backbone/`).
        A stray is a defect even when it is gitignored."""
        root = self.build()
        self.assertEqual(cli(root, "resolve", "--root", ".").returncode, 0)
        self.assertFalse((root / "state").exists(), "no --sid, no receipt, no stray")

    def test_a_library_resolve_writes_nothing(self) -> None:
        """session_continuity and five test modules call resolve: none may be made to write."""
        root = self.build()
        contextpack.resolve(root, "", [], degrade=True)
        self.assertFalse((root / "state").exists(), "resolve as a library must stay read-only")


class TheReceiptIsDeterministic(Built):
    def test_two_resolves_at_a_still_head_differ_only_in_sid_and_timestamp(self) -> None:
        root = self.build()
        first, second = self.emit(root, "s1"), self.emit(root, "s2")
        self.assertEqual(first["pack_seal"], second["pack_seal"])
        self.assertEqual(sorted(k for k in first if first[k] != second[k]), ["sid", "ts"])


if __name__ == "__main__":
    unittest.main()
