#!/usr/bin/env python3
"""feature_gate.py — the per-stage gate of the feature workflow (operating model §3, §10).

Mirrors bugfix's fix_gate.py: a stage dict, exit 0 only with the stage's artifact. The stages are
the steps of the Beads formula `formulas/feature.formula.toml` (plan → critic → phase… → implement
→ ship), poured — never a wisp, which takes no lease (adoption tests 2026-10-24, §2.4) — and a step
closes only through `close`, which runs the step's stage and diffs the molecule's live `blocks`
edges against the formula and the plan's phase chain, so a `bd dep remove` cannot unblock a phase
(§2.1). Every bd read is scoped to the plan's molecule (§2.9).

Exit: 0 PASS · 1 FAIL · 2 usage (or bd missing). Fail-closed: absent or unreadable input never 0.

    feature_gate.py check  --stage plan|critic|phase|implement|ship --record PLAN --repo R [artifacts]
    feature_gate.py pour   --record PLAN --repo R      # epic + phases + tasks; plan → in-progress
    feature_gate.py close  --step ID --record PLAN --repo R [artifacts]
    feature_gate.py claim  --step ID --record PLAN --repo R   # reap expired leases of THIS mol, claim
    feature_gate.py edges  --record PLAN --repo R | --mol ID --formula NAME --repo R
    feature_gate.py finish --record PLAN --repo R --merged | --abandoned REASON
artifacts: --report critic.json · --pr N (--receipt/--base are accepted and ignored: a phase takes no
real-test since 2026-10-26 — real-testing runs once, at the GitHub boundary, on the PR)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMULA = HERE.parent / "formulas" / "feature.formula.toml"
SKILLS = Path(os.environ.get("POLARIS_SKILLS_ROOT") or HERE.parents[1])
INSTALL = "bd (Beads) is required: `brew install beads` — https://github.com/gastownhall/beads"
STARTABLE = {"accepted", "in-progress"}
BLOCKING = {"critical", "important"}                      # critic severities that block
ORDER = ["plan", "critic", "phase", "implement", "ship"]


class Usage(Exception):
    """Exit 2: the call itself is wrong, never a verdict."""


class Refused(Exception):
    """Exit 1 from deep inside a check: the state itself is wrong."""


# --- the plan file -------------------------------------------------------------------------------

def front(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    pairs = re.findall(r"^([A-Za-z_]+):[ \t]*(.*?)\s*$", m.group(1), re.M) if m else []
    return {k: v.split(" #", 1)[0].strip().strip("\"'") for k, v in pairs}  # `# …` is a comment


def section(text: str, name: str) -> str:
    m = re.search(rf"^##\s+(?:\d+\.\s*)?{name}.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return m.group(1) if m else ""


def phases(text: str) -> list[tuple[int, str, list[str]]]:
    """`### Phase N: title` under Approach, each with its `- task` bullets."""
    out = []
    for m in re.finditer(r"^###\s+Phase\s+(\d+)\s*[:.\-—]\s*(.+?)\s*$(.*?)(?=^###?\s|\Z)",
                         section(text, "Approach"), re.M | re.S):
        out.append((int(m.group(1)), m.group(2), re.findall(r"^\s*-\s+(.+?)\s*$", m.group(3), re.M)))
    return out


def epic_of(text: str) -> str | None:
    m = re.search(r"Beads epic:\s*`?([\w.-]+)", section(text, "Links"))
    return m.group(1) if m else None


# --- bd ------------------------------------------------------------------------------------------

def bd(repo: Path, *args: str) -> subprocess.CompletedProcess:
    if not shutil.which("bd"):
        raise Usage(INSTALL)
    return subprocess.run(["bd", *args], cwd=repo, capture_output=True, text=True, timeout=300)


def bd_json(repo: Path, *args: str):
    r = bd(repo, *args, "--json")
    try:
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except json.JSONDecodeError:
        return None


def mol(repo: Path, epic: str) -> tuple[list[dict], list[dict]]:
    out = bd_json(repo, "mol", "show", epic)
    if not out:
        raise Usage(f"molecule {epic} not found in {repo}")
    return out["issues"], out["dependencies"] or []


def meta(issue: dict) -> dict:
    return issue.get("metadata") or {}


def formula_steps(repo: Path, name: str, canonical: Path | None) -> list[dict]:
    """The formula bd will use, refused if it drifted from the canonical file the skill ships."""
    out = bd_json(repo, "formula", "show", name)
    if not out:
        raise Usage(f"formula {name} not found in {repo}/.beads/formulas (run `pour` first)")
    if canonical and Path(out["source"]).read_bytes() != canonical.read_bytes():
        raise Refused(f"formula drift: {out['source']} differs from {canonical}; restore it")
    return out["steps"]


def edge_errors(repo: Path, epic: str, n_phases: int | None, name="feature",
                canonical: Path | None = FORMULA) -> list[str]:
    """Every `blocks` edge the formula (and the plan's phase chain) demands must still exist."""
    issues, deps = mol(repo, epic)
    by_step = {meta(i)["step"]: i["id"] for i in issues if meta(i).get("step") not in (None, "phase", "task")}
    want = {(by_step.get(s["id"]), by_step.get(n)) for s in formula_steps(repo, name, canonical)
            for n in s.get("needs") or []}
    errs = []
    if n_phases is not None:
        chain = [i["id"] for i in sorted((i for i in issues if meta(i).get("step") == "phase"),
                                         key=lambda i: meta(i).get("phase", 0))]
        if len(chain) != n_phases:
            errs.append(f"the molecule has {len(chain)} phase beads, the plan names {n_phases}")
        links = [by_step.get("critic"), *chain, by_step.get("implement")]
        want |= set(zip(links[1:], links[:-1]))
        # bd does not pass a parent's blockers to its children: each task waits on what its phase
        # waits on, or `bd ready --mol` shows phase-2 tasks while critic is still open
        pred, step_of = dict(zip(chain, links)), {i["id"]: meta(i).get("step") for i in issues}
        want |= {(d["issue_id"], pred[d["depends_on_id"]]) for d in deps if d["type"] == "parent-child"
                 and d["depends_on_id"] in pred and step_of.get(d["issue_id"]) == "task"}
    have = {(d["issue_id"], d["depends_on_id"]) for d in deps if d["type"] == "blocks"}
    errs += [f"missing edge: {a} must be blocked by {b}" for a, b in sorted(want - have, key=str)]
    return errs


# --- stages --------------------------------------------------------------------------------------

def _sh(cmd: str, repo: Path, timeout: int = 3600) -> int:
    return subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, timeout=timeout).returncode


def _py(script: Path, *args, repo: Path) -> subprocess.CompletedProcess:
    if not script.is_file():
        raise Usage(f"sibling skill script missing: {script}")
    return subprocess.run([sys.executable, str(script), *map(str, args)], cwd=repo,
                          capture_output=True, text=True, timeout=900)


def stage_plan(c) -> list[str]:
    errs, fm = [], c.fm
    if "open" not in c.plan.parent.parts:
        errs.append(f"the plan is not in a plans/open/ folder: {c.plan}")
    if fm.get("status") not in STARTABLE:
        errs.append(f"status is {fm.get('status')!r}, the founder's `accepted` is required")
    for key in ("area", "tests"):
        if not fm.get(key):
            errs.append(f"frontmatter `{key}:` is empty")
    if not re.search(r"^\s*-\s+\S", section(c.text, "DoD"), re.M):
        errs.append("the DoD section has no line")
    if not phases(c.text):
        errs.append("Approach names no `### Phase N: title`")
    epic = epic_of(c.text)
    if not epic:
        errs.append("no `Beads epic:` in Links — the epic is not poured")
    elif not bd_json(c.repo, "mol", "show", epic):
        errs.append(f"Beads epic {epic} not found")
    check = c.repo / "scripts" / "check_plan_files.py"
    if check.is_file():
        rel = c.plan.resolve().relative_to(c.repo.resolve()).as_posix()
        r = _py(check, "--root", c.repo, "--json", repo=c.repo)
        try:
            found = json.loads(r.stdout)["findings"] if r.returncode == 0 else None
        except (ValueError, KeyError):
            found = None
        if found is None:
            errs.append(f"check_plan_files.py did not answer (exit {r.returncode})")
        errs += [f"check_plan_files: {f['rule']} {f['detail']}" for f in found or []
                 if f["path"] in (rel, rel.rsplit("/", 1)[0])]
    return errs


def stage_critic(c) -> list[str]:
    if not c.report or not Path(c.report).is_file():
        return ["critic report missing (--report): the plan is attacked before it is built"]
    r = _py(SKILLS / "critic/scripts/critic_gate.py", "--validate", c.report, repo=c.repo)
    if r.returncode != 0:
        return [f"critic_gate rejects the report (exit {r.returncode}): {(r.stdout + r.stderr).strip()[:300]}"]
    found = json.loads(Path(c.report).read_text()).get("findings") or []
    hit = [f.get("claim", "?") for f in found if f.get("severity") in BLOCKING]
    return [f"{len(hit)} blocking critic finding(s): {'; '.join(hit)[:300]}"] if hit else []


def open_blockers(c) -> list[str]:
    """Open beads blocking this step — a finding filed with `blocks:<phase>` among them."""
    issues, deps = mol(c.repo, c.epic)
    status = {i["id"]: i["status"] for i in issues}
    return [d["depends_on_id"] for d in deps if d["type"] == "blocks" and d["issue_id"] == c.step
            and status.get(d["depends_on_id"]) != "closed"]


def stage_phase(c) -> list[str]:
    """Tests green and nothing open blocking the phase. No review, no real-test: a Beads phase is
    too small for either, and both run once at the GitHub boundary, on the PR (`ship`, and the ship
    stage below demands real-test's receipt). Founder, 2026-10-26; supersedes the per-phase receipt
    and review approval of b4b, 2026-10-25."""
    errs = []
    if not c.step:
        errs.append("--step missing: the phase's open findings are read from its bead")
    if _sh(c.fm.get("tests") or "false", c.repo) != 0:
        errs.append(f"tests fail: {c.fm.get('tests')!r}")
    if c.step and c.epic:  # --step without an epic is refused by the plan stage, never reached here
        left = open_blockers(c)
        if left:
            errs.append(f"open finding(s) or step(s) block this phase: {', '.join(left)}")
    return errs


def stage_implement(c) -> list[str]:
    issues, _ = mol(c.repo, c.epic)
    ph = [i for i in issues if meta(i).get("step") == "phase"]
    if not ph:
        return ["no phase bead in the molecule"]
    left = [i["id"] for i in ph if i["status"] != "closed"]
    return [f"phase(s) still open: {', '.join(left)}"] if left else []


def stage_ship(c) -> list[str]:
    if not c.pr:
        return ["--pr missing: ship's receipts live on the PR"]
    r = subprocess.run(["gh", "pr", "view", str(c.pr), "--json", "state,headRefOid,comments"],
                       cwd=c.repo, capture_output=True, text=True, timeout=120)
    pr = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    if pr.get("state") != "MERGED":
        return [f"PR #{c.pr} is {pr.get('state') or 'unreadable'}, not MERGED"]
    spec = importlib.util.spec_from_file_location("receipt", SKILLS / "babysit/scripts/receipt.py")
    receipt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(receipt)
    signed = {m.group(1) for cm in pr.get("comments") or []
              for m in [receipt.RECEIPT.search(cm.get("body") or "")] if m}
    return [] if pr.get("headRefOid") in signed else [
        f"no real-test receipt on PR #{c.pr} for its merged head {pr.get('headRefOid')}"]


STAGES = {"plan": stage_plan, "critic": stage_critic, "phase": stage_phase,
          "implement": stage_implement, "ship": stage_ship}


# --- commands ------------------------------------------------------------------------------------

def _fail(errs: list[str]) -> int:
    for e in errs:
        print(f"FAIL: {e}", file=sys.stderr)
    return 1 if errs else 0


def cmd_check(c) -> int:
    if c.stage not in STAGES:
        raise Usage(f"unknown stage {c.stage} (known: {', '.join(STAGES)})")
    return _fail(STAGES[c.stage](c))


def _step(c) -> dict:
    issues, _ = mol(c.repo, c.epic)
    found = [i for i in issues if i["id"] == c.step]
    if not found:
        raise Usage(f"{c.step} is not a step of molecule {c.epic}")
    return found[0]


def cmd_close(c) -> int:
    stage = meta(_step(c)).get("step")
    if stage not in STAGES:
        raise Usage(f"{c.step} is a {stage or 'plain'} bead: tasks close with `bd close`, not the gate")
    blockers = open_blockers(c)
    errs = edge_errors(c.repo, c.epic, len(phases(c.text)))
    errs = errs or ([f"blocked by open step(s): {', '.join(blockers)}"] if blockers else STAGES[stage](c))
    if errs:
        return _fail(errs)
    r = bd(c.repo, "close", c.step, "-r", f"feature_gate {stage} exit 0")
    return _fail([] if r.returncode == 0 else [f"bd refused the close: {r.stderr.strip()[:300]}"])


def cmd_claim(c) -> int:
    _step(c)
    issues, _ = mol(c.repo, c.epic)
    held = [x for i in issues if i["status"] == "in_progress" for x in ("--id", i["id"])]
    if held:  # the reaper: a dead claimant's lease (TTL 5 min) is freed before anyone claims
        bd(c.repo, "reclaim", "--older-than", "0s", *held)
    r = bd(c.repo, "update", c.step, "--claim")
    return _fail([] if r.returncode == 0 else [r.stderr.strip()[:300]])


def cmd_edges(c) -> int:
    if c.record:
        return _fail(edge_errors(c.repo, c.epic, len(phases(c.text))))
    if not (c.mol and c.formula):
        raise Usage("edges needs --record, or --mol and --formula")
    return _fail(edge_errors(c.repo, c.mol, None, c.formula, None))


def cmd_pour(c) -> int:
    if epic_of(c.text):
        return _fail([f"already poured: {epic_of(c.text)}"])
    errs = [e for e in stage_plan(c) if "epic" not in e]
    if c.fm.get("status") != "accepted":
        errs.append("pour needs status `accepted`")
    if errs:
        return _fail(errs)
    target = c.repo / ".beads" / "formulas" / FORMULA.name
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(FORMULA, target)
        print(f"installed {target} from the plan skill")
    formula_steps(c.repo, "feature", FORMULA)
    stem = c.plan.stem
    out = bd_json(c.repo, "mol", "pour", "feature", "--var", f"plan={stem}")
    if not out:
        return _fail(["bd mol pour failed"])
    epic = out["new_epic_id"]
    issues, _ = mol(c.repo, epic)
    ids = {meta(i).get("step"): i["id"] for i in issues}
    prev = ids["critic"]
    for n, title, tasks in phases(c.text):
        pred = prev
        r = bd(c.repo, "create", f"phase {n}: {title}", "--parent", epic, "-l", "kind:phase",
               "--metadata", json.dumps({"step": "phase", "phase": n}), "--deps", f"blocked-by:{prev}",
               "--description", f"plan {stem}, phase {n}", "--silent")
        if r.returncode != 0:
            bd(c.repo, "mol", "burn", epic, "--force")
            return _fail([f"phase {n} not created, epic burned: {r.stderr.strip()[:200]}"])
        prev = r.stdout.strip()
        for t in tasks:
            r = bd(c.repo, "create", t, "--parent", prev, "-l", "kind:task", "--silent", "--deps", f"blocked-by:{pred}",
                   "--metadata", json.dumps({"step": "task"}), "--description", f"plan {stem}")
            if r.returncode != 0:
                bd(c.repo, "mol", "burn", epic, "--force")
                return _fail([f"task {t!r} not created, epic burned: {r.stderr.strip()[:200]}"])
    r = bd(c.repo, "dep", "add", ids["implement"], prev)
    if r.returncode != 0:
        bd(c.repo, "mol", "burn", epic, "--force")
        return _fail([f"implement not chained to the last phase, epic burned: {r.stderr.strip()[:200]}"])
    text = re.sub(r"^status:\s*accepted\s*$", "status: in-progress", c.text, count=1, flags=re.M)
    text = re.sub(r"^(##\s+(?:\d+\.\s*)?Links.*?\n)", rf"\1- Beads epic: {epic}\n", text, count=1, flags=re.M)
    c.plan.write_text(text)
    c.text, c.epic = text, epic
    errs = edge_errors(c.repo, epic, len(phases(text)))
    print(f"poured {epic}: {len(phases(text))} phase(s)")
    return _fail(errs)


def digest(c, reason: str) -> str:
    issues, _ = mol(c.repo, c.epic)
    shown = bd_json(c.repo, "show", *[i["id"] for i in issues])
    if not shown:
        raise Refused("bd show failed: no digest, nothing burned")
    rank = {s: n for n, s in enumerate(ORDER)}
    rows = sorted((i for i in shown if meta(i).get("step") in rank),
                  key=lambda i: (rank[meta(i)["step"]], meta(i).get("phase", 0)))
    lines = [f"abandoned: {reason}", f"plan: {c.plan.stem}", ""]
    lines += [f"- {i['title']}: {i['status']}" + (f" — {i['close_reason']}" if i.get("close_reason") else "")
              for i in rows]
    return "\n".join(lines)


def cmd_finish(c) -> int:
    """Merge → burn (the PR comment is the record). Abandon → a digest bead, then burn (§2.7):
    `bd mol squash` writes nothing for a poured molecule, so the gate writes bd's digest itself."""
    if c.merged:
        issues, _ = mol(c.repo, c.epic)
        left = [i["id"] for i in issues if meta(i).get("step") and i["status"] != "closed"]
        if left:
            return _fail([f"merge burns a complete molecule only; still open: {', '.join(left)}"])
    if c.abandoned:
        d = bd(c.repo, "create", f"digest: {c.plan.stem}", "-l", f"kind:digest,area:{c.fm.get('area')}",
               "--description", digest(c, c.abandoned), "--silent")
        if d.returncode != 0:
            return _fail([f"digest not written, nothing burned: {d.stderr.strip()[:200]}"])
        if bd(c.repo, "close", d.stdout.strip(), "-r", "digest of an abandoned plan").returncode != 0:
            return _fail([f"digest {d.stdout.strip()} written but not closed; nothing burned"])
    r = bd(c.repo, "mol", "burn", c.epic, "--force")
    return _fail([] if r.returncode == 0 else [f"burn failed: {r.stderr.strip()[:300]}"])


def _context(a) -> argparse.Namespace:
    a.repo = Path(a.repo)
    if getattr(a, "record", None):
        a.plan = Path(a.record)
        if not a.plan.is_file():
            raise Usage(f"no such plan file: {a.plan}")
        a.text = a.plan.read_text(encoding="utf-8", errors="replace")
        a.fm, a.epic = front(a.text), epic_of(a.text)
        if a.cmd in ("close", "claim", "finish") and not a.epic:
            raise Usage("the plan has no `Beads epic:` — pour it first")
    return a


def _selfcheck() -> int:
    text = "## 7. Approach\n### Phase 1: a\n- x\n- y\n### Phase 2 — b\n## 8. Links\n- Beads epic: t-1\n"
    assert phases(text) == [(1, "a", ["x", "y"]), (2, "b", [])], phases(text)
    assert epic_of(text) == "t-1" and front("---\nstatus: accepted  # x\n---\n") == {"status": "accepted"}
    assert section(text, "DoD") == "" and set(STAGES) == set(ORDER)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:  # the "I don't know" branch: empty input never passes
        bare = argparse.Namespace(plan=Path(tmp) / "x.md", text="", fm={}, repo=Path(tmp), epic=None,
                                  receipt=None, base=None, report=None, pr=None, step=None)
        assert len(stage_plan(bare)) >= 6 and stage_critic(bare) and stage_ship(bare)
        assert len(stage_phase(bare)) == 2, stage_phase(bare)  # step, tests
    print("SELFCHECK OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="feature_gate.py", description=__doc__.splitlines()[0])
    ap.add_argument("--selfcheck", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("check", "close", "claim", "edges", "pour", "finish"):
        p = sub.add_parser(name)
        p.add_argument("--repo", required=True)
        p.add_argument("--record", required=name not in ("edges",))
        for flag in ("--report", "--receipt", "--base", "--pr", "--mol", "--formula", "--abandoned"):
            p.add_argument(flag)
        p.add_argument("--stage", required=name == "check")
        p.add_argument("--step", required=name in ("close", "claim"))
        p.add_argument("--merged", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    if a.cmd == "finish" and bool(a.merged) == bool(a.abandoned):
        ap.error("finish needs exactly one of --merged / --abandoned REASON")
    cmds = {"check": cmd_check, "close": cmd_close, "claim": cmd_claim, "edges": cmd_edges,
            "pour": cmd_pour, "finish": cmd_finish}
    if a.cmd not in cmds:
        ap.print_help()
        return 2
    try:
        return cmds[a.cmd](_context(a))
    except Usage as e:
        print(f"USAGE: {e}", file=sys.stderr)
        return 2
    except Refused as e:
        return _fail([str(e)])
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
