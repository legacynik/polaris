"""Staging is decided on the exception object, not on console text: a field missing from what the
base returns is the missing behaviour; a name missing from the module under test is staged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_value_grade import grade  # noqa: E402

BASE = "class Quote:\n    def __init__(self, total):\n        self.total = total\n\ndef price(total):\n    return Quote(total)\n"
SOLUTION = BASE.replace("self.total = total", "self.total = total\n        self.discount = total // 20")
REFACTOR = "from types import SimpleNamespace\n\ndef price(total):\n    return SimpleNamespace(total=total, discount=int(total * 0.05))\n"
MUTANTS = {"ten_pct": SOLUTION.replace("// 20", "// 10"), "no_total": SOLUTION.replace("self.total = total", "self.total = 0")}


def _feature(root: Path) -> Path:
    for name, body in {"base": BASE, "solution": SOLUTION, "refactor": REFACTOR}.items():
        (root / name).mkdir(parents=True)
        (root / name / "feature.py").write_text(body)
    for name, body in MUTANTS.items():
        (root / "mutants" / name).mkdir(parents=True)
        (root / "mutants" / name / "feature.py").write_text(body)
    (root / "spec.md").write_text("price(total).discount is 5% of total\n")
    return root


def _grade(tmp_path: Path, body: str) -> dict:
    candidate = tmp_path / "test_candidate.py"
    candidate.write_text(body)
    return grade(_feature(tmp_path / "feature"), candidate)


def test_field_missing_from_the_returned_value_is_a_valid_red(tmp_path):
    body = "from feature import price\n\ndef test_discount():\n    q = price(100)\n    assert (q.total, q.discount) == (100, 5)\n"
    assert _grade(tmp_path, body)["verdict"] == "VALUABLE"


def test_function_missing_from_the_module_is_staged(tmp_path):
    body = "import feature\n\ndef test_discount():\n    assert feature.discount_for(100) == 5\n"
    assert "staged_red" in _grade(tmp_path, body)["reasons"]
