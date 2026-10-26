"""grill opens the plan file: the skeleton is a `discovery` plan the vault's checker accepts."""
import re
import shutil
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
SKELETON = SKILL / "references" / "plan-file.md"
CHECKER = SKILL.parents[1] / "scripts" / "check_plan_files.py"
sys.path.insert(0, str(SKILL.parent / "_standard"))
import validate_suite  # noqa: E402

SECTIONS = ["Area", "Why and outcome", "Discovery", "Prototype verdicts", "Contracts",
            "DoD and regression checks", "Approach", "Links", "Trajectory changes"]


def test_passes_the_suite_gate():
    assert validate_suite.run(SKILL) == 0


def test_skeleton_carries_the_nine_sections_in_order():
    text = SKELETON.read_text(encoding="utf-8")
    found = re.findall(r"^## (\d)\. (.+)$", text, re.M)
    assert found == [(str(i), s) for i, s in enumerate(SECTIONS, 1)], found


@pytest.mark.skipif(not CHECKER.is_file(), reason="check_plan_files.py ships with the vault only")
def test_skeleton_is_a_discovery_plan_the_checker_accepts(tmp_path):
    sys.path.insert(0, str(CHECKER.parent))
    import check_plan_files
    rel = "docs/areas/demo/plans/open/2026-10-24-demo.md"
    (tmp_path / rel).parent.mkdir(parents=True)
    shutil.copy(SKELETON, tmp_path / rel)
    assert check_plan_files._status((tmp_path / rel).read_text()) == "discovery"
    assert check_plan_files.findings(tmp_path, [rel]) == []
