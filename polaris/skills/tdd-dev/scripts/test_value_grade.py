#!/usr/bin/env python3
"""Grade a frozen candidate through base, solution, private refactor and behavioural mutants."""
import argparse
import json
import sys
from pathlib import Path

from value_run import run_variant


def _variants(feature: Path) -> dict:
    mutants = sorted((feature / "mutants").iterdir()) if (feature / "mutants").is_dir() else []
    if len(mutants) < 2 or not (feature / "spec.md").is_file():
        raise ValueError("fixture requires spec.md and at least two mutant directories")
    variants = {name: feature / name for name in ("base", "solution", "refactor")}
    variants.update({f"mutants/{path.name}": path for path in mutants})
    if not all(path.is_dir() for path in variants.values()):
        raise ValueError("fixture requires base, solution, refactor and mutant directories")
    return variants


def _base_red(base: dict) -> bool:
    """Before the feature, a test assertion OR an exception from the call is the missing behaviour;
    import and collection failures stay staged."""
    return base["assertion_failure"] or base.get("call_failure", False)


def _reasons(runs: dict, identical: bool) -> list:
    reasons = []
    if not _base_red(runs["base"]):
        base = runs["base"]
        staged = base["exit"] == 2 or base.get("staged", False)
        failure = "staged_red" if staged else "base_not_assertion"
        reasons.append("base_passed" if base["passed"] else failure)
    for name in ("solution", "refactor"):
        if not runs[name]["passed"]:
            reasons.append(f"{name}_failed")
    for name, run in runs.items():
        if name.startswith("mutants/") and not run["assertion_failure"]:
            kind = "mutant_survived" if run["passed"] else "mutant_not_assertion"
            reasons.append(f"{kind}:{name.partition('/')[2]}")
    if not identical:
        reasons.append("test_changed")
    return reasons


def grade(feature: Path, candidate: Path) -> dict:
    """Return observed outcomes; candidate bytes are never rewritten to fit a variant."""
    feature, candidate = Path(feature), Path(candidate)
    frozen = candidate.read_bytes()
    runs = {name: run_variant(path, candidate) for name, path in _variants(feature).items()}
    identical = candidate.read_bytes() == frozen and all(run["byte_identical"] for run in runs.values())
    reasons = _reasons(runs, identical)
    return {"fails_on_base_at_assertion": _base_red(runs["base"]),
            "passes_on_solution": runs["solution"]["passed"],
            "survives_refactor": runs["refactor"]["passed"],
            "kills": {name.partition("/")[2]: run["assertion_failure"]
                      for name, run in runs.items() if name.startswith("mutants/")},
            "byte_identical": identical, "verdict": "WEAK" if reasons else "VALUABLE",
            "reasons": reasons, "runs": runs}


def _request(args) -> tuple[dict, bool]:
    if args.check_fixtures:
        from value_corpus import check_fixtures
        report = check_fixtures(Path(__file__).resolve().parents[1] / "eval" / "behaviour")
        return report, not report["failures"]
    if args.feature is None or args.candidate is None:
        raise ValueError("provide a feature directory and candidate file, or --check-fixtures")
    report = grade(args.feature, args.candidate)
    return report, report["verdict"] == "VALUABLE"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature", nargs="?", type=Path)
    parser.add_argument("candidate", nargs="?", type=Path)
    parser.add_argument("--check-fixtures", "--selfcheck", action="store_true",
                        help="execute every pinned good/negative control; exit 1 on disagreement")
    args = parser.parse_args()
    try:
        report, passed = _request(args)
    except (OSError, ValueError) as error:
        print(json.dumps({"verdict": "WEAK", "reasons": ["input_error"], "error": str(error)}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
