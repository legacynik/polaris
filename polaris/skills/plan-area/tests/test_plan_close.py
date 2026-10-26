"""plan_close.py: phase 8 leaves nothing of the work open (operating model §3, §6).

Observed: plans piled up in open/ (≈60% without status), and accepted decisions stayed accepted
after their probe passed (13 EXECUTED_IN_FACT on 2026-10-24) because nothing promoted them. Close
absorbs, moves, promotes through check_decision_execution's own verdict (never by hand) and burns.
"""
import json
import re
import shutil
import subprocess

from conftest import CLOSE, GATE, SUITE, bd, bd_init, needs_bd, plan_text, run, walk_to_ship, write_plan

VAULT_SCRIPTS = SUITE.parent / "scripts"


def dec(repo, slug, status, probe):
    rec = {"decision_id": slug, "status": status, "closure_check": "prose", "probe": probe,
           "call_sites": ["marker"], "probe_kills": "marker"}
    (repo / "decisions").mkdir(exist_ok=True)
    (repo / "decisions" / f"{slug}.md").write_text(f"---\n{json.dumps(rec, indent=2)}\n---\n\n# {slug}\n")


def setup_vault(repo, decs):
    """The repo carries the real decision gate and two DEC records; committed, as the probe shadow needs."""
    (repo / "scripts").mkdir(exist_ok=True)
    for name in ("check_decision_execution.py", "decision_probe_shadow.py"):
        shutil.copy(VAULT_SCRIPTS / name, repo / "scripts" / name)
    (repo / "marker").write_text("call site\n")
    for d in decs:
        dec(repo, *d)
    for cmd in (["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "f"]):
        subprocess.run(["git", *cmd], cwd=repo, check=True, capture_output=True)


def status_of(repo, slug):
    text = (repo / "decisions" / f"{slug}.md").read_text()
    return json.loads(text.split("---\n")[1])["status"]


def poured_plan(repo, links):
    bd_init(repo)
    p = write_plan(repo, plan_text(links=links))
    assert run(GATE, "pour", "--record", p, "--repo", repo, cwd=repo, env=repo.env).returncode == 0
    return p


def merged_with_receipt(repo):
    head = "b" * 40
    open(repo.env["GH_STUB"], "w").write(json.dumps({"state": "MERGED", "headRefOid": head, "comments": [
        {"body": f"<!-- real-test v1 sha={head} verdict=MERGEABLE -->"}]}))


def close(repo, p, *extra):
    return run(CLOSE, "--record", p, "--repo", repo, *extra, cwd=repo, env=repo.env)


@needs_bd
def test_close_refuses_until_the_canonical_doc_absorbed_the_plan(repo):
    p = poured_plan(repo, "- Issues: none")
    merged_with_receipt(repo)
    r = close(repo, p, "--merged", "--pr", "7")
    assert r.returncode == 1 and "canonical" in r.stderr
    assert p.exists()


@needs_bd
def test_close_promotes_a_passing_dec_moves_the_file_and_burns(repo):
    setup_vault(repo, [("DEC-demo-ready-001", "accepted", "test -f marker")])
    p = poured_plan(repo, "- Decisions: DEC-demo-ready-001")
    (repo / "docs/modules/demo/demo.md").write_text("# demo\n\nProven by 2026-10-24-demo: X.\n")
    epic = re.findall(r"Beads epic:\s*`?([\w.-]+)", p.read_text())[-1]
    merged_with_receipt(repo)
    r = close(repo, p, "--merged", "--pr", "7")
    assert r.returncode == 1 and "ship" in r.stderr  # a skipped stage: implement still open
    walk_to_ship(repo, p, epic)
    r = close(repo, p, "--merged", "--pr", "7")
    assert r.returncode == 0, r.stderr
    assert status_of(repo, "DEC-demo-ready-001") == "executed"
    done = repo / "docs/modules/demo/plans/done/2026-10-24-demo.md"
    assert done.exists() and not p.exists() and "status: done" in done.read_text()
    assert bd(repo, "mol", "show", epic, "--json").returncode != 0
    gate = subprocess.run(["python3", "scripts/check_decision_execution.py", "--root", "."],
                          cwd=repo, capture_output=True, text=True)
    assert re.search(r"\bEXECUTED\s+DEC-demo-ready-001", gate.stdout), gate.stdout


@needs_bd
def test_close_refuses_a_dec_whose_probe_fails_and_changes_nothing(repo):
    setup_vault(repo, [("DEC-demo-pend-001", "accepted", "exit 1")])
    p = poured_plan(repo, "- Decisions: DEC-demo-pend-001")
    (repo / "docs/modules/demo/demo.md").write_text("2026-10-24-demo\n")
    merged_with_receipt(repo)
    r = close(repo, p, "--merged", "--pr", "7")
    assert r.returncode == 1 and "NOT_DONE" in r.stderr
    assert status_of(repo, "DEC-demo-pend-001") == "accepted" and p.exists()


@needs_bd
def test_abandon_archives_with_a_reason_and_leaves_a_digest(repo):
    p = poured_plan(repo, "- Issues: none")
    r = close(repo, p, "--abandoned", "superseded by the pricing plan")
    assert r.returncode == 0, r.stderr
    arch = repo / "docs/modules/demo/archive/2026-10-24-demo.md"
    assert arch.exists() and "status: abandoned" in arch.read_text()
    assert "superseded by the pricing plan" in arch.read_text()
    digests = json.loads(bd(repo, "list", "--all", "--label", "kind:digest", "--json").stdout)
    assert len(digests) == 1
