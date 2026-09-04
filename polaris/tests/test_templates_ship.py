"""The package ships blank forms; `npx skills` installs only `skills/`.

`.claude-plugin/marketplace.json` declares `./skills/*` and nothing else, so anything outside a
skill directory never reaches `~/.agents`. Measured 2026-09-04 on the live install: `~/.agents/
templates` does not exist, `/start` Step 2 provisioning fails with exit 1, `plan-week` and `report`
have no template, and four shipped selfchecks crash. These tests run against a tree shaped like the
INSTALL, not like the repository — the difference is the whole bug.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]          # polaris/
SKILLS = PKG / "skills"
PLUGIN_ROOT = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT(?::-[^}]*)?\}?/([A-Za-z0-9_./-]+)")
GUARD = re.compile(r"\[\s+!?\s*-[fd]\s")   # the skill says what it does without the path


def installed_tree() -> Path:
    """What `npx skills` actually lays down: the skill directories, and nothing beside them."""
    root = Path(tempfile.mkdtemp())
    shutil.copytree(SKILLS, root / "skills")
    return root


class TheInstalledTreeCarriesWhatTheSkillsAskFor(unittest.TestCase):

    def test_every_plugin_root_path_named_by_a_shipped_skill_exists_once_installed(self):
        """A path a skill names must exist once installed — UNLESS the skill declares what to do
        without it. `git-power/scripts/cantiere.py` is a legitimate optional dependency: it is
        guarded and it prints why it is skipping. An unguarded path that the install does not
        carry is a first-use failure, which is exactly what the templates were."""
        missing = []
        for skill in sorted(SKILLS.glob("*/SKILL.md")):
            lines = skill.read_text(encoding="utf-8").splitlines()
            for n, line in enumerate(lines):
                for rel in PLUGIN_ROOT.findall(line):
                    if (INSTALLED / rel).exists() or GUARD.search("\n".join(lines[n:n + 3])):
                        continue
                    missing.append(f"{skill.parent.name} -> {rel}")
        self.assertEqual([], missing, "a skill names a path the install lacks, with no fallback")

    def test_the_state_templates_the_selfchecks_seed_from_resolve_when_installed(self):
        sys.path.insert(0, str(INSTALLED / "skills" / "update" / "scripts"))
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); import _selfcheck_parts as s;"
             "print(s.TEMPLATES)",
             str(INSTALLED / "skills" / "update" / "scripts")],
            capture_output=True, text=True)
        resolved = Path(out.stdout.strip())
        self.assertTrue(resolved.is_dir(), f"selfcheck templates unresolved when installed: {resolved}")
        for name in ("current.md", "todos.md"):
            self.assertTrue((resolved / name).is_file(), f"{name} missing from {resolved}")

    def test_a_selfcheck_that_seeds_from_a_template_runs_in_the_installed_tree(self):
        script = INSTALLED / "skills" / "update" / "scripts" / "recent_context.py"
        done = subprocess.run([sys.executable, str(script), "--selfcheck"],
                              capture_output=True, text=True)
        self.assertEqual(0, done.returncode, f"crashed when installed:\n{done.stderr[-400:]}")


INSTALLED = installed_tree()

if __name__ == "__main__":
    unittest.main()
