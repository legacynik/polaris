"""Il cancello che avrebbe bocciato #20 e #21, provato su un repo costruito apposta."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "scripts" / "check_skill_versions.py"


def repo_with(change: str, bump: bool) -> tuple[Path, str]:
    """Un repo con una skill versionata, un commit base, e una modifica con o senza bump."""
    root = Path(tempfile.mkdtemp())
    skill = root / "polaris" / "skills" / "start"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: start\nversion: 1.5.0\n---\n\nbody\n")
    for cmd in (["init", "-q", "-b", "main"], ["add", "-A"],
                ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"]):
        subprocess.run(["git", *cmd], cwd=root, check=True)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                          capture_output=True, text=True).stdout.strip()
    body = "---\nname: start\nversion: {}\n---\n\n{}\n".format("1.6.0" if bump else "1.5.0", change)
    (skill / "SKILL.md").write_text(body)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
                   cwd=root, check=True)
    return root, base


def run(root: Path, base: str):
    return subprocess.run([sys.executable, str(CHECK), base], cwd=root,
                          capture_output=True, text=True)


class ASkillChangedWithoutABump(unittest.TestCase):

    def test_a_touched_skill_that_did_not_move_is_refused(self):
        root, base = repo_with("cambiata davvero", bump=False)
        done = run(root, base)
        self.assertEqual(1, done.returncode, done.stdout)
        self.assertIn("start: toccata e ferma a 1.5.0", done.stdout)

    def test_a_touched_skill_that_moved_passes(self):
        root, base = repo_with("cambiata davvero", bump=True)
        self.assertEqual(0, run(root, base).returncode)

    def test_a_removed_skill_needs_no_version(self):
        root, base = repo_with("x", bump=True)
        subprocess.run(["git", "rm", "-rq", "polaris/skills/start"], cwd=root, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "rm"],
                       cwd=root, check=True)
        done = run(root, base)
        self.assertEqual(0, done.returncode, done.stdout)

    def test_a_bad_ref_is_unusable_not_a_pass(self):
        root, _ = repo_with("x", bump=True)
        self.assertEqual(2, run(root, "non-esiste").returncode)


if __name__ == "__main__":
    unittest.main()
