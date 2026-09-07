"""area_map.py — the README map is generated from frontmatter; archive is a count, not rows."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "area_map.py"


def make_area(tmp: Path) -> Path:
    area = tmp / "polmem"
    (area / "specs").mkdir(parents=True)
    (area / "archive").mkdir()
    (area / "specs" / "a.md").write_text("---\ntitle: Spec A\nstatus: active\nsummary: what A does\n---\n# x\n")
    (area / "specs" / "b.md").write_text("# Spec B without frontmatter\n")
    (area / "archive" / "old.md").write_text("---\ntitle: Old\nstatus: superseded\n---\n")
    (area / "polmem.md").write_text('---\n{"document_type": "prd", "status": "final"}\n---\n# Canon JSON\n')
    (area / "specs" / "sub").mkdir()
    (area / "specs" / "sub" / "deep.md").write_text("# Deep spec\n")
    (area / "notes").mkdir()
    (area / "notes" / "n.md").write_text("---\ntitle: Stray note\nstatus: draft\n---\n")
    return area


class TestAreaMap(unittest.TestCase):
    def test_map_rows_and_archive_count(self):
        with tempfile.TemporaryDirectory() as d:
            area = make_area(Path(d))
            r = subprocess.run([sys.executable, str(CLI), str(area)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            readme = (area / "README.md").read_text()
            self.assertIn("| [Spec A](specs/a.md) | `active` | what A does |", readme)
            self.assertIn("| [Spec B without frontmatter](specs/b.md) | `UNKNOWN` |", readme)
            self.assertIn("| ~~[Old](archive/old.md)~~ | `archived` |", readme)
            self.assertIn("- canonical: [Canon JSON](polmem.md) `final`", readme)
            self.assertIn("| [Deep spec](specs/sub/deep.md) | `UNKNOWN` |", readme)
            self.assertIn("| [Stray note](notes/n.md) | `draft` |", readme)

    def test_regeneration_is_idempotent_and_keeps_prose(self):
        with tempfile.TemporaryDirectory() as d:
            area = make_area(Path(d))
            (area / "README.md").write_text("# polmem\n\nHand-written intro.\n")
            for _ in range(2):
                subprocess.run([sys.executable, str(CLI), str(area)], check=True, capture_output=True)
            readme = (area / "README.md").read_text()
            self.assertIn("Hand-written intro.", readme)
            self.assertEqual(readme.count("area-map:begin"), 1)


if __name__ == "__main__":
    unittest.main()
