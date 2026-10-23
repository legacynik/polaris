"""`red_check.py break`, breaker round 3 (PR #562): the named test is matched exactly, and the copy is
what runs. Each test is one of the breaker's reproductions: a same-named method in a class, a file
with the same basename elsewhere, a test skipped in the copy, an editable install pointing at the
real tree — and the ordinary ways a test catches a break (`pytest.raises`, a mock assertion, a
shared assertion helper) that the junit reading called inconclusive.
"""
import subprocess
import sys

import pytest

from test_red_break import CALC, REAL, RUN, brk, cli, record, repo, rows  # noqa: F401  (fixture)


def _nested_venv(repo):
    """A `--system-site-packages` venv inside the fixture repo; returns its purelib path. It sees
    pytest only when the interpreter running this suite has pytest in its own site-packages —
    not under `uv run --with pytest`, whose packages live in an overlay a child venv never
    inherits. That is the environment, not the code under test: skip, saying so."""
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", "--without-pip", str(repo / ".venv")],
                   check=True)
    py = str(repo / ".venv/bin/python")
    if subprocess.run([py, "-c", "import pytest"], capture_output=True).returncode != 0:
        pytest.skip("environment: a --system-site-packages venv of this interpreter cannot import pytest "
                    "(e.g. `uv run --with pytest`); run the suite with an interpreter that has pytest installed")
    return subprocess.run([py, "-c", "import sysconfig;print(sysconfig.get_path('purelib'))"],
                          capture_output=True, text=True, check=True).stdout.strip()


MIRROR_FN = "import calc\n\n\ndef test_p():\n    assert calc.price(3) == 3 * calc.RATE\n"


def test_a_method_with_the_same_name_in_a_class_does_not_lend_its_red(repo):
    (repo / "test_t.py").write_text(MIRROR_FN + "\n\nclass TestK:\n    def test_p(self):\n"
                                    "        assert calc.price(3) == 30\n")
    out = brk(repo, "test_t.py::test_p", cmd="python3 -m pytest -q -p no:cacheprovider test_t.py")
    assert out.returncode == 1, out.stderr
    assert rows(repo)[-1]["rosso"] is False


def test_a_class_named_whole_is_matched_by_its_methods(repo):
    (repo / "test_t.py").write_text("import calc\n\n\nclass TestK:\n    def test_p(self):\n"
                                    "        assert calc.price(3) == 30\n")
    out = brk(repo, "test_t.py::TestK", cmd="python3 -m pytest -q -p no:cacheprovider test_t.py")
    assert out.returncode == 0, out.stderr


def test_a_file_with_the_same_basename_elsewhere_does_not_lend_its_red(repo):
    for side, body in (("a", MIRROR_FN), ("b", REAL.replace("def test_price", "def test_p"))):
        (repo / side / "tests").mkdir(parents=True)
        (repo / side / "tests" / "test_x.py").write_text(body)
    cmd = "cd .. && python3 -m pytest -q -p no:cacheprovider --import-mode=importlib ."
    out = brk(repo, "tests/test_x.py::test_p", cmd=cmd, file="../calc.py", cwd=repo / "a")
    assert out.returncode == 1, out.stderr
    assert rows(repo / "a")[-1]["rosso"] is False


def test_a_test_skipped_in_the_copy_is_inconclusive_not_green(repo):
    (repo / "data").mkdir()
    (repo / "data" / "fixture.json").write_text("{}")
    (repo / ".gitignore").write_text("data/\n__pycache__/\n*.jsonl\n")
    (repo / "test_e.py").write_text("import os\n\nimport pytest\n\nfrom calc import price\n\n\n"
                                    "@pytest.mark.skipif(not os.path.exists('data/fixture.json'), reason='no data')\n"
                                    "def test_e():\n    assert price(3) == 30\n")
    out = brk(repo, "test_e.py", cmd="python3 -m pytest -q -p no:cacheprovider test_e.py test_real.py")
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr
    assert rows(repo) == []


def test_an_editable_install_runs_the_copy_and_writes_nothing_in_the_real_tree(repo):
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "src" / "pkg" / "__init__.py").write_text(CALC)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_p.py").write_text("from pkg import price\n\n\ndef test_p():\n    assert price(3) == 30\n")
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n*.jsonl\n")
    site = _nested_venv(repo)
    (repo / ".venv" / site.split("/.venv/", 1)[1] / "pkg.pth").write_text(f"{repo / 'src'}\n")
    out = brk(repo, "tests/test_p.py::test_p", cmd=".venv/bin/python -m pytest -q -p no:cacheprovider tests",
              file="src/pkg/__init__.py")
    assert out.returncode == 0, out.stderr
    assert not list((repo / "src").rglob("*.pyc"))


def test_pytest_raises_catching_a_removed_raise_is_a_catch(repo):
    (repo / "calc.py").write_text(CALC.replace("    return", "    if q < 0:\n        raise ValueError(q)\n    return"))
    (repo / "test_raise.py").write_text("import pytest\n\nfrom calc import price\n\n\ndef test_raise():\n"
                                        "    with pytest.raises(ValueError):\n        price(-1)\n")
    out = brk(repo, "test_raise.py", old="        raise ValueError(q)\n", new="        pass\n")
    assert out.returncode == 0, out.stderr


def test_a_mock_assertion_catching_a_removed_call_is_a_catch(repo):
    (repo / "calc.py").write_text(CALC + "\n\ndef charge(q, send):\n    send(price(q))\n")
    (repo / "test_mock.py").write_text("from unittest import mock\n\nfrom calc import charge\n\n\ndef test_mock():\n"
                                       "    send = mock.Mock()\n    charge(3, send)\n    send.assert_called_once_with(30)\n")
    out = brk(repo, "test_mock.py", old="    send(price(q))\n", new="    price(q)\n")
    assert out.returncode == 0, out.stderr


def test_an_assertion_helper_in_the_tests_folder_is_a_catch(repo):
    (repo / "tests").mkdir()
    (repo / "tests" / "helpers.py").write_text("def assert_price(got, want):\n    assert got == want\n")
    (repo / "tests" / "test_h.py").write_text("from calc import price\nfrom helpers import assert_price\n\n\n"
                                              "def test_h():\n    assert_price(price(3), 30)\n")
    out = brk(repo, "tests/test_h.py", cmd="python3 -m pytest -q -p no:cacheprovider tests/test_h.py",
              file="calc.py")
    assert out.returncode == 0, out.stderr


def test_a_green_break_warns_but_a_later_red_break_passes_verify(repo):
    """A good test is green under a break of code it does not cover; that is a warning, not a ban."""
    (repo / "calc.py").write_text("RATE = 10\n\n\ndef price(q):\n    return 0\n")
    record(repo, "test_real.py")
    (repo / "calc.py").write_text(CALC + "\nUNUSED = 1\n")
    record(repo, "test_real.py")
    assert brk(repo, "test_real.py", old="UNUSED = 1", new="UNUSED = 2").returncode == 1
    assert brk(repo, "test_real.py").returncode == 0
    out = cli(repo, "verify", "--log", "r.jsonl", "--test", "test_real.py", "--break")
    assert out.returncode == 0 and "UNUSED = 1" in out.stderr, out.stderr


# --- breaker round 4: test code is never a break target nor production; an editable root install ---

def test_a_break_in_a_test_helper_is_refused(repo):
    (repo / "tests").mkdir()
    (repo / "tests" / "helpers.py").write_text("def check(a, b):\n    assert a == b\n")
    (repo / "tests" / "test_m.py").write_text("import calc\nfrom helpers import check\n\n\n"
                                              "def test_m():\n    check(calc.price(3), 3 * calc.RATE)\n")
    out = brk(repo, "tests/test_m.py", cmd="python3 -m pytest -q -p no:cacheprovider tests/test_m.py",
              file="tests/helpers.py", old="assert a == b", new="assert a == b + 1")
    assert out.returncode == 2 and out.stderr.startswith("break refused:"), out.stderr


def test_an_assert_in_a_production_module_named_like_a_test_is_not_a_catch(repo):
    for where in ("app/test_mode.py", "lib/test/mode.py"):
        (repo / where).parent.mkdir(parents=True, exist_ok=True)
        (repo / where).write_text("from limits import LIMIT\n\n\ndef enable(n):\n    assert n <= LIMIT\n    return n\n")
    (repo / "limits.py").write_text("LIMIT = 100\n")
    (repo / "tests").mkdir()
    for name, mod in (("test_a.py", "app.test_mode"), ("test_b.py", "lib.test.mode")):
        (repo / "tests" / name).write_text(f"from {mod} import enable\n\n\ndef test_s():\n    enable(50)\n")
    for name in ("test_a.py", "test_b.py"):
        out = brk(repo, f"tests/{name}", cmd=f"python3 -m pytest -q -p no:cacheprovider tests/{name}",
                  file="limits.py", old="LIMIT = 100", new="LIMIT = 10")
        assert out.returncode == 2 and "break inconclusive:" in out.stderr, (name, out.stderr)


def test_an_editable_install_of_the_repository_root_reaches_a_subprocess(repo):
    (repo / "tests").mkdir()
    (repo / "tests" / "test_cli.py").write_text(
        "import subprocess\nimport sys\n\n\ndef test_cli(tmp_path):\n"
        "    out = subprocess.run([sys.executable, '-c', 'import calc; print(calc.price(3))'],\n"
        "                         cwd=tmp_path, capture_output=True, text=True)\n    assert out.stdout.strip() == '30'\n")
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n*.jsonl\n")
    site = _nested_venv(repo)
    (repo / ".venv" / site.split("/.venv/", 1)[1] / "__editable__.calc-0.1.pth").write_text(f"{repo}\n")
    out = brk(repo, "tests/test_cli.py", cmd=".venv/bin/python -m pytest -q -p no:cacheprovider tests")
    assert out.returncode == 0, out.stderr


# --- breaker round 5: the real tree is checked, not promised; doctests are not test code ---------

def test_a_command_that_writes_into_the_linked_venv_is_inconclusive(repo):
    """`uv run` re-pointed the real `.venv` at the copy: any write through a linked tool folder,
    whoever makes it, is seen and the run is thrown away."""
    (repo / "venv").mkdir()
    (repo / "venv" / "lib.txt").write_text("real\n")
    out = brk(repo, "test_real.py", cmd="echo synced >> venv/lib.txt && " + RUN.format("test_real.py"))
    assert out.returncode == 2 and "venv" in out.stderr and "break inconclusive:" in out.stderr, out.stderr
    assert rows(repo) == []


def test_a_command_that_writes_a_file_of_the_real_tree_is_inconclusive(repo):
    out = brk(repo, "test_real.py", cmd='echo "# x" >> "$OLDPWD/calc.py" && ' + RUN.format("test_real.py"))
    assert out.returncode == 2 and "calc.py" in out.stderr and "break inconclusive:" in out.stderr, out.stderr
    assert rows(repo) == []


def test_a_doctest_does_not_make_production_code_test_code(repo):
    (repo / "calc.py").write_text('RATE = 10\n\n\ndef price(q):\n    """\n    >>> price(0)\n    0\n    """\n'
                                  '    assert q >= 0, "negative quantity"\n    return q * RATE\n')
    (repo / "pytest.ini").write_text("[pytest]\naddopts = --doctest-modules\n")
    (repo / "test_mirror.py").write_text("import calc\n\n\ndef test_price():\n    calc.price(3)\n")
    out = brk(repo, "test_mirror.py::test_price", cmd="python3 -m pytest -q -p no:cacheprovider",
              old="assert q >= 0", new="assert q > 3")
    assert out.returncode == 2 and "production code" in out.stderr, out.stderr


def test_a_command_that_sets_pythonpath_is_told_how_to_keep_the_probe(repo):
    out = brk(repo, "test_real.py", cmd="PYTHONPATH=. " + RUN.format("test_real.py"))
    assert out.returncode == 2 and "-o pythonpath" in out.stderr, out.stderr


# --- breaker round 6: the break edits a file the copy holds; a crash is never a verdict ----------

def test_an_ignored_target_is_refused_not_created_in_the_copy(repo):
    """An ignored `local_settings.py` is not in the copy: writing the break there created it, and the
    file's presence, not the replacement, turned the test red."""
    (repo / ".gitignore").write_text("local_settings.py\nbuild/\n__pycache__/\n*.jsonl\n")
    (repo / "local_settings.py").write_text("DEBUG = True\n")
    (repo / "build").mkdir()
    (repo / "build" / "gen.py").write_text("X = 1\n")
    for target, old, new in (("local_settings.py", "DEBUG = True", "DEBUG = False"), ("build/gen.py", "X = 1", "X = 2")):
        out = brk(repo, "test_real.py", file=target, old=old, new=new)
        assert out.returncode == 2 and out.stderr.startswith("break refused:"), (target, out.stderr)
    assert rows(repo) == []


def test_a_crash_of_the_tool_is_inconclusive_never_the_green_verdict(repo):
    secret = repo / "secret.json"
    secret.write_text("{}")
    secret.chmod(0)
    try:
        out = brk(repo, "test_real.py")
    finally:
        secret.chmod(0o600)
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr
    assert rows(repo) == []


def test_a_broken_report_line_is_inconclusive_not_the_green_verdict(repo):
    (repo / "test_junk.py").write_text("import os\n\nfrom calc import price\n\n\ndef test_junk():\n"
                                       "    open(os.environ['RED_BREAK_REPORT'], 'a').write('{partial\\n')\n"
                                       "    assert price(3) == 30\n")
    out = brk(repo, "test_junk.py")
    assert out.returncode == 2 and "break inconclusive:" in out.stderr, out.stderr
