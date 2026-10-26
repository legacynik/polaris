"""Fixtures for the plan skill: a throwaway repo with a real `bd` db, a plan file, a fake skills root.

Nothing is mocked inside the gate. The sibling skills it calls (critic, real-testing, babysit) are
replaced by stub scripts in a fake skills root, the way fix_gate's selfcheck stubs red_check.py,
and `gh` by a stub on PATH. `bd` is the real one: without it the bd tests skip and say why.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
SUITE = SKILL.parent
GATE = SKILL / "scripts" / "feature_gate.py"
CLOSE = SKILL / "scripts" / "plan_close.py"
class Repo(type(Path())):
    """A repo path that also carries the environment its commands run with."""


needs_bd = pytest.mark.skipif(shutil.which("bd") is None or bool(os.environ.get("PLAN_TESTS_NO_BD")),
                              reason="bd not installed (hard dependency), or PLAN_TESTS_NO_BD set")

PLAN = """---
title: Demo feature
status: {status}
area: {area}
created: 2026-10-24
tests: {tests}
---

# Demo feature

## 1. Area
`{area}` (assumed: from config outputs)

## 2. Why + outcome
Operators see X. Success: Y is observable (assumed).

## 3. Discovery
Prior art: none we own (assumed).

## 4. Prototype verdicts
None needed.

## 5. Contracts
`demo()` returns 1 (assumed).

## 6. DoD + regression checks
{dod}

## 7. Approach
### Phase 1: parser
- write the parser
- test the parser
### Phase 2: wiring
- wire it

## 8. Links
{links}

## 9. Trajectory changes
"""


def plan_text(status="accepted", area="demo", tests="true", dod="- demo() returns 1 on input a",
              links="- Issues: none"):
    return PLAN.format(status=status, area=area, tests=tests, dod=dod, links=links)


def run(script, *args, cwd=None, env=None):
    return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True,
                          text=True, cwd=cwd, env=env)


@pytest.fixture
def skills_root(tmp_path):
    """critic_gate / verdict.py / review gate_hook.py stubs: exit code from a file next to them, argv
    recorded beside it; the real receipt.py."""
    root = tmp_path / "skills"
    for rel in ("critic/scripts/critic_gate.py", "real-testing/scripts/verdict.py",
                "review/scripts/gate_hook.py"):
        p = root / rel
        p.parent.mkdir(parents=True)
        p.write_text("import sys, pathlib\nd = pathlib.Path(__file__).parent\n"
                     "(d / 'argv').write_text(' '.join(sys.argv[1:]))\n"
                     "sys.exit(int((d / 'rc').read_text()))\n")
        (p.parent / "rc").write_text("0")
    (root / "babysit/scripts").mkdir(parents=True)
    shutil.copy(SUITE / "babysit/scripts/receipt.py", root / "babysit/scripts/receipt.py")
    shutil.copytree(SKILL / "formulas", root / "plan-area/formulas")
    return root


@pytest.fixture
def repo(tmp_path, skills_root):
    """A git repo with docs/modules/demo/plans/open/<plan>.md and a gh stub on PATH."""
    r = Repo(tmp_path / "repo")
    (r / "docs/modules/demo/plans/open").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "gh").write_text("#!/bin/sh\ncat \"$GH_STUB\"\n")
    (bindir / "gh").chmod(0o755)
    (tmp_path / "pr.json").write_text(json.dumps({"state": "OPEN", "headRefOid": "a" * 40,
                                                   "comments": []}))
    env = dict(os.environ, POLARIS_SKILLS_ROOT=str(skills_root), GH_STUB=str(tmp_path / "pr.json"),
               PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}", POLARIS_TELEMETRY_OFF="1",
               BEADS_ACTOR="b1-test")
    r.env = env
    return r


def write_plan(repo, text=None, name="2026-10-24-demo.md", where="open"):
    p = repo / "docs/modules/demo/plans" / where / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text or plan_text())
    return p


def bd_init(repo):
    subprocess.run(["bd", "init", "--stealth", "--skip-agents", "--skip-hooks", "--non-interactive",
                    "-p", "tst"], cwd=repo, capture_output=True, check=True, env=repo.env)


def bd(repo, *args):
    return subprocess.run(["bd", *args], cwd=repo, capture_output=True, text=True, env=repo.env)


def mol_issues(repo, epic):
    out = json.loads(bd(repo, "mol", "show", epic, "--json").stdout)
    return out["issues"], out["dependencies"]


def step_id(repo, epic, step, phase=None):
    for i in mol_issues(repo, epic)[0]:
        m = i.get("metadata") or {}
        if m.get("step") == step and (phase is None or m.get("phase") == phase):
            return i["id"]
    raise AssertionError(f"no {step} {phase} in {epic}")


def walk_to_ship(repo, plan, epic):
    """Close every step before `ship` through the gate, with stub-valid artifacts."""
    (repo / "critic.json").write_text(json.dumps({"findings": [], "halt": {"reason": "none survived"}}))
    (repo / "receipt.json").write_text(json.dumps({"verdetto": "MERGEABLE"}))
    g = ("--record", plan, "--repo", repo)
    issues, _ = mol_issues(repo, epic)
    for step, extra in (("plan", ()), ("critic", ("--report", repo / "critic.json"))):
        r = run(GATE, "close", "--step", step_id(repo, epic, step), *g, *extra, cwd=repo, env=repo.env)
        assert r.returncode == 0, (step, r.stderr)
    phases = sorted((i for i in issues if (i.get("metadata") or {}).get("step") == "phase"),
                    key=lambda i: i["metadata"]["phase"])
    for ph in phases:
        for t in issues:
            if (t.get("metadata") or {}).get("step") == "task" and t["id"].startswith(ph["id"] + "."):
                assert bd(repo, "close", t["id"], "-r", "done").returncode == 0
        r = run(GATE, "close", "--step", ph["id"], *g, "--receipt", repo / "receipt.json",
                "--base", "abc123", cwd=repo, env=repo.env)
        assert r.returncode == 0, (ph["id"], r.stderr)
    r = run(GATE, "close", "--step", step_id(repo, epic, "implement"), *g, cwd=repo, env=repo.env)
    assert r.returncode == 0, r.stderr
