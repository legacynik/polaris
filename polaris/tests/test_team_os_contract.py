"""Release contract for the small, repository-first Polaris Team OS surface."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
TEMPLATES = ROOT / "templates" / "repo-contract"


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
    # plan-week must pull live issues; report must gather tracker evidence.
    assert "gh issue list" in plan
    assert "weekly_capacity" in plan
    assert "gh pr list" in report
    assert "gh issue list" in report


def test_report_uses_login_evidence_not_local_git_identity() -> None:
    # The off-by-one + wrong-identity defects from the live benchmark: the report
    # must query the tracker by the contributor's GitHub login and must NOT fall
    # back to git-author-by-local-email (resolves to the running machine, useless
    # for a teammate report).
    report = (SKILLS / "report" / "SKILL.md").read_text()
    assert 'git config user.email' not in report or 'Never use' in report
    assert 'author:$LOGIN' in report


def test_report_pins_the_iso_week_computation() -> None:
    # Week = ISO week of the reported period; the evidence window is derived from
    # WEEK so filename and evidence cannot disagree (the W29-vs-W28 misfile).
    report = (SKILLS / "report" / "SKILL.md").read_text()
    assert "date +%G-W%V" in report
    assert "fromisocalendar" in report


def test_plan_week_ranks_severity_over_staleness_and_grounds_scope() -> None:
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    flat = " ".join(plan.split())
    assert "[CRITICAL]" in plan  # severity signal in the title is a first-tier rank
    assert "severity outranks age" in flat
    # staleness must be introduced after the severity rule (final tiebreak only).
    assert flat.index("severity outranks age") < flat.index("final tiebreak")
    # scope grounding when preferred_areas is empty.
    assert "preferred_areas` is empty" in plan
    assert "CODEOWNERS" in plan


def test_start_handles_not_memory_wired_without_running_init() -> None:
    start = (SKILLS / "start" / "SKILL.md").read_text()
    flat = " ".join(start.split())
    assert "not memory-wired" in start
    assert "Do not run `polmem init` yourself" in start
    # recall is assumed context, not current state.
    assert "not current state" in flat


def test_repo_contract_templates_exist_are_english_and_match_worked_examples() -> None:
    for name in ("config.yml", "profile.yml", "weekly-plan.md", "weekly-report.md",
                 "state.gitignore"):
        assert (TEMPLATES / name).is_file(), f"missing template {name}"

    plan_tpl = (TEMPLATES / "weekly-plan.md").read_text()
    report_tpl = (TEMPLATES / "weekly-report.md").read_text()

    # English, reconciled to the skills' worked examples — no residual Italian headers.
    for stale in ("Previsto vs consegnato", "Lavoro proposto", "Non iniziare", "Cosa abbiamo"):
        assert stale not in plan_tpl and stale not in report_tpl

    # Headers must match the skills' worked examples exactly.
    plan_skill = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report_skill = (SKILLS / "report" / "SKILL.md").read_text()
    for header in ("## Outcome", "## Not starting", "## Evidence"):
        assert header in plan_tpl and header in plan_skill
    for header in ("## Planned versus actual", "## What we learned", "## Blocker and next week"):
        assert header in report_tpl and header in report_skill

    # Contributor schema is explicit about the exact GitHub login.
    config_tpl = (TEMPLATES / "config.yml").read_text()
    profile_tpl = (TEMPLATES / "profile.yml").read_text()
    assert "exact GitHub login" in config_tpl
    assert "exact GitHub login" in profile_tpl


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
