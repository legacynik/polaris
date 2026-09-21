"""The `init` door ships as a door, and never carries the harness it calls."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "init" / "SKILL.md"


def front_matter() -> dict[str, str]:
    raw = SKILL.read_text()
    assert raw.startswith("---\n"), "SKILL.md must open with frontmatter"
    block = raw.split("\n---\n", 1)[0]
    return dict(re.findall(r"(?m)^([a-z-]+):\s*(.*)$", block))


def test_it_is_a_door_with_a_version() -> None:
    front = front_matter()
    assert front["name"] == "init"
    assert front["description"].startswith("◇ ")
    assert re.fullmatch(r"\d+\.\d+\.\d+", front["version"])
    assert front["user-invocable"] == "true"


def test_it_is_at_most_150_lines() -> None:
    assert len(SKILL.read_text().splitlines()) <= 150


def test_it_walks_the_four_founder_steps_in_order() -> None:
    body = SKILL.read_text()
    steps = [body.index(needle) for needle in ("audit --root", "propose --root",
                                               "apply --mode minimal", "contextpack.py")]
    assert steps == sorted(steps), "audit → propose → apply → pack must stay in order"
    assert "wait" in body.casefold(), "the plan is signed before apply runs"


def test_it_resolves_the_harness_and_stays_silent_without_one() -> None:
    body = SKILL.read_text()
    assert "git config --get polaris.vault" in body
    assert "no harness declared here" in body
    assert "exit 0" in body, "a repository with no vault is not an error"


def test_it_ships_no_copy_of_the_harness() -> None:
    shipped = [path.name for path in (ROOT / "skills" / "init").rglob("*")]
    assert "polaris_init.py" not in shipped, "the package must not vendor the harness"
    assert "check_context_backbone.py" not in shipped


def test_it_refuses_to_create_areas() -> None:
    body = " ".join(SKILL.read_text().casefold().split())
    assert "never derived" in body
    assert "proposed and signed" in body
