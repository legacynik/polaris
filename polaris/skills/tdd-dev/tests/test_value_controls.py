"""Execute every calibrated candidate through the grader's public interface."""
import json
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from test_value_grade import grade

FEATURES = SKILL / "eval" / "behaviour"
CASES = [(feature, case) for feature in sorted(FEATURES.iterdir())
         for case in json.loads((feature / "cases.json").read_text())]


@pytest.mark.parametrize("feature, case", CASES,
                         ids=[f"{f.name}/{c['file']}" for f, c in CASES])
def test_frozen_test_value(feature, case):
    report = grade(feature, feature / case["file"])
    assert report["verdict"] == case["verdict"], report
    if case["reason"]:
        assert case["reason"] in report["reasons"], report
