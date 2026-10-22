#!/usr/bin/env python3
"""red_break.py — the declared BREAK, applied: does the test catch the defect it guards?

A recorded RED proves a test failed once, not that it fails when the code it protects breaks:
a mirror test (expected value computed by the implementation) has a clean RED→GREEN chain and
catches nothing. `red_check.py break` copies the working tree as it is (tracked and untracked,
never ignored; `venv`, `.venv`, `node_modules` linked so the repository's own commands start),
runs the command once unbroken — it must pass there, or a red would be the copy's, not the
break's — then replaces one exact text, present once, in one production file and runs it again
from the same subfolder. The real tree is never written: the target must resolve inside the copy.

Both runs load `red_break_probe.py` into pytest (`-p`, through PYTEST_ADDOPTS and PYTHONPATH) and
never write bytecode; `uv run` does not sync (UV_NO_SYNC). The real tree is read before and after:
any change there throws the run away as inconclusive. A red is a catch only if pytest's own facts say the NAMED test failed with a
check raised in test code (`red_break_report.py`); a crash, an assert in production code, another
test's failure, a skipped test, an import from the real tree, or a runner that is not pytest is
inconclusive.

Exit: 0 the test turns red (recorded) · 1 it stays green (recorded: it proves nothing about that
code) · 2 refused or inconclusive (nothing recorded). Limits: one replacement per break; a full
copy per break (~3 s on 9k files) and two runs; a test that writes next to an imported real-tree
file, or a workspace link into the real tree (`node_modules`), is not caught; pytest only.
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import red_break_copy as copy_src  # noqa: E402  — the throwaway copy and its bytecode
import red_break_report as report  # noqa: E402  — the verdict, from what pytest itself reported


refused = report.refused  # `verify --break`: what the break rows say, read in red_break_report


def _stop(kind: str, why: str) -> int:
    print(f"break {kind}: {why}", file=sys.stderr)
    return 2


def _target(a, root: Path, here: Path) -> tuple[str, str] | int:
    """(repository-relative production file, its text) or the refusal's exit code."""
    path, test = here / a.file, here / a.test.split("::")[0]
    real = path.resolve()
    if path.is_symlink() or not real.is_relative_to(root) or copy_src.TOOLS & set(real.relative_to(root).parts):
        return _stop("refused", f"{a.file} is a link, outside the repository or in a linked tool folder")
    if report.looks_like_test(real.relative_to(root)):
        return _stop("refused", f"{a.file} is test code (test_*, *_test, conftest.py or under tests/): "
                                "a break there proves nothing about the code — break production code")
    if test.exists() and real.exists() and os.path.samefile(real, test):
        return _stop("refused", "the break edits the test itself: it would prove nothing about the code")
    try:
        text = real.read_bytes().decode("utf-8") if real.is_file() else ""
    except UnicodeDecodeError:
        return _stop("refused", f"{a.file} is not UTF-8 text")
    if a.old == a.new or text.count(a.old) != 1:
        return _stop("refused", f"{a.file} must hold the old text exactly once, and new must differ "
                                f"(found {text.count(a.old)})")
    return real.relative_to(root).as_posix(), text


def _command(a, tmp: Path, where: tuple[Path, Path, list[str]]) -> str:
    """The command, from the copy's subfolder, with the probe loaded and no bytecode written."""
    root, here, extra = where
    (tmp / "probe").mkdir()
    shutil.copy2(Path(__file__).resolve().parent / f"{report.PROBE}.py", tmp / "probe")
    path = ":".join([str(tmp / "probe"), *extra])
    return (f'export PYTEST_ADDOPTS="$PYTEST_ADDOPTS -p {report.PROBE}" '
            f'PYTHONPATH={shlex.quote(path)}"${{PYTHONPATH:+:$PYTHONPATH}}" PYTHONDONTWRITEBYTECODE=1 UV_NO_SYNC=1 '
            f"RED_BREAK_REPORT={shlex.quote(str(tmp / 'report.jsonl'))} RED_BREAK_REAL={shlex.quote(str(root))}; "
            f"cd {shlex.quote(str(tmp / 'tree' / here.relative_to(root)))} && {str(a.cmd).strip()}")


def _trial(a, where: tuple[Path, Path, tuple[str, str]], run):
    """Unbroken run (the named test must pass), then the broken one, in one throwaway copy:
    (completed run, red) or an exit code."""
    root, here, (rel, text) = where
    with tempfile.TemporaryDirectory(prefix="red-break-") as tmp:
        tmp = Path(tmp).resolve()
        base, file, rest = tmp / "tree", *a.test.partition("::")[::2]
        cmd = _command(a, tmp, (root, here, copy_src.pythonpath(root, base, copy_src.copy(root, base))))
        if (base / rel).is_symlink() or not (base / rel).is_file() or not (base / rel).resolve().is_relative_to(base):
            return _stop("refused", f"{rel} is not a file of the copy (ignored by git?): the break would create it")
        named = (tmp / "report.jsonl", ((base / here.relative_to(root) / file).resolve(), rest), base)
        if (control := _verdict(run(cmd), named)) is not False:
            return control if control is not True else _stop(
                "inconclusive", "the named test does not pass in the copy without the break "
                                "(an ignored file, git or a path it needs is missing there)")
        copy_src.write(base, base / rel, text.replace(a.old, a.new))
        return _verdict(run(cmd), named, keep=True)


def _verdict(esito, named: tuple, keep: bool = False):
    """The probe's word on the named test (then its report is removed for the next run)."""
    red, why = report.verdict(*named) if esito is not None else (None, report.NO_REPORT)
    named[0].unlink(missing_ok=True)
    if red is None:
        return _stop("inconclusive", why)
    return (esito[0], red) if keep else red


def cmd_break(a, run, sha) -> int:
    """`run` and `sha` are red_check's own: one verdict on whether the runner spoke, one hash."""
    here = Path.cwd().resolve()
    top = "".join(copy_src.git(here, "rev-parse", "--show-toplevel")).strip()
    if not top or not str(a.cmd).strip():
        return _stop("refused", "not inside a git checkout" if not top else "--cmd is empty")
    root = Path(top).resolve()
    if top in str(a.cmd) or str(root) in str(a.cmd):
        return _stop("refused", "the command names the real repository's path: it would run there, not in the copy")
    target = _target(a, root, here)
    if isinstance(target, int):
        return target
    before = copy_src.snapshot(root)
    esito = _trial(a, (root, here, target), run)
    if moved := copy_src.changed(root, before):
        return _stop("inconclusive", f"the real tree changed during the break ({', '.join(moved[:3])}): the command "
                                     "wrote outside the copy (a runner that syncs, like `uv run`?) or someone else edited it")
    return esito if isinstance(esito, int) and not isinstance(esito, bool) else _record(a, (target[0], esito), sha)


def _record(a, found: tuple, sha) -> int:
    """Append the break row; 0 when the test turned red, 1 when it stayed green."""
    rel, (r, rosso) = found
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "test": a.test, "cmd": str(a.cmd).strip(),
             "exit": r.returncode, "tail": ((r.stdout or "") + (r.stderr or ""))[-800:], "rosso": rosso,
             "file_sha": sha(Path(a.test.split("::")[0])), "break": {"file": rel, "old": a.old, "new": a.new}}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with Path(a.out).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if not rosso:
        print(f"break: {a.test} stays GREEN with {rel} broken — it proves nothing about that code", file=sys.stderr)
        return 1
    print(f"break: ROSSO with {rel} broken -> {a.out}")
    return 0


def add_parser(sub, verify, own: tuple) -> dict:
    """The `break` subcommand and the opt-in `verify --break` (existing callers unchanged); returns
    the action, bound to red_check's own `(run, sha)`."""
    verify.add_argument("--break", dest="rompi", action="store_true", help="also require a red break after GREEN")
    b = sub.add_parser("break", help="applies the declared BREAK in a copy: the test must turn red")
    for flag in ("--test", "--cmd", "--out", "--file", "--old", "--new"):
        b.add_argument(flag, required=True)
    return {"break": lambda a: _guarded(a, own)}


def _guarded(a, own: tuple) -> int:
    """A crash of the tool is inconclusive (2), never the GREEN verdict's exit 1 (round 6)."""
    try:
        return cmd_break(a, *own)
    except (OSError, ValueError) as exc:  # ValueError: UnicodeError, a broken report line
        return _stop("inconclusive", f"the tool could not finish: {type(exc).__name__}: {exc}")


def _selfcheck() -> int:
    """The whole point, on a scratch repository: a real test turns red under the break, a mirror
    of the same code stays green and is named, and the real tree is left as it was."""
    code = "RATE = 10\n\ndef price(q):\n    return q * RATE\n"
    tests = {"t_real.py": "from c import price\ndef test_p():\n    assert price(3) == 30\n",
             "t_mirror.py": "import c\ndef test_p():\n    assert c.price(3) == 3 * c.RATE\n"}
    script, expected = Path(__file__).resolve().parent / "red_check.py", {"t_real.py": 0, "t_mirror.py": 1}
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "c.py").write_text(code)
        for name, text in tests.items():
            (Path(d) / name).write_text(text)
        subprocess.run(["git", "init", "-q", d], check=True)
        got = {t: subprocess.run([sys.executable, str(script), "break", "--test", t, "--out", "o.jsonl",
                                  "--cmd", f"{sys.executable} -m pytest -q -p no:cacheprovider {t}",
                                  "--file", "c.py", "--old", "RATE = 10", "--new", "RATE = 11"],
                                 cwd=d, capture_output=True, text=True).returncode for t in tests}
        intact = (Path(d) / "c.py").read_text() == code
    ok = got == expected and intact
    print(f"{'SELFCHECK OK' if ok else 'SELFCHECK ROSSO'} — exits {got}, tree intact: {intact}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_selfcheck() if sys.argv[1:] == ["--selfcheck"] else 2)
