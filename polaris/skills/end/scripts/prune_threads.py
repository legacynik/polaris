#!/usr/bin/env python3
"""`/end` is the only command that closes a thread, and now it closes them against proven truth.

Removal used to be a declared manual step, because the merge truth available at the time answered
`None` exactly when a PR had been merged with `--delete-branch`. `merge_truth.py` replaces that
answer; this file is what `/end` does with it, and the rule it adds is fail-closed:

  • PROVEN     → the thread leaves `## Open`, its todo row lands in `## Completed`, and the verdict
                 is appended to the session log — the thread does not vanish, it moves.
  • AMBIGUOUS  → stays, and says why. A branch reused after its merge is a live lane.
  • OPEN       → stays. An open PR is not a closed thread.
  • BLOCKED    → NOTHING is removed, anywhere, and the run exits 2 naming the line it could not
                 resolve. A prune that removes four lanes and quietly skips the fifth is the same
                 silent no-op it replaces, inverted.

Every verdict is collected before the first byte is written, the same order `state_close.precheck`
already uses: a close touches two files, so both are decided first and then both are written.

    prune_threads.py <current.md> --owner <l> --now <d> --log <session log> [--todos <f>] [--apply]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPDATE = HERE.parent.parent / "update" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(UPDATE))
from datetime import date  # noqa: E402
from merge_truth import CITES, default_branch, verdict  # noqa: E402  (F3: every citation)
from state_lines import kinds, lane_id, read, section  # noqa: E402
from state_sections import heading  # noqa: E402

OPEN = heading("## Open")   # the ONE registry (gate round 2, F1)
CLOSER = UPDATE / "state_close.py"


def candidates(path: Path) -> list[str]:
    """The open threads citing an issue or a PR — the predicate `state_close candidates` uses."""
    lines, _, _ = read(path)
    tags = kinds(lines)
    span = section(lines, OPEN) or (0, 0)
    return [lines[i] for i in range(*span) if tags[i] == "thread" and CITES.search(lines[i])]


STALE_DAYS = 14
SINCE = re.compile(r"since (\d{4}-\d{2}-\d{2})")


def stale(path: Path, now: str) -> list[str]:
    """Lanes citing nothing, older than STALE_DAYS: no verdict can close them, so /end names them."""
    lines, _, _ = read(path)
    tags, span = kinds(lines), section(lines, OPEN) or (0, 0)
    out = []
    for line in (lines[i] for i in range(*span) if tags[i] == "thread" and not CITES.search(lines[i])):
        hit = SINCE.search(line)
        if hit and now and (date.fromisoformat(now) - date.fromisoformat(hit[1])).days > STALE_DAYS:
            out.append(line)
    return out


def note(log: Path, line: str, why: str) -> int:
    """The thread does not vanish: it lands in the append-only log with the verdict that moved it."""
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"- Closed thread {line.strip().lstrip('-*+ ')} — {why}\n")
    return 0


def close(path: Path, line: str, opts: argparse.Namespace) -> int:
    """Delegate to the shipped closer: one notion of what removing a thread does to two files.

    A `--todos` naming a file that is not there is NOT an instruction to fail: the contract does not
    require `state/todos.md`, and the SKILL passes the path unconditionally. Before this, every
    close on a repo without one came back `UNWRITABLE` and the prune removed nothing.
    """
    args = [sys.executable, str(CLOSER), "close", str(path), "--key", lane_id(line),
            "--owner", opts.owner, "--now", opts.now]
    if opts.todos and Path(opts.todos).is_file():
        args += ["--todos", opts.todos]
    done = subprocess.run(args, capture_output=True, text=True)
    if done.returncode:
        print(f"BLOCKED={line.strip()} :: the closer refused it — {done.stderr.strip()}")
    elif done.stdout.strip():
        print(done.stdout.strip())      # the closer says what it did to the todos file; relay it
    return done.returncode


def apply(rows: list[tuple], opts: argparse.Namespace) -> int:
    """Every PROVEN row is attempted and reported. One failure never silences the rows after it —
    `bad = bad or (...)` short-circuited the loop, so a lane could be left unclosed and unmentioned.
    """
    path, log, bad = Path(opts.path), Path(opts.log), 0
    for line, kind, why in rows:
        if kind not in ("PROVEN", "DEAD"):
            continue
        if close(path, line, opts):
            bad = 2
            continue
        note(log, line, f"{kind}: {why}")
    return bad


def run(opts: argparse.Namespace) -> int:
    rows = [(line, *verdict(line, default_branch())) for line in candidates(Path(opts.path))]
    for line, kind, why in rows:
        print(f"{kind}={line.strip()} :: {why}")
    for line in stale(Path(opts.path), opts.now):
        print(f"STALE={line.strip()} :: cites nothing and is older than {STALE_DAYS} days — "
              "open an issue for it or close it with state_close.py")
    if not rows:
        print("NOTE=no open thread cites an issue or a PR")
    elif any(r[1] == "BLOCKED" for r in rows):
        print("NOTE=fail-closed — nothing removed: a candidate's state could not be read")
        return 2
    elif not opts.apply:
        print("NOTE=read-only: re-run with --apply to remove the PROVEN and DEAD threads")
    elif not (opts.log and opts.owner):
        print("prune_threads: --apply needs --log and --owner", file=sys.stderr)
        return 64
    else:
        return apply(rows, opts)
    return 0


def _fixture(root: Path) -> Path:
    """The SHIPPED template, with the lanes placed by the SHIPPED writer — never a hand-typed copy."""
    import shutil
    src = HERE.parents[1] / "start" / "templates" / "repo-contract" / "state" / "current.md"
    path = root / "current.md"
    shutil.copyfile(src, path)
    for row in ("- `feat/b` (acme-api) — chiude #77 · since 2026-09-02",
                "- `feat/a` (acme-api) — nessuna citazione · since 2026-09-01"):
        done = subprocess.run([sys.executable, str(UPDATE / "state_upsert.py"), "thread", str(path),
                               "--owner", "probe", "--now", "2026-09-03"],
                              input=row + "\n", capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(f"the shipped writer refused the fixture: {done.stderr}")
    return path


def _selfcheck() -> int:
    """The branches that would remove a live lane, or write while a verdict is unknown."""
    import os
    import tempfile
    opts = argparse.Namespace(owner="probe", now="2026-09-03", todos="", log="", apply=True)
    os.environ["PATH"] = ""      # no tracker on PATH: the BLOCKED branch, forced, and never online
    with tempfile.TemporaryDirectory() as d:
        path = _fixture(Path(d))
        opts.path, opts.log = str(path), str(Path(d) / "log.md")
        Path(opts.log).write_text("## 10:00 — probe\n")
        rows = candidates(path)
        ok = [len(rows) == 1 and "feat/b" in rows[0],       # only the citing lane is a candidate
              run(opts) == 2,                                # no gh here → BLOCKED → fail-closed
              "feat/b" in path.read_text(),                  # and nothing was removed
              Path(opts.log).read_text() == "## 10:00 — probe\n",
              apply([("- `x` — y", "AMBIGUOUS", "z")], opts) == 0,     # a non-PROVEN row is skipped
              note(Path(opts.log), "- `x` — y", "perché") == 0,
              Path(opts.log).read_text().startswith("## 10:00 — probe\n- Closed thread `x`")]
    print(f"prune_threads selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="close the threads whose work provably landed")
    ap.add_argument("path", nargs="?", help="the cockpit, `state/current.md`")
    ap.add_argument("--log", default="", help="the session log the verdicts are written to")
    ap.add_argument("--todos", default="", help="the host repo's state/todos.md")
    ap.add_argument("--owner", default="")
    ap.add_argument("--now", default="")
    ap.add_argument("--apply", action="store_true", help="remove the PROVEN threads")
    ap.add_argument("--selfcheck", action="store_true")
    return ap


def main() -> int:
    opts = _parser().parse_args()
    if opts.selfcheck:
        return _selfcheck()
    if not opts.path:
        print("prune_threads: a cockpit path is required", file=sys.stderr)
        return 64
    try:
        return run(opts)
    except (OSError, ValueError) as exc:
        print(f"UNREADABLE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
