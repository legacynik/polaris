"""An AttributeError raised by production code on the new input is missing behaviour, not a staged RED;
the same error raised by the test reaching for a function that does not exist yet is staged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_value_grade import grade  # noqa: E402

BASE = "def norm(x):\n    return x.lower()\n"
SOLUTION = "def norm(x):\n    return '' if x is None else x.lower()\n"
REFACTOR = "def norm(x):\n    return (x or '').lower()\n"
MUTANTS = {"upper": SOLUTION.replace("x.lower()", "x.upper()"), "none_is_dash": SOLUTION.replace("''", "'-'")}


def _feature(root: Path) -> Path:
    for name, body in {"base": BASE, "solution": SOLUTION, "refactor": REFACTOR}.items():
        (root / name).mkdir(parents=True)
        (root / name / "feature.py").write_text(body)
    for name, body in MUTANTS.items():
        (root / "mutants" / name).mkdir(parents=True)
        (root / "mutants" / name / "feature.py").write_text(body)
    (root / "spec.md").write_text("norm(None) returns ''\n")
    return root


def _grade(tmp_path: Path, body: str) -> dict:
    candidate = tmp_path / "test_candidate.py"
    candidate.write_text(body)
    return grade(_feature(tmp_path / "feature"), candidate)


def test_production_attribute_error_on_base_is_a_valid_red(tmp_path):
    body = "from feature import norm\n\ndef test_none():\n    assert norm(None) == ''\n\ndef test_text():\n    assert norm('AB') == 'ab'\n"
    assert _grade(tmp_path, body)["verdict"] == "VALUABLE"


def test_missing_function_reached_by_the_test_stays_staged(tmp_path):
    body = "import feature\n\ndef test_none():\n    assert feature.normalise(None) == ''\n"
    assert "staged_red" in _grade(tmp_path, body)["reasons"]
