"""A base that raises on input the feature must accept is the missing behaviour: a valid RED."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_value_grade import grade  # noqa: E402

BASE = "def parse(text):\n    if text.endswith('s'):\n        return int(text[:-1])\n    raise ValueError(text)\n"
SOLUTION = "def parse(text):\n    unit = {'s': 1, 'm': 60}[text[-1]]\n    return int(text[:-1]) * unit\n"
REFACTOR = "_U = (('m', 60), ('s', 1))\n\ndef parse(text):\n    return int(text[:-1]) * dict(_U)[text[-1]]\n"
MUTANTS = {"minutes_x100": SOLUTION.replace("60", "100"), "seconds_x2": SOLUTION.replace("'s': 1", "'s': 2")}
CANDIDATE = "from feature import parse\n\ndef test_minutes():\n    assert parse('2m') == 120\n\ndef test_seconds():\n    assert parse('5s') == 5\n"


def _feature(root: Path) -> Path:
    for name, body in {"base": BASE, "solution": SOLUTION, "refactor": REFACTOR}.items():
        (root / name).mkdir(parents=True)
        (root / name / "feature.py").write_text(body)
    for name, body in MUTANTS.items():
        (root / "mutants" / name).mkdir(parents=True)
        (root / "mutants" / name / "feature.py").write_text(body)
    (root / "spec.md").write_text("parse('<n>m') returns seconds\n")
    return root


def test_base_raising_on_the_new_input_is_a_valid_red(tmp_path):
    candidate = tmp_path / "test_candidate.py"
    candidate.write_text(CANDIDATE)
    report = grade(_feature(tmp_path / "feature"), candidate)
    assert (report["verdict"], report["fails_on_base_at_assertion"]) == ("VALUABLE", True)
