"""Round 1 — the nine defects a fresh-context breaker found in the first doctor.

Each test here was written against the implementation that shipped in the first commit and
observed failing on it for the real defect, not for a missing import. Every fixture is built
in this file.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import arch_doctor  # noqa: E402

STUB = "#!/usr/bin/env python3\nimport sys\n"
SKILL = Path(__file__).resolve().parents[1]
CLEAN_ENV = {k: v for k, v in os.environ.items() if k != "POLARIS_VAULT"}
DRIFT = "polaris_drift_check.py"


def stub(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STUB + body, encoding="utf-8")


def rows_of(root: Path, quick: bool = False) -> dict:
    return {r["check"]: r for r in arch_doctor.rows(root, quick=quick)}


def tree(root: Path) -> list:
    return sorted((str(p.relative_to(root)), p.stat().st_size, p.read_bytes())
                  for p in root.rglob("*") if p.is_file())


def wire_intents(root: Path) -> None:
    """Whatever the doctor accepts as the intent source, so scope-drift can measure."""
    for rel in ("state/intents.json", "intents.json"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('[{"id": "i1", "scope": ["src/"], "status": "active"}]', encoding="utf-8")


def test_g_clean_is_a_word_not_a_substring(tmp_path: Path) -> None:
    """A1 — a file named cleanup.py in drift must not read GREEN."""
    wire_intents(tmp_path)
    drifted = ('print("\\u2550 iCPG SCOPE-DRIFT (CONTEXT) \\u2014 1 unowned change(s) \\u2550")\n'
               'print("  [note] cleanup.py \\u2014 no active intent claims it")\n')
    stub(tmp_path, f"scripts/{DRIFT}", drifted)
    assert rows_of(tmp_path)["scope-drift"]["verdict"] == "RED", "cleanup.py faked a GREEN"
    stub(tmp_path, f"scripts/{DRIFT}", drifted.replace("cleanup.py", "tidy.py"))
    assert rows_of(tmp_path)["scope-drift"]["verdict"] == "RED"
    stub(tmp_path, f"scripts/{DRIFT}",
         'print("iCPG scope-drift: clean \\u2014 every changed file is claimed")\n')
    assert rows_of(tmp_path)["scope-drift"]["verdict"] == "GREEN"


def test_h_scope_drift_without_intents_measures_nothing(tmp_path: Path) -> None:
    """A2 — with no intent source every changed file is unowned: RED by construction."""
    stub(tmp_path, f"scripts/{DRIFT}", 'print("\\u2550 iCPG SCOPE-DRIFT \\u2014 11 unowned \\u2550")\n')
    row = rows_of(tmp_path)["scope-drift"]
    assert row["verdict"] == "UNKNOWN", f"RED without an intent source: {row}"
    assert "intent" in row["evidence"].lower()


def test_i_a_repository_without_the_backbone_has_not_adopted_it(tmp_path: Path) -> None:
    """A5 — LIVE_DOC_MISSING is non-adoption, not a failing repository."""
    for cause in ("LIVE_DOC_MISSING", "FRONTMATTER_MISSING"):
        stub(tmp_path, "scripts/check_context_backbone.py",
             f'print(\'{{"kind": "BLOCK", "cause": "{cause}"}}\')\nsys.exit(2)\n')
        result = arch_doctor.rows(tmp_path)
        row = {r["check"]: r for r in result}["backbone"]
        assert row["verdict"] == "UNKNOWN", f"{cause} read as RED: {row}"
        assert "adopt" in (row["evidence"] + row["fix"]).lower()
        assert arch_doctor.exit_code(result) == 0, f"{cause} blocked the run"


def test_j_a_crashing_checker_is_unknown_not_red(tmp_path: Path) -> None:
    """A5 — a traceback is the checker failing, never a verdict about the repository."""
    stub(tmp_path, "scripts/check_context_backbone.py", 'raise ValueError("boom")\n')
    result = arch_doctor.rows(tmp_path)
    row = {r["check"]: r for r in result}["backbone"]
    assert row["verdict"] == "UNKNOWN", f"a crash read as a verdict: {row}"
    assert "checker failed" in row["evidence"].lower()
    assert arch_doctor.exit_code(result) == 0


def test_k_quick_holds_a_total_budget(tmp_path: Path) -> None:
    """A6 — the naked invocation cannot stall on one hung checker."""
    stub(tmp_path, "scripts/check_context_backbone.py", "import time\ntime.sleep(70)\n")
    stub(tmp_path, "scripts/decisions_health.py", "import time\ntime.sleep(70)\n")
    started = time.monotonic()
    result = arch_doctor.rows(tmp_path, quick=True)
    elapsed = time.monotonic() - started
    assert elapsed < 20, f"--quick took {elapsed:.1f}s"
    assert any("budget" in r["evidence"].lower() for r in result), result
    assert arch_doctor.exit_code(result, quick=True) == 0


def test_l_no_ledger_the_doctor_passes_can_be_written(tmp_path: Path) -> None:
    """A7 — the never-writes guarantee may not rest on the checker behaving."""
    for name, ledger in (("polaris_decision_drift", "decision-drift.jsonl"),
                         ("polaris_dependency_drift", "dependency-drift.jsonl"),
                         ("polaris_test_drift", "test-drift.jsonl")):
        (tmp_path / ledger).write_text('{"recorded": 1}\n', encoding="utf-8")
        stub(tmp_path, f"scripts/{name}.py",
             'i = sys.argv.index("--ledger")\n'
             'open(sys.argv[i + 1], "a").write("APPENDED\\n")\n'
             'print("drift: clean")\n')
    before = tree(tmp_path)
    arch_doctor.rows(tmp_path)
    assert tree(tmp_path) == before, "a checker wrote inside the repository under test"


def test_m_the_table_carries_every_field_the_json_carries(tmp_path: Path) -> None:
    """A8 — menu.md says lead with the blocking row, so the table must show which."""
    run = subprocess.run([sys.executable, str(Path(arch_doctor.__file__)), "--root",
                          str(tmp_path)], capture_output=True, text=True, env=CLEAN_ENV)
    table = run.stdout
    for row in json.loads(subprocess.run(
            [sys.executable, str(Path(arch_doctor.__file__)), "--root", str(tmp_path), "--json"],
            capture_output=True, text=True, env=CLEAN_ENV).stdout):
        line = next((ln for ln in table.splitlines() if ln.startswith(row["check"] + " ")), None)
        assert line, f"{row['check']} not in the table"
        assert row["verdict"] in line and row["fix"] in line
        assert ("blocking" in line) == bool(row["blocking"]), f"blocking not shown: {line}"


def test_n_the_menu_answers_every_verdict_the_doctor_can_emit() -> None:
    """A4 — four of eight rows read UNKNOWN on the vault; a menu that ignores them is empty."""
    menu = (SKILL / "references" / "menu.md").read_text()
    missing = [f"`{spec['check']}` {verdict}"
               for spec in arch_doctor.CHECKS for verdict in ("RED", "UNKNOWN")
               if f"`{spec['check']}` {verdict}" not in menu]
    assert not missing, f"menu.md has no row for: {missing}"


def test_o_c5_and_c6_can_be_green_on_the_same_trace(tmp_path: Path) -> None:
    """A3 — the trace this PR ships carries the doctor's own repair text."""
    doctor_out = (
        "check | verdict | blocking | evidence | realignment\n"
        "backbone | RED | blocking | check_context_backbone.py · exit 2 · "
        '{"kind": "BLOCK", "cause": "CITED_PATH_MISSING"} | restore the cited path, or fix the '
        "citation: `/architecture doc` or `/architecture land <DEC-id>`\n")
    trace = ("$ python3 scripts/arch_doctor.py --root . --quick\n" + doctor_out
             + "Lead with `doc`: the document cites a path that is gone.\n")
    (tmp_path / "doctor.txt").write_text(doctor_out, encoding="utf-8")
    (tmp_path / "trace.txt").write_text(trace, encoding="utf-8")
    env = dict(CLEAN_ENV, DOCTOR=str(tmp_path / "doctor.txt"), TRACE=str(tmp_path / "trace.txt"))
    checks = {c["id"]: c for c in json.loads(
        (SKILL / "eval" / "checks.json").read_text())}
    for cid in ("c5", "c6"):
        code = subprocess.run(checks[cid]["cmd"], shell=True, env=env,
                              capture_output=True, text=True).returncode
        assert code == 0, f"{cid} red on the trace the PR ships"


def test_p_assumed_stays_a_field_of_the_record() -> None:
    """A9 — nine fields, and c1 greps them; ASSUMED was dropped from the grep."""
    c1 = next(c for c in json.loads((SKILL / "eval" / "checks.json").read_text())
              if c["id"] == "c1")
    for field in ("prossimo", "ASSUMED"):
        assert field in c1["cmd"], f"c1 does not grep {field}"
    body = (SKILL / "references" / "process.md").read_text()
    assert re.search(r"^\| `ASSUMED` \|", body, re.M), "ASSUMED is not a row of the record table"
