#!/usr/bin/env python3
"""L2-T3 (#410) — the half of the flight layer that talks to the tracker.

Split out of `contextpack_flight.py` on one seam, and it is the seam that matters: this
is the ONLY part of the pack that leaves the machine. Everything else in the flight layer
reads git; this shells out to `gh`, over a network, against a remote that may not exist,
with an answer nobody can bound in advance. Keeping it in its own file means the network
boundary is one import away from being read in full, and the git half never grows a
second way to reach out.

It hands back DATA, not rows: `answer` returns the items the tracker listed plus the
reasons it could not be read, and `contextpack_flight` shapes them. That direction is
deliberate — it keeps the row vocabulary in one module and stops the two files importing
each other, which is what a "tracker module that builds flight rows" would have needed.

Three rules the git half does not have to know about:

- **An area is a label slug, and the tracker is asked for `LABEL:<slug>`.** The prefix was
  `area:` until the #426 gate measured it against a tracker whose issues carry
  `domain:<slug>` and nothing else: the pack said `issues: 10` at time 0 and carried none
  at time 1. A `polaris.*` domain id is the sealed layer's vocabulary and names no label at
  all, so it is never queried — which also keeps the resolver off the network for every
  call that passes domains rather than areas, the vault's own gates included.
- **`origin` when it exists.** `git remote` prints alphabetically, and a fork added as
  `aaa` was choosing which tracker the pack asked about.
- **Empty is not unreadable.** An empty list means the area has no open work; `None`
  means nobody could look. Collapsing them is how a pack lies by omission, so `answer`
  reports the second as a reason and never as silence.

`gh` is invoked, never imported: it is the tracker client we have and it carries its own
auth; shelling out with a timeout degrades to a reason when it is absent. Tests replay it
from `scripts/test/fixtures/flight/bin/gh`, so no gate reaches GitHub.

It ships with the resolver (`_standard/sync_scripts.py`).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

FETCH_MAX = 32          # rows taken from one tracker answer, whatever it volunteers
KINDS = ("issue", "pr")
TIMEOUT = 30
LABEL = "domain:"      # the prefix this tracker's issues actually carry — see above
TRACKER = "gh:issues+prs"


def _gh(root: Path, kind: str, area: str) -> list[dict] | None:
    """What `gh` lists for `area:<area>`, or None when it did not answer at all.

    Truncated at FETCH_MAX: `--limit` is what we ask for, and a tracker that volunteers
    ten thousand issues must not decide how big the pack is."""
    fields = ("number,title,state,updatedAt" if kind == "issue"
              else "number,title,headRefName,updatedAt")
    try:
        done = subprocess.run(["gh", kind, "list", "--label", f"{LABEL}{area}", "--state",
                               "open", "--limit", str(FETCH_MAX), "--json", fields],
                              cwd=root, capture_output=True, text=True, timeout=TIMEOUT)
        listed = json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return listed[:FETCH_MAX] if isinstance(listed, list) else None


def _remote(root: Path) -> tuple[str, str]:
    """(name, url) of the remote this repository answers for, or ("", "")."""
    try:
        done = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "remote"],
                              capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return "", ""
    names = done.stdout.split() if done.returncode == 0 else []
    name = "origin" if "origin" in names else (names[0] if names else "")
    return name, (_url(root, name) if name else "")


def _url(root: Path, name: str) -> str:
    try:
        done = subprocess.run(["git", "--no-optional-locks", "-C", str(root),
                               "remote", "get-url", name],
                              capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def areas(names: list[str]) -> list[str]:
    """The area slugs among the names the pack was asked for, in order, without repeats."""
    return [name for name in dict.fromkeys(names) if name and "." not in name]


def _found(root: Path, area: str, where: tuple[str, str]) -> tuple[list[dict], bool]:
    """(what the tracker listed for one area, whether it answered for both kinds)."""
    name, repo = where
    out, answered = [], True
    for kind in KINDS:
        listed = _gh(root, kind, area)
        answered = answered and listed is not None
        out += [{"kind": kind, "area": area, "remote": name, "repo": repo, "item": item}
                for item in listed or []]
    return out, answered


def answer(root: Path, names: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """(what the tracker listed for the asked areas, why it could not be read).

    No area asked means no question asked: the tracker is a per-area source, so a request
    naming none never expected it and gets neither rows nor a reason. A remote that does
    not exist, or a `gh` that refuses, is the other thing entirely — and says so."""
    wanted = areas(names)
    if not wanted:
        return [], []
    name, url = _remote(root)
    if not url:
        return [], ["no remote: no tracker to ask"]
    repo = url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
    found, answered = [], True
    for area in wanted:
        listed, ok = _found(root, area, (name, repo))
        found, answered = found + listed, answered and ok
    return found, ([] if answered else ["unreadable: gh did not answer"])
