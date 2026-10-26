"""feature_gate.py: a feature step closes only with its stage's artifact (operating model §3, §10).

Observed: bugfix is the only gated workflow (fix_gate.py); a feature phase "closed" when someone
said so. The Beads adoption tests (2026-10-24, §3) add what the gate must refuse beyond a missing
artifact: a `bd dep remove` that unblocks a phase without `--force`, a wisp step no lease can
recover, and a close that skips the judge.
"""
import json
import os
import subprocess
import sys
import tomllib

import pytest
from conftest import (GATE, SKILL, SUITE, bd, bd_init, mol_issues, needs_bd, plan_text, run,
                      step_id, write_plan)


def gate(repo, *args):
    return run(GATE, *args, "--repo", repo, cwd=repo, env=repo.env)


# --- plan stage: the file, in open/, with area + DoD + tests, accepted, epic poured -------------

@pytest.mark.parametrize("text, why", [
    (plan_text(area=""), "area"),
    (plan_text(dod=""), "DoD"),
    (plan_text(status="proposed"), "status"),
    (plan_text(tests=""), "tests"),
])
def test_plan_stage_refuses_a_missing_artifact(repo, text, why):
    p = write_plan(repo, text)
    r = gate(repo, "check", "--stage", "plan", "--record", p)
    assert r.returncode == 1, r.stderr
    assert why in r.stderr


def test_plan_stage_refuses_a_plan_outside_open(repo):
    p = write_plan(repo, where="done")
    r = gate(repo, "check", "--stage", "plan", "--record", p)
    assert r.returncode == 1 and "open/" in r.stderr


def test_plan_stage_refuses_before_the_epic_is_poured(repo):
    r = gate(repo, "check", "--stage", "plan", "--record", write_plan(repo))
    assert r.returncode == 1 and "epic" in r.stderr


def test_unknown_stage_and_missing_record_are_usage_errors(repo):
    assert gate(repo, "check", "--stage", "nope", "--record", write_plan(repo)).returncode == 2
    assert gate(repo, "check", "--stage", "plan", "--record", repo / "x.md").returncode == 2


# --- critic stage: a valid report, no blocking finding -----------------------------------------

def critic_report(repo, severity=None):
    finding = {"claim": "c", "severity": severity, "contract_quote": "q",
               "evidence": {"path": "a.md", "line": 1, "quote": "q"},
               "falsification": {"counter": "c", "survived": True, "why": "w"}}
    rep = {"artifact": ".", "contract": "c", "ledger": {"opened": ["a.md"], "not_opened": [],
           "accepted_unverified": []}, "findings": [finding] if severity else [],
           "halt": None if severity else {"reason": "no defect survived falsification"}}
    p = repo / "critic.json"
    p.write_text(json.dumps(rep))
    return p


def test_critic_stage(repo):
    p = write_plan(repo)
    rc = repo.env["POLARIS_SKILLS_ROOT"] + "/critic/scripts/rc"
    assert gate(repo, "check", "--stage", "critic", "--record", p).returncode == 1  # no report
    for sev in ("critical", "important"):
        r = gate(repo, "check", "--stage", "critic", "--record", p, "--report", critic_report(repo, sev))
        assert r.returncode == 1 and "blocking" in r.stderr, (sev, r.stderr)
    assert gate(repo, "check", "--stage", "critic", "--record", p,
                "--report", critic_report(repo, "minor")).returncode == 0
    open(rc, "w").write("1")  # critic_gate.py says the report is invalid
    r = gate(repo, "check", "--stage", "critic", "--record", p, "--report", critic_report(repo))
    assert r.returncode == 1 and "critic_gate" in r.stderr


# --- phase stage: tests green, nothing open blocking it; no review, no real-test (2026-10-26) ----

def test_phase_stage(repo):
    ok = ("--step", "any")
    red = write_plan(repo, plan_text(tests="false"))
    r = gate(repo, "check", "--stage", "phase", "--record", red, *ok)
    assert r.returncode == 1 and "tests" in r.stderr
    p = write_plan(repo)
    assert gate(repo, "check", "--stage", "phase", "--record", p, *ok).returncode == 0
    r = gate(repo, "check", "--stage", "phase", "--record", p)
    assert r.returncode == 1 and "--step" in r.stderr


def test_a_phase_closes_on_green_tests_alone(repo):
    """Founder 2026-10-26: a Beads phase is too small for review and real-testing; both run once,
    at the GitHub boundary (ship)."""
    stubs = repo.env["POLARIS_SKILLS_ROOT"]
    open(stubs + "/review/scripts/rc", "w").write("2")  # no review approval anywhere
    p = write_plan(repo)
    r = gate(repo, "check", "--stage", "phase", "--record", p, "--step", "any")
    assert r.returncode == 0, r.stderr
    assert not os.path.exists(stubs + "/real-testing/scripts/argv")  # real-testing never ran


# --- ship stage: merged, with real-test's receipt on the merged head ----------------------------

def test_ship_stage(repo):
    p, pr = write_plan(repo), repo.env["GH_STUB"]
    assert gate(repo, "check", "--stage", "ship", "--record", p, "--pr", "7").returncode == 1  # open
    head = "a" * 40
    merged = {"state": "MERGED", "headRefOid": head, "comments": []}
    open(pr, "w").write(json.dumps(merged))
    r = gate(repo, "check", "--stage", "ship", "--record", p, "--pr", "7")
    assert r.returncode == 1 and "receipt" in r.stderr
    merged["comments"] = [{"body": f"<!-- real-test v1 sha={head} verdict=MERGEABLE -->"}]
    open(pr, "w").write(json.dumps(merged))
    assert gate(repo, "check", "--stage", "ship", "--record", p, "--pr", "7").returncode == 0


# --- the engine on a real bd db -----------------------------------------------------------------

def epic_of(plan):
    import re
    return re.search(r"Beads epic:\s*`?([\w.-]+)", plan.read_text()).group(1)


@needs_bd
def test_pour_writes_epic_phases_and_status(repo):
    bd_init(repo)
    p = write_plan(repo)
    r = gate(repo, "pour", "--record", p)
    assert r.returncode == 0, r.stderr
    text = p.read_text()
    assert "status: in-progress" in text
    epic = epic_of(p)
    issues, deps = mol_issues(repo, epic)
    steps = {(i.get("metadata") or {}).get("step") for i in issues}
    assert {"plan", "critic", "implement", "ship", "phase", "task"} <= steps
    blocks = {(d["issue_id"], d["depends_on_id"]) for d in deps if d["type"] == "blocks"}
    p1, p2 = step_id(repo, epic, "phase", 1), step_id(repo, epic, "phase", 2)
    assert (p1, step_id(repo, epic, "critic")) in blocks
    assert (p2, p1) in blocks and (step_id(repo, epic, "implement"), p2) in blocks
    assert gate(repo, "pour", "--record", p).returncode == 1  # never twice


@needs_bd
def test_close_runs_the_stage_and_refuses_a_removed_edge(repo):
    bd_init(repo)
    p = write_plan(repo)
    assert gate(repo, "pour", "--record", p).returncode == 0
    epic = epic_of(p)
    plan_step, critic = step_id(repo, epic, "plan"), step_id(repo, epic, "critic")
    r = gate(repo, "close", "--step", critic, "--record", p, "--report", critic_report(repo))
    assert r.returncode == 1 and "blocked by open step" in r.stderr  # the gate's own order check
    assert gate(repo, "close", "--step", plan_step, "--record", p).returncode == 0
    assert gate(repo, "edges", "--record", p).returncode == 0
    p1 = step_id(repo, epic, "phase", 1)
    assert bd(repo, "dep", "remove", p1, critic).returncode == 0  # the hole §2.1 found
    r = gate(repo, "edges", "--record", p)
    assert r.returncode == 1 and p1 in r.stdout + r.stderr
    r = gate(repo, "close", "--step", critic, "--record", p, "--report", critic_report(repo))
    assert r.returncode == 1 and "edge" in r.stderr
    assert json.loads(bd(repo, "show", critic, "--json").stdout)[0]["status"] != "closed"


@needs_bd
def test_task_steps_are_not_the_gate_s_and_implement_waits_for_every_phase(repo):
    bd_init(repo)
    p = write_plan(repo)
    gate(repo, "pour", "--record", p)
    epic = epic_of(p)
    r = gate(repo, "close", "--step", step_id(repo, epic, "task"), "--record", p)  # tasks: plain bd close
    assert r.returncode == 2
    r = gate(repo, "check", "--stage", "implement", "--record", p)
    assert r.returncode == 1 and "phase" in r.stderr


@needs_bd
def test_claim_takes_a_lease_and_a_second_claimant_is_refused(repo):
    bd_init(repo)
    p = write_plan(repo)
    gate(repo, "pour", "--record", p)
    step = step_id(repo, epic_of(p), "plan")
    assert gate(repo, "claim", "--step", step, "--record", p).returncode == 0
    shown = json.loads(bd(repo, "show", step, "--json").stdout)[0]
    assert shown["status"] == "in_progress" and shown.get("lease_expires_at")
    other = dict(repo.env, BEADS_ACTOR="someone-else")
    r = run(GATE, "claim", "--step", step, "--record", p, "--repo", repo, cwd=repo, env=other)
    assert r.returncode == 1


@needs_bd
def test_finish_abandoned_keeps_a_digest_and_merged_refuses_an_incomplete_molecule(repo):
    bd_init(repo)
    p = write_plan(repo)
    gate(repo, "pour", "--record", p)
    epic = epic_of(p)
    assert gate(repo, "close", "--step", step_id(repo, epic, "plan"), "--record", p).returncode == 0
    r = gate(repo, "finish", "--record", p, "--abandoned", "scope moved to another area")
    assert r.returncode == 0, r.stderr
    assert bd(repo, "mol", "show", epic, "--json").returncode != 0  # burned
    digests = json.loads(bd(repo, "list", "--all", "--label", "kind:digest", "--json").stdout)
    assert len(digests) == 1
    body = digests[0]["description"]
    assert "scope moved" in body and "plan" in body and "closed" in body
    assert body.index("plan") < body.index("critic") < body.index("ship")  # phase order, not hash
    q = write_plan(repo, name="2026-10-24-other.md")
    gate(repo, "pour", "--record", q)
    epic2 = epic_of(q)
    r = gate(repo, "finish", "--record", q, "--merged")  # a merge burns a complete molecule only
    assert r.returncode == 1 and "still open" in r.stderr
    assert bd(repo, "mol", "show", epic2, "--json").returncode == 0
    assert len(json.loads(bd(repo, "list", "--all", "--label", "kind:digest", "--json").stdout)) == 1


@needs_bd
def test_pour_refuses_a_formula_that_drifted_from_the_skill(repo):
    bd_init(repo)
    f = repo / ".beads/formulas/feature.formula.toml"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text((SKILL / "formulas/feature.formula.toml").read_text().replace(
        'needs = ["plan"]\n', ""))
    r = gate(repo, "pour", "--record", write_plan(repo))
    assert r.returncode == 1 and "drift" in r.stderr


# --- bugfix.toml: the same engine, fix_gate's stages one-to-one ---------------------------------

def test_bugfix_formula_is_fix_gate_s_stages_linear():
    sys.path.insert(0, str(SUITE / "bugfix/scripts"))
    import fix_gate
    root = SUITE.parent
    f = tomllib.loads((root / ".beads/formulas/bugfix.formula.toml").read_text())
    ids = [s["id"] for s in f["steps"]]
    assert sorted(ids) == sorted(fix_gate.STAGES)
    assert all(s["needs"] == [ids[i]] for i, s in enumerate(f["steps"][1:]))
    assert all(s["metadata"]["step"] == s["id"] for s in f["steps"])


def test_the_repo_formula_is_the_skill_s():
    root = SUITE.parent
    assert (root / ".beads/formulas/feature.formula.toml").read_bytes() == \
        (SKILL / "formulas/feature.formula.toml").read_bytes()


def test_selfcheck():
    assert subprocess.run([sys.executable, str(GATE), "--selfcheck"]).returncode == 0


@needs_bd
def test_an_open_finding_blocking_the_phase_refuses_its_close(repo):
    """implement files findings as epic children with blocks:<phase> (one dep per pair in bd 1.3.1)."""
    bd_init(repo)
    p = write_plan(repo)
    gate(repo, "pour", "--record", p)
    epic = epic_of(p)
    walk = ()
    for step, extra in (("plan", ()), ("critic", ("--report", critic_report(repo)))):
        assert gate(repo, "close", "--step", step_id(repo, epic, step), "--record", p, *extra).returncode == 0
    p1 = step_id(repo, epic, "phase", 1)
    f = bd(repo, "create", "duplicated parser gh#7", "--parent", epic, "-l", "src:review,kind:finding",
           "--deps", f"discovered-from:{p1},blocks:{p1}", "--silent").stdout.strip()
    for t in (p1 + ".1", p1 + ".2"):
        bd(repo, "close", t, "-r", "done")
    r = gate(repo, "check", "--stage", "phase", "--record", p, "--step", p1, *walk)
    assert r.returncode == 1 and f in r.stderr
    assert gate(repo, "edges", "--record", p).returncode == 0  # an extra edge is not a missing one
    bd(repo, "close", f, "-r", "fixed in phase 1")
    assert gate(repo, "close", "--step", p1, "--record", p, *walk).returncode == 0


@needs_bd
def test_tasks_are_not_ready_before_their_phase_is(repo):
    """bd does not pass a parent's blockers to its children (measured by B2 on bd 1.3.1): right
    after pour every phase's tasks were in `bd ready --mol`, while critic was still open."""
    bd_init(repo)
    p = write_plan(repo)
    gate(repo, "pour", "--record", p)
    epic = epic_of(p)
    ready = {s["issue"]["id"] for s in json.loads(bd(repo, "ready", "--mol", epic, "--json").stdout)["steps"]}
    tasks = [i["id"] for i in mol_issues(repo, epic)[0] if (i.get("metadata") or {}).get("step") == "task"]
    assert tasks and not ready & set(tasks), ready & set(tasks)
    assert gate(repo, "edges", "--record", p).returncode == 0
    for step, extra in (("plan", ()), ("critic", ("--report", critic_report(repo)))):
        assert gate(repo, "close", "--step", step_id(repo, epic, step), "--record", p, *extra).returncode == 0
    ready = {s["issue"]["id"] for s in json.loads(bd(repo, "ready", "--mol", epic, "--json").stdout)["steps"]}
    p1 = step_id(repo, epic, "phase", 1)
    assert {p1 + ".1", p1 + ".2"} <= ready and not {t for t in tasks if t.startswith(p1)} ^ {p1 + ".1", p1 + ".2"}
    p2, t2 = step_id(repo, epic, "phase", 2), step_id(repo, epic, "phase", 2) + ".1"
    assert t2 not in ready  # phase 2's task still waits on phase 1
    assert bd(repo, "dep", "remove", t2, step_id(repo, epic, "phase", 1)).returncode == 0
    r = gate(repo, "edges", "--record", p)
    assert r.returncode == 1 and t2 in r.stderr, (p2, r.stderr)
