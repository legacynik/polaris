#!/usr/bin/env python3
"""run_behavior — behavioural evals for the Polaris session skills.

Trigger evals (does the skill fire?) belong to skill-creator's `run_eval.py`; this
is the other half: given a repo in a declared state, does invoking the skill leave
the RIGHT state behind. Assertions read the filesystem and git, so a case has one
answer, not a graded opinion.

Every case declares `fails_before`: the git ref of the skill version it MUST fail
on. A case that passes both before and after the change is not testing anything —
`--verify-red` is what proves the suite has teeth.

  run_behavior.py --list                 # the cases and what each proves
  run_behavior.py --selfcheck            # harness only, no model, no tokens
  run_behavior.py --case state-health-quiet   # run one case for real
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixtures  # noqa: E402

CASES_PATH = Path(__file__).parent / "cases.json"
TIMEOUT = 300


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text())["cases"]


def invoke(repo: Path, prompt: str, model: str | None) -> str:
    """Run the skill in the fixture. The prompt is what a user would actually type."""
    cmd = ["claude", "-p", prompt, "--permission-mode", "acceptEdits"]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=TIMEOUT)
    return r.stdout


def check(case: dict, repo: Path, out: str) -> list[tuple[str, bool, str]]:
    """Each assertion: (name, passed, observed). Deterministic, filesystem-first."""
    res = []
    for a in case["assertions"]:
        kind, want = a["kind"], a.get("value")
        if kind == "open_threads":
            got = fixtures.open_threads(repo)
        elif kind == "cockpit_blocks":
            got = fixtures.cockpit_blocks(repo)
        elif kind == "commits":
            got = fixtures.commits(repo)
        elif kind == "head_files_contain":
            got = any(want in f for f in fixtures.head_files(repo))
            want = True
        elif kind == "output_mentions":
            got = want.lower() in out.lower()
            want = True
        elif kind == "output_omits":
            got = want.lower() not in out.lower()
            want = True
        else:
            res.append((a["name"], False, f"tipo ignoto: {kind}"))
            continue
        res.append((a["name"], got == want, f"atteso {want}, ottenuto {got}"))
    return res


def run_case(case: dict, model: str | None) -> bool:
    repo = fixtures.build(**case.get("fixture", {}))
    print(f"\n▸ {case['id']} — {case['proves']}")
    print(f"  fixture: {case.get('fixture', {})} → {repo}")
    try:
        out = invoke(repo, case["prompt"], model)
    except subprocess.TimeoutExpired:
        print("  ✗ TIMEOUT"); return False
    ok = True
    for name, passed, detail in check(case, repo, out):
        print(f"  {'✓' if passed else '✗'} {name} ({detail})")
        ok = ok and passed
    return ok


def _selfcheck() -> int:
    """The harness itself, with no model in the loop — so it can be trusted for free."""
    r = fixtures.build(threads=5, blocks=3)
    assert fixtures.open_threads(r) == 5, fixtures.open_threads(r)
    assert fixtures.cockpit_blocks(r) == 3, fixtures.cockpit_blocks(r)
    assert fixtures.commits(r) == 1
    print("  ✓ fixture costruisce lo stato dichiarato (5 thread, 3 blocchi, 1 commit)")

    r2 = fixtures.build(threads=12, blocks=25, branch="feat/x")
    assert fixtures.open_threads(r2) == 12 and fixtures.cockpit_blocks(r2) == 25
    br = subprocess.run(["git", "-C", str(r2), "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True).stdout.strip()
    assert br == "feat/x", br
    print("  ✓ fixture sopra soglia + branch non-default")

    fake = {"assertions": [{"name": "conta", "kind": "open_threads", "value": 5},
                           {"name": "dice", "kind": "output_mentions", "value": "healthy"},
                           {"name": "tace", "kind": "output_omits", "value": "purge"}]}
    got = check(fake, r, "state healthy, nothing to do")
    assert [p for _, p, _ in got] == [True, True, True], got
    got_bad = check(fake, r2, "avvio la purge dei thread")
    assert [p for _, p, _ in got_bad] == [False, False, False], got_bad
    print("  ✓ le asserzioni distinguono pass da fail (3/3 e 0/3)")

    cases = load_cases()
    assert cases, "nessun caso"
    for c in cases:
        for k in ("id", "prompt", "proves", "fails_before", "assertions"):
            assert k in c, f"{c.get('id')}: manca {k}"
    print(f"  ✓ {len(cases)} casi, ognuno dichiara cosa prova e su cosa deve fallire")
    print("SELF-CHECK OK — harness verificato senza spendere un token")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case"); ap.add_argument("--model")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    cases = load_cases()
    if a.list:
        for c in cases:
            print(f"  {c['id']:<28} prova: {c['proves']}\n{'':<30}rosso su: {c['fails_before']}")
        return 0
    sel = [c for c in cases if not a.case or c["id"] == a.case]
    if not sel:
        print(f"nessun caso '{a.case}'", file=sys.stderr); return 2
    results = [run_case(c, a.model) for c in sel]
    print(f"\n{sum(results)}/{len(results)} casi passati")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
