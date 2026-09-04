#!/usr/bin/env python3
"""The adversarial fixtures for the state writers, kept out of the writers themselves.

Three scripts were carrying their own fixture bodies and each was over the file and function
budget because of them. The checks are worth more than the budget, so the checks moved rather
than shrank — and they live together because they share one rule: **a fixture is produced by the
shipped template or the shipped writer, never typed by hand in the shape the reader happens to
like.** A hand-made fixture only ever proves the reader agrees with itself.

Each `check_*` returns a list of booleans, one per branch that would silently corrupt a state
file. The caller prints the score and sets the exit code.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parents[2] / "templates" / "repo-contract" / "state"
FOOTER = "<!-- pol:state-contract -->"


def seeded(path: Path, name: str) -> Path:
    """A state file in the shape the package really ships to a host repo."""
    path.write_text((TEMPLATES / name).read_text(encoding="utf-8"), encoding="utf-8")
    return path


def written(path: Path, row: str, week: str = "") -> None:
    """A row placed by the shipped writer, so the fixture cannot flatter the reader.

    A `week` picks the todos door and its stamp; without one it is a cockpit thread.
    """
    cmd = [sys.executable, str(HERE / "state_upsert.py"), "week" if week else "thread", str(path)]
    cmd += ["--week", week] if week else ["--owner", "ada", "--now", "2026-09-03"]
    done = subprocess.run(cmd, input=row + "\n", capture_output=True, text=True)
    if done.returncode:
        raise AssertionError(f"the shipped writer refused the fixture: {done.stderr.strip()}")


def _two_lanes(tmp: Path) -> tuple[Path, Path]:
    """A cockpit and a todos file carrying the same two lanes, both placed by the writer."""
    cur, todos = seeded(tmp / "current.md", "current.md"), seeded(tmp / "todos.md", "todos.md")
    written(cur, "- `feat/a` (acme) — uno · since 2026-09-01")
    written(cur, "- `feat/b` (acme) — chiude #77 · since 2026-09-02")
    written(todos, "| `feat/a` — uno | | x |", "W32")
    written(todos, "| `feat/b` — due | | y |", "W36")
    return cur, todos


def check_close(tmp: Path, close, refuses) -> list[bool]:
    """A close removes, moves and re-stamps — or refuses and leaves both files identical."""
    cur, todos = _two_lanes(tmp)
    opts = argparse.Namespace(path=str(cur), todos=str(todos), key="feat/a",
                              owner="ada", now="2026-09-03")
    ok = [close(opts) == 0]
    body, rows = cur.read_text(), todos.read_text()
    active, done = rows.split("## Completed")[0], rows.split("## Completed")[1]
    stamps = [ln for ln in body.splitlines() if ln.startswith("Updated:")]
    ok += ["feat/a" not in body, "feat/b" in body,
           len(stamps) == 1 and "@ada" in stamps[0],
           "| `feat/b` — due | W36 | y |" in active,
           "| `feat/a` — uno | 2026-09-03 | x |" in done,
           done.index("| `feat/a`") < done.index(FOOTER)]   # inside the table, above the contract
    return ok + _check_refusals((cur, todos), opts, refuses)


def _check_refusals(files: tuple[Path, Path], opts, refuses) -> list[bool]:
    """An unknown key, and a todos file with no `## Completed`: both leave every byte in place."""
    cur, todos = files
    opts.key = "feat/nope"
    ok = [refuses(opts)]
    seeded(todos, "todos.md")
    written(todos, "| `feat/b` — due | | y |", "W36")
    todos.write_text(todos.read_text().split("## Completed")[0])
    was_cur, was_todos = cur.read_text(), todos.read_text()
    opts.key = "feat/b"
    return ok + [refuses(opts), cur.read_text() == was_cur, todos.read_text() == was_todos]


def check_ring(tmp: Path, append, locked) -> list[bool]:
    """Five newest first, the sixth evicts, and the same session never lands twice."""
    path = seeded(tmp / "current.md", "current.md")
    head = path.read_text().split("## Recent Context")[0]
    for n in range(1, 7):
        with locked(path):
            append(path, f"### 2026-09-0{n} — sessione {n}")
    body = path.read_text()
    ok = [body.count("### 2026-09-0") == 5, "sessione 1" not in body,
          body.index("sessione 6") < body.index("sessione 5"), body.startswith(head)]
    with locked(path):
        ok.append(append(path, "### 2026-09-06 — sessione 6")["added"] is False)
    return ok + _check_multiline(path, append, locked)


def _check_multiline(path: Path, append, locked) -> list[bool]:
    """The dedup compared a saved FIRST line against a whole incoming block, so it only ever
    fired on one-line entries: a second `/end` in one session duplicated and evicted a real one."""
    with locked(path):
        append(path, "### 2026-09-07 — sesta\n- Done: x\n")
    with locked(path):
        ok = [append(path, "### 2026-09-07 — sesta\n- Done: y\n")["added"] is False]
    ok.append(path.read_text().count("### 2026-09-07") == 1)
    path.write_text("Updated: x\n")
    try:
        with locked(path):
            append(path, "### y")
        ok.append(False)
    except ValueError:
        ok.append(True)
    return ok


def check_roll(tmp: Path, roll, locked) -> list[bool]:
    """Last week's `Completed` goes; a follow-up that came due is promoted with ITS week."""
    f = seeded(tmp / "todos.md", "todos.md")
    written(f, "| `a` — x | | ctx |", "W32")
    body = f.read_text().replace("| *None* | | |", "| `old` | 2026-08-10 | |\n| `new` | 2026-09-03 | |")
    f.write_text(body.replace("|------|-------------|------|\n| | | |",
                              "|------|-------------|------|\n| riprendi | 2026-08-24 | nota |\n"
                              "| dopo | 2999-01-01 | |"))
    with locked(f):
        out = roll(f, "2026-09-03")
    body = f.read_text()
    active, later = body.split("## Completed")[0], body.split("## Follow-ups")[1]
    return [out["dropped"] == 1, "`old`" not in body, "`new`" in body,
            "| `a` — x | W32 | ctx |" in active, out["promoted"] == 1,
            "| riprendi | W35 | nota |" in active,   # the week it CAME DUE, never today
            "riprendi" not in later, "dopo" in later]


def score(name: str, ok: list[bool]) -> int:
    """Print the score and answer with the exit code the caller returns."""
    print(f"{name} selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


def check_brief(tmp: Path, report, options) -> list[bool]:
    """The brief says only what it has, and the pack line exists only where the backbone does."""
    root = tmp / "_polaris"
    (root / "state").mkdir(parents=True)
    seeded(root / "state" / "current.md", "current.md")
    todos = seeded(root / "state" / "todos.md", "todos.md")
    written(todos, "| #1 — x | | ctx |", "W32")
    due = "|------|-------------|------|\n| scaduto | 2000-01-01 | |\n| futuro | 2999-01-01 | |"
    todos.write_text(todos.read_text().replace("|------|-------------|------|\n| | | |", due))
    opts = options(str(root), str(root / "state" / "current.md"), str(tmp))
    out = report(opts)
    silent = ("futuro", "DEFERRED=", "SECTIONS_MISSING=", "PACK=")   # nothing to say, no line
    ok = ["TODOS_ACTIVE=1" in out,
          any(o.startswith("FOLLOWUP_DUE=") and "scaduto" in o for o in out)]
    ok += [not any(o.startswith(q) or q in o for o in out) for q in silent]
    return ok + _check_pack(root, report, opts)


def _check_pack(root: Path, report, opts) -> list[bool]:
    """The pack line comes from RUNNING the resolver: a stub that only exists is not a backbone,
    and a resolver that refuses must be loud. The manifest carries no `pack_id` — the live one
    has none, and a fixture that invents it keeps a dead signal green."""
    (root / "decisions").mkdir(exist_ok=True)
    (root / "decisions" / "manifest.json").write_text('{"schema_version": 1, "decisions": []}')
    (root / "scripts").mkdir(exist_ok=True)
    resolver = root / "scripts" / "contextpack.py"
    resolver.write_text("print('{\"context_pack_id\": \"p-1\"}')\n")
    ok = ["PACK=p-1" in report(opts)]
    resolver.write_text("import sys\nsys.stderr.write('SCOPE_STALE: x\\n')\nsys.exit(1)\n")
    out = report(opts)
    return ok + [any(o.startswith("PACK=BLOCKED") and "SCOPE_STALE" in o for o in out)]
