"""Package contract — what an installer reads from the shipped tree, and two perimeter walks.

Behaviour is tested by running the shipped scripts (test_update_gates, test_end_*, test_merge_truth,
test_commit_*, ...). What stays here is what a machine reads: the marketplace manifest against the
tree, each frontmatter parsed the way the installer parses it, and two denylist walks that keep
private or unshippable things out of the public package.
"""

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SKILLS = ROOT / "skills"


def frontmatter(skill_md: Path) -> dict:
    raw = skill_md.read_text()
    assert raw.startswith("---\n"), f"{skill_md}: no frontmatter"
    return yaml.safe_load(raw.split("\n---\n", 1)[0].removeprefix("---\n"))


def shipped() -> set[str]:
    return {path.name for path in SKILLS.iterdir() if path.is_dir()}


def test_marketplace_exposes_the_same_skills_to_agent_skills_cli() -> None:
    marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    plugin = marketplace["plugins"][0]
    declared = {Path(path).name for path in plugin["skills"]}
    assert plugin["source"] == "./polaris"
    assert declared == shipped()
    for relative in plugin["skills"]:
        assert (ROOT / relative.removeprefix("./") / "SKILL.md").is_file()


def test_every_skill_frontmatter_loads_the_way_an_installer_reads_it() -> None:
    # The skills CLI and the agent hosts parse this block as strict YAML and skip, without an
    # error anyone sees, a skill whose block does not load (polaris-os#545: five skills, one
    # unquoted `: ` each). The limits are the Agent Skills ones the hosts warn on.
    for name in sorted(shipped()):
        meta = frontmatter(SKILLS / name / "SKILL.md")
        assert meta["name"] == name, f"{name}: frontmatter name is {meta['name']!r}"
        assert isinstance(meta["description"], str) and meta["description"].strip(), name
        assert len(meta["description"]) <= 1024, f"{name}: description is {len(meta['description'])} chars"
        assert meta["user-invocable"] is True, name


def test_no_shipped_skill_tells_the_user_to_run_the_memory_cli() -> None:
    # The memory CLI is experimental and does not ship: `npx skills` installs skill folders only,
    # so any step that runs it fails for every user of the package. Every file of every skill except
    # `eval/`, whose prompts are requests a user might type, not steps the skill runs.
    hits = []
    for skill in sorted(shipped()):
        for path in sorted((SKILLS / skill).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and "eval" not in path.relative_to(SKILLS / skill).parts:
                text = path.read_text(encoding="utf-8", errors="replace")
                if "polmem" in text or "polaris-memory" in text or "polaris_memory_repo" in text:
                    hits.append(str(path.relative_to(SKILLS)))
    assert hits == [], hits


def test_the_shipped_tree_carries_no_machine_path_and_no_real_login() -> None:
    """polaris#5 — the public package never leaves the private perimeter.

    A walk, not a list of files to check: a guard that names seven files has a hole the size of the
    eighth. What IS a list, deliberately, is the exemption — each path named with its reason, so an
    exemption cannot be granted by accident the way a `# perimeter-guard` comment anywhere in the
    tree could.
    """
    allowed = {
        "polaris/bin/polaris-update": "the repository's own public slug, in its own installer",
        "polaris/.claude-plugin/plugin.json": "the plugin author URL — identity, not leakage",
        "polaris/scripts/check_skills.sh": "the denylist guard: the needles ARE its subject",
        "polaris/tests/test_team_os_contract.py": "this test: the needles are its subject too",
    }
    needles = re.compile(r"/Users/|All Vibe|nichome|legacynik")
    offenders = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(REPO).as_posix()
        if not path.is_file() or relative in allowed or "__pycache__" in relative:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        offenders += [f"{relative}:{n}" for n, line in enumerate(text.splitlines(), 1)
                      if needles.search(line)]
    assert offenders == [], f"the package ships a private-perimeter string: {offenders}"
