#!/usr/bin/env python3
"""next_bead.py — the next bead of the epic's CURRENT phase (implement Step 2).

The current phase is the lowest open phase bead; its work is its child tasks and the open beads
that block it. A parent's blockers do not reach its children in bd, so any bead outside the
current phase that bd lists as ready is skipped (plan 0.2.1's `pour` blocks its own tasks; a
hand-added one is not). Prints the bead id (nothing when the current phase
has no ready bead) and, on stderr, the ready beads it skipped and the current phase's held ones.

    next_bead.py --mol EPIC [--repo R]
    next_bead.py --selfcheck

Exit: 0 answered (a bead or nothing) · 2 bd failed or is missing (fail closed).
"""
import argparse
import json
import subprocess
import sys

STAGES = ("phase", "plan", "critic", "implement", "ship")  # never a worker's bead


def current(mol):
    """The current phase's work: ids of its child tasks and of the beads blocking it."""
    meta = {i["id"]: i.get("metadata") or {} for i in mol["issues"]}
    status = {i["id"]: i["status"] for i in mol["issues"]}
    phases = sorted((m["phase"], i) for i, m in meta.items()
                    if m.get("step") == "phase" and status[i] != "closed")
    if not phases:
        return set()
    cur, deps = phases[0][1], mol["dependencies"]
    mine = {d["issue_id"] for d in deps if d["type"] == "parent-child" and d["depends_on_id"] == cur}
    return mine | {d["depends_on_id"] for d in deps if d["type"] == "blocks" and d["issue_id"] == cur}


def pick(mol, ready):
    """(bead id or None, ready ids of other phases skipped) from `bd mol show --json` and
    `bd ready --mol --json`."""
    meta = {i["id"]: i.get("metadata") or {} for i in mol["issues"]}
    ready_open = [s["issue"]["id"] for s in ready["steps"]
                  if s["parallel_info"]["is_ready"] and s["issue"]["status"] == "open"
                  and meta.get(s["issue"]["id"], {}).get("step") not in STAGES
                  and s["issue"]["id"] != mol.get("root", {}).get("id")]
    mine = current(mol)
    if not mine:
        return None, []
    take = sorted((i for i in ready_open if i in mine), key=plan_order)
    return (take[0] if take else None), [i for i in ready_open if i not in mine]


def plan_order(bead_id):
    """`e2e-mol-x.1.10` after `.1.2`: pour numbers a phase's tasks in the plan's bullet order."""
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in bead_id.split(".")]


def held(mol):
    """Beads of the current phase someone holds: a dead claimant's comes back on `G claim`."""
    status = {i["id"]: i["status"] for i in mol["issues"]}
    return sorted(i for i in current(mol) if status.get(i) == "in_progress")


def bd_json(repo, *args):
    r = subprocess.run(["bd", *args, "--json"], cwd=repo, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or f"bd {' '.join(args)} failed")
    return json.loads(r.stdout)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mol", required=True, help="the epic id (the plan's `Beads epic:` link)")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    try:
        mol = bd_json(a.repo, "mol", "show", a.mol)
        bead, skipped = pick(mol, bd_json(a.repo, "ready", "--mol", a.mol))
    except (OSError, RuntimeError, ValueError) as e:
        print(f"next_bead: {e}", file=sys.stderr)
        return 2
    if skipped:
        print(f"skipped, not the current phase: {', '.join(skipped)}", file=sys.stderr)
    if not bead and held(mol):
        print(f"held: {', '.join(held(mol))} — claim it with feature_gate.py claim (the reaper"
              " frees a dead claimant's lease)", file=sys.stderr)
    print(bead or "")
    return 0


def selfcheck():
    mol = {"issues": [{"id": "p1", "status": "open", "metadata": {"step": "phase", "phase": 1}},
                      {"id": "p2", "status": "open", "metadata": {"step": "phase", "phase": 2}},
                      {"id": "a", "status": "open", "metadata": {"step": "task"}},
                      {"id": "b", "status": "open", "metadata": {"step": "task"}}],
           "dependencies": [{"issue_id": "a", "depends_on_id": "p1", "type": "parent-child"},
                            {"issue_id": "b", "depends_on_id": "p2", "type": "parent-child"}]}
    ready = {"steps": [{"issue": {"id": i, "status": "open"}, "parallel_info": {"is_ready": True}}
                       for i in ("b", "a")]}
    assert pick(mol, ready) == ("a", ["b"]), pick(mol, ready)
    print("next_bead selfcheck: ok")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if sys.argv[1:] == ["--selfcheck"] else main())
