#!/usr/bin/env python3
"""Selfcheck for the T3 strongest-donor promotion gate."""

from __future__ import annotations

import argparse

from eval_verdict import ATTACK_KEYS, render


def _arm(passes: tuple[bool, bool], *, tokens: int, wall_ms: int, tools: int,
         limits: bool = False, consistent: int = 3) -> dict:
    value = {
        "checks": [
            {"id": "defect", "assertion": "finds the real defect", "passed": passes[0], "evidence": "case A"},
            {"id": "clean", "assertion": "suppresses false positives", "passed": passes[1], "evidence": "case B"},
        ],
        "metrics": {"model": "same-model", "input_tokens": tokens - 2, "output_tokens": 2,
                    "wall_ms": wall_ms, "tool_calls": tools, "repeated_commands": 0,
                    "consistent_runs": consistent, "runs": 3,
                    "context_reuse": "not_available"},
    }
    if limits:
        value["limits"] = {"max_total_tokens": 30, "max_wall_ms": 100,
                           "max_tool_calls": 5, "max_repeated_commands": 0,
                           "min_consistency": 1.0}
    return value


def _critic() -> dict:
    return {
        "agent_type": "critic", "fork_turns": "none", "verdict": "PASS",
        "findings": [], "review_lanes": ["critic"],
        "reviewed_diff_sha256": "a" * 64, "transcript_sha256": "b" * 64,
        "graded_checks": [{"id": "c1", "passed": True, "evidence": "verified output"}],
        "attacks": {key: {
            "inventory": [f"bundle/{key}:negative-branch"],
            "probes": [{"target": f"bundle/{key}:negative-branch", "passed": True,
                        "evidence": f"forced {key} negative branch"}],
        } for key in ATTACK_KEYS},
        "model": "same-model", "input_tokens": "UNKNOWN", "output_tokens": "UNKNOWN",
        "wall_ms": 50,
    }


def selfcheck() -> int:
    baseline = _arm((False, True), tokens=10, wall_ms=30, tools=2)
    donor = _arm((False, True), tokens=15, wall_ms=40, tools=3)
    candidate = _arm((True, True), tokens=12, wall_ms=30, tools=2, limits=True)
    kwargs = {"donor": donor, "donor_label": "BMAD best applicable",
              "diff_sha256": "a" * 64, "transcript_sha256": "b" * 64}
    verdict, report = render("demo", baseline, candidate, _critic(), {"c1"}, **kwargs)
    assert verdict == "PASS" and "Donor BMAD best applicable" in report

    weaker_but_cheaper = _arm((False, True), tokens=10, wall_ms=20, tools=1)
    slower_but_better = _arm((True, True), tokens=16, wall_ms=40, tools=3, limits=True)
    better_kwargs = {**kwargs, "donor": weaker_but_cheaper}
    verdict, report = render("demo", baseline, slower_but_better, _critic(), {"c1"},
                             **better_kwargs)
    assert verdict == "PASS" and "Donor delta: tokens=+6" in report

    tied = _arm((True, True), tokens=15, wall_ms=40, tools=3, limits=True)
    tie_kwargs = {**kwargs, "donor": tied}
    verdict, report = render("demo", baseline, tied, _critic(), {"c1"}, **tie_kwargs)
    assert verdict == "FAIL" and "no strict quality win over donor" in report

    inconsistent = _arm((True, True), tokens=12, wall_ms=30, tools=2,
                        limits=True, consistent=2)
    verdict, report = render("demo", baseline, inconsistent, _critic(), {"c1"}, **kwargs)
    assert verdict == "FAIL" and "consistency" in report

    mismatched = _arm((True, True), tokens=12, wall_ms=30, tools=2, limits=True)
    mismatched["checks"][0]["id"] = "different-case"
    verdict, report = render("demo", baseline, mismatched, _critic(), {"c1"}, **kwargs)
    assert verdict == "FAIL" and "not a cohort" in report

    mismatched_baseline = _arm((False, True), tokens=10, wall_ms=30, tools=2)
    mismatched_baseline["checks"][0]["id"] = "different-baseline-case"
    verdict, report = render("demo", mismatched_baseline, candidate, _critic(), {"c1"},
                             **kwargs)
    assert verdict == "FAIL" and "not a cohort" in report
    print("SELFCHECK OK — donor quality, cost, determinism and strict-win gates block")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selfcheck", action="store_true")
    if not parser.parse_args().selfcheck:
        parser.error("--selfcheck")
    return selfcheck()


if __name__ == "__main__":
    raise SystemExit(main())
