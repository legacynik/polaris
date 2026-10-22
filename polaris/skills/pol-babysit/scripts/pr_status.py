#!/usr/bin/env python3
"""pr_status — one snapshot of an open PR: READY, WAITING, ACTION or CLOSED, and why.

Port of pr-status.ts (tester-army/e2e, Apache-2.0), plus: a receipt from the signing environment on the
head (or an older head when only inert files changed), a body pr's checker accepts, a label bound to the
head, GitHub's merge state, declared non-gating checks. pr_fetch.py reads GitHub; this file judges.

    pr_status.py [pr] [--repo o/r] [--ignore name=reason ...] [--inert glob ...] [--env staging]
    pr_status.py --selfcheck

Run it from the root of the PR's repo. Exit: 0 READY · 1 ACTION or CLOSED · 3 WAITING · 2 no data.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from receipt import RECEIPT, receipt_ok, receipts  # noqa: E402,F401  RECEIPT is read by pr_fetch

FAILED = {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE", "ERROR"}
AGENT_REPLY = re.compile(r"^_\[[^\]]+\] responding on behalf of ")
ESCALATED = "<!-- escalated -->"
LABEL_MARK = re.compile(r"<!-- owner-label sha=([0-9a-f]{40}) -->")
MERGE_STATE = {"BEHIND": "behind-base", "BLOCKED": "blocked", "DIRTY": "conflict"}
PLACEHOLDER = {"", "todo", "x", ".", "-", "tbd", "n/a"}
SETTLE_S = 120


def _t(stamp: str | None) -> float | None:
    if not stamp or stamp.startswith("0001"):
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def latest_runs(rollup: list[dict]) -> list[dict]:
    """The same check run twice (a red draft run, a green ready run) counts as its latest run."""
    by_key: dict[tuple, dict] = {}
    for c in rollup:
        key = (c.get("workflowName"), c.get("name") or c.get("context"))
        if key not in by_key or (_t(c.get("startedAt")) or 0) >= (_t(by_key[key].get("startedAt")) or 0):
            by_key[key] = c
    return list(by_key.values())


def checks(pr: dict, ignore: dict[str, str], now: float) -> dict:
    failing, pending, ignored = [], [], []
    for c in latest_runs(pr.get("statusCheckRollup") or []):
        name, outcome = c.get("name") or c.get("context"), c.get("conclusion") or c.get("state")
        if c.get("status") not in (None, "COMPLETED") or outcome in ("PENDING", "EXPECTED"):
            pending.append(name)
        elif outcome in FAILED and name in ignore:
            ignored.append({"name": name, "reason": ignore[name]})
        elif outcome in FAILED:
            failing.append({"name": name, "link": c.get("detailsUrl") or c.get("targetUrl")})
    starts = sorted(t for c in pr.get("statusCheckRollup") or [] if (t := _t(c.get("startedAt"))))
    if not pr.get("statusCheckRollup"):
        pending.append("checks not reported yet")
    elif starts and now - starts[0] < SETTLE_S:
        pending.append("checks settling after push")
    if pr.get("mergeable") == "UNKNOWN" or pr.get("mergeStateStatus") == "UNKNOWN":
        pending.append("mergeability")
    return {"failing": failing, "pending": pending, "ignored": ignored}


def by_agent(login: str | None, body: str | None, viewer: str) -> bool:
    return login is not None and login == viewer and bool(AGENT_REPLY.match(body or ""))


def threads(nodes: list[dict], viewer: str) -> tuple[list[dict], list[dict]]:
    """Open threads block; one whose last word is the agent's reply marked escalated waits for the owner."""
    open_, escalated = [], []
    for t in (n for n in nodes if not n.get("isResolved")):
        first, last = t["root"]["nodes"][0], (t["latest"]["nodes"] or [{}])[-1]
        item = {"id": t["id"], "commentId": first.get("databaseId"), "path": t.get("path"),
                "line": t.get("line"), "url": first.get("url"), "body": (first.get("body") or "")[:600]}
        handed = by_agent((last.get("author") or {}).get("login"), last.get("body"), viewer) \
            and ESCALATED in (last.get("body") or "")
        (escalated if handed else open_).append(item)
    return open_, escalated


def own_marker(c: dict, viewer: str) -> bool:
    return (c.get("user") or {}).get("login") == viewer and bool(RECEIPT.search(c.get("body") or "")
                                                               or LABEL_MARK.search(c.get("body") or ""))


def pending_comments(comments: list[dict], viewer: str) -> list[dict]:
    return [{"id": c.get("id"), "author": (c.get("user") or {}).get("login"), "url": c.get("html_url"),
             "body": (c.get("body") or "")[:600]}
            for c in comments
            if not c.get("acknowledged") and not own_marker(c, viewer)
            and not by_agent((c.get("user") or {}).get("login"), c.get("body"), viewer)]


def review_notes(reviews: list[dict], comments: list[dict], viewer: str) -> list[dict]:
    """A review left as a plain comment with a body waits for an agent reply posted after it."""
    replies = [c.get("created_at") or "" for c in comments if by_agent((c.get("user") or {}).get("login"),
                                                                       c.get("body"), viewer)]
    return [{"id": r.get("id"), "author": (r.get("user") or {}).get("login"), "url": r.get("html_url"),
             "body": (r.get("body") or "")[:600]}
            for r in reviews if r.get("state") == "COMMENTED" and (r.get("body") or "").strip()
            and (r.get("user") or {}).get("login") != viewer
            and not any(t > (r.get("submitted_at") or "") for t in replies)]


def changes_requested(reviews: list[dict]) -> list[str]:
    verdicts: dict[str, dict] = {}
    for r in sorted((r for r in reviews if r.get("submitted_at")), key=lambda r: r["submitted_at"]):
        if r.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            verdicts[(r.get("user") or {}).get("login") or f"deleted:{r.get('id')}"] = r
    return [who for who, r in verdicts.items() if r["state"] == "CHANGES_REQUESTED"]


def summarize(pr, threads, comments, reviews, viewer, now, ignore, label,  # noqa: PLR0913
              body_errors, changed_since, inert, env):
    """Pure: the same inputs give the same verdict."""
    head, env = pr.get("headRefOid"), env.strip().lower()  # `--env LOCAL` is `local`, everywhere below
    now_t = (_t(now) if isinstance(now, str) else now) or datetime.now().timestamp()
    ck = checks(pr, ignore, now_t)
    if env == "local" and not pr.get("statusCheckRollup"):  # the repo's CI runs on the machine
        ck["pending"].remove("checks not reported yet")
        ck["ignored"].append({"name": "github checks", "reason": "none reported: signing_env local, CI runs locally"})
    open_, escalated = globals()["threads"](threads, viewer)
    unack = pending_comments(comments, viewer) + review_notes(reviews, comments, viewer)
    cr = changes_requested(reviews)
    signed = receipts(comments, viewer, env)
    state = MERGE_STATE.get(pr.get("mergeStateStatus") or "")
    conflict = pr.get("mergeable") == "CONFLICTING" or state == "conflict"
    blockers = [b for b, on in (
        ("conflict", conflict), (state, state and state != "conflict"), ("draft", pr.get("isDraft")),
        ("failing:" + ",".join(f["name"] for f in ck["failing"]), ck["failing"]),
        (f"threads:{len(open_)}", open_), (f"comments:{len(unack)}", unack), (f"changes-requested:{len(cr)}", cr),
        ("receipt", not receipt_ok(head, signed, changed_since, inert)), ("body", body_errors),
        ("label-stale", label and label.get("sha") != head)) if on]
    verdict = ("CLOSED" if pr.get("state") != "OPEN" else "ACTION" if blockers
               else "WAITING" if ck["pending"] else "READY")
    return {"verdict": verdict, "blockers": blockers, "pr": pr.get("number"), "head": head, "checks": ck,
            "threads": open_, "escalated": escalated, "comments": unack, "changesRequested": cr,
            "body_errors": body_errors}


def selfcheck() -> int:
    head = "a" * 40
    pr = {"state": "OPEN", "headRefOid": head, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
          "statusCheckRollup": [
              {"name": "ci", "status": "COMPLETED", "conclusion": "FAILURE", "startedAt": "2026-01-01T00:00:00Z"},
              {"name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS", "startedAt": "2026-01-02T00:00:00Z"}]}
    me = {"user": {"login": "me"}, "body": f"<!-- real-test v1 sha={head} verdict=MERGEABLE -->\nambiente: staging x"}
    base = dict(pr=pr, threads=[], comments=[me], reviews=[], viewer="me", now="2026-02-01T00:00:00Z", ignore={},
                label=None, body_errors=[], changed_since={}, inert=[], env="staging")
    run = lambda **k: summarize(**(base | k))  # noqa: E731
    cases = [run()["verdict"] == "READY", run(comments=[])["verdict"] == "ACTION",
             run(pr=pr | {"statusCheckRollup": []})["verdict"] == "WAITING",
             run(pr=pr | {"state": "MERGED"})["verdict"] == "CLOSED",
             "label-stale" in run(label={"sha": None})["blockers"], "body" in run(body_errors=["x"])["blockers"],
             "behind-base" in run(pr=pr | {"mergeStateStatus": "BEHIND"})["blockers"],
             "receipt" in run(env="prod")["blockers"]]
    print(f"pr_status selfcheck: {sum(cases)}/{len(cases)}")
    return 0 if all(cases) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("pr", nargs="?")
    for opt, default in (("--repo", None), ("--label", "ready-for-owner"), ("--env", "staging")):
        ap.add_argument(opt, default=default)
    ap.add_argument("--ignore", action="append", default=[], help="check=reason, the reason is required")
    ap.add_argument("--inert", action="append", default=[], help="glob of files a push may change keeping the receipt")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    pairs = [i.split("=", 1) for i in a.ignore]
    if not a.env.strip() or any(len(p) < 2 or p[1].strip().lower() in PLACEHOLDER for p in pairs):
        print("--env names the signing environment (never blank); --ignore wants check=reason, with a reason",
              file=sys.stderr)
        return 2
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import pr_fetch
        data = pr_fetch.fetch(a.pr, a.repo, a.label, a.inert)
        s = summarize(**data, now=datetime.now().timestamp(), ignore=dict(pairs), env=a.env, inert=a.inert)
    except Exception as e:  # noqa: BLE001 - no verdict without data, never a guess
        print(f"no verdict, data unreadable ({type(e).__name__}: {e})", file=sys.stderr)
        return 2
    print(json.dumps(s, indent=1, ensure_ascii=False))
    return {"READY": 0, "WAITING": 3}.get(s["verdict"], 1)


if __name__ == "__main__":
    sys.exit(main())
