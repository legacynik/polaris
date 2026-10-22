"""Package contract — what a machine reads from the shipped tree.

No test here asserts a sentence of a SKILL.md body. A sentence can be rewritten while the
behaviour stays, and can stay while the behaviour breaks: a substring tests neither. This file
was red on main for weeks for exactly that reason, and a real breach hid behind the noise.

- A rule a script enforces is tested by running the script, or the shipped block that calls it:
  test_update_gates, test_end_*, test_merge_truth, test_commit_*, test_report_week,
  test_start_identity, test_end_journal_wiring.
- A rule that lives only in prose is judged by review and by the evals under `polaris/evals`.
- What stays here is structure: the manifest, frontmatter, links, templates, size budgets, and
  denylists that walk the tree. A denylist survives any rewording and fails only when the banned
  thing comes back.
"""

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SKILLS = ROOT / "skills"
TEMPLATES = ROOT / "skills" / "start" / "templates" / "repo-contract"

SESSION_COMMANDS = {
    "start",
    "polaris-grill",
    "polaris-status",
    "update",
    "end",
    "plan-week",
    "report",
    "polaris-memory",
}
# A Polaris door marks itself in its own description, and the door set is READ from the
# tree rather than repeated here. A door promoted upstream and forgotten in a hand list
# is the drift this package exists to prevent, and a hand list would stay green over a
# package that is missing one.
DOOR_MARKER = "◇ "


def body(skill: str) -> str:
    return (SKILLS / skill / "SKILL.md").read_text()


def frontmatter(skill_md: Path) -> dict:
    raw = skill_md.read_text()
    assert raw.startswith("---\n"), f"{skill_md}: no frontmatter"
    return yaml.safe_load(raw.split("\n---\n", 1)[0].removeprefix("---\n"))


def shipped() -> set[str]:
    return {path.name for path in SKILLS.iterdir() if path.is_dir()}


def shipped_doors() -> set[str]:
    return {name for name in shipped()
            if str(frontmatter(SKILLS / name / "SKILL.md").get("description", "")).startswith(DOOR_MARKER)}


def test_marketplace_exposes_the_same_skills_to_agent_skills_cli() -> None:
    marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    plugin = marketplace["plugins"][0]
    declared = {Path(path).name for path in plugin["skills"]}
    assert plugin["source"] == "./polaris"
    assert declared == shipped()
    for relative in plugin["skills"]:
        assert (ROOT / relative.removeprefix("./") / "SKILL.md").is_file()


def test_only_the_team_commands_and_the_marked_doors_are_shipped() -> None:
    doors = shipped_doors()
    assert doors, "no Polaris door in the package: the sync never ran"
    assert shipped() == SESSION_COMMANDS | doors


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


def test_polaris_grill_ships_a_reviewed_skillopt_benchmark() -> None:
    benchmark = json.loads((ROOT / "evals" / "polaris-grill-skillopt.tasks.json").read_text())

    assert benchmark["format"] == "skillopt_sleep.tasks.v1"
    assert benchmark["target_skill_path"] == "polaris/skills/polaris-grill/SKILL.md"
    assert benchmark["reviewed"] is True
    assert {task["split"] for task in benchmark["tasks"]} == {"train", "val"}
    assert len(benchmark["tasks"]) >= 4
    assert all(task["origin"] == "real" for task in benchmark["tasks"])


def test_the_repo_contract_templates_a_host_repo_needs_are_shipped() -> None:
    for name in ("config.yml", "profile.yml", "weekly-plan.md", "weekly-report.md",
                 "state.gitignore", "README.md", "state/current.md", "state/todos.md",
                 "state/goals.md"):
        assert (TEMPLATES / name).is_file(), f"missing template {name}"


def test_the_state_templates_carry_the_sections_the_state_scripts_look_for() -> None:
    todos = (TEMPLATES / "state" / "todos.md").read_text()
    for section in ("## Active", "## Completed", "## Follow-ups"):
        assert section in todos
    assert "## Recent Context" in (TEMPLATES / "state" / "current.md").read_text()


def test_agents_md_links_every_session_command_to_a_file_that_exists() -> None:
    agents = (REPO / "AGENTS.md").read_text()
    linked = set(re.findall(r"\]\((polaris/skills/([a-z0-9-]+)/SKILL\.md)\)", agents))
    assert linked, "AGENTS.md links no skill"
    for path, _name in linked:
        assert (REPO / path).is_file(), f"AGENTS.md links a skill that is not shipped: {path}"
    assert SESSION_COMMANDS <= {name for _path, name in linked}


def test_start_stays_inside_its_size_budget() -> None:
    # /start runs at the top of every session: what it costs is paid every time. The v0.8.1 body
    # was 10,949 bytes and had turned into a status dashboard; the cap was 7,000 bytes / 940 words.
    # 2026-10-12: five merges between 09-18 and 09-23 (#36, #37, #39, #40, #42) took it to 11,677
    # bytes and 1,743 words with this check red on main. Both caps are re-based on that measured
    # size so the guard bites again from here; bringing the body back under 7,000 / 940 is
    # tracked in polaris-os#546.
    start = body("start")
    assert len(start.encode()) <= 12_000
    assert len(start.split()) <= 1_800


def test_start_runs_none_of_the_commands_that_belong_to_status() -> None:
    # /start resumes from local files. Network calls, history scans and memory queries are what
    # /polaris-status is for, and each one here was once in /start.
    start = body("start")
    for forbidden in ("git fetch", "git log origin/main", "git branch -vv", "gh pr list",
                      "polmem", "10 most recent", "team/*/weeks/"):
        assert forbidden not in start, forbidden


def test_no_skill_reads_a_personal_vault() -> None:
    for skill in shipped():
        for banned in ("POLARIS_VAULT", "Desktop/All Vibe Proj"):
            assert banned not in body(skill), f"{skill}: {banned}"


def test_no_permission_language_survives_anywhere_in_the_shipped_surface() -> None:
    # A sweep, not a list of files: a live grep found the signature gate in /plan-week's
    # `description:` after the body had been cleaned, and the description is the one string a
    # model reads when deciding whether to run the skill.
    surface = [
        *SKILLS.glob("*/SKILL.md"),
        *TEMPLATES.glob("*"),
        REPO / "README.md",
        REPO / "AGENTS.md",
        REPO / "docs" / "TEAM-ONBOARDING.md",
    ]
    # "CEO" is banned as a bare word, not as a phrase: the first pass banned "CEO signs" and
    # "the CEO reviews and signs it" sailed through. A title that grants authority by rank is
    # how the gate grows back.
    banned = ("ceo_signature", "execution_authorized", "auto_authorized",
              "auto-authorized", "unapproved proposal", "CEO", "ceo",
              "signature gates", "until signed", "proposal until")
    offenders = [
        f"{path.relative_to(REPO)}: {term}"
        for path in surface if path.is_file()
        for term in banned
        if re.search(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", path.read_text())
    ]
    assert not offenders, f"permission-gate language still ships: {offenders}"


def test_retired_conventions_do_not_come_back() -> None:
    docs = {
        "README.md": (REPO / "README.md").read_text(),
        "docs/TEAM-ONBOARDING.md": (REPO / "docs" / "TEAM-ONBOARDING.md").read_text(),
        "weekly-plan.md": (TEMPLATES / "weekly-plan.md").read_text(),
        "weekly-report.md": (TEMPLATES / "weekly-report.md").read_text(),
        **{name: body(name) for name in ("start", "update", "plan-week", "report")},
    }
    retired = {
        # A second contract root: one repo ended up carrying both `polaris/` and `_polaris/`.
        "`polaris/` or `_polaris/`": ("start", "update", "README.md", "docs/TEAM-ONBOARDING.md"),
        "`polaris/` if": ("start", "update", "README.md", "docs/TEAM-ONBOARDING.md"),
        # Worked examples with a placeholder login shipped a broken contract into a product repo.
        "team/jeanpierre": ("plan-week", "report"),
        "team/somebody-else": ("plan-week", "report"),
        # Capacity as a hard cap turned an honesty device into a lid on output.
        "Capacity rule (hard)": ("plan-week",),
        # Commits looked up by the noreply e-mail return nothing for squash merges.
        "@users.noreply.github.com": ("report",),
        # The templates are English; these are the headers the Italian drafts carried.
        "Previsto vs consegnato": ("weekly-plan.md", "weekly-report.md"),
        "Lavoro proposto": ("weekly-plan.md", "weekly-report.md"),
        "Non iniziare": ("weekly-plan.md", "weekly-report.md"),
        "Cosa abbiamo": ("weekly-plan.md", "weekly-report.md"),
    }
    offenders = [f"{where}: {term}" for term, places in retired.items() for where in places
                 if term in " ".join(docs[where].split())]
    assert not offenders, f"a retired convention is back: {offenders}"


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
