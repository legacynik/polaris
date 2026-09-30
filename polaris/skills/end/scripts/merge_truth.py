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


def _gh(kind: str, num: str, fields: str) -> dict | None:
    """The tracker's answer, or None for every kind of silence: absent, error, rate limit, empty.

    An object whose requested keys are ALL null is silence wearing a JSON hat — it says nothing
    about the PR, so it must reach the caller as BLOCKED, not as a state of `None` reading `OPEN`.
    """
    if not shutil.which("gh"):
        return None
    rc, out = _run(["gh", kind, "view", num, "--json", fields])
    if rc or not out:
        return None
    try:
        facts = json.loads(out)
    except ValueError:
        return None
    return facts if facts and any(v is not None for v in facts.values()) else None


def _pr(num: str, facts: dict, default: str) -> tuple[str, str]:
    if facts.get("state") == "CLOSED":      # closed without a merge: the work was abandoned
        return "DEAD", f"PR #{num} closed without merge"
    if facts.get("state") != "MERGED":
        return "OPEN", f"PR #{num} is {facts.get('state')}, not MERGED"
    head = facts.get("headRefOid") or ""
    merge = (facts.get("mergeCommit") or {}).get("oid") or ""
    name = facts.get("headRefName") or ""
    if not (_reaches(head, default) or _reaches(merge, default)):
        return "AMBIGUOUS", f"PR #{num} says MERGED, but neither {head[:7]} nor its merge commit is in {default} here"
    # The local ref is usually GONE (merged with --delete-branch): that is not an answer either way.
    tip = _run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{name}"])[1] if name else ""
    if tip and tip != head and not _reaches(tip, default):
        return "AMBIGUOUS", f"PR #{num} merged {head[:7]}, but {name} carries commits past it — reused, not closed"
    return "PROVEN", f"PR #{num} MERGED, head {head[:7]} reachable in {default}"


def _issue(num: str, facts: dict) -> tuple[str, str]:
    if facts.get("state") != "CLOSED":
        return "OPEN", f"issue #{num} is {facts.get('state')}"
    if (facts.get("stateReason") or "").upper() != "COMPLETED":
        return "DEAD", f"issue #{num} closed as {facts.get('stateReason')}, not completed"
    return "PROVEN", f"issue #{num} CLOSED as completed"


def cites(text: str) -> list[tuple[str, str]]:
    """EVERY (number, kind) the line names, in order, de-duplicated.

    `search` used to stop at the first one, so a lane reading «chiude #77, poi #79» closed the
    moment #77 merged, with #79 still open. A lane is done when everything it points at is done.
    `PR 12` is a PR citation and never falls back to the issue of that number.
    """
    out = []
    for m in CITES.finditer(text):
        hit = (m.group(1), "any") if m.group(1) else (m.group(2), "pr")
        if hit not in out:
            out.append(hit)
    return out


def _one(num: str, kind: str, default: str) -> tuple[str, str]:
    """The verdict for a single citation."""
    if facts := _gh("pr", num, PR_FIELDS):
        return _pr(num, facts, default)
    if kind == "pr":
        return "BLOCKED", f"PR {num} could not be read, and a PR citation is not an issue"
    if facts := _gh("issue", num, "state,stateReason"):
        return _issue(num, facts)
    return "BLOCKED", f"neither PR nor issue #{num} could be read — absent gh, error or empty answer"


def verdict(line: str, default: str) -> tuple[str, str]:
    """Closable only when EVERY citation is PROVEN or DEAD; otherwise the worst answer, and why.

    DEAD (a PR closed unmerged, an issue closed as not planned) is abandoned work: it closes the
    lane like PROVEN does, but only when nothing it cites is still open or unknown.
    """
    found = cites(line)
    if not found:
        return "OPEN", "no issue or PR cited"
    seen = [_one(num, kind, default) for num, kind in found]
    for want in ("BLOCKED", "AMBIGUOUS", "OPEN", "DEAD"):  # worst answer wins, in this order
        if bad := [why for kind, why in seen if kind == want]:
            return want, "; ".join(bad)
    return "PROVEN", "; ".join(why for _, why in seen)


def _selfcheck() -> int:
    """Every verdict branch, forced. The tracker is stubbed; the repo half is real git below."""
    merged = {"state": "MERGED", "headRefOid": "a" * 40, "mergeCommit": {"oid": "b" * 40},
              "headRefName": "feat/x"}
    ok = [_pr("1", {"state": "OPEN"}, "main")[0] == "OPEN",
          _pr("1", {"state": "CLOSED"}, "main")[0] == "DEAD",
          _pr("1", merged, "main")[0] == "AMBIGUOUS",          # no such sha in this repo
          _issue("2", {"state": "OPEN"})[0] == "OPEN",
          _issue("2", {"state": "CLOSED", "stateReason": "NOT_PLANNED"})[0] == "DEAD",
          _issue("2", {"state": "CLOSED", "stateReason": "COMPLETED"})[0] == "PROVEN",
          cites("- `a` — chiude #77") == [("77", "any")],
          cites("- `a` — attende PR 77") == [("77", "pr")],
          cites("- `a` — PR #77") == [("77", "any")],
          cites("- `a` — niente") == [],
          cites("- `a` — chiude #77, poi #79") == [("77", "any"), ("79", "any")],
          cites("- `a` — #77 e ancora #77") == [("77", "any")],
          verdict("- `a` — niente", "main")[0] == "OPEN",
          not _reaches("", "main"), not _reaches("c" * 40, "main"),
          _run(["definitely-not-a-binary-here"]) == (127, "")]   # absent tool ≠ crash
    print(f"merge_truth selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selfcheck())
