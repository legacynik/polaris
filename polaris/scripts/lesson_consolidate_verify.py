#!/usr/bin/env python3
"""#156 (L4) — the `verified_against` a lesson does not have, PROPOSED under four rules.

The founder's answer to question 2 of the lifecycle plan (2026-09-17) is that a lesson
enters the area pack only with a `verified_against` that resolves to a commit. On
2026-09-19 the three ledgers carried 471 lessons and zero such fields.

Round 1 of the critic and the breaker on PR #439 rejected three of the four signatures
this module proposed, and every one of them was a different way of dating a lesson instead
of verifying it:

- **the commit that WROTE the lesson** (`a1941eb`, found by a text match on a name the
  lesson itself introduced). Circular: the lesson cannot be its own evidence.
- **a commit that PRECEDES the lesson's own `last_triggered`** (`5fc5a14`). A rule that
  fired after a commit is not verified by that commit.
- **`git log -S <name>`**, the last commit whose diff MENTIONS a string. `python3`,
  `wiki_aggregate.py` in a paragraph, a skill name in prose — all dated something.

So the search is now narrow on purpose, and four rules hold it there:

1. **A path, never a mention.** Only a path the repository carries at HEAD, cited in
   backticks by the lesson, and the commit that last MODIFIED it.
2. **Not the ledger, and not a global prose authority.** `lessons.md` moves every time a
   lesson is written and `CLAUDE.md` every time a rule is edited; "the last commit that
   touches it" verifies nothing about any single lesson.
3. **Independent of the lesson.** A commit whose diff also touches the ledger is the
   commit that wrote the lesson, and that is circularity, not evidence.
4. **Newer than the lesson.** The commit date must not precede the latest date the block
   states — its `last_triggered`, or the newest date in its prose.

What survives is offered, with the path it came from; `--apply --sign` writes it and
`verified_why: <path>@<sha>`, so a reader checks the claim without rerunning anything.
Nothing here reaches the network, and the ledger's line endings come back as they went in.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import contextpack_lessons as lessons
import contextpack_prose as prose

CITED = re.compile(r"`([^`\s]{3,120})`")
TIMEOUT = 30
LIMIT = 12   # the first cited things of a block; a lesson that cites 40 is a document
# A path whose every commit is somebody writing prose about everything: it dates a lesson
# and verifies none. The ledger and the instructions were named by the critic; the three
# live authorities are the same class — `DOMAIN.md` moved for a component list this very
# PR added, which would have "verified" a lesson about something else entirely.
DENIED = {"lessons.md", "CLAUDE.md", "AGENTS.md", "decisions.md", "POLARIS.md",
          "CONTEXT.md", "ARCHITECTURE.md", "DOMAIN.md"}


def _git(root: Path, *args: str) -> str:
    """One read of history, or nothing at all. A missing repository is not a traceback."""
    try:
        done = subprocess.run(["git", "--no-optional-locks", "-C", str(root), *args],
                              capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip().splitlines()[0] if done.returncode == 0 and done.stdout else ""


def _evidence(root: Path, token: str, ledger: str) -> bool:
    """Whether this cited token is ONE file of this repository (rules 1 and 2).

    A directory and a glob both satisfy `ls-files`, and `git log -1 -- scripts/` is the
    last commit that touched anything at all under it — the same "it moved, therefore the
    lesson holds" that got `CLAUDE.md` rejected. The listing must name the token itself,
    which only one tracked file does."""
    if not token or token.startswith("-") or Path(token).name in DENIED or token == ledger:
        return False
    return _git(root, "ls-files", "--error-unmatch", "--", token) == token


def _independent(root: Path, sha: str, ledger: str) -> bool:
    """Rule 3: a commit that also writes the ledger is the one that wrote the lesson."""
    return not _git(root, "show", "--name-only", "--format=", sha, "--", ledger)


def _newer(root: Path, sha: str, stated: str) -> bool:
    """Rule 4: the commit must not precede the latest date the lesson states."""
    when = _git(root, "show", "-s", "--format=%cs", sha)
    return bool(when) and (not stated or when >= stated)


def _stamp(text: str) -> str:
    """The latest date the block states — `last_triggered`, or the newest date in it."""
    found = prose.DATE.findall(text)
    return max(found) if found else ""


def _for_token(root: Path, token: str, ledger: str) -> tuple[str, str, str] | None:
    """(sha, why, path) for a cited path, once all four rules hold."""
    if not _evidence(root, token, ledger):
        return None
    sha = _git(root, "log", "-1", "--format=%H", "--", token)
    if not sha or not lessons._resolves(root, sha) or not _independent(root, sha, ledger):
        return None
    return sha, f"last commit that modifies `{token}`", token


def _commit(root: Path, row: dict, ledger: str) -> tuple[str, str, str] | None:
    """The first cited path of this lesson that names an independent, later commit."""
    for token in dict.fromkeys(CITED.findall(row["text"])[:LIMIT]):
        found = _for_token(root, token, ledger)
        if found and _newer(root, found[0], _stamp(row["text"])):
            return found
    return None


def propose(root: Path, rows: list[dict], ledger: str = "lessons.md") -> dict[str, tuple]:
    """id -> (sha, why, path) for every unverified lesson that cites a path git can date."""
    found: dict[str, tuple] = {}
    for row in rows:
        if row.get("verified_against"):
            continue
        hit = _commit(root, row, ledger)
        if hit:
            found[row["id"]] = hit
    return found


def _fields(row: dict, made: tuple, area: str) -> list[str]:
    """What a signature writes: the field, why it holds, and an `area:` if asked for.

    A lesson of no area is nobody's lesson — `contextpack_lessons.rows` filters on it. The
    `verified_why` line is what round 1 was missing: a sha alone is a claim, `<path>@<sha>`
    is a claim a reader can check without rerunning the proposal."""
    sha, _, path = made
    lines = [f"- verified_against: {sha}", f"- verified_why: {path}@{sha}"]
    return lines if row.get("area") or not area else lines + [f"- area: {area}"]


def apply(path: Path, signed: list[tuple[dict, tuple]], area: str) -> int:
    """Write the signed fields bottom-up, in the line endings the ledger already had."""
    raw = path.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")
    for row, made in sorted(signed, key=lambda pair: -pair[0]["line"]):
        lines[row["line"]:row["line"]] = _fields(row, made, area)
    path.write_bytes(eol.join(lines).encode("utf-8"))
    return 0
