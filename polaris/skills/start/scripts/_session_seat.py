#!/usr/bin/env python3
"""WHERE a session lives, and which one the doors are talking about.

One root, or the feature is invisible: `emit_pack` compiles the pack against
`git rev-parse --show-toplevel`, the pack receipt is written beside it, and the dashboard
looks for the session under the root it was given. A seat under `$ROOT` (`<repo>/_polaris`,
which in a product repository is NOT the checkout) would be read by nobody — the brief would
keep saying `RECEIPT: none` and the reinsertion `NO_OPEN_SESSION`.

The sid is derived from checkout + day + login so three processes agree without passing
anything. Derivation alone is not enough on a real day, though: at midnight it rolls over
while the session is still open, a panel may never have run `/start`, and the second session
of one day would land on a seat already closed. So the doors ask for the OPEN seat, and only
`open` derives.
"""
from __future__ import annotations

import hashlib
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _brief_parts import git  # noqa: E402

ISSUE = re.compile(r"(?:^|[/_-])(\d+)(?:[/_-]|$)")
LIMIT = 100  # sessions of one day on one checkout; beyond it something else is wrong


def top_of(root: Path) -> Path:
    """The checkout the session belongs to — the same root the pack is compiled against."""
    return Path(git(root, "rev-parse", "--show-toplevel") or root)


def seats(root: Path) -> Path:
    return top_of(root) / "state" / "session"


def is_open(home: Path) -> bool:
    return (home / "start.json").is_file() and not (home / "end.json").exists()


def who(root: Path, login: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-",
                  login or git(root, "config", "--get", "polaris.login") or "anon")


def sid_for(root: Path, login: str) -> str:
    """`s-<login>-<YYYYMMDD>-<hash6 of the checkout>`: one session per checkout per day."""
    digest = hashlib.sha256(str(top_of(root)).encode()).hexdigest()[:6]
    return f"s-{who(root, login)}-{time.strftime('%Y%m%d')}-{digest}"


def free_sid(root: Path, login: str) -> str:
    """The derived sid, or the next free one when today's is already CLOSED.

    A closed seat cannot be resumed and must not be overwritten: the second work session of
    one day is a session of its own, and the `-2` says so."""
    base = sid_for(root, login)
    if not (seats(root) / base / "end.json").exists():
        return base
    return next(f"{base}-{n}" for n in range(2, LIMIT)
                if not (seats(root) / f"{base}-{n}").exists())


def open_seat(root: Path, login: str) -> Path | None:
    """The session still open in this checkout for this contributor, newest first."""
    found = [home for home in seats(root).glob(f"s-{who(root, login)}-*") if is_open(home)]
    return max(found, key=lambda home: home.stat().st_mtime) if found else None


def ignore_itself(root: Path) -> None:
    """The seat directory ignores its own contents.

    Receipts are ephemeral and `state/session/` is not in any product repository's
    `.gitignore`. One `*` inside the directory keeps it out of `git status` without editing
    a tracked file of somebody else's repository, and `/end`'s clean-tree gate stays true.
    """
    mark = seats(root) / ".gitignore"
    if not mark.exists():
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.write_text("*\n")


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
