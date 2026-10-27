"""slop_check.py: the mechanical check for documents people read.

Each test writes a real Markdown file and runs the CLI on it: the exit code and the reported
line are the behaviour (0 clean, 1 findings, 2 usage or unreadable). Nothing is mocked.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "slop_check.py"


def check(text, *args):
    d = Path(tempfile.mkdtemp())
    f = d / "doc.md"
    f.write_text(text, encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(f), *args],
                          capture_output=True, text=True, timeout=30)


def lines(done):
    """Line numbers reported, from --json."""
    return sorted(f["line"] for f in json.loads(done.stdout))


class Rules(unittest.TestCase):
    def test_clean_document_exits_zero(self):
        done = check("# Cache\n\nThe cache holds 512 entries and evicts the oldest first.\n")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_buzzword_is_reported_with_its_line(self):
        done = check("# Cache\n\nThe cache holds 512 entries.\nIt is a robust and seamless layer.\n")
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("doc.md:4", done.stdout)

    def test_hedge_is_reported(self):
        done = check("# Cache\n\nThe cache holds 512 entries.\nThis might potentially fail under load.\n", "--json")
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertEqual(lines(done), [4])

    def test_adjective_triad_is_reported_but_a_colour_list_is_not(self):
        done = check("# Cache\n\nThe cache holds 512 entries.\nIt is fast, reliable, and scalable.\n", "--json")
        self.assertEqual(lines(done), [4])
        done = check("# Flags\n\nThe flags are red, green, and blue.\n")
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_sentence_over_forty_words_is_reported(self):
        long = " ".join(["word"] * 45) + "."
        done = check("# Cache\n\nThe cache holds 512 entries.\n" + long + "\n", "--json")
        self.assertEqual(lines(done), [4])

    def test_list_items_are_not_one_long_sentence(self):
        items = "".join(f"- item number {i} has five words\n" for i in range(12))
        done = check("# List\n\nThe list follows.\n\n" + items)
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_heading_with_no_content_is_reported(self):
        done = check("# Cache\n\n## Eviction\n\n## Size\n\nThe cache holds 512 entries.\n", "--json")
        self.assertEqual(lines(done), [3])

    def test_buzzword_inside_an_identifier_is_not_reported(self):
        done = check("# Gates\n\nThe holistic-local-gate job runs on every push.\n")
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_heading_followed_by_child_heading_is_fine(self):
        done = check("# Cache\n\n## Size\n\n### Default\n\nThe cache holds 512 entries.\n")
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_first_sentence_restating_the_heading_is_reported(self):
        done = check("# Cache eviction policy\n\nThis is the cache eviction policy.\nOldest entries go first.\n", "--json")
        self.assertEqual(lines(done), [3])

    def test_this_document_describes_opener_is_reported(self):
        done = check("# Cache\n\nThis document describes how the cache evicts entries.\n", "--json")
        self.assertEqual(lines(done), [3])


class Skipping(unittest.TestCase):
    def test_code_urls_and_frontmatter_are_not_checked(self):
        text = ("---\ntitle: a robust and seamless page\n---\n# Cache\n\n"
                "The cache holds 512 entries, see https://example.com/robust-seamless-leverage.\n"
                "Call `robust_seamless()` to flush it.\n\n"
                "```python\n# leverage this robust, seamless, powerful code\n```\n\n"
                "~~~\nit's worth noting\n~~~\n")
        done = check(text)
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_allow_comment_with_reason_silences_the_line(self):
        done = check("# Cache\n\nThe cache is robust. <!-- slop-ok: quoting the vendor's claim -->\n")
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_allow_comment_without_reason_is_itself_a_finding(self):
        done = check("# Cache\n\nThe cache is robust. <!-- slop-ok -->\n", "--json")
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn(("slop-ok", 3), [(f["rule"], f["line"]) for f in json.loads(done.stdout)])


class Usage(unittest.TestCase):
    def test_missing_file_exits_two(self):
        done = subprocess.run([sys.executable, str(SCRIPT), "/nonexistent/x.md"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)

    def test_selfcheck_passes(self):
        done = subprocess.run([sys.executable, str(SCRIPT), "--selfcheck"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
