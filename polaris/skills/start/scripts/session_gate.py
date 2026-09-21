#!/usr/bin/env python3
"""polaris-os#155 — the three doors reach ONE session, or the receipts are stumps.

The engine (`scripts/session_continuity.py`) has been in the vault for weeks and nothing called
its `start`: the pack receipt and the reinsertion after a compaction both answered
`NO_OPEN_SESSION`, so the resolver's whole output died with the context window it was printed
into. This is the wiring, and only the wiring — the engine stays where it is, host first and
then the vault the repository declares, exactly as the brief's compiler is found.

The sid is DERIVED, never passed: the checkout, the day and the login. `/update` and `/end`
recompute the same string and therefore reach the session `/start` opened, with nothing carried
between processes. A second `/start` the same day is a RESUME, not an error.

Feature detection is the rule of #155: a repository with no engine — its own or its vault's —
must not even learn the feature exists. No engine, no line, no file, exit 0.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _brief_parts import _resolver, _vault, git  # noqa: E402

ENGINE = Path("scripts") / "session_continuity.py"
TIMEOUT = 40  # the engine resolves a pack: the brief's 25 s is the budget of a read, not this
ISSUE = re.compile(r"(?:^|[/_-])(\d+)(?:[/_-]|$)")


def top_of(root: Path) -> Path:
    """The CHECKOUT the session belongs to — the same root the pack is compiled against."""
    return Path(git(root, "rev-parse", "--show-toplevel") or root)


def sid_for(root: Path, login: str) -> str:
    """`s-<login>-<YYYYMMDD>-<hash6 of the checkout>`: one session per checkout per day."""
    top = top_of(root)
    who = re.sub(r"[^A-Za-z0-9._-]", "-", login or git(root, "config", "--get", "polaris.login")
                 or "anon")
    return f"s-{who}-{time.strftime('%Y%m%d')}-{hashlib.sha256(str(top).encode()).hexdigest()[:6]}"


def work_item(root: Path) -> str:
    """`issue:<repo>#<n>` when the branch carries a number, else nothing.

    Nothing is the safe answer: an undeclared work item makes the resolver raise
    WORK_ITEM_UNVERIFIED, and a session that refuses to open over a branch name is worse than
    a session opened on the repository's own foundation pack. `open` retries without it.
    """
    found = ISSUE.search(git(root, "rev-parse", "--abbrev-ref", "HEAD"))
    if not found:
        return ""
    remote = git(root, "config", "--get", "remote.origin.url") or str(top_of(root))
    return f"issue:{remote.rstrip('/').split('/')[-1].removesuffix('.git')}#{found.group(1)}"


def sid_of(opts: argparse.Namespace) -> str:
    """The sid this invocation is about: the one given, else the one today's checkout derives."""
    return opts.sid or sid_for(Path(opts.root), opts.login)


def run(engine: Path, args: list[str]) -> subprocess.CompletedProcess:
    """The engine, isolated from the caller's site-packages, never allowed to hang a session."""
    try:
        return subprocess.run([sys.executable, "-I", str(engine), *args], capture_output=True,
                              text=True, errors="replace", timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(args, 2, "", "GATE_UNREACHABLE: the engine did not answer\n")


def cause(done: subprocess.CompletedProcess) -> str:
    """The refusal code the engine printed, or the whole first line when it printed no code."""
    first = ((done.stderr or done.stdout).strip().splitlines() or ["no cause given"])[0]
    return first[:120]


def cmd_open(engine: Path, root: Path, sid: str) -> int:
    """Open the session, or say in ONE line why there is none. Never fails the brief."""
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
    """One checkpoint event on the open session. No session, no line, no error."""
    top, sid = top_of(root), sid_of(opts)
    if not (top / "state" / "session" / sid / "start.json").is_file():
        return 0
    done = run(engine, ["update", "--root", str(top), "--sid", sid, "--note", opts.note])
    if done.returncode:
        print(f"SESSION: checkpoint refused — {cause(done)}", file=sys.stderr)
    return 0


def cmd_close(engine: Path, root: Path, opts: argparse.Namespace) -> int:
    """Close the session. A refusal STOPS `/end`; only an absent engine degrades (caller)."""
    done = run(engine, ["end", "--root", str(top_of(root)), "--sid", sid_of(opts),
                        "--handoff", opts.handoff])
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    return done.returncode


def dispatch(engine: Path, opts: argparse.Namespace) -> int:
    root = Path(opts.root)
    if opts.command == "open":
        return cmd_open(engine, root, sid_of(opts))
    if opts.command == "note":
        return cmd_note(engine, root, opts)
    return cmd_close(engine, root, opts)


NO_ENGINE = "NOTA: nessun gate del backbone in questo repo — le sei righe sopra sono la checklist"


def main() -> int:
    ap = argparse.ArgumentParser(description="#155 — the session the three doors share")
    ap.add_argument("command", choices=["open", "note", "close", "sid", "vault"])
    ap.add_argument("--root", default=".", help="the Polaris root of THIS worktree")
    for flag in ("--login", "--sid", "--note", "--handoff"):
        ap.add_argument(flag, default="")
    opts = ap.parse_args()
    root = Path(opts.root)
    if opts.command == "sid":
        print(sid_of(opts))
        return 0
    if opts.command == "vault":
        print(_vault(root) or "")
        return 0
    engine = _resolver(root, ENGINE)
    if engine is None:
        if opts.command == "close":
            print(NO_ENGINE)
        return 0
    return dispatch(engine, opts)


if __name__ == "__main__":
    sys.exit(main())
