"""Drive the shipped CLI: its JSON verdict and exit code are the caller contract."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
CLI = SKILL / "scripts" / "test_value_grade.py"
PRICE = SKILL / "eval" / "behaviour" / "price"


@pytest.mark.parametrize("candidate, expected", [("good_1.py", 0), ("weak_fixture.py", 1)])
def test_cli_returns_the_observed_verdict(candidate, expected):
    run = subprocess.run([sys.executable, str(CLI), str(PRICE),
                          str(PRICE / "candidates" / candidate)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected, run.stderr
    assert run.stdout.strip(), "the public CLI must emit its JSON verdict"
    report = json.loads(run.stdout)
    assert report["verdict"] == ("VALUABLE" if expected == 0 else "WEAK")
    assert report["byte_identical"] is True
    assert set(report["kills"]) == {"toward_zero", "wrong_precision"}
    assert report["fails_on_base_at_assertion"] is (expected == 0)
    assert report["passes_on_solution"] is True
    assert report["survives_refactor"] is True
    assert all(report["kills"].values()) is (expected == 0)


@pytest.mark.parametrize("flag", ["--check-fixtures", "--selfcheck"])
def test_fixture_check_executes_every_manifest_case(flag):
    run = subprocess.run([sys.executable, str(CLI), flag],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip(), "the outcome check must report executed cases"
    report = json.loads(run.stdout)
    assert report["checked"] == 24
    assert report["failures"] == []


def test_missing_fixture_is_a_json_usage_error(tmp_path):
    run = subprocess.run([sys.executable, str(CLI), str(tmp_path), "absent.py"],
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 2
    assert json.loads(run.stdout)["verdict"] == "WEAK"
