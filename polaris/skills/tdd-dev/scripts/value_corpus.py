"""Calibrate the outcome grader against pinned controls, not prose claims."""
import json
import sys
from pathlib import Path

from test_value_grade import grade

FEATURES = ("price", "slug", "window")


def _check_case(feature: Path, case: dict) -> dict | None:
    report = grade(feature, feature / case["file"])
    reason_matches = case["reason"] is None or case["reason"] in report["reasons"]
    if report["verdict"] == case["verdict"] and reason_matches:
        return None
    return {"feature": feature.name, "candidate": case["file"], "expected": case["verdict"],
            "actual": report["verdict"], "reasons": report["reasons"]}


def check_fixtures(root: Path) -> dict:
    checked, failures = 0, []
    for name in FEATURES:
        feature = root / name
        cases = json.loads((feature / "cases.json").read_text())
        declared = {case["file"] for case in cases}
        present = {str(path.relative_to(feature)) for path in (feature / "candidates").glob("*.py")}
        if not cases or declared != present or len(declared) != len(cases):
            raise ValueError(f"{name}: candidates must be listed exactly once in cases.json")
        for case in cases:
            failure = _check_case(feature, case)
            checked += 1
            if failure:
                failures.append(failure)
    return {"checked": checked, "failures": failures}


if __name__ == "__main__":
    if sys.argv[1:] != ["--selfcheck"]:
        sys.exit(2)
    result = check_fixtures(Path(__file__).resolve().parents[1] / "eval" / "behaviour")
    print(json.dumps(result))
    sys.exit(1 if result["failures"] else 0)
