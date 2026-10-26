#!/usr/bin/env python3
"""Mechanical scans `finalize_review.py` runs before it will write an approval.

Two blocking scans (money-path, untracked-dangerous) plus one non-blocking
detector (mock-only test) that `finalize_review.py` cross-checks against the
findings the reviewer actually wrote:

  money_path_files      G3.7 — financial bugs (price/margin/tax) are caught
                         only by adversarial review, never the default suite.
                         A diff touching a money keyword with no CORRELATED
                         test file in the same changeset is a reason to
                         block, not a note. "Correlated" = the test's path
                         stem or content names the money-path file — an
                         unrelated test elsewhere in the changeset does not
                         satisfy this (closes the exact bypass EVAL-review-
                         bypass.md 3a/copertura G3.7 reproduced: a hardcoded-
                         margin bug riding past the gate next to a companion
                         test that never touches pricing.py).
  untracked_dangerous    G9.1 — a real command-injection incident lived in a
                         file git never tracked, so no diff-only gate ever
                         saw it. `git status --porcelain` catches what
                         `git diff --staged` structurally cannot. Patterns
                         cover AWS keys, PEM blocks, JWTs (Supabase-style
                         service-role keys), generic `*_KEY=`/`*_TOKEN=`/
                         `*_SECRET=` assignments, and shell/eval/exec
                         injection including `os.popen` (EVAL-review-bypass
                         3a found both the JWT and popen gap unpatched).
  suspect_mock_tests     G2.1/G2.6 — a test file that only ever touches
                         Mock/MagicMock/monkeypatch and never carries a
                         STRUCTURED real-test marker (`@real_test`,
                         `@pytest.mark.integration`, a `# real-test`/
                         `# integration-test` comment) can pass green while
                         proving nothing. This does NOT block by itself
                         (heuristic, false-positive prone — that judgment
                         belongs to `real-test`); it forces the reviewer to
                         have looked at it: finalize_review blocks only if a
                         flagged file is never cited in either axis'
                         findings. The marker is a structured token, not a
                         bare word — a stray "real" in an unrelated comment
                         no longer clears the flag (EVAL-review-copertura
                         G2.1/G2.6: this was the exact reproduced bypass).

Standalone use: `scan_blockers.py [--cwd DIR]` prints a JSON summary against
the currently staged changes — useful on its own, not only as a library.

    scan_blockers.py [--cwd DIR]   print a JSON summary and exit
    scan_blockers.py --selfcheck   prove each scan fires on the input it names
"""
from __future__ import annotations
import json
import pathlib
import re
import subprocess
import sys
import tempfile

MONEY_RE = re.compile(r"\b(price|pricing|margin|tax|iva|invoice|total|amount|currency|quote)\b", re.I)
TEST_PATH_RE = re.compile(r"(^|/)(test|tests|spec|specs)(/|_|\.)", re.I)
MOCK_RE = re.compile(r"\b(Mock|MagicMock|mock\.patch|monkeypatch|stub)\b")
REAL_MARK_RE = re.compile(
    r"@real_test\b|@pytest\.mark\.integration\b|#\s*real[-_ ]test\b|#\s*integration[-_ ]test\b",
    re.I,
)
SECRET_RE = re.compile(
    r"AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    r"|\b[A-Z][A-Z0-9_]*(?:_KEY|_TOKEN|_SECRET)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+.=]{16,}['\"]?"
)
DANGEROUS_CODE_RE = re.compile(
    r"subprocess\.\w+\([^)]*shell\s*=\s*True|os\.system\(|os\.popen\(|\beval\(|\bexec\("
)


def changed_files(cwd: str) -> list[str]:
    """Paths staged for commit right now — the perimeter every scan reads."""
    r = subprocess.run(["git", "diff", "--staged", "--name-only"],
                        cwd=cwd, capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l]


def staged_content(cwd: str, path: str) -> str:
    """The staged (indexed) blob for `path`, or "" if it can't be read."""
    r = subprocess.run(["git", "show", f":{path}"], cwd=cwd, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def money_path_files(cwd: str, files: list[str]) -> list[str]:
    return [f for f in files if MONEY_RE.search(staged_content(cwd, f))]


def has_test_companion(cwd: str, files: list[str], money_files: list[str]) -> bool:
    """A test file only counts as a companion if it CORRELATES with one of
    the money-path files (filename stem, or the stem named in its staged
    content) — any test file anywhere in the changeset is not enough. This
    is the exact gap G3.7's bypass reproduced: `pricing.py` gets a hardcoded
    margin regression riding past the gate next to an unrelated
    `test_unrelated.py`."""
    stems = {pathlib.Path(m).stem.lower() for m in money_files if pathlib.Path(m).stem}
    if not stems:
        return False
    for f in files:
        if not TEST_PATH_RE.search(f):
            continue
        fstem = pathlib.Path(f).stem.lower()
        if any(stem in fstem for stem in stems):
            return True
        content = staged_content(cwd, f).lower()
        if any(stem in content for stem in stems):
            return True
    return False


def _read_small(path: pathlib.Path, limit: int = 200_000) -> str:
    try:
        if path.is_file() and path.stat().st_size <= limit:
            return path.read_text(errors="replace")
    except OSError:
        pass
    return ""


def untracked_dangerous(cwd: str) -> list[str]:
    """Untracked files matching a secret or shell-injection pattern — the
    perimeter `git diff --staged` structurally cannot see (G9.1)."""
    r = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True)
    hits = []
    for line in r.stdout.splitlines():
        if not line.startswith("??"):
            continue
        path = line[3:].strip()
        text = _read_small(pathlib.Path(cwd) / path)
        if SECRET_RE.search(text) or DANGEROUS_CODE_RE.search(text):
            hits.append(path)
    return hits


def suspect_mock_tests(cwd: str, files: list[str]) -> list[str]:
    out = []
    for f in files:
        if not TEST_PATH_RE.search(f):
            continue
        text = staged_content(cwd, f)
        if MOCK_RE.search(text) and not REAL_MARK_RE.search(text):
            out.append(f)
    return out


def summary(cwd: str) -> dict:
    files = changed_files(cwd)
    money = money_path_files(cwd, files)
    return {
        "money_path_files": money,
        "has_test_companion": has_test_companion(cwd, files, money),
        "untracked_dangerous": untracked_dangerous(cwd),
        "suspect_mock_tests": suspect_mock_tests(cwd, files),
    }


def main() -> int:
    cwd = "."
    argv = sys.argv[1:]
    if "--cwd" in argv:
        cwd = argv[argv.index("--cwd") + 1]
    print(json.dumps(summary(cwd), indent=2))
    return 0


def _repo(tmp: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)


def _stage(tmp: pathlib.Path, rel: str, text: str) -> None:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    subprocess.run(["git", "add", rel], cwd=tmp, check=True)


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        _repo(tmp)
        cwd = str(tmp)

        _stage(tmp, "pricing.py", "price = 10\n")
        files = changed_files(cwd)
        assert money_path_files(cwd, files) == ["pricing.py"], "money keyword must be caught"
        assert not has_test_companion(cwd, files, ["pricing.py"]), \
            "no test staged yet — must be False"

        _stage(tmp, "tests/test_unrelated.py", "def test_x(): assert 1 == 1\n")
        assert not has_test_companion(cwd, changed_files(cwd), ["pricing.py"]), \
            "an UNRELATED test path must NOT satisfy the companion check " \
            "(G3.7 — the exact reported bypass: pricing.py + test_unrelated.py)"

        _stage(tmp, "tests/test_pricing.py", "from pricing import assemble_quote\n")
        assert has_test_companion(cwd, changed_files(cwd), ["pricing.py"]), \
            "a stem-correlated test path must satisfy the companion check"

        # Fake scanner inputs, assembled at run time: the check sees byte-identical data, and the
        # file carries no AKIA/sk- shape that push protection or a package leak scan would block.
        key_body = "ABCDEFGHIJKLMNOP"
        (tmp / "leak.env").write_text("KEY=AKIA" + key_body + "\n")
        assert untracked_dangerous(cwd) == ["leak.env"], "AWS-style secret must be flagged"
        (tmp / "leak.env").unlink()

        (tmp / "leak2.env").write_text(
            "SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig\n"
            "OPENAI_API_KEY=sk-proj-" + key_body.lower() + "qrstuvwx\n"
        )
        assert untracked_dangerous(cwd) == ["leak2.env"], \
            "JWT-shaped and generic *_KEY= secrets must be flagged (the exact repro miss)"
        (tmp / "leak2.env").unlink()

        (tmp / "notes.txt").write_text("just notes\n")
        assert "notes.txt" not in untracked_dangerous(cwd), "ordinary untracked file must not be flagged"

        (tmp / "worker.py").write_text("import os\ndef run(c): os.popen(c)\n")
        assert untracked_dangerous(cwd) == ["worker.py"], \
            "os.popen injection must be flagged (the exact repro miss, not just shell=True/system/eval/exec)"
        (tmp / "worker.py").unlink()

        _stage(tmp, "tests/test_mocked.py", "from unittest.mock import MagicMock\nMagicMock()\n")
        assert "tests/test_mocked.py" in suspect_mock_tests(cwd, changed_files(cwd))

        _stage(tmp, "tests/test_mocked.py",
               "# real quick note: this suite is fast, it never touches a real socket\n"
               "from unittest.mock import MagicMock\nMagicMock()\n")
        assert "tests/test_mocked.py" in suspect_mock_tests(cwd, changed_files(cwd)), \
            "a stray word 'real' in an unrelated comment must NOT clear the flag " \
            "(G2.1/G2.6 — the exact reported bypass)"

        _stage(tmp, "tests/test_mocked.py",
               "# real-test: hits a live staging DB below\n"
               "from unittest.mock import MagicMock\nMagicMock()\n")
        assert "tests/test_mocked.py" not in suspect_mock_tests(cwd, changed_files(cwd)), \
            "a structured real-test marker must still clear the flag"
    print("SELFCHECK OK — money-path (correlated), untracked-secret (JWT/generic/popen), "
          "and mock-only-test (structured marker) scans each fire as designed")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv[1:] else main())
