#!/usr/bin/env python3
"""Writes the content-addressed approval `.review-gate/approvals/<hash>.json`
that `gate_hook.py` consumes. This is the ONLY writer of that file — the
protocol is designed so hand-writing one (`{"verdict":"PASS"}`, the G2.5
shortcut: "the merge wall is self-reported discipline, not a mechanical
block") is not enough, because `gate_hook.py` cross-checks the approval's
`findings_digest` against the two findings files it names.

Never trusts a hash handed to it: recomputes `git write-tree` itself.
Requires two structurally separate findings files (Standards, Spec — G2.7:
merging axes into one ranking hides which one actually caught something)
where every finding cites `evidence` (an unquoted finding is a validation
error, not a silently dropped one), AND each findings file declares `scope`
(the real staged file list + diff line count) matching what is actually
staged right now — an empty `findings: []` with no `scope`, or a `scope`
that doesn't cover the real diff, is rejected the same way a missing
`evidence` is: nothing gets written. This closes the reproduced bypass
where two hand-typed empty JSON files pass as "reviewed, nothing found"
with zero relation to the diff (EVAL-review-bypass.md 3a) — it does NOT
prove the pass reasoned about the diff's semantics (that stays LLM
judgment, undecidable by this script), only that whoever wrote the
findings file knew what was actually staged.

`decide_verdict` re-validates findings and scope itself — it does not trust
`load_findings` to have been called first. A caller that imports this
module and drives `decide_verdict`/`write_approval` directly (skipping the
CLI) is gated exactly like the CLI (EVAL-review-bypass.md 3b: previously
`load_findings` was the only validator, and it's only reachable from
`main()` — a direct import bypassed severity/scope validation entirely).

Runs two mechanical blocking scans before deciding anything: money-path
diffs with no CORRELATED test companion or waiver (G3.7), and untracked
files with dangerous patterns a diff-only gate never sees (G9.1) — see
`scan_blockers.py`.

A FAIL verdict is still WRITTEN, with reasons: only a hash-computation
failure (not a git repo, or `git write-tree` erroring) or a structural
validation error (missing evidence, bad severity, scope mismatch) aborts
writing anything at all, because there is no key/no trustworthy content to
file it under. That is the one case this script treats as "cannot review",
never as "reviewed and clean" — the failure mode this whole job exists to
close (registro G2 #8: a gate that approves in silence when it does not
know).

    finalize_review.py <standards.json> <spec.json> [--cwd DIR]
                        [--waive ID:approver:reason ...] [--waive MONEY-PATH:...]
    finalize_review.py --print-scope [--cwd DIR]
    finalize_review.py --prune-older-than N [--cwd DIR]
    finalize_review.py --selfcheck
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

import scan_blockers as sb

SEVERITIES = {"CRITICAL", "INFORMATIONAL"}
REQUIRED_KEYS = ("file", "line", "severity", "summary", "evidence")


@dataclass
class Inputs:
    cwd: str
    standards: dict
    spec: dict
    waived: set[str] = field(default_factory=set)


@dataclass
class Decision:
    tree_hash: str
    verdict: str
    reasons: list[str]


def validate_finding(f: dict) -> str | None:
    """None if `f` is well-formed. A finding without cited evidence is a
    validation error, not a silently accepted or silently dropped item."""
    missing = [k for k in REQUIRED_KEYS if not f.get(k) and f.get(k) != 0]
    if missing:
        return f"finding missing {missing}: {f!r}"
    if f["severity"] not in SEVERITIES:
        return f"finding has unknown severity {f['severity']!r}: {f!r}"
    return None


def real_scope(cwd: str) -> dict:
    """The authoritative "what is actually staged right now" the reviewer
    must have looked at. `--print-scope` exposes this so a real Standards/
    Spec pass (or a test) can query it instead of guessing."""
    files = sb.changed_files(cwd)
    r = subprocess.run(["git", "diff", "--staged", "--numstat"],
                        cwd=cwd, capture_output=True, text=True)
    lines = 0
    for row in r.stdout.splitlines():
        parts = row.split("\t")
        if len(parts) >= 2:
            for p in parts[:2]:
                if p.isdigit():
                    lines += int(p)
    return {"files": sorted(files), "diff_lines": lines}


def scope_error(findings: dict, real: dict) -> str | None:
    """None if `findings["scope"]` is honest about the real staged diff.
    Closes 'zero relation to diff' (3a): a forged/empty findings file must
    at minimum correctly name what's staged and how big the diff is."""
    axis = findings.get("axis")
    scope = findings.get("scope")
    if not isinstance(scope, dict):
        return f"{axis}: missing 'scope' — run `finalize_review.py --print-scope` " \
               "and embed its output, even when findings is empty"
    claimed = set(scope.get("files") or [])
    missing = sorted(set(real["files"]) - claimed)
    if missing:
        return f"{axis}: scope.files doesn't cover the real staged diff — missing {missing}"
    if scope.get("diff_lines") != real["diff_lines"]:
        return f"{axis}: scope.diff_lines={scope.get('diff_lines')!r} != real " \
               f"{real['diff_lines']} (stale scope — the tree changed since this pass ran)"
    return None


def validate_findings_file(data: dict, axis: str, real: dict) -> str | None:
    if data.get("axis") != axis:
        return f"expected axis={axis!r}, got {data.get('axis')!r}"
    for f in data.get("findings", []):
        err = validate_finding(f)
        if err:
            return err
    return scope_error(data, real)


def compute_tree_hash(cwd: str) -> str:
    r = subprocess.run(["git", "write-tree"], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git write-tree failed: {r.stderr.strip()}")
    return r.stdout.strip()


def parse_waiver(raw: str) -> str:
    """`ID:approver:reason`, ID = `MONEY-PATH` or `file:line` (itself
    colon-bearing) — reconstructs ID from every part except the trailing
    approver/reason, so a `file:line` id round-trips instead of silently
    truncating to `file` (finalize_review previously never matched a
    per-finding waiver in this exact documented CLI form — copertura §2)."""
    parts = raw.split(":")
    if len(parts) < 3:
        raise ValueError(f"malformed --waive {raw!r}: expected ID:approver:reason")
    return ":".join(parts[:-2])


def critical_reasons(findings: dict, waived: set[str]) -> list[str]:
    out = []
    for f in findings.get("findings", []):
        fid = f"{f['file']}:{f['line']}"
        if f["severity"] == "CRITICAL" and fid not in waived:
            out.append(f"{findings['axis']} CRITICAL unwaived at {fid}: {f['summary']}")
    return out


def scan_reasons(inputs: Inputs) -> list[str]:
    cwd, waived = inputs.cwd, inputs.waived
    files = sb.changed_files(cwd)
    reasons = [f"untracked dangerous file: {p}" for p in sb.untracked_dangerous(cwd)]
    touched = sb.money_path_files(cwd, files)
    if touched and not sb.has_test_companion(cwd, files, touched) and "MONEY-PATH" not in waived:
        reasons.append(f"money-path files changed, no correlated test companion, no waiver: {touched}")
    cited = {f["file"] for d in (inputs.standards, inputs.spec) for f in d.get("findings", [])}
    for f in sb.suspect_mock_tests(cwd, files):
        if f not in cited:
            reasons.append(f"mock-only test suspected, not addressed in findings: {f}")
    return reasons


def decide_verdict(inputs: Inputs) -> tuple[str, list[str]]:
    """The single decision point — re-validates structure AND scope itself
    so a direct-import caller is gated exactly like the CLI (3b)."""
    real = real_scope(inputs.cwd)
    for data, axis in ((inputs.standards, "standards"), (inputs.spec, "spec")):
        err = validate_findings_file(data, axis, real)
        if err:
            raise ValueError(err)
    reasons = (critical_reasons(inputs.standards, inputs.waived)
               + critical_reasons(inputs.spec, inputs.waived)
               + scan_reasons(inputs))
    if reasons:
        return "FAIL", reasons
    raw = Inputs(inputs.cwd, inputs.standards, inputs.spec, set())
    raw_reasons = (critical_reasons(raw.standards, set())
                   + critical_reasons(raw.spec, set())
                   + scan_reasons(raw))
    return ("PASS-WITH-WAIVER" if raw_reasons else "PASS"), raw_reasons


def write_approval(inputs: Inputs, decision: Decision, findings_paths: tuple[str, str]) -> pathlib.Path:
    blob = b"".join(pathlib.Path(inputs.cwd, p).read_bytes() for p in findings_paths)
    approval = {
        "tree_hash": decision.tree_hash, "verdict": decision.verdict, "reasons": decision.reasons,
        "standards_findings": len(inputs.standards.get("findings", [])),
        "spec_findings": len(inputs.spec.get("findings", [])),
        "waivers": sorted(inputs.waived), "findings_digest": hashlib.sha256(blob).hexdigest(),
        "standards_path": findings_paths[0], "spec_path": findings_paths[1],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    out = pathlib.Path(inputs.cwd) / ".review-gate" / "approvals" / f"{decision.tree_hash}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(approval, indent=2))
    return out


def prune_stale(cwd: str, days: int) -> int:
    """Lifecycle drain: nothing else deletes these. Called on a cadence by
    `ship` or a maintenance cron — an artifact with no one draining it is
    the exact failure this suite's own standard names as a defect."""
    cutoff = time.time() - days * 86400
    removed = 0
    for sub in ("approvals", "findings"):
        d = pathlib.Path(cwd) / ".review-gate" / sub
        for p in d.glob("*.json") if d.exists() else []:
            if p.stat().st_mtime < cutoff:
                p.unlink()
                removed += 1
    return removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("standards", nargs="?")
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--waive", action="append", default=[])
    ap.add_argument("--prune-older-than", type=int)
    ap.add_argument("--print-scope", action="store_true")
    args = ap.parse_args(sys.argv[1:])
    if args.print_scope:
        print(json.dumps(real_scope(args.cwd)))
        return 0
    if args.prune_older_than is not None:
        print(f"pruned {prune_stale(args.cwd, args.prune_older_than)} stale gate file(s)")
        return 0
    if not args.standards or not args.spec:
        print("usage: finalize_review.py <standards.json> <spec.json> [--waive ID:approver:reason]",
              file=sys.stderr)
        return 2
    try:
        standards = json.loads(pathlib.Path(args.standards).read_text())
        spec = json.loads(pathlib.Path(args.spec).read_text())
        tree_hash = compute_tree_hash(args.cwd)
        waived = {parse_waiver(w) for w in args.waive}
        inputs = Inputs(args.cwd, standards, spec, waived)
        verdict, reasons = decide_verdict(inputs)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as e:
        print(f"finalize_review: cannot write an approval — {e}", file=sys.stderr)
        return 3
    out = write_approval(inputs, Decision(tree_hash, verdict, reasons), (args.standards, args.spec))
    print(f"{verdict} -> {out}")
    for r in reasons:
        print(f"  - {r}")
    return 0 if verdict != "FAIL" else 1


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as td:
        cwd = td
        subprocess.run(["git", "init", "-q"], cwd=cwd, check=True)
        pathlib.Path(cwd, "app.py").write_text("price = 10\n")
        subprocess.run(["git", "add", "app.py"], cwd=cwd, check=True)
        scope = real_scope(cwd)
        assert scope["files"] == ["app.py"] and scope["diff_lines"] > 0, \
            "--print-scope's underlying real_scope must reflect the real staged diff"

        empty = {"axis": "standards", "findings": [], "scope": scope}
        spec = {"axis": "spec", "findings": [], "scope": scope}

        try:
            decide_verdict(Inputs(cwd, {"axis": "standards", "findings": []}, spec, set()))
            raise AssertionError("findings with no 'scope' must be rejected, not silently accepted")
        except ValueError as e:
            assert "scope" in str(e), f"rejection reason must name the missing scope: {e}"

        stale = {"axis": "standards", "findings": [],
                 "scope": {"files": ["app.py"], "diff_lines": 999}}
        try:
            decide_verdict(Inputs(cwd, stale, spec, set()))
            raise AssertionError("a scope with the wrong diff_lines must be rejected (3a — the "
                                  "reproduced 'two empty JSON files, zero relation to the diff' bypass)")
        except ValueError as e:
            assert "diff_lines" in str(e), f"rejection reason must name the mismatch: {e}"

        verdict, reasons = decide_verdict(Inputs(cwd, empty, spec, set()))
        assert verdict == "FAIL" and any("money-path" in r for r in reasons), \
            "unwaived money-path change with no test companion must FAIL"

        verdict, _ = decide_verdict(Inputs(cwd, empty, spec, {"MONEY-PATH"}))
        assert verdict == "PASS-WITH-WAIVER", "an explicit waiver must clear the money-path block"

        crit = {"axis": "standards", "scope": scope, "findings": [
            {"file": "app.py", "line": 1, "severity": "CRITICAL", "summary": "x", "evidence": "price = 10"}]}
        verdict, reasons = decide_verdict(Inputs(cwd, crit, spec, {"MONEY-PATH"}))
        assert verdict == "FAIL" and any("CRITICAL unwaived" in r for r in reasons), \
            "a CRITICAL not itself waived must FAIL even if MONEY-PATH is waived"

        verdict, reasons = decide_verdict(Inputs(cwd, crit, spec, {"MONEY-PATH", "app.py:1"}))
        assert verdict == "PASS-WITH-WAIVER", "waiving the specific finding id must clear it"

        # 3b: a caller that imports this module and drives decide_verdict directly
        # (never touching load_findings/main's CLI validation) with a lowercase,
        # invalid severity must be gated exactly like the CLI would gate it.
        bad_severity = {"axis": "standards", "scope": scope, "findings": [
            {"file": "app.py", "line": 1, "severity": "critical", "summary": "x", "evidence": "price = 10"}]}
        try:
            decide_verdict(Inputs(cwd, bad_severity, spec, {"MONEY-PATH"}))
            raise AssertionError("an invalid severity must be rejected by decide_verdict itself, "
                                  "not only by the CLI's load_findings (3b)")
        except ValueError as e:
            assert "severity" in str(e), f"rejection reason must name the bad severity: {e}"

        err = validate_finding({"file": "x", "line": 1, "severity": "CRITICAL", "summary": "y", "evidence": ""})
        assert err, "a finding with empty evidence must be rejected, not silently accepted"

        assert parse_waiver("app.py:1:approver:looks-fine") == "app.py:1", \
            "a file:line waiver id (itself colon-bearing) must round-trip through parse_waiver"
        assert parse_waiver("MONEY-PATH:approver:reason") == "MONEY-PATH"
        try:
            parse_waiver("bad")
            raise AssertionError("a malformed --waive must raise, not silently misparse to an empty id")
        except ValueError:
            pass

        h = compute_tree_hash(cwd)
        sp, spp = pathlib.Path(cwd, "s.json"), pathlib.Path(cwd, "p.json")
        sp.write_text(json.dumps(empty)); spp.write_text(json.dumps(spec))
        out = write_approval(Inputs(cwd, empty, spec, set()), Decision(h, "PASS", []), ("s.json", "p.json"))
        saved = json.loads(out.read_text())
        assert saved["tree_hash"] == h and saved["verdict"] == "PASS" and saved["findings_digest"]

        try:
            compute_tree_hash(tempfile.mkdtemp())
            raise AssertionError("a non-git directory must raise, never return a fabricated hash")
        except RuntimeError:
            pass
    print("SELFCHECK OK — money-path block, waiver scoping (incl. file:line round-trip), "
          "empty-evidence rejection, scope-mismatch rejection (3a), direct-call severity "
          "validation (3b), real write-tree all hold")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv[1:] else main())
