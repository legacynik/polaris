"""L2-T6 (#405) — the one ruler the brief is measured with.

The acceptance of #405 is a number: the time-0 dashboard under 1.500 tokens. A number is
only an acceptance if two people measuring it get the same answer, so the formula is
DECLARED and pinned here rather than estimated per caller: four UTF-8 bytes to a token,
rounded up. It is the arithmetic `contextpack_receipt._estimate` and `contextpack._area`
already bill the pack with — one ruler for the 1.500 of the brief and the 4.000 of the pack.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import token_count  # noqa: E402


class TheFormulaIsDeclaredNotEstimated(unittest.TestCase):
    def test_four_utf8_bytes_make_one_token_rounded_up(self) -> None:
        self.assertEqual(token_count.tokens(""), 0)
        self.assertEqual(token_count.tokens("a"), 1)
        self.assertEqual(token_count.tokens("abcd"), 1)
        self.assertEqual(token_count.tokens("abcde"), 2)

    def test_it_counts_bytes_and_not_characters(self) -> None:
        """A one-character decision title in Italian is two bytes, and a budget that counts
        characters under-reports every non-ASCII brief it will ever measure."""
        self.assertEqual(token_count.tokens("e" * 8), 2)
        self.assertEqual(token_count.tokens("è" * 8), 4)

    def test_the_docstring_states_the_formula(self) -> None:
        """An undeclared ruler is not a gate: the next reader must find the arithmetic."""
        self.assertIn("4", token_count.__doc__ or "")
        self.assertIn("utf-8", (token_count.__doc__ or "").lower())


class TheCliAnswersForAFileOrAStream(unittest.TestCase):
    def run_cli(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(SCRIPTS / "token_count.py"), *args],
                              input=stdin, capture_output=True, text=True)

    def test_stdin_is_counted(self) -> None:
        done = self.run_cli(stdin="abcdefgh")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "2")

    def test_a_file_is_counted(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brief.txt"
            path.write_text("abcd" * 10, encoding="utf-8")
            done = self.run_cli(str(path))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "10")

    def test_a_missing_file_is_a_code_and_not_a_traceback(self) -> None:
        done = self.run_cli("/nonexistent/brief.txt")
        self.assertEqual(done.returncode, 2)
        self.assertNotIn("Traceback", done.stderr)


if __name__ == "__main__":
    unittest.main()
