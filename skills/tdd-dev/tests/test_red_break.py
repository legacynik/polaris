"""`red_check.py break` — the declared BREAK, applied: does the test catch the defect it guards?

A RED proves a test failed once; it does not prove the test fails when the code it protects
breaks. A mirror test (its expected value computed by the implementation) has a clean RED→GREEN
chain and catches nothing. `break` applies one exact replacement to one production file in a
throwaway copy of the working tree and reruns the same command: the test must turn red. The real
tree is never touched. `verify --break` requires that red, after GREEN, on the same test hash.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "red_check.py"
CALC = "RATE = 10\n\n\ndef price(q):\n    return q * RATE if q > 0 else 0\n"
REAL = "from calc import price\n\n\ndef test_price():\n    assert price(3) == 30\n    assert price(0) == 0\n"
MIRROR = "import calc\n\n\ndef test_price():\n    assert calc.price(3) == 3 * calc.RATE\n"
RUN = "python3 -m pytest -q -p no:cacheprovider {}"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for name, text in {"calc.py": CALC, "test_real.py": REAL, "test_mirror.py": MIRROR,
                       ".gitignore": "venv/\n__pycache__/\n*.jsonl\n"}.items():
        (root / name).write_text(text, encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "fixture")
    return root


def cli(root: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd or root,
                          capture_output=True, text=True, timeout=300)


def record(root: Path, test: str, log: str = "r.jsonl") -> None:
    out = cli(root, "record", "--test", test, "--cmd", RUN.format(test), "--out", log)
    assert out.returncode == 0, out.stderr


def brk(root: Path, test: str, **kw) -> subprocess.CompletedProcess:
    """Break `kw["file"]` (calc.py), replacing `kw["old"]` (RATE = 10) with `kw["new"]` (RATE = 11)."""
    return cli(root, "break", "--test", test, "--cmd", kw.get("cmd", RUN.format(test)), "--out", kw.get("log", "r.jsonl"),
               "--file", kw.get("file", "calc.py"), "--old", kw.get("old", "RATE = 10"),
               "--new", kw.get("new", "RATE = 11"), cwd=kw.get("cwd"))


def rows(root: Path, log: str = "r.jsonl") -> list[dict]:
    path = root / log
    return [json.loads(x) for x in path.read_text().splitlines()] if path.is_file() else []


def red_then_green(root: Path, test: str) -> None:
    """A real RED (the implementation missing), then GREEN on the same, unchanged test file."""
    (root / "calc.py").write_text("RATE = 10\n\n\ndef price(q):\n    return 0\n")
    record(root, test)
    (root / "calc.py").write_text(CALC)
    record(root, test)


def test_a_real_test_turns_red_under_the_declared_break(repo):
    out = brk(repo, "test_real.py")
    assert out.returncode == 0, out.stderr
    last = rows(repo)[-1]
    assert last["break"]["file"] == "calc.py" and last["rosso"] is True


def test_a_mirror_test_stays_green_and_is_named_as_proving_nothing(repo):
    out = brk(repo, "test_mirror.py")
    assert out.returncode == 1
    assert "proves nothing" in out.stderr
    assert rows(repo)[-1]["rosso"] is False


def test_the_real_tree_is_never_touched(repo):
    (repo / "calc.py").write_text(CALC + "# uncommitted work\n")
    before = {p.name: p.read_bytes() for p in repo.iterdir() if p.is_file()}
    assert brk(repo, "test_real.py").returncode == 0
    after = {p.name: p.read_bytes() for p in repo.iterdir() if p.is_file() and p.name != "r.jsonl"}
    assert after == {k: v for k, v in before.items() if k != "r.jsonl"}
    assert git(repo, "status", "--porcelain") == " M calc.py\n"


def test_uncommitted_and_untracked_work_is_what_gets_broken(repo):
    (repo / "test_new.py").write_text(REAL)
    (repo / "calc.py").write_text(CALC.replace("RATE = 10", "RATE = 10  # tuned"))
    out = brk(repo, "test_new.py", old="RATE = 10  # tuned", new="RATE = 12")
    assert out.returncode == 0, out.stderr
    assert rows(repo)[-1]["rosso"] is True


@pytest.mark.parametrize("why,kw", [
    ("the break edits the test itself", {"file": "test_real.py", "old": "== 30", "new": "== 31"}),
    ("old text absent", {"old": "RATE = 99"}),
    ("old text twice", {"old": "q"}),
    ("file outside the tree", {"file": "../calc.py"}),
    ("a no-op break", {"new": "RATE = 10"}),
])
def test_an_unusable_break_is_refused_and_writes_nothing(repo, why, kw):
    out = brk(repo, "test_real.py", **kw)
    assert out.returncode == 2, (why, out.stdout, out.stderr)
    assert out.stderr.startswith("break refused:"), (why, out.stderr)
    assert rows(repo) == [], why


def test_a_break_that_kills_collection_is_not_a_red(repo):
    out = brk(repo, "test_real.py", new="RATE = (")
    assert out.returncode == 2, out.stderr
    assert "break inconclusive:" in out.stderr, out.stderr
    assert rows(repo) == []


def test_ignored_tool_folders_are_reachable_from_the_copy(repo):
    venv = repo / "venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "py").write_text(f"#!/bin/sh\nexec {sys.executable} \"$@\"\n")
    (venv / "py").chmod(0o755)
    out = cli(repo, "break", "--test", "test_real.py", "--cmd", "venv/bin/py -m pytest -q -p no:cacheprovider test_real.py",
              "--out", "r.jsonl", "--file", "calc.py", "--old", "RATE = 10", "--new", "RATE = 11")
    assert out.returncode == 0, out.stderr
    assert rows(repo)[-1]["rosso"] is True


def test_a_break_run_from_a_subfolder_runs_from_the_same_subfolder(repo):
    sub = repo / "pkg"
    sub.mkdir()
    (sub / "calc.py").write_text(CALC)
    (sub / "test_real.py").write_text(REAL)
    out = brk(repo, "test_real.py", file="calc.py", cwd=sub, log="../r.jsonl")
    assert out.returncode == 0, out.stderr
    assert rows(repo)[-1]["break"]["file"] == "pkg/calc.py"


def test_verify_without_break_ignores_break_rows(repo):
    red_then_green(repo, "test_real.py")
    assert brk(repo, "test_real.py").returncode == 0 and rows(repo)[-1]["rosso"] is True
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_real.py")
    assert out.returncode == 0, out.stderr


def test_verify_with_break_passes_only_with_a_red_break_after_green(repo):
    red_then_green(repo, "test_real.py")
    assert cli(repo, "verify", "--log", "r.jsonl", "--test", "test_real.py", "--break").returncode == 1
    brk(repo, "test_real.py")
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_real.py", "--break")
    assert out.returncode == 0, out.stderr


def test_verify_with_break_refuses_a_mirror(repo):
    red_then_green(repo, "test_mirror.py")
    brk(repo, "test_mirror.py")
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_mirror.py", "--break")
    assert out.returncode == 1 and "break" in out.stderr


def test_verify_with_break_refuses_a_break_older_than_green(repo):
    brk(repo, "test_real.py")
    red_then_green(repo, "test_real.py")
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_real.py", "--break")
    assert out.returncode == 1


def test_verify_with_break_refuses_a_test_rewritten_after_the_break(repo):
    red_then_green(repo, "test_real.py")
    brk(repo, "test_real.py")
    (repo / "test_real.py").write_text(REAL + "\n")
    red_then_green(repo, "test_real.py")  # the new file has its own clean RED→GREEN
    assert cli(repo, "verify", "--log", "r.jsonl", "--test", "test_real.py").returncode == 0
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_real.py", "--break")
    assert out.returncode == 1


# --- breaker round 1 (PR #562) ------------------------------------------------------------------

def test_a_command_that_cannot_pass_in_the_copy_is_inconclusive_not_red(repo):
    """The red must come from the break: an ignored file the test needs is absent from the copy."""
    (repo / ".gitignore").write_text("venv/\n__pycache__/\n*.jsonl\nlocal.json\n")
    (repo / "local.json").write_text("{}")
    (repo / "test_env.py").write_text("import os\nfrom calc import price\n\n\ndef test_env():\n"
                                      "    assert os.path.exists('local.json')\n    assert price(3) == 30\n")
    out = brk(repo, "test_env.py", old="RATE = 10", new="RATE = 11")
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr
    assert rows(repo) == []


def test_a_break_never_writes_through_a_linked_tool_folder(repo):
    lib = repo / "node_modules" / "lib.py"
    lib.parent.mkdir()
    lib.write_text("X = 1\n")
    (repo / ".gitignore").write_text("venv/\n__pycache__/\n*.jsonl\nnode_modules/\n")
    out = brk(repo, "test_real.py", file="node_modules/lib.py", old="X = 1", new="X = 2")
    assert out.returncode == 2 and out.stderr.startswith("break refused:"), out.stderr
    assert lib.read_text() == "X = 1\n"


def test_a_break_that_crashes_the_code_is_not_a_catch(repo):
    out = brk(repo, "test_mirror.py", old="return q * RATE", new="return q * RATEX")
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr
    assert rows(repo) == []


def test_a_break_in_test_code_is_refused_and_a_green_break_stays_on_the_record(repo):
    """Round 4: breaking `conftest.py` turned a mirror red and passed `verify --break`; test code is
    never a break target. The green break of production code is printed by every `verify --break`."""
    red_then_green(repo, "test_mirror.py")
    assert brk(repo, "test_mirror.py").returncode == 1
    (repo / "conftest.py").write_text("import calc\nBROKEN = False\nif BROKEN:\n    calc.price = lambda q: 0\n")
    out = brk(repo, "test_mirror.py", file="conftest.py", old="BROKEN = False", new="BROKEN = True")
    assert out.returncode == 2 and out.stderr.startswith("break refused:"), out.stderr
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_mirror.py", "--break")
    assert out.returncode == 1 and "stayed green" in out.stderr and "RATE = 10" in out.stderr, out.stderr


def test_a_break_run_with_another_command_does_not_count(repo):
    red_then_green(repo, "test_mirror.py")
    other = cli(repo, "break", "--test", "test_mirror.py", "--cmd", RUN.format("test_real.py"), "--out", "r.jsonl",
                "--file", "calc.py", "--old", "RATE = 10", "--new", "RATE = 11")
    assert other.returncode == 2 and "not in pytest's report" in other.stderr, other.stderr
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_mirror.py", "--break")
    assert out.returncode == 1, out.stderr


def test_the_test_file_is_refused_under_any_spelling(repo):
    out = brk(repo, "test_real.py", file="./TEST_REAL.PY" if os.path.exists(repo / "TEST_REAL.PY") else "./test_real.py",
              old="== 30", new="== 31")
    assert out.returncode == 2 and out.stderr.startswith("break refused:"), out.stderr


def test_a_new_log_folder_is_created_and_line_endings_survive(repo):
    (repo / "calc.py").write_bytes(CALC.replace("\n", "\r\n").encode())
    out = brk(repo, "test_real.py", log="logs/new/r.jsonl")
    assert out.returncode == 0, out.stderr
    assert (repo / "calc.py").read_bytes().count(b"\r\n") == CALC.count("\n")


def test_a_file_that_is_not_text_is_refused(repo):
    (repo / "blob.py").write_bytes(b"\xff\xfeRATE = 10\n")
    out = brk(repo, "test_real.py", file="blob.py")
    assert out.returncode == 2 and out.stderr.startswith("break refused:"), out.stderr


def test_bugfix_circuit_breaker_does_not_count_break_rows(repo):
    gate = Path(__file__).resolve().parents[2] / "bugfix" / "scripts" / "fix_gate.py"
    spec = importlib.util.spec_from_file_location("fix_gate", gate)
    fix_gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fix_gate)
    log = repo / "fg.jsonl"
    rows_ = [{"test": "t", "rosso": True}, {"test": "t", "rosso": False}] + \
        [{"test": "t", "rosso": True, "break": {"file": "c.py"}}] * 3
    log.write_text("\n".join(json.dumps(r) for r in rows_) + "\n")
    assert fix_gate._thrashing({"rosso_log": str(log), "test": "t"}) is False


# --- breaker round 2 (PR #562): the verdict is pytest's own report, never a regex on output --------

def test_a_dotted_exception_is_a_crash_not_a_catch(repo):
    (repo / "calc.py").write_text("import json\nRATE = 10\n\n\ndef price(q):\n    return q * RATE * json.loads('1')\n")
    out = brk(repo, "test_mirror.py", old="json.loads('1')", new="json.loads('one')")
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr


def test_a_crash_with_tracebacks_switched_off_is_not_a_catch(repo):
    out = brk(repo, "test_mirror.py", old="return q * RATE", new="return q * RATEX",
              cmd=RUN.format("--tb=no test_mirror.py"))
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr


def test_the_word_expected_in_the_test_does_not_turn_a_crash_into_a_catch(repo):
    (repo / "test_mirror.py").write_text(MIRROR.replace("calc.RATE\n", 'calc.RATE, "Expected price to scale"\n'))
    out = brk(repo, "test_mirror.py", old="return q * RATE", new="return q * RATEX")
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr


def test_an_assert_in_production_code_is_not_the_test_catching(repo):
    (repo / "calc.py").write_text(CALC.replace("    return", "    assert RATE > 0, 'rate'\n    return"))
    out = brk(repo, "test_mirror.py", old="RATE = 10", new="RATE = -1")
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr


def test_the_red_belongs_to_the_named_test_only(repo):
    (repo / "test_both.py").write_text(MIRROR.replace("def test_price", "def test_mirror") + "\n\n" +
                                       REAL.replace("from calc import price\n", "from calc import price\n")
                                       .replace("def test_price", "def test_real"))
    out = brk(repo, "test_both.py::test_mirror", cmd=RUN.format("test_both.py"))
    assert out.returncode == 1, out.stderr
    assert rows(repo)[-1]["rosso"] is False


def test_a_green_break_is_not_erased_by_recording_green_again(repo):
    red_then_green(repo, "test_mirror.py")
    assert brk(repo, "test_mirror.py").returncode == 1
    record(repo, "test_mirror.py")
    assert brk(repo, "test_mirror.py", old="return q * RATE", new="return q * RATE + 1").returncode == 0
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_mirror.py", "--break")
    assert out.returncode == 0 and "stayed green" in out.stderr, out.stderr


def test_a_command_aimed_at_the_real_tree_is_refused(repo):
    out = brk(repo, "test_real.py", cmd=f"cd {repo} && " + RUN.format("test_real.py"))
    assert out.returncode == 2 and out.stderr.startswith("break refused:"), out.stderr


def test_a_runner_without_a_pytest_report_is_inconclusive(repo):
    (repo / "test_unit.py").write_text("import unittest\nfrom calc import price\n\n\nclass T(unittest.TestCase):\n"
                                       "    def test_p(self):\n        self.assertEqual(price(3), 30)\n")
    out = brk(repo, "test_unit.py", cmd="python3 -m unittest test_unit")
    assert out.returncode == 2 and "pytest" in out.stderr, out.stderr


def test_a_whole_file_catches_when_one_of_its_tests_asserts_even_if_another_crashes(repo):
    (repo / "test_file.py").write_text(REAL + "\n\ndef test_unpack():\n    (one,) = [price(1), price(2)] if price(1) != 10 else [price(1)]\n")
    out = brk(repo, "test_file.py", cmd=RUN.format("test_file.py"))
    assert out.returncode == 0, out.stderr
    assert rows(repo)[-1]["rosso"] is True
