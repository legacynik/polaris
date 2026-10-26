"""arch_doctor's six decisions, each with its own fixture repository.

Every fixture is built here — no test reads the vault it happens to run in, which is
what lets the same file prove the same contract inside the package.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import arch_doctor  # noqa: E402

STUB = "#!/usr/bin/env python3\nimport sys\n"
CLEAN_ENV = {k: v for k, v in os.environ.items() if k != "POLARIS_VAULT"}


def write_stub(root: Path, rel: str, body: str) -> Path:
    """A fake harness script at `rel`, executable, running on this interpreter."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STUB + body, encoding="utf-8")
    return path


def doctor(root: Path, *flags: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(Path(arch_doctor.__file__)), "--root", str(root), *flags]
    return subprocess.run(cmd, capture_output=True, text=True, env=CLEAN_ENV, timeout=120)


def tree_hash(root: Path) -> str:
    items = sorted(p for p in root.rglob("*") if p.is_file())
    return "|".join(f"{p.relative_to(root)}:{p.stat().st_size}" for p in items)


def test_a_no_harness_every_row_unknown(tmp_path: Path) -> None:
    """(a) A repository where the harness is not installed reports UNKNOWN, never zero."""
    run = doctor(tmp_path)
    assert run.returncode == 0, run.stderr
    assert "Traceback" not in run.stderr
    rows = json.loads(doctor(tmp_path, "--json").stdout)
    assert rows, "no rows emitted"
    assert {r["verdict"] for r in rows} == {"UNKNOWN"}
    # The backbone checker ships in the skill: its row runs and reads "never adopted".
    backbone = next(r for r in rows if r["check"] == "backbone")
    assert "LIVE_DOC_MISSING" in backbone["evidence"], backbone
    assert all("harness not installed here" in r["evidence"] for r in rows if r is not backbone)


def test_b_a_gone_cited_path_is_red_with_a_repair(tmp_path: Path) -> None:
    """(b) A blocking backbone exit names the cause and says how to repair it."""
    write_stub(tmp_path, "scripts/check_context_backbone.py",
               'print(\'{"kind": "BLOCK", "cause": "CITED_PATH_MISSING", '
               '"detail": "ARCHITECTURE.md: src/gone.py"}\')\nsys.exit(2)\n')
    rows = json.loads(doctor(tmp_path, "--json").stdout)
    backbone = next(r for r in rows if r["check"] == "backbone")
    assert backbone["verdict"] == "RED"
    assert "CITED_PATH_MISSING" in backbone["evidence"]
    assert "restore the cited path" in backbone["fix"]
    assert doctor(tmp_path).returncode == 2, "a blocking RED must fail the full run"


def test_c_a_hung_subprocess_is_unknown_not_a_crash(tmp_path: Path) -> None:
    """(c) A check that never returns degrades to UNKNOWN and still exits 0."""
    write_stub(tmp_path, "scripts/check_context_backbone.py", "import time\ntime.sleep(30)\n")
    arch_doctor.TIMEOUT = 0.5
    try:
        rows = arch_doctor.rows(tmp_path, quick=True)
    finally:
        arch_doctor.TIMEOUT = 60
    backbone = next(r for r in rows if r["check"] == "backbone")
    assert backbone["verdict"] == "UNKNOWN"
    assert "timeout" in backbone["evidence"].lower()
    assert arch_doctor.exit_code(rows, quick=True) == 0


def test_d_quick_never_reaches_the_slow_checks(tmp_path: Path) -> None:
    """(d) `--quick` is the cheap measure: the sibling drift ledgers are not walked."""
    marker = tmp_path / "invoked.log"
    for name in ("polaris_symbol_drift", "polaris_decision_drift",
                 "polaris_dependency_drift", "polaris_test_drift"):
        write_stub(tmp_path, f"scripts/{name}.py",
                   f'open({str(marker)!r}, "a").write("{name}\\n")\n')
        (tmp_path / f"{name.split('_', 1)[1].replace('_', '-')}.jsonl").write_text("", encoding="utf-8")
    assert doctor(tmp_path, "--quick").returncode == 0
    assert not marker.exists(), "quick mode invoked a full-mode check"
    quick_rows = json.loads(doctor(tmp_path, "--quick", "--json").stdout)
    full_rows = json.loads(doctor(tmp_path, "--json").stdout)
    assert len(quick_rows) < len(full_rows)


def test_e_json_and_table_carry_the_same_rows(tmp_path: Path) -> None:
    """(e) `--json` is the same measurement, not a second one."""
    rows = json.loads(doctor(tmp_path, "--json").stdout)
    table = doctor(tmp_path).stdout
    for row in rows:
        assert row["check"] in table
        assert row["verdict"] in table


def test_f_the_doctor_never_writes_to_the_repository(tmp_path: Path) -> None:
    """(f) Measuring is read-only: the tree is byte-for-byte what it was."""
    write_stub(tmp_path, "scripts/check_context_backbone.py", "print('{}')\n")
    write_stub(tmp_path, "scripts/decisions_health.py", "print('{}')\n")
    # scope-drift needs its intent source before it measures anything; without it the row is
    # UNKNOWN by contract and this fixture would prove nothing about writing.
    (tmp_path / "state").mkdir(exist_ok=True)
    (tmp_path / "state" / "intents.json").write_text("[]", encoding="utf-8")
    write_stub(tmp_path, "scripts/polaris_drift_check.py",
               "print('iCPG scope-drift: clean')\n")
    before = tree_hash(tmp_path)
    rows = json.loads(doctor(tmp_path, "--json").stdout)
    ran = [r for r in rows if r["verdict"] != "UNKNOWN"]
    assert len(ran) >= 2, f"nothing was measured, so nothing was proved: {rows}"
    assert tree_hash(tmp_path) == before


def test_g_quick_ends_with_the_next_verbs(tmp_path: Path) -> None:
    """(g) The naked invocation must hand the work on by itself: after the rows, a
    `prossimo:` block naming the /architecture verbs the menu maps to what was measured —
    on a repository with no harness every row is UNKNOWN; the skill's own backbone checker reads
    it as never adopted, so the menu says `init`.
    Break: drop the block from main() and this fails; the rows alone were never the menu."""
    run = doctor(tmp_path, "--quick")
    assert run.returncode == 0, run.stderr
    lines = run.stdout.rstrip().splitlines()
    tail = lines[lines.index("prossimo:") + 1:] if "prossimo:" in lines else []
    assert tail, f"no `prossimo:` block after the rows:\n{run.stdout}"
    assert any(t.strip().startswith("/architecture init") for t in tail), tail
