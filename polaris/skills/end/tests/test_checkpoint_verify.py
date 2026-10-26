"""checkpoint.sh verify — a cockpit it cannot read is named as unreadable, never read as empty.

    python3 -m pytest skills-suite/end/tests/test_checkpoint_verify.py
"""
from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "checkpoint.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a mode-000 file")
def test_an_unreadable_cockpit_is_named_not_counted_as_zero(tmp_path):
    _git(tmp_path, "init", "-q", ".")
    for key, value in (("polaris.login", "probe"), ("user.email", "p@x.test"), ("user.name", "P")):
        _git(tmp_path, "config", "--local", key, value)
    root = tmp_path / "_polaris"
    (root / "state").mkdir(parents=True)
    (root / "config.yml").write_text("")
    log = root / "team" / "probe" / "sessions" / f"{date.today():%Y-%m-%d}-@probe.md"
    log.parent.mkdir(parents=True)
    log.write_text("## 10:00 — probe entry\n- Key context: x\n- Files: y\n")
    _git(tmp_path, "add", "--", str(log))
    _git(tmp_path, "commit", "-qm", "checkpoint")
    cockpit = root / "state" / "current.md"
    cockpit.write_text(f"Updated: {date.today():%Y-%m-%d} — @probe\n")
    cockpit.chmod(0)
    try:
        done = subprocess.run(["bash", str(SCRIPT), "verify"], cwd=tmp_path,
                              capture_output=True, text=True, env={**os.environ, "POLARIS_SID": ""})
    finally:
        cockpit.chmod(0o644)
    out = done.stdout + done.stderr
    assert done.returncode == 1, out
    assert "current.md is unreadable" in out, f"the gate misread an unreadable cockpit:\n{out}"
    assert "no 'Updated:' line" not in out, f"an unreadable file was read as empty:\n{out}"
