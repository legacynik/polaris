"""Round 2 — the three ways the doctor still turned someone else's failure into its own verdict.

Written against the head that shipped round 1 and observed failing on it. Fixtures built here.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import arch_doctor  # noqa: E402
import arch_doctor_sources  # noqa: E402

STUB = "#!/usr/bin/env python3\nimport sys\n"
CLEAN_ENV = {k: v for k, v in os.environ.items() if k != "POLARIS_VAULT"}


def stub(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STUB + body, encoding="utf-8")


def adopted(root: Path) -> None:
    """The markers a repository that HAS adopted the register carries."""
    (root / "decisions").mkdir(exist_ok=True)
    (root / "decisions" / "manifest.json").write_text("{}", encoding="utf-8")


def test_q_an_unreadable_ledger_is_unknown_not_a_crash(tmp_path: Path) -> None:
    """B1 — copying the recording is the doctor's own step, so its failure is its own row."""
    if os.geteuid() == 0:
        return  # root reads anything; the branch is unreachable here
    adopted(tmp_path)
    ledger = tmp_path / "decision-drift.jsonl"
    ledger.write_text('{"recorded": 1}\n', encoding="utf-8")
    stub(tmp_path, "scripts/polaris_decision_drift.py", 'print("decision-drift: clean")\n')
    os.chmod(ledger, 0o000)
    try:
        run = subprocess.run(
            [sys.executable, str(Path(arch_doctor.__file__)), "--root", str(tmp_path)],
            capture_output=True, text=True, env=CLEAN_ENV, timeout=120)
        assert "Traceback" not in run.stderr, run.stderr
        assert run.returncode == 0, run.stderr
        row = {r["check"]: r for r in arch_doctor.rows(tmp_path)}["decision-drift"]
        assert row["verdict"] == "UNKNOWN", row
        assert "unreadable" in row["evidence"].lower(), row
    finally:
        os.chmod(ledger, 0o644)


def test_r_a_traceback_is_a_crash_even_when_the_code_means_red(tmp_path: Path) -> None:
    """B2 — exit 1 is `decisions`' declared RED, so a crash borrowed a verdict it never earned."""
    adopted(tmp_path)
    for slot in ("decisions_health", "check_install_hygiene"):
        rel = ("scripts/decisions_health.py" if slot == "decisions_health"
               else "skills-suite/_standard/check_install_hygiene.py")
        stub(tmp_path, rel, 'raise ValueError("boom")\n')
    result = arch_doctor.rows(tmp_path)
    for name in ("decisions", "install-hygiene"):
        row = {r["check"]: r for r in result}[name]
        assert row["verdict"] == "UNKNOWN", f"{name} took a crash for a verdict: {row}"
        assert "checker failed" in row["evidence"].lower(), row
    assert arch_doctor.exit_code(result) == 0


def test_s_a_repository_without_a_register_has_not_adopted_it(tmp_path: Path) -> None:
    """B3 — non-adoption was neutralised on `backbone` alone, so `decisions` still blocked."""
    stub(tmp_path, "scripts/decisions_health.py",
         'print(\'{"green": 0, "of": 3}\')\nsys.exit(1)\n')
    result = arch_doctor.rows(tmp_path)
    row = {r["check"]: r for r in result}["decisions"]
    assert row["verdict"] == "UNKNOWN", f"a repository with no register read as failing: {row}"
    assert row["blocking"] is False, row
    assert "--init" in row["fix"], row
    assert arch_doctor.exit_code(result) == 0, "non-adoption blocked the full run"
    adopted(tmp_path)
    after = {r["check"]: r for r in arch_doctor.rows(tmp_path)}["decisions"]
    assert after["verdict"] == "RED", f"an adopted register must still be judged: {after}"


def test_t_a_row_cut_by_the_budget_says_so(tmp_path: Path) -> None:
    """The quick budget clipping a check is not that check being slow."""
    stub(tmp_path, "scripts/check_context_backbone.py", "import time\ntime.sleep(70)\n")
    stub(tmp_path, "scripts/decisions_health.py", "import time\ntime.sleep(70)\n")
    adopted(tmp_path)
    cut = [r for r in arch_doctor.rows(tmp_path, quick=True)
           if "timeout" in r["evidence"].lower()]
    assert not cut, f"a budget cut reported as the checker timing out: {cut}"


def test_u_the_sources_selfcheck_asserts_something(tmp_path: Path) -> None:
    """A tautology in a gate is a gate that cannot fail."""
    body = Path(arch_doctor_sources.__file__).read_text()
    assert "or True" not in body, "a dead assertion is still in the selfcheck"
    assert arch_doctor_sources.selfcheck() == 0
