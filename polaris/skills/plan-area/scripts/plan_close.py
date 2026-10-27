#!/usr/bin/env python3
"""plan_close.py — phase 8: nothing of the work left open (operating model §3, §5, §6).

Called by `ship` after the merge (the loop included), never by `/end`. Everything is checked
before anything is written:

  merged     the area README names the plan (proven content absorbed); every DEC the
             plan's Links name passes the repository's own `check_decision_execution.py` verdict
             (EXECUTED, or EXECUTED_IN_FACT → promoted to `executed` by this script, then re-judged);
             the `ship` step closes through feature_gate.py; the epic is burned (the PR comment is
             the record); the file moves to `done/` with `status: done`.
  abandoned  `status: abandoned` + the reason; feature_gate.py writes the digest and burns; the file
             moves to the area's `archive/`.

Exit: 0 closed · 1 refused (nothing changed) · 2 usage.

    plan_close.py --record PLAN --repo R --merged --pr N
    plan_close.py --record PLAN --repo R --abandoned "<one-line reason>"
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from feature_gate import Usage, epic_of, front, meta, mol, section  # noqa: E402

DEC_ID = re.compile(r"\bDEC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-\d{3}\b")
FRONTMATTER = re.compile(r"^---\n(\{.*?\n\})\n---", re.S)


def gate(*args) -> subprocess.CompletedProcess:
    r = subprocess.run([sys.executable, str(HERE / "feature_gate.py"), *map(str, args)],
                       capture_output=True, text=True)
    r.stderr = re.sub(r"^FAIL: ", "", r.stderr, flags=re.M)  # relayed under this script's own FAIL:
    return r


def judge(repo: Path):
    """The repository's own decision gate — the only logic allowed to say `executed`."""
    script = repo / "scripts" / "check_decision_execution.py"
    if not script.is_file():
        return None
    sys.path.insert(0, str(script.parent))
    return importlib.import_module("check_decision_execution")


def dec_plan(repo: Path, ids: list[str]) -> tuple[list[tuple[Path, str, dict]], list[str]]:
    """(records to promote, errors). EXECUTED passes as is; EXECUTED_IN_FACT is promoted."""
    if not ids:
        return [], []
    mod = judge(repo)
    if mod is None:
        return [], [f"the plan enacts {', '.join(ids)} but {repo}/scripts/check_decision_execution.py is absent"]
    todo, errs = [], []
    for slug in ids:
        path = repo / "decisions" / f"{slug}.md"
        m = FRONTMATTER.match(path.read_text()) if path.is_file() else None
        if not m:
            errs.append(f"{slug}: no decision record with JSON frontmatter at {path}")
            continue
        text, rec = m.group(1), json.loads(m.group(1))
        verdict, note = mod._verdict(rec, repo, 120) if rec.get("status") in mod.JUDGED else (rec.get("status"), "not judged")
        if verdict == "EXECUTED_IN_FACT":
            todo.append((path, text, rec))
        elif verdict != "EXECUTED":
            errs.append(f"{slug} {verdict}: {note}")
    return todo, errs


def move(src: Path, dst: Path, text: str, repo: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(src)], cwd=repo,
                             capture_output=True).returncode == 0
    if tracked:
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=repo, check=True, capture_output=True)
    else:
        src.rename(dst)
    dst.write_text(text)


def set_status(text: str, status: str, extra: str = "") -> str:
    return re.sub(r"^status:.*$", f"status: {status}{extra}", text, count=1, flags=re.M)


def _revert(done: list[tuple[Path, str, str]]) -> None:
    for path, old, new in done:
        path.write_text(path.read_text().replace(new, old, 1))


def promote(repo: Path, todo: list[tuple[Path, str, dict]]) -> tuple[list, list[str]]:
    """Write `executed`, then re-judge each record FROM DISK; any doubt reverts every write."""
    done, mod = [], judge(repo)
    for path, old, rec in todo:
        now, new = path.read_text(), json.dumps({**rec, "status": "executed"}, indent=2)
        if old not in now:
            _revert(done)
            return [], [f"{rec['decision_id']} changed on disk since it was judged; nothing promoted"]
        path.write_text(now.replace(old, new, 1))
        done.append((path, old, new))
    for path, _, _ in done:
        rec = json.loads(FRONTMATTER.match(path.read_text()).group(1))
        verdict, note = mod._verdict(rec, repo, 120)
        if verdict != "EXECUTED":
            _revert(done)
            return [], [f"{rec['decision_id']} re-judged {verdict} after promotion, all reverted: {note}"]
    return done, []


def merged(a, plan: Path, text: str) -> list[str]:
    """Every check first; then promote (revertible), close ship, burn, move."""
    area_dir = plan.parent.parent.parent              # <area>/plans/open/<file>
    canon = area_dir / "README.md"
    if not canon.is_file() or plan.stem not in canon.read_text(errors="replace"):
        return [f"absorb the proven content into the area README {canon} first (it must name {plan.stem})"]
    todo, errs = dec_plan(a.repo, sorted(set(DEC_ID.findall(section(text, "Links")))))
    if errs:
        return errs
    check = gate("check", "--stage", "ship", "--record", plan, "--repo", a.repo, "--pr", a.pr)
    if check.returncode != 0:
        return [check.stderr.strip()]
    issues, _ = mol(a.repo, epic_of(text))
    ship = [i for i in issues if meta(i).get("step") == "ship"]
    left = [i["id"] for i in issues if meta(i).get("step") not in (None, "ship") and i["status"] != "closed"]
    if not ship or left:
        return [f"a skipped stage: still open before ship: {', '.join(left) or 'no ship step'}"]
    done, errs = promote(a.repo, todo)
    if errs:
        return errs
    if ship[0]["status"] != "closed":
        r = gate("close", "--step", ship[0]["id"], "--record", plan, "--repo", a.repo, "--pr", a.pr)
        if r.returncode != 0:
            _revert(done)
            return [f"the ship step did not close, promotions reverted: {r.stderr.strip()}"]
    r = gate("finish", "--record", plan, "--repo", a.repo, "--merged")
    if r.returncode != 0:
        return [f"ship closed and DECs promoted, but the burn failed (re-run plan close): {r.stderr.strip()}"]
    move(plan, plan.parent.parent / "done" / plan.name, set_status(text, "done"), a.repo)
    return []


def abandoned(a, plan: Path, text: str) -> list[str]:
    if epic_of(text):
        r = gate("finish", "--record", plan, "--repo", a.repo, "--abandoned", a.abandoned)
        if r.returncode != 0:
            return [r.stderr.strip()]
    area_dir = plan.parent.parent.parent
    move(plan, area_dir / "archive" / plan.name, set_status(text, "abandoned", f" — {a.abandoned}"), a.repo)
    return []


def _selfcheck() -> int:
    links = "- Decisions: DEC-polaris-operating-model-001, DEC-demo-x-002; not DEC-bad"
    assert DEC_ID.findall(links) == ["DEC-polaris-operating-model-001", "DEC-demo-x-002"]
    assert set_status("---\nstatus: in-progress\n---", "done") == "---\nstatus: done\n---"
    print("SELFCHECK OK (the bd paths are tests/test_plan_close.py)")
    return 0


def main() -> int:
    if "--selfcheck" in sys.argv:
        return _selfcheck()
    ap = argparse.ArgumentParser(prog="plan_close.py", description=__doc__.splitlines()[0])
    ap.add_argument("--record", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--merged", action="store_true")
    ap.add_argument("--pr")
    ap.add_argument("--abandoned")
    a = ap.parse_args()
    a.repo, plan = Path(a.repo), Path(a.record)
    if bool(a.merged) == bool(a.abandoned) or (a.merged and not a.pr):
        ap.error("exactly one of --merged --pr N / --abandoned REASON")
    if not plan.is_file() or "open" not in plan.parent.parts:
        print(f"USAGE: not a plan in open/: {plan}", file=sys.stderr)
        return 2
    text = plan.read_text()
    if not front(text).get("status"):
        print("USAGE: the plan has no `status:` line", file=sys.stderr)
        return 2
    if a.merged and front(text).get("status") != "in-progress":
        print(f"USAGE: status is {front(text).get('status')!r}; only in-progress work merges", file=sys.stderr)
        return 2
    try:
        errs = merged(a, plan, text) if a.merged else abandoned(a, plan, text)
    except (Usage, OSError, ValueError, KeyError, subprocess.CalledProcessError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    for e in errs:
        print(f"FAIL: {e}", file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
