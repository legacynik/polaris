#!/usr/bin/env python3
"""polaris-os#155 — the three doors reach ONE session, or the receipts are stumps.

The engine (`scripts/session_continuity.py`) has been in the vault for weeks and nothing called
its `start`: the pack receipt and the reinsertion after a compaction both answered
`NO_OPEN_SESSION`, so the resolver's whole output died with the context window it was printed
into. This is the wiring, and only the wiring — the engine stays where it is, host first and
then the vault the repository declares, exactly as the brief's compiler is found. `reinsert`
is here for the same reason: three copies of «host, then the declared vault, then nothing» is
two too many, and the copy in the compaction hook was the one nobody could see failing.

`open` derives the sid (checkout + day + login); `note` and `close` act on the session that is
OPEN. A second `/start` the same day resumes; one after a close opens a new seat.

Feature detection is the rule of #155: a repository with no engine — its own or its vault's —
must not even learn the feature exists. No engine, no line, no file, exit 0.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _brief_parts import _resolver, _vault  # noqa: E402
from _session_seat import (free_sid, ignore_itself, open_seat,  # noqa: E402
                           top_of, work_item)

ENGINE = Path("scripts") / "session_continuity.py"
REINSERT = Path("scripts") / "contextpack_reinsert.py"
TIMEOUT = 40  # the engine resolves a pack: the brief's 25 s is the budget of a read, not this
CODE = re.compile(r"^[A-Z][A-Z_]{2,}:")


def run(script: Path, args: list[str]) -> subprocess.CompletedProcess:
    """The engine, isolated from the caller's site-packages, never allowed to hang a session."""
    try:
        return subprocess.run([sys.executable, "-I", str(script), *args], capture_output=True,
                              text=True, errors="replace", timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(args, 2, "", "GATE_UNREACHABLE: no answer\n")


def cause(done: subprocess.CompletedProcess) -> str:
    """The engine's refusal CODE, else its last word.

    The first line was not it: a crash starts with `Traceback (most recent call last):`, the
    header of a cause and never the cause. A coded line comes first when there is one, and a
    traceback says what actually happened on its LAST line."""
    said = [line for line in (done.stderr or done.stdout).strip().splitlines() if line.strip()]
    coded = [line for line in said if CODE.match(line)]
    return (coded[0] if coded else said[-1] if said else "no cause given")[:120]


def cmd_open(engine: Path, root: Path, opts: argparse.Namespace) -> int:
    """Open the session, or say in ONE line why there is none. Never fails the brief."""
    sid = opts.sid or free_sid(root, opts.login)
    ignore_itself(root)
    args = ["start", "--root", str(top_of(root)), "--sid", sid]
    item = work_item(root)
    done = run(engine, args + (["--work-item", item] if item else []))
    if done.returncode and item and "WORK_ITEM_UNVERIFIED" in cause(done):
        done = run(engine, args)  # the branch named an issue this repo never declared
    if done.returncode == 0:
        print(f"SESSION: opened {sid}")
    elif cause(done).startswith("SESSION_EXISTS"):
        print(f"SESSION: resumed {sid}")
    else:
        print(f"SESSION: blocked — {cause(done)}")
    return 0


def cmd_note(engine: Path, root: Path, opts: argparse.Namespace) -> int:
    """One checkpoint event on the open session. No open session, no line, no error."""
    home = open_seat(root, opts.login)
    if home is None:
        return 0
    done = run(engine, ["update", "--root", str(top_of(root)), "--sid", home.name,
                        "--note", opts.note])
    if done.returncode:
        print(f"SESSION: checkpoint refused — {cause(done)}", file=sys.stderr)
    return 0


def cmd_close(engine: Path, root: Path, opts: argparse.Namespace) -> int:
    """Close the open session. A refusal STOPS `/end`; nothing open does not.

    Nothing open is the midnight case, the panel that never ran `/start`, and the second
    `/end` of one session — three ways to lose the handoff commit if this exited non-zero,
    and none of them a broken boundary. A receipt already written is never rewritten.
    """
    home = open_seat(root, opts.login)
    if home is None:
        print("SESSION: none open — nothing to close")
        return 0
    done = run(engine, ["end", "--root", str(top_of(root)), "--sid", home.name,
                        "--handoff", opts.handoff])
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    return done.returncode


def cmd_reinsert(script: Path, root: Path, opts: argparse.Namespace) -> int:
    """Put the pack back from the receipt, against the root the session actually lives under."""
    done = run(script, ["reinsert", "--root", str(top_of(root))]
               + (["--sid", opts.sid] if opts.sid else []))
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    return 0  # a reinsertion that cannot happen is a cost, never a failed session


DOORS = {"open": (ENGINE, cmd_open), "note": (ENGINE, cmd_note),
         "close": (ENGINE, cmd_close), "reinsert": (REINSERT, cmd_reinsert)}
NO_ENGINE = "NOTA: nessun gate del backbone in questo repo — le sei righe sopra sono la checklist"


def main() -> int:
    ap = argparse.ArgumentParser(description="#155 — the session the three doors share")
    ap.add_argument("command", choices=[*DOORS, "sid", "vault"])
    ap.add_argument("--root", default=".", help="the Polaris root of THIS worktree")
    for flag in ("--login", "--sid", "--note", "--handoff"):
        ap.add_argument(flag, default="")
    opts = ap.parse_args()
    root = Path(opts.root)
    if opts.command == "sid":
        print(opts.sid or (home.name if (home := open_seat(root, opts.login)) else
                           free_sid(root, opts.login)))
        return 0
    if opts.command == "vault":
        print(_vault(root) or "")
        return 0
    rel, door = DOORS[opts.command]
    script = _resolver(root, rel)
    if script is None:
        if opts.command == "close":
            print(NO_ENGINE)
        return 0
    return door(script, root, opts)


if __name__ == "__main__":
    sys.exit(main())
