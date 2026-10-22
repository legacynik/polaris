#!/usr/bin/env python3
"""Post-deploy canary: alert on CHANGE vs baseline, never on absolute value —
and a deploy/main drift check (closes G4 voce 3: "prod va stale... senza
avviso"). Debounce 2 consecutive failing checks before alerting, so a single
network blip never pages anyone. Stdlib-only HTTP (urllib), no proprietary
screenshot/console-error binary — that observability is explicitly NOT ported
here (B1 verdict: rewrite the design, not the binary); a page that needs
visual/console checks plugs in a --urls target that serves a health JSON
instead.

    canary_check.py baseline --urls U1 U2 --state FILE
    canary_check.py check    --urls U1 U2 --state FILE   # exit 1 = ALERT
    canary_check.py drift --local-sha SHA --deployed-sha SHA --repo PATH
    canary_check.py verdict --baseline B.json --now N.json   # 0 ADVANCE · 1 ROLLBACK proposed · 3 HOLD
    canary_check.py --selfcheck

`verdict` is the post-deploy verification window: B.json and N.json hold what the repository
exposes before and after the deploy, `{"health_ok": bool, "error_rate": float, "p95_ms": float}`.
A rollback is proposed, never run. A metric missing on either side is UNKNOWN and holds.
"""
from __future__ import annotations
import sys, json, time, argparse, subprocess, urllib.request, urllib.error
from pathlib import Path

DEBOUNCE = 2


def probe(url: str, timeout: float = 5.0) -> dict:
    start = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return {"status": resp.status, "latency_ms": round((time.monotonic() - start) * 1000, 1), "error": None}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "latency_ms": round((time.monotonic() - start) * 1000, 1), "error": None}
    except Exception as e:  # connection refused, timeout, DNS — all "unreachable"
        return {"status": None, "latency_ms": None, "error": str(e)}


def load_state(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {"baseline": {}, "consecutive_fail": {}}


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2))


def do_baseline(urls: list[str], state_path: Path) -> dict:
    baseline = {u: probe(u) for u in urls}
    save_state(state_path, {"baseline": baseline, "consecutive_fail": {u: 0 for u in urls}})
    return baseline


def changed(base: dict, now: dict) -> bool:
    """Alert-on-change, not absolute: a URL already erroring in baseline that
    keeps erroring the SAME way is not news. A new error, or a status that
    newly differs from baseline, is."""
    if base.get("error") and now.get("error"):
        return False
    return base.get("status") != now.get("status") or bool(now.get("error")) != bool(base.get("error"))


def do_check(urls: list[str], state_path: Path) -> dict:
    state = load_state(state_path)
    baseline = state.get("baseline", {})
    fails = state.setdefault("consecutive_fail", {})
    report = {}
    for u in urls:
        now = probe(u)
        base = baseline.get(u, now)
        is_changed = changed(base, now)
        fails[u] = fails.get(u, 0) + 1 if is_changed else 0
        report[u] = {"now": now, "baseline": base, "changed": is_changed,
                     "consecutive_fail": fails[u], "alert": fails[u] >= DEBOUNCE}
    save_state(state_path, state)
    return report


def do_drift(local_sha: str, deployed_sha: str, repo: str | None) -> dict:
    if local_sha == deployed_sha:
        return {"drift": False, "commits_behind": 0}
    commits_behind = None
    if repo:
        r = subprocess.run(["git", "-C", repo, "rev-list", "--count", f"{deployed_sha}..{local_sha}"],
                            capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip().isdigit():
            commits_behind = int(r.stdout.strip())
    return {"drift": True, "local_sha": local_sha, "deployed_sha": deployed_sha, "commits_behind": commits_behind}


# ponytail: fixed thresholds; per-repo thresholds belong in the contract when one asks for them.
ROLLBACK_ERROR, ROLLBACK_P95 = 2.0, 1.5     # error rate > 2x baseline, p95 > +50%
HOLD_ERROR, HOLD_P95 = 1.25, 1.2            # a smaller rise holds the rollout for a person to read
ERROR_FLOOR = 0.001                         # a zero-error baseline compares against 0.1%


def do_verdict(base: dict, now: dict) -> tuple[str, list[str]]:
    """(ADVANCE | HOLD | ROLLBACK proposed, reasons)."""
    reasons, worst = [], "ADVANCE"
    rank = {"ADVANCE": 0, "HOLD": 1, "ROLLBACK proposed": 2}

    def raise_to(level: str, why: str) -> None:
        nonlocal worst
        reasons.append(why)
        worst = level if rank[level] > rank[worst] else worst

    if base.get("health_ok") is None or now.get("health_ok") is None:
        raise_to("HOLD", "UNKNOWN health_ok")
    elif base["health_ok"] and not now["health_ok"]:
        raise_to("ROLLBACK proposed", "health_ok turned false")
    for key, roll, hold, floor in (("error_rate", ROLLBACK_ERROR, HOLD_ERROR, ERROR_FLOOR),
                                   ("p95_ms", ROLLBACK_P95, HOLD_P95, 1.0)):
        b, n = base.get(key), now.get(key)
        if not isinstance(b, (int, float)) or not isinstance(n, (int, float)):
            raise_to("HOLD", f"UNKNOWN {key}")
            continue
        ratio = n / max(b, floor)
        if ratio > roll:
            raise_to("ROLLBACK proposed", f"{key} {b} -> {n} ({ratio:.2f}x, limit {roll}x)")
        elif ratio > hold:
            raise_to("HOLD", f"{key} {b} -> {n} ({ratio:.2f}x, hold above {hold}x)")
    return worst, reasons


def sync_alert(path: str | None, result: dict) -> None:
    """G4 voice 3 (MANIFEST fix #1): `drift` needs zero Phase B state to run —
    write/clear a standalone alert file so a cron independent of Phase B can
    surface it (see SKILL.md "Passive deploy-drift check"). Self-healing:
    once drift resolves, the alert file is removed, not left lingering."""
    if not path:
        return
    p = Path(path)
    if result["drift"]:
        p.write_text(json.dumps(result, indent=2))
    elif p.exists():
        p.unlink()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("baseline", "check"):
        p = sub.add_parser(name)
        p.add_argument("--urls", nargs="+", default=[])
        p.add_argument("--state", required=True)
    d = sub.add_parser("drift")
    d.add_argument("--local-sha", required=True)
    d.add_argument("--deployed-sha", required=True)
    d.add_argument("--repo")
    d.add_argument("--write-alert", help="path to a JSON alert file, written on drift and "
                    "cleared once resolved — for a cron/hook that runs independently of Phase B")
    v = sub.add_parser("verdict")
    v.add_argument("--baseline", required=True)
    v.add_argument("--now", required=True)
    args = ap.parse_args(argv)

    if args.selfcheck:
        return selfcheck()
    if args.cmd == "baseline":
        print(json.dumps(do_baseline(args.urls, Path(args.state)), indent=2))
        return 0
    if args.cmd == "check":
        report = do_check(args.urls, Path(args.state))
        print(json.dumps(report, indent=2))
        return 1 if any(r["alert"] for r in report.values()) else 0
    if args.cmd == "drift":
        result = do_drift(args.local_sha, args.deployed_sha, args.repo)
        sync_alert(args.write_alert, result)
        print(json.dumps(result, indent=2))
        return 1 if result["drift"] else 0
    if args.cmd == "verdict":
        try:
            base = json.loads(Path(args.baseline).read_text())
            now = json.loads(Path(args.now).read_text())
            if not isinstance(base, dict) or not isinstance(now, dict):
                raise ValueError("metrics must be JSON objects")
        except (OSError, ValueError) as exc:
            print(f"metrics unusable ({exc}): a window that cannot read never advances", file=sys.stderr)
            return 2
        level, reasons = do_verdict(base, now)
        print(level + (" — " + "; ".join(reasons) if reasons else " — every metric within its limit"))
        return {"ADVANCE": 0, "ROLLBACK proposed": 1, "HOLD": 3}[level]
    ap.print_help()
    return 2


def selfcheck() -> int:
    import http.server, threading, tempfile

    class OKHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        def log_message(self, *a): pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), OKHandler)
    port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    healthy = f"http://127.0.0.1:{port}/"
    dead = "http://127.0.0.1:1/"  # nothing listens on privileged port 1 -> connection refused

    with tempfile.TemporaryDirectory() as td:
        state = Path(td) / "canary-state.json"
        do_baseline([healthy], state)
        assert do_check([healthy], state)[healthy]["alert"] is False, "no change from baseline -> no alert"

        # point the SAME url key at a dead target by hand-editing baseline to simulate an outage starting
        st = load_state(state); st["baseline"][dead] = probe(healthy); save_state(state, st)
        r1 = do_check([dead], state)[dead]
        assert r1["changed"] and r1["consecutive_fail"] == 1 and r1["alert"] is False, r1  # 1st blip: no alert (debounce)
        r2 = do_check([dead], state)[dead]
        assert r2["changed"] and r2["consecutive_fail"] == 2 and r2["alert"] is True, r2  # 2nd in a row: ALERT

        st = load_state(state); st["baseline"][dead] = probe(healthy); save_state(state, st)
        r3 = do_check([healthy], state)[healthy]  # unrelated url recovers/matches baseline -> resets its own counter
        assert r3["alert"] is False and r3["consecutive_fail"] == 0, r3

    srv.shutdown()

    with tempfile.TemporaryDirectory() as td2:
        repo = Path(td2)
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.t", "PATH": "/usr/bin:/bin"}
        shas = []
        for i in range(3):
            (repo / "f.txt").write_text(str(i))
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", f"c{i}"], check=True, env=env)
            shas.append(subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                        capture_output=True, text=True).stdout.strip())
        same = do_drift(shas[2], shas[2], str(repo))
        assert same["drift"] is False
        behind = do_drift(shas[2], shas[0], str(repo))
        assert behind["drift"] is True and behind["commits_behind"] == 2, behind

        # G4 voice 3: --write-alert must work standalone (no Phase B / canary-state.json
        # involved at all), and must self-heal once drift resolves.
        alert = Path(td2) / "alert.json"
        sync_alert(str(alert), behind)
        assert alert.exists() and json.loads(alert.read_text())["commits_behind"] == 2, "alert must be written on drift"
        sync_alert(str(alert), same)
        assert not alert.exists(), "alert must clear once drift resolves, not linger forever"

    ok = {"health_ok": True, "error_rate": 0.01, "p95_ms": 400}
    assert do_verdict(ok, ok)[0] == "ADVANCE"
    assert do_verdict(ok, dict(ok, error_rate=0.03))[0] == "ROLLBACK proposed"
    assert do_verdict(ok, dict(ok, p95_ms=500))[0] == "HOLD"
    assert do_verdict(ok, {"health_ok": True})[0] == "HOLD", "unknown never advances"
    print("SELFCHECK OK — verdict (advance, rollback, hold, unknown), debounce (no alert on blip, alert on 2nd), per-url counter isolation, "
          "drift count, standalone alert write/clear, all as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
