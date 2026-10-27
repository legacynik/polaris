"""Isolated pytest execution; --selfcheck drives the public grader's disaster cases."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import red_break_report

SCRIPTS = Path(__file__).resolve().parent



def _environment(report: Path, real: Path) -> dict:
    env = {key: value for key, value in os.environ.items()
           if key not in {"PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONPATH"}}
    return {**env, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(SCRIPTS), "RED_BREAK_REPORT": str(report),
            "RED_BREAK_REAL": str(real)}


def _outcome(run, report: Path, test: Path) -> dict:
    rows = [json.loads(line) for line in report.read_text().splitlines()] if report.exists() else []
    cases = [row for row in rows if "outcome" in row]
    failed = [row for row in cases if row["outcome"] == "failed"]
    calls = [row for row in cases if row["when"] == "call"]
    escaped = any(row.get("escaped") for row in rows)
    passed = bool(calls) and all(row["outcome"] == "passed" for row in cases)
    caught = bool(failed) and all(row["when"] == "call" and
        red_break_report.verdict(report, (test, row["name"]), test.parent)[0] is True
        for row in failed)
    in_call = bool(failed) and all(row["when"] == "call" for row in failed)
    staged = any(row.get("absent") for row in failed)
    return {"exit": run.returncode, "passed": run.returncode == 0 and passed and not escaped,
            "assertion_failure": run.returncode == 1 and caught and not escaped,
            "call_failure": run.returncode == 1 and in_call and not staged and not escaped,
            "staged": staged,
            "output": (run.stdout + run.stderr)[-2000:]}


def run_variant(variant: Path, candidate: Path) -> dict:
    frozen = candidate.read_bytes()
    with tempfile.TemporaryDirectory(prefix="test-value-") as home:
        root, report = Path(home) / "run", Path(home) / "report.jsonl"
        shutil.copytree(variant, root, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        target = root / candidate.name
        target.write_bytes(frozen)
        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                   "-p", "red_break_probe", target.name]
        try:
            run = subprocess.run(command, cwd=root, env=_environment(report, variant.resolve()),
                                 capture_output=True, text=True, timeout=30)
            result = _outcome(run, report, target.resolve())
        except (subprocess.TimeoutExpired, OSError, ValueError) as error:
            result = {"exit": None, "passed": False, "assertion_failure": False, "error": str(error)}
        result["byte_identical"] = target.is_file() and target.read_bytes() == frozen
    return result


if __name__ == "__main__":
    test = SCRIPTS.parent / "tests" / "test_value_failures.py"
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", str(test)])
             if sys.argv[1:] == ["--selfcheck"] else 2)
