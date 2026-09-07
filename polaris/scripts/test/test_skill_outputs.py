"""#320 — every skill that writes declares kinds the host map has, and invokes only skills that exist."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "skill_outputs_check.py"
CONFIG = "outputs:\n  spec: docs/modules/<area>/specs/x.md\n  plan: docs/modules/<area>/plans/x.md\n"
SKILL = """---
name: {name}
description: ◇ demo
invokes: {invokes}
---
# {name}

## Where this goes (host repository decides)

This skill produces: **{kinds}**. Kinds: `spec` `plan`.

## Polaris doors this skill invokes instead of doing the job itself

- none
"""


def suite(tmp: Path, **skills) -> Path:
    root = tmp / "skills"
    for name, (kinds, invokes) in skills.items():
        (root / name).mkdir(parents=True)
        (root / name / "SKILL.md").write_text(SKILL.format(name=name, kinds=kinds, invokes=invokes))
    (tmp / "config.yml").write_text(CONFIG)
    return root


def run(tmp: Path, root: Path):
    return subprocess.run([sys.executable, str(CLI), "--skills", str(root), "--config", str(tmp / "config.yml")],
                          capture_output=True, text=True)


class SkillOutputs(unittest.TestCase):
    def test_conforming_suite_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = suite(Path(d), writer=("spec", "[reader]"), reader=("none — writes nothing", "[]"))
            r = run(Path(d), root)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_kind_missing_from_map_is_red(self):
        with tempfile.TemporaryDirectory() as d:
            root = suite(Path(d), writer=("audit", "[]"))
            r = run(Path(d), root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("writer: kind 'audit' not in outputs map", r.stdout)

    def test_skill_without_block_is_red(self):
        with tempfile.TemporaryDirectory() as d:
            root = suite(Path(d), writer=("spec", "[]"))
            p = root / "writer" / "SKILL.md"
            p.write_text(p.read_text().split("## Where this goes")[0])
            r = run(Path(d), root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("writer: no 'Where this goes' block", r.stdout)

    def test_invoking_an_unknown_skill_is_red(self):
        with tempfile.TemporaryDirectory() as d:
            root = suite(Path(d), writer=("spec", "[ghost]"))
            r = run(Path(d), root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("writer: invokes unknown skill 'ghost'", r.stdout)


if __name__ == "__main__":
    unittest.main()
