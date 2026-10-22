#!/usr/bin/env python3
"""red_break_report.py — did the NAMED test catch the break? Read from what pytest itself reported.

A regex on console output was half-closed twice (#562), and pytest's junit report a third time: it
names a test by basename and class suffix (a same-named method, or a test file with the same
basename elsewhere, lent its red), counts a skipped test as passed, and keeps tracebacks as text.
`red_break_probe.py` writes pytest's own facts instead. The named test is matched by its absolute
file in the copy and its exact nodeid after the file (a parametrized case or a class's methods
too). A catch is a named test failing in its call with a check (an AssertionError, `pytest.fail`,
`pytest.raises`) whose innermost frame inside the copy, outside its tool folders, is test code: a
test module pytest ran a test function from (a doctest makes no module test code), a `conftest.py`, or a file under a `tests/`/`test/` folder that holds the
named test. So a mock's assertion (raised in the standard library) and a shared assertion helper
catch, and an assert in production code does not — even in a module named `test_*.py` that pytest
ran no test from, or under a `test/` folder elsewhere (round 4). A skipped or xfail named test, a module imported from the real tree, or
no report at all is inconclusive.
"""
import json
import sys
import tempfile
from pathlib import Path

TOOLS = {"venv", ".venv", "node_modules"}
PROBE = "red_break_probe"
NO_REPORT = ("no pytest report: `break` reads pytest's own report — run the test through pytest; a command "
             "that sets PYTHONPATH drops the probe: use pytest's `-o pythonpath=<dirs>` instead")


def _rows(report: Path) -> list[dict]:
    lines = report.read_text(encoding="utf-8").splitlines() if report.is_file() else []
    return [json.loads(x) for x in lines if x.strip()]


def _named(rows: list[dict], named: tuple[Path, str]) -> list[dict]:
    """The rows of the named test: its file, then its exact nodeid (or what that nodeid contains)."""
    file, rest = named
    return [r for r in rows if "file" in r and Path(r["file"]).resolve() == file and (
            not rest or r["name"] == rest or r["name"].startswith((rest + "[", rest + "::")))]


def looks_like_test(rel: Path) -> bool:
    """A break target that is test code by its name or folder: a break there proves nothing about
    the code (round 4: a broken `conftest.py` or helper turned a mirror test red)."""
    return (rel.name.startswith("test_") or rel.stem.endswith("_test") or rel.name == "conftest.py"
            or bool({"tests", "test"} & set(rel.parts[:-1])))


def _test_code(path: Path, ctx: tuple[Path, Path, set]) -> bool:
    test, base, ran = ctx
    homes = [d for d in test.parents if d.is_relative_to(base) and d.name in ("tests", "test")]
    return path in ran or path.name == "conftest.py" or any(path.is_relative_to(d) for d in homes)


def _caught(row: dict, ctx: tuple[Path, Path, set]) -> bool:
    """A failed check, raised (innermost frame in the copy, outside its tool folders) in test code."""
    base = ctx[1]
    inside = [p for p in (Path(f).resolve() for f in row["frames"])
              if p.is_relative_to(base) and not TOOLS & set(p.relative_to(base).parts)]
    return (row["when"] == "call" and row["outcome"] == "failed" and row["check"]
            and bool(inside) and _test_code(inside[-1], ctx))


def verdict(report: Path, named: tuple[Path, str], base: Path) -> tuple[bool | None, str]:
    """(True: a named test caught it, even if another crashed · False: all passed · None: why not)."""
    rows = _rows(report)
    if not rows:
        return None, NO_REPORT
    if escaped := next((r["escaped"] for r in rows if r.get("escaped")), ""):
        return None, f"the run imported {escaped} from the real tree, not the copy (an editable install?)"
    cases = _named(rows, named)
    if not cases:
        return None, f"{named[1] or named[0].name} is not in pytest's report: name the test as pytest collects it"
    ran = {Path(r["file"]).resolve() for r in rows if r.get("function")}
    if any(_caught(r, (named[0], base, ran)) for r in cases):
        return True, ""
    if any(r["outcome"] in ("skipped", "xfail") for r in cases):
        return None, "the named test is skipped or xfail in the copy: it ran nothing to catch"
    if not any(r["outcome"] == "failed" for r in cases):
        return False, ""
    if not all(r["check"] for r in cases if r["outcome"] == "failed"):
        return None, "the break made the code crash and no check failed: choose a break that returns a wrong value"
    return None, "the failed check was raised in production code, not in the test: the test did not catch it"


def refused(runs: list[dict], test: str, verde: dict) -> bool:
    """`verify --break`: a red break after GREEN, with GREEN's command and test hash. Every break of
    that test, command and hash that stayed green is printed, never erased: a good test is green
    under a break of code it does not cover (round 3), so the reader judges each declared break."""
    same = [r for r in runs if r.get("break") and r.get("test") == test and r.get("cmd") == verde.get("cmd")
            and r.get("file_sha") == verde.get("file_sha")]
    for r in (r for r in same if not r.get("rosso")):
        print(f"warning: {test} stayed green with {r['break']['file']} broken "
              f"({r['break']['old']!r} -> {r['break']['new']!r}): it does not guard that code", file=sys.stderr)
    if any(r.get("rosso") and r.get("ts", "") > verde["ts"] for r in same):
        return False
    print(f"no red break of {test} after its GREEN, with the same command and test file: run "
          "`red_check.py break`", file=sys.stderr)
    return True


def _selfcheck() -> int:
    """A catch, a mock's catch, a production assert, a skip and a same-named method, as rows."""
    def row(name: str, frames: list[str], **kw) -> dict:
        return {"file": "/c/t.py", "name": name, "when": "call", "outcome": "failed", "check": True,
                "function": True, "frames": frames, **kw}
    shapes = {"catch": ([row("test_p", ["/c/t.py"])], True), "mock": ([row("test_p", ["/c/t.py", "/lib/mock.py"])], True),
              "prod": ([row("test_p", ["/c/t.py", "/c/calc.py"])], None),
              "skip": ([row("test_p", [], outcome="skipped", check=False)], None),
              "class": ([row("TestK::test_p", ["/c/t.py"]), row("test_p", [], outcome="passed", check=False)], False)}
    got = {}
    with tempfile.TemporaryDirectory() as d:
        for name, (rows, _) in shapes.items():
            (Path(d) / name).write_text("\n".join(json.dumps(r) for r in rows))
            got[name] = verdict(Path(d) / name, (Path("/c/t.py"), "test_p"), Path("/c"))[0]
    ok = got == {name: shape[1] for name, shape in shapes.items()}
    print("SELFCHECK OK" if ok else f"SELFCHECK ROSSO — {got}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_selfcheck() if sys.argv[1:] == ["--selfcheck"] else 2)
