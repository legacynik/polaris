#!/usr/bin/env python3
"""critic_gate_selfcheck — the adversarial branches of critic_gate, kept out of
the gate so both files stay inside the repo's size limits. Run it through
`critic_gate.py --selfcheck`; this module is not a CLI of its own.
"""

from __future__ import annotations

import json
import tempfile
from contextlib import chdir
from pathlib import Path

from critic_gate import Unusable, load, run
from critic_rules import validate


def _good() -> dict:
    root = Path(__file__).resolve().parent
    return {
        "artifact": str(root), "contract": "must match the file it describes",
        "ledger": {"opened": ["a.md"], "not_opened": [], "accepted_unverified": []},
        "findings": [{
            "claim": "row describes a file it does not measure", "severity": "important",
            "contract_quote": "must match the file it describes",
            "evidence": {"path": Path(__file__).name, "line": 1,
                         "quote": "#!/usr/bin/env python3"},
            "falsification": {"counter": "maybe the section is inlined", "survived": True,
                              "why": "grep shows zero occurrences in the measured file"},
        }],
        "halt": None,
    }


def _assert_fails(report: dict, needle: str, checks: list[int]) -> None:
    reasons = validate(report)
    assert any(needle in r for r in reasons), f"expected a reason containing {needle!r}, got {reasons}"
    checks.append(1)


def _ledger_branches(checks: list[int]) -> None:
    assert validate(_good()) == [], validate(_good())
    checks.append(1)
    report = _good(); del report["ledger"]["accepted_unverified"]
    _assert_fails(report, "accepted_unverified", checks)
    report = _good(); report["ledger"]["opened"] = []
    _assert_fails(report, "nothing was read", checks)


def _finding_branches(checks: list[int]) -> None:
    report = _good(); report["findings"][0]["evidence"]["quote"] = "  "
    _assert_fails(report, "unquoted is not a finding", checks)
    report = _good(); del report["findings"][0]["falsification"]
    _assert_fails(report, "no donor has this step", checks)
    report = _good(); report["findings"][0]["falsification"]["survived"] = False
    _assert_fails(report, "did not survive", checks)
    report = _good(); report["findings"] = []; report["halt"] = None
    _assert_fails(report, "zero findings must be declared", checks)
    report = _good(); report["findings"] = []
    report["halt"] = {"reason": "artifact is three lines of configuration"}
    assert validate(report) == [], validate(report)
    checks.append(1)
    report = _good(); report["findings"][0]["severity"] = "blocker"
    _assert_fails(report, "severity", checks)
    _assert_fails({"findings": []}, "artifact: missing", checks)
    assert validate("not an object") == ["report: must be a JSON object"]
    checks.append(1)


def _io_branches(checks: list[int]) -> None:
    with tempfile.TemporaryDirectory(prefix="critic gate ") as box:
        base = Path(box)
        for name, body in (("missing.json", None), ("empty.json", "   "), ("bad.json", "{nope")):
            path = base / name
            if body is not None:
                path.write_text(body, encoding="utf-8")
            try:
                load(path)
                raise AssertionError(f"{name} was accepted")
            except Unusable as exc:
                assert exc.code == 2, f"unusable input must exit 2, got {exc.code}"
            checks.append(1)


def _placeholder_branches(checks: list[int]) -> None:
    """The pattern SKILL-STANDARD names by name: `.`, empty string, TODO."""
    report = _good(); report["artifact"] = ""
    _assert_fails(report, "artifact", checks)

    report = _good(); report["ledger"]["opened"] = [""]
    _assert_fails(report, "nothing was read", checks)

    report = _good(); report["findings"] = []; report["halt"] = {"reason": "."}
    _assert_fails(report, "placeholder", checks)

    report = _good(); report["findings"][0]["falsification"]["counter"] = "TODO"
    _assert_fails(report, "placeholder", checks)


def _dropped_branches(checks: list[int]) -> None:
    """An honest negative must be recordable, not deletable."""
    report = _good()
    report["dropped"] = [{"candidate": "gate exceeds the function limit",
                          "counter": "Unusable.__init__ is a method, not a module function",
                          "why_it_died": "exactly 10 module-level defs"}]
    assert validate(report) == [], validate(report)
    checks.append(1)

    report = _good(); report["dropped"] = [{"candidate": "x"}]
    _assert_fails(report, "dropped[0]", checks)


def _fabricated_quote_branch(checks: list[int]) -> None:
    """A quote is evidence only when the cited artifact contains it at that line."""
    with tempfile.TemporaryDirectory(prefix="critic artifact ") as box:
        root = Path(box)
        (root / "a.md").write_text("the real line\n", encoding="utf-8")
        report = _good()
        report["artifact"] = str(root)
        report["findings"][0]["evidence"]["path"] = "a.md"
        report["findings"][0]["evidence"]["quote"] = "fabricated line"
        _assert_fails(report, "does not match artifact", checks)

        report = _good()
        report["artifact"] = str(root)
        report["findings"][0]["evidence"]["path"] = "missing.md"
        _assert_fails(report, "path:line is unreadable", checks)

        report = _good()
        report["artifact"] = str(root)
        report["findings"][0]["evidence"].update({"path": "a.md", "line": 0})
        _assert_fails(report, "positive integer", checks)


def _portable_artifact_branch(checks: list[int]) -> None:
    """Committed reports resolve artifact paths from the report, not the caller cwd."""
    with tempfile.TemporaryDirectory(prefix="critic portable ") as box:
        root = Path(box)
        artifact = root / "artifact"
        artifact.mkdir()
        (artifact / "a.md").write_text("the real line\n", encoding="utf-8")
        report = _good()
        report["artifact"] = "artifact"
        report["findings"][0]["evidence"] = {
            "path": "a.md", "line": 1, "quote": "the real line",
        }
        report_path = root / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        caller = root / "empty-caller-cwd"
        caller.mkdir()
        with chdir(caller):
            assert run(report_path) == 0, "relative artifact path must survive checkout relocation"
        checks.append(1)


def run_branches() -> int:
    checks: list[int] = []
    _ledger_branches(checks)
    _finding_branches(checks)
    _io_branches(checks)
    _placeholder_branches(checks)
    _dropped_branches(checks)
    _fabricated_quote_branch(checks)
    _portable_artifact_branch(checks)
    print(f"SELFCHECK OK — {len(checks)} branches, ignorance branches included")
    return 0
