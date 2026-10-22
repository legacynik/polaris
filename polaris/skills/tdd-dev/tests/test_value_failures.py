"""Disasters at the grader's public interface: setup is not behaviour and crashes are not kills."""
import shutil
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from test_value_grade import grade

PRICE = SKILL / "eval" / "behaviour" / "price"


@pytest.mark.parametrize("body", [
    "from absent_module import round_price\n",
    "def round_price(text):\n    raise ImportError('missing adapter')\n",
], ids=["collection", "call"])
def test_import_only_red_is_staged(tmp_path, body):
    feature = tmp_path / "price"
    shutil.copytree(PRICE, feature)
    (feature / "base" / "feature.py").write_text(body)
    report = grade(feature, feature / "candidates" / "good_1.py")
    assert report["verdict"] == "WEAK"
    assert report["fails_on_base_at_assertion"] is False
    assert "staged_red" in report["reasons"], report


@pytest.mark.parametrize("body", [
    "def round_price(text):\n    assert False, 'production assertion'\n",
    "def round_price(text):\n    raise RuntimeError('crashed')\n",
    "from absent_module import round_price\n",
], ids=["production_assertion", "runtime_crash", "collection"])
def test_a_crashed_mutant_is_not_a_kill(tmp_path, body):
    feature = tmp_path / "price"
    shutil.copytree(PRICE, feature)
    (feature / "mutants" / "toward_zero" / "feature.py").write_text(body)
    report = grade(feature, feature / "candidates" / "good_1.py")
    assert report["verdict"] == "WEAK"
    assert report["kills"]["toward_zero"] is False
    assert "mutant_not_assertion:toward_zero" in report["reasons"]


def test_a_candidate_that_rewrites_itself_is_not_frozen(tmp_path):
    candidate = tmp_path / "candidate.py"
    candidate.write_text("from pathlib import Path\n\ndef test_mutating():\n"
                         "    Path(__file__).write_text('# rewritten')\n    assert True\n")
    before = candidate.read_bytes()
    report = grade(PRICE, candidate)
    assert report["byte_identical"] is False
    assert "test_changed" in report["reasons"]
    assert candidate.read_bytes() == before


@pytest.mark.parametrize("body", [
    "",
    "import pytest\n\n@pytest.mark.skip(reason='not executed')\ndef test_skip():\n    pass\n",
])
def test_no_executed_test_never_counts_as_a_pass(tmp_path, body):
    candidate = tmp_path / "candidate.py"
    candidate.write_text(body)
    report = grade(PRICE, candidate)
    assert report["passes_on_solution"] is False
    assert report["verdict"] == "WEAK"
