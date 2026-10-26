#!/usr/bin/env python3
"""Merge safety — closes G7#1 (25 PR aperte, 11>14gg, 4 in conflitto).

Hard rule, not a suggestion: after a merge attempt with exit != 0, the ONLY
source of truth is a fresh `gh pr view --json state` requery — NEVER a second
blind `gh pr merge` call (cli/cli#3442, cli/cli#13380: a retried merge on a
PR the server already merged, or already closed, does real damage). This
script is the sole caller of `gh pr merge` in the whole skill for that reason.

    merge_gate.py decide  --pr-json FILE|-        classify current server state
    merge_gate.py execute --pr N [--repo owner/r]  requery -> merge once -> requery
    merge_gate.py --selfcheck                      prove the never-retry branch
"""
from __future__ import annotations
import sys, json, argparse, subprocess, time
from typing import Callable, Any

STALE_DAYS = 14


def classify(view: dict) -> dict:
    """One PR's `gh pr view --json state,mergeable,mergeStateStatus,statusCheckRollup,updatedAt` -> verdict.

    Missing/empty/degenerate input NEVER resolves to READY (closes L2,
    EVAL-ship-bypass.md): an unknown or incomplete state is refused, not
    approved. `{}`, `{"mergeable":"UNKNOWN"}`, and a `gh` failure that left
    no usable field all used to fall through to READY — the most permissive
    verdict, one step from a real `gh pr merge`. READY now requires every
    signal to be explicitly the healthy value, not merely "not conflicting"."""
    if view.get("_gh_error"):
        return {"verdict": "UNKNOWN", "stale": None,
                "gate_warning": f"gh command failed: {view['_gh_error']} — refusing to guess a verdict"}

    state = view.get("state")
    mergeable = view.get("mergeable")
    mss = view.get("mergeStateStatus")
    checks = view.get("statusCheckRollup", []) or []
    required = [c for c in checks if c.get("isRequired")]

    if state == "MERGED":
        verdict = "ALREADY_DONE"
    elif state == "CLOSED":
        verdict = "ABORTED"
    elif mergeable == "CONFLICTING":
        verdict = "BLOCKED_CONFLICT"
    elif mss == "BEHIND":
        verdict = "NEEDS_UPDATE"
    elif mss == "BLOCKED":
        verdict = "BLOCKED_CHECKS"
    elif state == "OPEN" and mergeable == "MERGEABLE" and mss == "CLEAN":
        verdict = "READY"
    else:
        verdict = "UNKNOWN"

    stale = None
    updated = view.get("updatedAt")
    if updated:
        try:
            import datetime
            age = (datetime.datetime.now(datetime.timezone.utc)
                    - datetime.datetime.fromisoformat(updated.replace("Z", "+00:00"))).days
            stale = age >= STALE_DAYS
        except ValueError:
            stale = None

    gate_warning = None
    if verdict == "READY" and not required:
        gate_warning = "no required status check — green here is advisory, not a gate"

    return {"verdict": verdict, "stale": stale, "gate_warning": gate_warning}


def gh_view(pr: str, repo: str | None, run: Callable[..., Any]) -> dict:
    args = ["gh", "pr", "view", pr, "--json",
            "state,mergeable,mergeStateStatus,statusCheckRollup,updatedAt"]
    if repo:
        args += ["--repo", repo]
    out, rc = run(args)
    if rc != 0:
        return {"_gh_error": f"gh pr view exited {rc}"}
    if not out:
        return {"_gh_error": "gh pr view produced no output"}
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        return {"_gh_error": f"gh pr view returned non-JSON: {e}"}


def gh_merge(pr: str, repo: str | None, run: Callable[..., Any],
             view_fn: Callable[[str, str | None], dict] | None = None) -> int:
    """The ONLY function allowed to call `gh pr merge`. Requeries and refuses
    unless the FRESH verdict is READY (closes the "Minore" finding in
    EVAL-ship-bypass.md: `from merge_gate import gh_merge; gh_merge(...)`
    used to skip execute()'s decide-first guard entirely — a direct call
    to the function must be gated exactly as much as the CLI path, so the
    guard now lives here, not only in the caller)."""
    view_fn = view_fn or (lambda p, r: gh_view(p, r, _real_run_json))
    verdict = classify(view_fn(pr, repo))
    if verdict["verdict"] != "READY":
        raise RuntimeError(
            f"gh_merge refused: verdict={verdict['verdict']!r}, not READY — "
            "call execute() (decide-first) instead of gh_merge() directly")
    args = ["gh", "pr", "merge", pr, "--squash"]  # never --auto: native auto-merge re-checks nothing
    if repo:
        args += ["--repo", repo]
    return run(args)


def _real_run_json(args: list[str]) -> tuple[str, int]:
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout, r.returncode


def _real_run_exit(args: list[str]) -> int:
    return subprocess.run(args, capture_output=True, text=True).returncode


def execute(pr: str, repo: str | None = None,
            view_fn: Callable[[str, str | None], dict] | None = None,
            merge_fn: Callable[[str, str | None], int] | None = None) -> dict:
    view_fn = view_fn or (lambda p, r: gh_view(p, r, _real_run_json))
    merge_fn = merge_fn or (lambda p, r: gh_merge(p, r, _real_run_exit,
                                                   view_fn=lambda p2, r2: gh_view(p2, r2, _real_run_json)))

    verdict = classify(view_fn(pr, repo))
    if verdict["verdict"] == "ALREADY_DONE":
        return {**verdict, "action": "NOOP", "why": "already merged — this is what stops the double-merge bug"}
    if verdict["verdict"] != "READY":
        return {**verdict, "action": "REFUSED", "why": f"not mergeable: {verdict['verdict']}"}

    rc = merge_fn(pr, repo)
    if rc == 0:
        post = classify(view_fn(pr, repo))
        if post["verdict"] == "ALREADY_DONE":
            return {**post, "action": "MERGED"}
        return {**post, "action": "ANOMALY", "why": "merge command exit 0 but server does not show MERGED"}

    # merge command failed — the hard rule: requery, NEVER call gh pr merge a second time.
    post = classify(view_fn(pr, repo))
    if post["verdict"] == "ALREADY_DONE":
        return {**post, "action": "MERGED", "why": "merge exit!=0 but requery shows MERGED — trusting server, not retrying"}
    return {**post, "action": "FAILED", "why": f"merge exit {rc}, requery confirms not merged: {post['verdict']}"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("decide")
    d.add_argument("--pr-json", default="-")
    e = sub.add_parser("execute")
    e.add_argument("--pr", required=True)
    e.add_argument("--repo")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)

    if args.selfcheck:
        return selfcheck()
    if args.cmd == "decide":
        text = sys.stdin.read() if args.pr_json == "-" else open(args.pr_json).read()
        try:
            view = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            view = {"_gh_error": "malformed JSON given to decide"}
        print(json.dumps(classify(view), indent=2))
        return 0
    if args.cmd == "execute":
        result = execute(args.pr, args.repo)
        print(json.dumps(result, indent=2))
        return 0 if result["action"] in ("NOOP", "MERGED") else 1
    ap.print_help()
    return 2


def selfcheck() -> int:
    already = {"state": "MERGED"}
    assert classify(already)["verdict"] == "ALREADY_DONE"

    conflicting = {"state": "OPEN", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
    assert classify(conflicting)["verdict"] == "BLOCKED_CONFLICT"

    no_gate = {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN", "statusCheckRollup": []}
    v = classify(no_gate)
    assert v["verdict"] == "READY" and v["gate_warning"], "0 required checks must warn, not silently pass"

    # L2 (EVAL-ship-bypass.md): degenerate/missing input must NEVER classify as READY.
    assert classify({})["verdict"] == "UNKNOWN", "empty payload must never be READY"
    assert classify({"mergeable": "UNKNOWN"})["verdict"] == "UNKNOWN", "partial payload must never be READY"
    assert classify({"_gh_error": "exit 1"})["verdict"] == "UNKNOWN"

    # gh_view must treat a non-zero `gh` returncode as failure, not "no fields = READY".
    fail_view = gh_view("1", None, lambda a: ("", 1))
    assert fail_view.get("_gh_error"), "non-zero gh returncode must produce _gh_error"
    assert classify(fail_view)["verdict"] == "UNKNOWN"
    empty_out = gh_view("1", None, lambda a: ("", 0))
    assert empty_out.get("_gh_error"), "empty stdout on success must still refuse, not silently pass"
    bad_json = gh_view("1", None, lambda a: ("not json", 0))
    assert bad_json.get("_gh_error"), "non-JSON stdout must not crash decide, must refuse"

    # rule 3 / "Minore" (EVAL-ship-bypass.md): a direct call to gh_merge() — bypassing
    # execute() entirely — must be gated exactly as much as the CLI path.
    def view_not_ready(p, r): return conflicting
    try:
        gh_merge("9", None, lambda a: 0, view_fn=view_not_ready)
        assert False, "gh_merge() must refuse to merge when the fresh verdict is not READY"
    except RuntimeError:
        pass
    def view_ready_now(p, r):
        return {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                "statusCheckRollup": [{"isRequired": True}]}
    direct_calls = {"n": 0}
    def direct_merge_run(a): direct_calls["n"] += 1; return 0
    rc = gh_merge("9", None, direct_merge_run, view_fn=view_ready_now)
    assert rc == 0 and direct_calls["n"] == 1, "gh_merge() must actually merge when fresh verdict IS READY"

    def view_ready_static(p, r):
        return {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                "statusCheckRollup": [{"isRequired": True}]}

    # execute(): READY + merge succeeds first try -> MERGED, merge called once
    calls = {"merge": 0, "merged": False}
    def view_ready(p, r):
        return {"state": "MERGED"} if calls["merged"] else view_ready_static(p, r)
    def merge_ok(p, r): calls["merge"] += 1; calls["merged"] = True; return 0
    r1 = execute("1", view_fn=view_ready, merge_fn=merge_ok)
    assert r1["action"] == "MERGED" and calls["merge"] == 1, r1

    # execute(): ALREADY_DONE up front -> NOOP, merge never called
    calls2 = {"merge": 0}
    def view_merged(p, r): return {"state": "MERGED"}
    def merge_should_not_run(p, r): calls2["merge"] += 1; return 0
    r2 = execute("2", view_fn=view_merged, merge_fn=merge_should_not_run)
    assert r2["action"] == "NOOP" and calls2["merge"] == 0, r2

    # execute(): CONFLICTING -> REFUSED, merge never attempted
    calls3 = {"merge": 0}
    def view_conflict(p, r): return conflicting
    def merge_should_not_run3(p, r): calls3["merge"] += 1; return 0
    r3 = execute("3", view_fn=view_conflict, merge_fn=merge_should_not_run3)
    assert r3["action"] == "REFUSED" and calls3["merge"] == 0, r3

    # execute(): merge exit!=0, requery shows MERGED anyway (server-side race) -> trust requery, no 2nd merge call
    calls4 = {"merge": 0, "views": 0}
    def view_toggle(p, r):
        calls4["views"] += 1
        return view_ready_static(p, r) if calls4["views"] == 1 else {"state": "MERGED"}
    def merge_fails(p, r): calls4["merge"] += 1; return 1
    r4 = execute("4", view_fn=view_toggle, merge_fn=merge_fails)
    assert r4["action"] == "MERGED" and calls4["merge"] == 1, r4  # exactly one merge attempt, never a retry

    # execute(): merge exit!=0, requery still OPEN -> FAILED, still only one merge call (no blind retry)
    calls5 = {"merge": 0}
    def merge_fails5(p, r): calls5["merge"] += 1; return 1
    r5 = execute("5", view_fn=view_ready_static, merge_fn=merge_fails5)
    assert r5["action"] == "FAILED" and calls5["merge"] == 1, r5

    print("SELFCHECK OK — 6 classify/execute branches + 6 L2/rule-3 branches "
          "(empty/partial/error payload never READY, gh non-zero/empty/non-JSON refused, "
          "direct gh_merge() gated same as execute()), merge() called at most once per execute() every time")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
