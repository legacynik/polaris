"""A probe is a falsifier or it is decoration, and three critics found three ways it was neither.

`probe: true` fills the field and reads nothing. A selfcheck over synthetic fixtures reads the
repository but never the governed part. And a shadow made of symlinks is not a shadow: a probe
resolving `__file__` follows the link back to the real tree.

So: `probe_kills` names a call site of that same record, present at HEAD, that the probe does not
execute; the probe holds no absolute path; and the shadow is a materialised copy of HEAD.
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


class TestProbeSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)

    def test_a_victim_the_probe_executes_is_not_a_falsifier(self) -> None:
        """Removing the script a probe runs breaks the command, not the claim it makes."""
        (self.fx.root / "runner.py").write_text("raise SystemExit(0)\n")
        self.fx.write("DEC-selfkill-001", status="accepted", probe="python3 runner.py",
                      call_sites=["runner.py"], probe_kills="runner.py")
        r = run(self.fx.root)
        self.assertNotEqual(r.returncode, 0, "a probe may not name its own interpreter argument")
        self.assertIn("DEC-selfkill-001", r.stdout + r.stderr)

    def test_a_victim_absent_from_head_is_fatal(self) -> None:
        """The skip that let `true` score EXECUTED_IN_FACT: no victim, so no shadow, so no check."""
        self.fx.write("DEC-ghost-001", status="accepted", probe="true",
                      call_sites=["gone"], probe_kills="gone")
        r = run(self.fx.root)
        self.assertNotEqual(r.returncode, 0, "a victim that is not at HEAD cannot falsify anything")
        self.assertIn("DEC-ghost-001", r.stdout + r.stderr)

    def test_a_probe_reaching_outside_the_repository_is_fatal(self) -> None:
        """An absolute path or a ~ reads past the shadow, so the removal proves nothing."""
        self.fx.write("DEC-absolute-001", status="accepted", probe="test -f /etc/hosts")
        r = run(self.fx.root)
        self.assertNotEqual(r.returncode, 0, "probes address the repository relatively")
        out = r.stdout + r.stderr
        self.assertIn("DEC-absolute-001", out)
        self.assertIn("absolute path", out, "the note must name the cause, not just the symptom")

    def test_a_probe_blind_to_its_call_site_is_fatal(self) -> None:
        """The failure a fresh critic found on the first cut: a probe that reads the repository,
        passes, and never touches the call site the record says it governs. It proves the checker
        runs, not that the decision holds, so the gate re-runs it with that call site removed."""
        self.fx.write("DEC-blind-001", status="accepted", probe="test -d decisions")
        r = run(self.fx.root)
        self.assertNotEqual(r.returncode, 0, "a probe blind to its call site must be fatal")
        self.assertIn("NO_ASSERTION", r.stdout + r.stderr)

    def test_probe_kills_must_name_one_of_the_call_sites(self) -> None:
        """Otherwise the falsifier is chosen to be something the probe happens to read anyway."""
        self.fx.write("DEC-astray-001", status="accepted", probe="test -f marker",
                      probe_kills="somewhere-else")
        r = run(self.fx.root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DEC-astray-001", r.stdout + r.stderr)

    def test_a_probe_that_asserts_nothing_is_fatal(self) -> None:
        """The way the ratchet gets defeated: satisfy `probe` with a command that cannot fail.

        A probe is a falsifier. `true` is not one, and neither is any command that still exits 0
        with no repository under it — so that is the test the gate runs on every passing probe."""
        self.fx.write("DEC-fake-001", status="accepted", probe="true")
        r = run(self.fx.root)
        self.assertNotEqual(r.returncode, 0, "`true` must not satisfy the probe requirement")
        out = r.stdout + r.stderr
        self.assertIn("NO_ASSERTION", out)
        self.assertIn("DEC-fake-001", out)

    def test_a_hanging_probe_is_bounded_not_inherited(self) -> None:
        self.fx.write("DEC-slow-001", status="accepted", probe="sleep 120")
        r = subprocess.run([sys.executable, str(CLI), "--root", str(self.fx.root), "--timeout", "2"],
                           capture_output=True, text=True, cwd=ROOT, timeout=60)
        self.assertIn("DEC-slow-001", r.stdout + r.stderr)
        self.assertIn("TIMEOUT", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
