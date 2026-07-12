"""Release contract for the small, repository-first Polaris Team OS surface."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def test_only_the_team_lifecycle_commands_are_shipped() -> None:
    assert {path.name for path in SKILLS.iterdir() if path.is_dir()} == {
        "start",
        "update",
        "end",
        "plan-week",
        "report",
    }


def test_every_command_is_repo_first_and_not_founder_vault_based() -> None:
    for skill in SKILLS.glob("*/SKILL.md"):
        text = skill.read_text()
        assert "user-invocable: true" in text
        assert "POLARIS_VAULT" not in text
        assert "Desktop/All Vibe Proj" not in text


def test_the_new_commands_have_one_shared_team_contract() -> None:
    start = (SKILLS / "start" / "SKILL.md").read_text()
    update = (SKILLS / "update" / "SKILL.md").read_text()
    end = (SKILLS / "end" / "SKILL.md").read_text()
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()

    assert "`polaris/`" in start
    assert "`_polaris/`" in start
    for lifecycle_skill in (start, update, end):
        assert "state/current.md" in lifecycle_skill
        assert "overwrite" in lifecycle_skill.lower()
    assert "does not create issues, branches, pull requests or assignments" in " ".join(
        plan.split()
    )
    assert "planned versus actual" in report


def test_evidence_skills_pin_the_iso_week_filename_convention() -> None:
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()
    # plan-week writes weeks/YYYY-Www.md, report writes reports/YYYY-Www.md — lock both.
    assert "weeks/YYYY-Www.md" in plan
    assert "reports/YYYY-Www.md" in report


def test_evidence_skills_ship_concrete_tracker_commands() -> None:
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()
    # plan-week must pull live issues; report must gather git + tracker evidence.
    assert "gh issue list" in plan
    assert "weekly_capacity" in plan
    assert "git log --since" in report
    assert "gh pr list" in report


def test_lifecycle_skills_verify_the_branch() -> None:
    for name in ("start", "end"):
        text = (SKILLS / name / "SKILL.md").read_text()
        assert "git rev-parse --abbrev-ref HEAD" in text


def test_onboarding_contains_a_real_tooling_preflight() -> None:
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()

    for required in (
        "superpowers@claude-plugins-official",
        "context7@claude-plugins-official",
        "claude plugin list",
        "claude mcp list",
        "codebase-memory-mcp",
    ):
        assert required in onboarding
