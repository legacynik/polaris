"""red_break_probe.py — the pytest plugin `red_check.py break` loads into the command (`-p red_break_probe`).

pytest's junit report names a test by basename and class suffix, so a same-named method or a file
with the same basename elsewhere lent its red to a mirror test (#562, round 3). The plugin writes
what pytest itself knows, one JSON line per outcome into $RED_BREAK_REPORT: the test's absolute
file and its nodeid after the file, phase and outcome, whether the failure is a check (an
AssertionError, or pytest's `Failed` that `pytest.fail` and `pytest.raises` raise) and the file of
every traceback frame, innermost last; `absent` says the failure is an absence (import, placeholder, unbound
name, attribute missing from a module) rather than behaviour; `function` says it is a test function, not a doctest. At the end of the session, one more line names a module
imported from the real tree ($RED_BREAK_REAL) outside its tool folders: an editable install that
made the copy run the unbroken code. Setup and teardown are written only when they did not pass.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

TOOLS = {"venv", ".venv", "node_modules"}


def _write(row: dict) -> None:
    with open(os.environ["RED_BREAK_REPORT"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def _escaped(real: str) -> str:
    """The first imported module whose file lives in the real tree, outside its tool folders."""
    for mod in list(sys.modules.values()):
        path = os.path.realpath(getattr(mod, "__file__", None) or os.devnull)
        if path.startswith(real + os.sep) and not TOOLS & set(os.path.relpath(path, real).split(os.sep)):
            return path
    return ""


def _absent(exc) -> bool:
    """The failure is an absence, not behaviour: an import, a placeholder, an unbound name, or an
    attribute missing from a module (the test reached for code that does not exist yet)."""
    if exc is None:
        return False
    if exc.errisinstance((ImportError, NotImplementedError, NameError)):
        return True
    return exc.errisinstance(AttributeError) and isinstance(getattr(exc.value, "obj", None), type(os))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    rep = (yield).get_result()
    if rep.when != "call" and rep.passed:
        return
    exc = call.excinfo
    _write({"file": str(getattr(item, "path", None) or item.fspath), "name": item.nodeid.partition("::")[2],
            "function": isinstance(item, pytest.Function), "when": rep.when, "outcome": "xfail" if hasattr(rep, "wasxfail") else rep.outcome,
            "check": bool(exc and exc.errisinstance((AssertionError, pytest.fail.Exception))),
            "frames": [str(e.path) for e in exc.traceback] if exc else [], "absent": _absent(exc)})


def pytest_sessionfinish(session):
    _write({"escaped": _escaped(os.path.realpath(os.environ["RED_BREAK_REAL"]))})


def _selfcheck() -> int:
    """pytest with the probe loaded, on a pass, a caught assert and a skip: one row each, plus the session's."""
    test = "import pytest\ndef test_ok():\n    pass\ndef test_bad():\n    assert 1 == 2\n" \
           "@pytest.mark.skip\ndef test_skip():\n    pass\n"
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "test_s.py").write_text(test)
        env = {**os.environ, "RED_BREAK_REPORT": str(Path(d) / "r.jsonl"), "RED_BREAK_REAL": "/nonexistent",
               "PYTHONPATH": str(Path(__file__).resolve().parent), "PYTHONDONTWRITEBYTECODE": "1"}
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "red_break_probe",
                        "test_s.py"], cwd=d, env=env, capture_output=True)
        rows = [json.loads(x) for x in (Path(d) / "r.jsonl").read_text().splitlines()]
    got = {r.get("name", "session"): (r.get("outcome"), r.get("check")) for r in rows}
    ok = got == {"test_ok": ("passed", False), "test_bad": ("failed", True), "test_skip": ("skipped", False),
                 "session": (None, None)}
    print("SELFCHECK OK" if ok else f"SELFCHECK ROSSO — {got}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_selfcheck() if sys.argv[1:] == ["--selfcheck"] else 2)
