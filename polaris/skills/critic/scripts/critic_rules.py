#!/usr/bin/env python3
"""critic_rules — what makes a critic report valid, as an importable library.

Split from the CLI so the rules stay unit-testable without spawning a process,
and so each file stays inside the repo's size limits. `critic_gate.py` is a thin
wrapper over this; both are pure stdlib.

Three failures were measured on three naked baseline runs over one artifact
(2026-08-21) and these rules exist to make each one impossible:
  1. no declaration of what was opened versus accepted -> `ledger` is mandatory
  2. a shape that varied run to run -> the schema is the shape
  3. a cited reference accepted unchecked -> every finding carries the
     counter-argument it survived

Placeholders are rejected uniformly. The donor's gate demoted an unquoted
finding into a band its own table still displayed, so the suppression leaked;
here there is no band and no field is exempt from the same emptiness test.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SEVERITIES = {"critical", "important", "minor"}
PLACEHOLDERS = {".", "-", "n/a", "na", "todo", "tbd", "your-key-here", "x", "?"}
DROPPED_FIELDS = ("candidate", "counter", "why_it_died")
REQUIRED_TOP = ("artifact", "contract", "ledger", "findings")
REQUIRED_LEDGER = ("opened", "not_opened", "accepted_unverified")


def blank(value: object) -> bool:
    """Empty, whitespace, or a placeholder the standard forbids by name."""
    text = str(value or "").strip()
    return not text or text.lower() in PLACEHOLDERS


def check_ledger(ledger: object, reasons: list[str]) -> None:
    """A critic that opened nothing verified nothing."""
    if not isinstance(ledger, dict):
        reasons.append("ledger: must be an object")
        return
    for key in REQUIRED_LEDGER:
        if key not in ledger:
            reasons.append(f"ledger.{key}: missing — the declaration is the point")
        elif not isinstance(ledger[key], list):
            reasons.append(f"ledger.{key}: must be a list")
    opened = ledger.get("opened")
    if isinstance(opened, list) and not [x for x in opened if not blank(x)]:
        reasons.append("ledger.opened: empty — nothing was read, so nothing was verified")


def check_evidence(finding: dict, index: int, reasons: list[str], artifact_root: Path | None) -> None:
    """Quote or it is not a finding. No demotion band: the donor's leaked."""
    evidence = finding.get("evidence")
    if not isinstance(evidence, dict):
        reasons.append(f"findings[{index}].evidence: missing")
        return
    path_value = evidence.get("path")
    if blank(path_value):
        reasons.append(f"findings[{index}].evidence.path: missing")
        return
    quote = evidence.get("quote")
    if blank(quote):
        reasons.append(f"findings[{index}].evidence.quote: missing — unquoted is not a finding")
        return
    line = evidence.get("line")
    if type(line) is not int or line < 1:
        reasons.append(f"findings[{index}].evidence.line: must be a positive integer")
        return
    if artifact_root is None:
        return
    try:
        source = (artifact_root / str(path_value)).resolve()
        source.relative_to(artifact_root)
        source_line = source.read_text(encoding="utf-8", errors="replace").splitlines()[line - 1]
    except (OSError, IndexError, ValueError):
        reasons.append(f"findings[{index}].evidence: cited path:line is unreadable")
        return
    if str(quote) not in source_line:
        reasons.append(f"findings[{index}].evidence.quote: does not match artifact path:line")


def check_falsification(finding: dict, index: int, reasons: list[str]) -> None:
    """No donor does this: the counter-argument must be attempted and must fail."""
    falsification = finding.get("falsification")
    if not isinstance(falsification, dict):
        reasons.append(f"findings[{index}].falsification: missing — no donor has this step")
        return
    if blank(falsification.get("counter")):
        reasons.append(f"findings[{index}].falsification.counter: missing or placeholder")
    if falsification.get("survived") is not True:
        reasons.append(f"findings[{index}]: did not survive its own counter-argument — drop it")


def check_finding(finding: object, index: int, reasons: list[str], artifact_root: Path | None,
                  contract: object) -> None:
    if not isinstance(finding, dict):
        reasons.append(f"findings[{index}]: must be an object")
        return
    if blank(finding.get("claim")):
        reasons.append(f"findings[{index}].claim: missing")
    contract_quote = finding.get("contract_quote")
    if blank(contract_quote):
        reasons.append(f"findings[{index}].contract_quote: missing")
    elif str(contract_quote) not in str(contract):
        reasons.append(f"findings[{index}].contract_quote: does not match contract")
    if finding.get("severity") not in SEVERITIES:
        reasons.append(f"findings[{index}].severity: must be one of {sorted(SEVERITIES)}")
    check_evidence(finding, index, reasons, artifact_root)
    check_falsification(finding, index, reasons)


def check_halt(report: dict, reasons: list[str]) -> None:
    """Zero findings is suspicious until it is declared (BMAD's halt-on-zero)."""
    halt = report.get("halt")
    if not isinstance(halt, dict) or blank(halt.get("reason")):
        reasons.append("findings: empty and halt.reason absent or placeholder — zero findings must be declared")


def check_required(report: dict, reasons: list[str]) -> None:
    """Present is not the same as filled: an empty field reviewed nothing."""
    for key in REQUIRED_TOP:
        if key not in report:
            reasons.append(f"{key}: missing")
        elif key in ("artifact", "contract") and blank(report[key]):
            reasons.append(f"{key}: empty or placeholder — a report about nothing reviewed nothing")


def validate(report: object, artifact_base: Path | None = None) -> list[str]:
    reasons: list[str] = []
    if not isinstance(report, dict):
        return ["report: must be a JSON object"]
    check_required(report, reasons)
    artifact_root = None
    if not blank(report.get("artifact")):
        candidate = Path(str(report["artifact"]))
        if artifact_base is not None and not candidate.is_absolute():
            candidate = artifact_base / candidate
        candidate = candidate.resolve()
        if not candidate.is_dir():
            reasons.append("artifact: must be a readable materialized directory")
        else:
            artifact_root = candidate
    if "ledger" in report:
        check_ledger(report["ledger"], reasons)
    findings = report.get("findings")
    if not isinstance(findings, list):
        reasons.append("findings: must be a list")
        return reasons
    if not findings:
        check_halt(report, reasons)
    for index, finding in enumerate(findings):
        check_finding(finding, index, reasons, artifact_root, report.get("contract"))
    check_dropped(report, reasons)
    return reasons




def check_dropped(report: dict, reasons: list[str]) -> None:
    """A candidate that was tried and killed is evidence, not litter."""
    for index, entry in enumerate(report.get("dropped") or []):
        missing = [f for f in DROPPED_FIELDS if not isinstance(entry, dict) or blank(entry.get(f))]
        if missing:
            reasons.append(f"dropped[{index}]: needs {', '.join(missing)} — a killed candidate is evidence")


def main(argv: list[str] | None = None) -> int:
    """The rules are exercised by the gate's own selfcheck; this entry point exists
    so the library is verifiable on its own terms, as T1 requires of every script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selfcheck", action="store_true")
    if not parser.parse_args(argv).selfcheck:
        parser.error("--selfcheck")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from critic_gate_selfcheck import run_branches

    return run_branches()


if __name__ == "__main__":
    sys.exit(main())
