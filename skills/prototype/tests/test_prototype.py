"""prototype passes the suite gate and credits the skill it was imported from."""
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parent / "_standard"))
import validate_suite  # noqa: E402


def test_passes_the_suite_gate():
    assert validate_suite.run(SKILL) == 0


def test_credits_name_the_upstream_and_its_license():
    credits = (SKILL / "CREDITS.md").read_text(encoding="utf-8")
    assert "mattpocock/skills" in credits and "MIT" in credits
