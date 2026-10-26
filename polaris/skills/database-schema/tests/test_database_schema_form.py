"""The skill passes the suite gate on its own, with no allowlist line to excuse it."""
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parent / "_standard"))
import validate_suite  # noqa: E402


def test_passes_the_suite_gate():
    assert validate_suite.run(SKILL) == 0
