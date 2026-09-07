"""A decision that was accepted and never executed is a decision that exists only as talk.

Measured 2026-09-05/06. `DEC-polaris-retrieval-rebuild-001` has been `accepted` since 2026-08-24.
Its own closure_check reads "no operating rule names polaris_query_index.py as a mandatory move,
and the retired modules are absent from HEAD". Thirteen days later both clauses are false: the
script is on disk untouched, and both CLAUDE.md files name it twice each as a first move declared
not optional. Every session executes a rule an accepted decision retired, and nothing anywhere
notices, because `accepted` is the terminal state of our lifecycle.

So the lifecycle gains one value — `executed` — and the record gains one field, `probe`: the exact
command, no prose. `closure_check` stays the human sentence it already is; thirteen of them are
shell commands with English tails ("exits 0", "on all five predicates in Consequences") and one is
pure prose, so none of them is runnable as written and the gate must not guess which part to cut.

GATED (non-zero exit): a false `executed` claim, a judged record offering no probe, and a probe
that still passes with the call site it governs removed. REPORTED, never fatal: an accepted record
whose probe fails, which is decided-and-not-done. A count that reads zero in silence is the
failure this gate exists to end.
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
CLI = ROOT / "scripts" / "check_decision_execution.py"

BASE = {
    "schema_version": 1,
    "decision_id": "DEC-x-001",
    "title": "One thing",
    "kind": "architecture",
    "status": "accepted",
    "closure_check": "the thing holds",
    "call_sites": ["marker"],
    "probe_kills": "marker",
}


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), "--root", str(root)],
                          capture_output=True, text=True, cwd=ROOT)


class Fixture:
    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="decision-exec-"))
        (self.root / "decisions").mkdir()
        (self.root / "marker").write_text("the call site the probes govern\n")

    def commit(self) -> None:
        """The shadow is materialised from HEAD, so a fixture must have one."""
        for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t",
                                                    "commit", "-qm", "fixture"]):
            subprocess.run(["git", *cmd], cwd=self.root, check=True, capture_output=True)

    def write(self, slug: str, **fields) -> None:
        record = {**BASE, "decision_id": slug, **fields}
        body = f"---\n{json.dumps(record, indent=2)}\n---\n\n# {slug}\n"
        (self.root / "decisions" / f"{slug}.md").write_text(body)
        self.commit()

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class TestAFalseExecutedClaimIsFatal(unittest.TestCase):
    """The only fatal case, and the reason it is fatal: it is the claim a reader trusts."""

    def setUp(self) -> None:
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)

    def test_executed_with_a_failing_probe_is_fatal_and_names_the_decision(self) -> None:
        self.fx.write("DEC-liar-001", status="executed", probe="exit 3")
        r = run(self.fx.root)
        self.assertNotEqual(r.returncode, 0, "a false executed claim must be fatal")
        out = r.stdout + r.stderr
        self.assertIn("DEC-liar-001", out, "must name the decision")

    def test_executed_with_a_passing_probe_is_clean(self) -> None:
        self.fx.write("DEC-honest-001", status="executed", probe="test -f marker")
        self.assertEqual(run(self.fx.root).returncode, 0)

    def test_executed_without_a_probe_is_fatal(self) -> None:
        """Claiming execution while offering no way to check it is the same claim, unfalsifiable."""
        self.fx.write("DEC-bare-001", status="executed")
        self.assertNotEqual(run(self.fx.root).returncode, 0)


class TestDecidedAndNotDoneIsReported(unittest.TestCase):
    """The case this gate was built for: accepted, probe fails, nobody noticed for thirteen days."""

    def setUp(self) -> None:
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)

    def test_accepted_with_a_failing_probe_is_named_but_not_fatal(self) -> None:
        self.fx.write("DEC-pending-001", status="accepted", probe="exit 1")
        r = run(self.fx.root)
        self.assertEqual(r.returncode, 0, "an honest accepted must not break the build today")
        out = r.stdout + r.stderr
        self.assertIn("DEC-pending-001", out, "but it must be named, every run")
        self.assertIn("NOT_DONE", out)

    def test_accepted_with_a_passing_probe_is_named_as_promotable(self) -> None:
        self.fx.write("DEC-ready-001", status="accepted", probe="test -f marker")
        out = run(self.fx.root).stdout
        self.assertIn("DEC-ready-001", out)
        self.assertIn("EXECUTED_IN_FACT", out, "a passing probe on accepted is a promotion owed")

    def test_accepted_without_a_probe_is_fatal(self) -> None:
        """Ratcheted 2026-09-06: the thirteen unverifiable records now carry probes, so a new
        decision written without one is the only way this count leaves zero — and it is fatal.
        An unverifiable record is not an honest `accepted`: it is a claim with no falsifier."""
        self.fx.write("DEC-mute-001", status="accepted")
        r = run(self.fx.root)
        self.assertNotEqual(r.returncode, 0, "a decision with no probe must break the build")
        out = r.stdout + r.stderr
        self.assertIn("UNVERIFIABLE", out)
        self.assertIn("DEC-mute-001", out)

    def test_a_superseded_decision_is_not_judged(self) -> None:
        self.fx.write("DEC-old-001", status="superseded", probe="exit 1")
        r = run(self.fx.root)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("DEC-old-001", r.stdout, "a superseded record owes nothing")


class TestTheReportNeverReadsZeroSilently(unittest.TestCase):
    """A count that quietly says zero is how this class of defect survives."""

    def setUp(self) -> None:
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)

    def test_an_empty_register_says_so(self) -> None:
        r = run(self.fx.root)
        self.assertEqual(r.returncode, 0)
        self.assertIn("0 accepted", r.stdout, "an empty register must say it is empty")

    def test_the_summary_carries_every_bucket(self) -> None:
        self.fx.write("DEC-a-001", status="accepted", probe="test -f marker")
        self.fx.write("DEC-b-001", status="accepted", probe="exit 1")
        self.fx.write("DEC-c-001", status="accepted")
        out = run(self.fx.root).stdout
        for token in ("EXECUTED_IN_FACT", "NOT_DONE", "UNVERIFIABLE"):
            self.assertIn(token, out, f"{token} missing from the summary")


class TestSelfcheck(unittest.TestCase):
    def test_selfcheck_exits_zero(self) -> None:
        r = subprocess.run([sys.executable, str(CLI), "--selfcheck"],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
