"""The `init` door ships as a door, with its own scripts, and needs no vault."""

import re
import subprocess
import sys
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


def test_the_pack_is_resolved_only_after_the_commit() -> None:
    """Resolving at a HEAD without the backbone prints CTX-UNKNOWN and exits 0."""
    body = SKILL.read_text()
    assert body.index("git commit") < body.index("contextpack.py"), \
        "a pack resolved before the commit is a false green"
    assert "CTX-UNKNOWN" in body and "documents: 0" in body


def test_the_proof_reads_values_not_exit_codes() -> None:
    body = " ".join(SKILL.read_text().split())
    assert "documents: 3" in body
    assert "not `UNKNOWN`" in body or "is not `UNKNOWN`" in body


def test_it_walks_the_four_founder_steps_in_order() -> None:
    body = SKILL.read_text()
    steps = [body.index(needle) for needle in ("audit --root", "propose --root",
                                               "apply --mode minimal", "contextpack.py")]
    assert steps == sorted(steps), "audit → propose → apply → pack must stay in order"
    assert "wait" in body.casefold(), "the plan is signed before apply runs"


def test_it_runs_from_its_own_folder_and_needs_no_vault() -> None:
    body = SKILL.read_text()
    assert '"$INIT/polaris_init.py" audit' in body
    assert "no harness declared here" not in body, "a collaborator has no vault to declare"
    assert "ContextPack check skipped" in body, "the vault-only step says it was skipped"


def test_it_ships_its_scripts_as_real_files() -> None:
    """The vault door links its scripts; the package must carry their bytes, never a link."""
    scripts = ROOT / "skills" / "init" / "scripts"
    for name in ("polaris_init.py", "polaris_init_apply.py", "polaris_init_docs.py",
                 "polaris_init_plan.py", "polaris_init_probe.py", "polaris_init_tx.py",
                 "check_context_backbone.py"):
        path = scripts / name
        assert path.is_file() and not path.is_symlink(), f"{name} must ship as a real file"
    assert (ROOT / "skills" / "architecture" / "scripts" / "check_context_backbone.py").is_file(), \
        "the shim resolves the checker from the sibling architecture skill"


def test_the_installed_copy_proves_itself_without_a_vault() -> None:
    """The skills CLI installs `init/` next to `architecture/`: that layout must run."""
    done = subprocess.run(
        [sys.executable, "-I", str(ROOT / "skills" / "init" / "scripts" / "polaris_init.py"),
         "--selfcheck"], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "no-pointer=ok" in done.stdout


def test_it_refuses_to_create_areas() -> None:
    body = " ".join(SKILL.read_text().casefold().split())
    assert "never derived" in body
    assert "proposed and signed" in body
