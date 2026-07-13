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

    assert "`_polaris/`" in start
    for lifecycle_skill in (start, update, end):
        assert "state/current.md" in lifecycle_skill
        assert "overwrite" in lifecycle_skill.lower()
    assert "does not create issues, branches, pull requests or assignments" in " ".join(
        plan.split()
    )
    assert "planned versus actual" in report


def test_contract_root_is_single_underscore_polaris() -> None:
    # The Polaris root is `_polaris/`, full stop — the dual-root (`polaris/` or
    # `_polaris/`) resolver was a drift from the convention every product repo
    # already uses, and "root chosen per-repo" is exactly how one repo ended up
    # carrying both.
    start = (SKILLS / "start" / "SKILL.md").read_text()
    update = (SKILLS / "update" / "SKILL.md").read_text()
    readme = (ROOT.parent / "README.md").read_text()
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()

    assert "_polaris/config.yml" in start
    for text in (start, update, readme, onboarding):
        flat = " ".join(text.split())
        assert "`polaris/` or `_polaris/`" not in flat
        assert "`polaris/` if" not in flat


def test_start_provisions_own_path_from_the_real_github_login() -> None:
    # A contributor's path is created on THEIR machine from THEIR GitHub login
    # (`gh api user`) — never pre-created for someone else and never guessed:
    # placeholder folders (team/jeanpierre) break every gh evidence query.
    start = (SKILLS / "start" / "SKILL.md").read_text()
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()

    assert "gh api user --jq .login" in start
    assert "Never create `team/<login>/` folders for other people" in start
    assert "gh api user --jq .login" in onboarding
    assert "Never create a `team/` folder for a teammate" in onboarding


def test_plans_and_reports_are_authored_by_their_owner() -> None:
    # Locked 2026-07-13: the contributor writes THEIR OWN plan (/plan-week runs
    # on their machine, in their own team/<login>/weeks/); the CEO signs it but
    # never writes it for them. Worked examples must not model placeholder
    # logins (team/jeanpierre) — that is the exact pattern that shipped a broken
    # contract into a product repo.
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()

    assert "Never write another contributor's plan" in " ".join(plan.split())
    for text in (plan, report):
        assert "team/jeanpierre" not in text
        assert "team/giovanni" not in text


def test_end_feeds_the_repo_journal() -> None:
    # The daily loop closes the memory cycle mechanically: /start consumes
    # (recall), /end FEEDS — one machine-readable line into the repo journal
    # via polmem remember; the offline distill decides what is durable. Without
    # this, the graph only grows when someone remembers to propose a decision.
    end = (SKILLS / "end" / "SKILL.md").read_text()
    assert "polmem remember" in end
    assert "not memory-wired" in end  # same failure branch as /start


def test_lessons_are_part_of_the_contract() -> None:
    # Product repos carry lessons.md next to decisions.md; /end proposes durable
    # lessons the same gated way it proposes decisions.
    end = (SKILLS / "end" / "SKILL.md").read_text()
    readme = (ROOT.parent / "README.md").read_text()
    assert "lessons.md" in end
    assert "lessons.md" in readme


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
    # The report is ground-truth-first: remote synced, commits resolved
    # login->commits SERVER-SIDE (the REAL test proved an author-email pattern
    # returns 0 on a real repo: squash commits carry the user's configured
    # email, e.g. gmail, not the noreply form), session logs as the day-by-day
    # backbone, decisions.md scanned in-range.
    assert "git fetch --prune" in report
    assert "commits?author=$LOGIN" in report
    assert "@users.noreply.github.com" not in report
    assert "team/<login>/sessions/" in report
    assert "decisions.md" in report


def test_report_is_a_real_report_not_just_a_diff_table() -> None:
    # Locked 2026-07-13: "il report non deve essere solo planned/actual" — the
    # real weekly reports (noemi W20–W27) carry a TL;DR, day-by-day evidence,
    # merged-PR ground truth, metrics, and an explicit PM-action section. The
    # skill and template pin that structure, and scale down honestly.
    report = (SKILLS / "report" / "SKILL.md").read_text()
    report_tpl = (TEMPLATES / "weekly-report.md").read_text()
    for header in ("## TL;DR", "## Planned versus actual", "## Metrics",
                   "## PM action", "## Next week"):
        assert header in report, f"missing {header} in skill"
        assert header in report_tpl, f"missing {header} in template"
    assert "never pad" in " ".join(report.split())


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
                 "state.gitignore", "README.md"):
        assert (TEMPLATES / name).is_file(), f"missing template {name}"

    # The root README is the contract's front door: it must pin the single root,
    # own-path provisioning, the signature gate and the privacy boundary.
    root_readme = (TEMPLATES / "README.md").read_text()
    for required in (
        "One root: `_polaris/`",
        "Never create another contributor's path",
        "ceo_signature: pending",
        "Privacy boundaries",
    ):
        assert required in root_readme

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
    for header in ("## TL;DR", "## Planned versus actual", "## PM action"):
        assert header in report_tpl and header in report_skill

    # Contributor schema is explicit about the exact GitHub login.
    config_tpl = (TEMPLATES / "config.yml").read_text()
    profile_tpl = (TEMPLATES / "profile.yml").read_text()
    assert "exact GitHub login" in config_tpl
    assert "exact GitHub login" in profile_tpl


def test_sessions_are_per_contributor_not_shared() -> None:
    # v0.4.4: session logs moved from the shared <root>/sessions/ to the per-contributor
    # <root>/team/<login>/sessions/ — same isolation as weeks/ and reports/, so contributors
    # never collide writing to the same directory.
    start = (SKILLS / "start" / "SKILL.md").read_text()
    update = (SKILLS / "update" / "SKILL.md").read_text()
    end = (SKILLS / "end" / "SKILL.md").read_text()
    for skill in (start, update, end):
        assert "team/<login>/sessions/" in skill

    # /start's collision check must glob across contributors' session logs too.
    assert "team/*/sessions/" in start

    readme = (ROOT.parent / "README.md").read_text()
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()
    assert "sessions/            # per-day handoffs" in readme
    assert "_polaris/team/<your-github-login>/sessions/" in onboarding
    assert "Migrating from" in onboarding


def test_agents_md_bridges_the_skills_to_non_claude_clis() -> None:
    # Codex/other agent CLIs consume the skills from a repo checkout via
    # AGENTS.md — it must link every shipped skill and explain the
    # $CLAUDE_PLUGIN_ROOT substitution.
    agents = (ROOT.parent / "AGENTS.md").read_text()
    for name in ("start", "update", "end", "plan-week", "report"):
        assert f"polaris/skills/{name}/SKILL.md" in agents
    assert "$CLAUDE_PLUGIN_ROOT" in agents
    assert "_polaris/" in agents


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
