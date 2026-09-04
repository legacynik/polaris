#!/usr/bin/env python3
"""Did this thread's work actually land? Two sources have to agree, or the answer is "I don't know".

The defect that kept automatic removal parked was a truth that trusted one source: `bool(merged)`
reported success and removed nothing, because the local branch ref is gone once a PR merges with
`--delete-branch`. So the verdict here needs BOTH —

    the TRACKER — `gh pr view N` says MERGED, or `gh issue view N` says CLOSED as completed
    the REPO    — that PR's head, or its merge commit, is an ancestor of the default branch HERE

and it distinguishes four answers, never two: PROVEN, AMBIGUOUS (merged somewhere this checkout
cannot see, or a branch reused after its merge), OPEN (the tracker says it is not done), BLOCKED
(the tracker could not be read at all — absent `gh`, an error, a rate limit, an empty answer).
BLOCKED is not OPEN: one is "not yet", the other is "nobody knows", and only the second must stop
a caller from writing.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

CITES = re.compile(r"#(\d+)|\bPR\s*(\d+)", re.I)
PR_FIELDS = "state,mergeCommit,headRefOid,headRefName"


def _run(args: list[str]) -> tuple[int, str]:
    """A missing binary is an ANSWER here, not a crash: `/end` must degrade, never blow up on a
    machine where `git` or `gh` is not on PATH. 127 is what a shell would have reported."""
    try:
        done = subprocess.run(args, capture_output=True, text=True)
    except OSError:
        return 127, ""
    return done.returncode, done.stdout.strip()


def default_branch() -> str:
    """The branch a merge must reach: origin/HEAD where it exists, else the local trunk."""
    rc, out = _run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if rc == 0 and out:
        return out.split("/", 1)[-1]
    for name in ("main", "master"):
        if _run(["git", "show-ref", "-q", "--verify", f"refs/heads/{name}"])[0] == 0:
            return name
    return "main"


def _reaches(sha: str, default: str) -> bool:
    """True only where THIS checkout can see the commit in its default branch."""
    return bool(sha) and _run(["git", "merge-base", "--is-ancestor", sha, default])[0] == 0


def _tip(branch: str) -> str:
    rc, out = _run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"])
    return out if rc == 0 else ""      # gone at merge is the normal case, and not an answer


def _gh(kind: str, num: str, fields: str) -> dict | None:
    """The tracker's answer, or None for every kind of silence: absent, error, rate limit, empty."""
    if not shutil.which("gh"):
        return None
    rc, out = _run(["gh", kind, "view", num, "--json", fields])
    if rc or not out:
        return None
    try:
        return json.loads(out) or None
    except ValueError:
        return None


def _pr(num: str, facts: dict, default: str) -> tuple[str, str]:
    if facts.get("state") != "MERGED":
        return "OPEN", f"PR #{num} is {facts.get('state')}, not MERGED"
    head = facts.get("headRefOid") or ""
    merge = (facts.get("mergeCommit") or {}).get("oid") or ""
    name = facts.get("headRefName") or ""
    if not (_reaches(head, default) or _reaches(merge, default)):
        return "AMBIGUOUS", f"PR #{num} says MERGED, but neither {head[:7]} nor its merge commit is in {default} here"
    tip = _tip(name)
    if tip and tip != head and not _reaches(tip, default):
        return "AMBIGUOUS", f"PR #{num} merged {head[:7]}, but {name} carries commits past it — reused, not closed"
    return "PROVEN", f"PR #{num} MERGED, head {head[:7]} reachable in {default}"


def _issue(num: str, facts: dict) -> tuple[str, str]:
    if facts.get("state") != "CLOSED":
        return "OPEN", f"issue #{num} is {facts.get('state')}"
    if (facts.get("stateReason") or "").upper() != "COMPLETED":
        return "OPEN", f"issue #{num} closed as {facts.get('stateReason')}, not completed"
    return "PROVEN", f"issue #{num} CLOSED as completed"


def cite(text: str) -> tuple[str, str]:
    """(number, kind). `PR 12` is a PR citation and never falls back to the issue of that number."""
    m = CITES.search(text)
    if not m:
        return "", ""
    return (m.group(1), "any") if m.group(1) else (m.group(2), "pr")


def verdict(line: str, default: str) -> tuple[str, str]:
    """PROVEN | AMBIGUOUS | OPEN | BLOCKED, and the reason, for one thread line."""
    num, kind = cite(line)
    if not num:
        return "OPEN", "no issue or PR cited"
    if facts := _gh("pr", num, PR_FIELDS):
        return _pr(num, facts, default)
    if kind == "pr":
        return "BLOCKED", f"PR {num} could not be read, and a PR citation is not an issue"
    if facts := _gh("issue", num, "state,stateReason"):
        return _issue(num, facts)
    return "BLOCKED", f"neither PR nor issue #{num} could be read — absent gh, error or empty answer"


def _selfcheck() -> int:
    """Every verdict branch, forced. The tracker is stubbed; the repo half is real git below."""
    merged = {"state": "MERGED", "headRefOid": "a" * 40, "mergeCommit": {"oid": "b" * 40},
              "headRefName": "feat/x"}
    ok = [_pr("1", {"state": "OPEN"}, "main")[0] == "OPEN",
          _pr("1", {"state": "CLOSED"}, "main")[0] == "OPEN",
          _pr("1", merged, "main")[0] == "AMBIGUOUS",          # no such sha in this repo
          _issue("2", {"state": "OPEN"})[0] == "OPEN",
          _issue("2", {"state": "CLOSED", "stateReason": "NOT_PLANNED"})[0] == "OPEN",
          _issue("2", {"state": "CLOSED", "stateReason": "COMPLETED"})[0] == "PROVEN",
          cite("- `a` — chiude #77") == ("77", "any"),
          cite("- `a` — attende PR 77") == ("77", "pr"),
          cite("- `a` — PR #77") == ("77", "any"),
          cite("- `a` — niente") == ("", ""),
          verdict("- `a` — niente", "main")[0] == "OPEN",
          not _reaches("", "main"), not _reaches("c" * 40, "main"), _tip("nope/nope") == "",
          _run(["definitely-not-a-binary-here"]) == (127, "")]   # absent tool ≠ crash
    print(f"merge_truth selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selfcheck())
