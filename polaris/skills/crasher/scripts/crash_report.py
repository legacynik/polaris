#!/usr/bin/env python3
"""crash_report — the two things a crasher run can lie about, made mechanical, and a proposal.

"No crash found" is worth nothing unless the run names the paths it visited against the surface
it was meant to cover, so a run with no attempted list, no declared surface, or more paths than
its budget is refused rather than believed. "Here is a crash" is worth nothing if the same crash
is proposed again next week, so a finding's identity is a fingerprint over route + failure class
+ a symptom with its numbers collapsed: a 421s hang and a 388s hang are ONE finding.

This script files nothing. It prints a PROPOSAL — one entry per distinct fingerprint, with its
title, reproducing command and any already-open twin — and a person picks which to file through
issue-contract. `--unattended` writes the same proposal into the run record and prints nothing
to file.

    crash_report.py --run RUN.json [--open-issues OPEN.json] [--unattended]
    crash_report.py --selfcheck

OPEN.json is `gh issue list --state all --search crasher --json number,title,state`.
Exit: 0 no crash (accepted) · 1 run refused · 2 unusable input · 3 finding(s) proposed. Stdlib
only, no network, no browser — the run record is produced by the drive, not here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DIGITS = re.compile(r"\d+")
IDENTITY = ("route", "klass", "symptom")     # what makes a failure THIS failure
# `domain` labels the issue rather than naming the failure, so it is required for filing but kept
# out of the fingerprint. B12 rejects a label outside the host glossary: never guess one.
REQUIRED_FINDING = IDENTITY + ("domain",)
def fingerprint(finding: dict) -> str:
    """Stable identity of a failure: route + class + de-numbered symptom."""
    seed = [DIGITS.sub("#", " ".join(str(finding.get(k, "")).lower().split())) for k in IDENTITY]
    return hashlib.sha256("|".join(seed).encode()).hexdigest()[:8]


def title_of(finding: dict) -> str:
    """The fingerprint rides in the title because that is what the tracker searches."""
    return f"crasher: {finding.get('klass', 'unknown')} on {finding.get('route', '?')} [{fingerprint(finding)}]"


def proposal(findings: list[dict], open_issues: list[dict]) -> list[dict]:
    """One entry per distinct fingerprint, in run order, with the open twin when the tracker
    already holds one. The draft fields are what issue-contract writes into the ticket."""
    out, seen = [], set()
    for f in findings:
        fp = fingerprint(f)
        if fp in seen:
            continue
        seen.add(fp)
        repro, route = str(f.get("repro") or "").strip(), f.get("route")
        twin = next((i for i in open_issues if fp in str(i.get("title", ""))), None)
        out.append({
            "fingerprint": fp, "title": title_of(f), "repro": repro or None,
            "twin": f"#{twin.get('number')} ({str(twin.get('state', '')).lower()})" if twin else None,
            # a transcript-only finding cannot be claimed by an unattended agent
            "afk_human": "no" if repro else "yes",
            "description": f"The crasher found a failure on {route}: {f.get('symptom')}",
            "dod": (f"`{repro}` exits 0 on the deployment" if repro else
                    f"a cold re-drive of {route} renders with 0 console errors and 2xx/401 endpoints"),
            "regression": f"the next crasher run on the same target no longer reports fingerprint {fp}",
            "domain": f.get("domain"), "evidence": f.get("evidence"),
        })
    return out


def proposal_lines(entries: list[dict]) -> list[str]:
    lines = [f"PROPOSAL — {len(entries)} confirmed finding(s). Nothing was filed: the owner picks "
             "which to file, and each picked one goes through issue-contract."]
    for n, e in enumerate(entries, 1):
        lines += [f"  {n}. [{e['fingerprint']}] {e['title']}",
                  f"     repro: {e['repro'] or 'none — transcript only, for a person to confirm'}",
                  f"     twin: {e['twin'] + ' — already open, do not file' if e['twin'] else 'none open'}",
                  f"     afk human: {e['afk_human']} · evidence: {e['evidence'] or '-'}"]
    return lines


def _refusals(run: dict) -> list[str]:
    """Everything that makes a run unbelievable. Empty list = the verdict may be reported."""
    out, attempted, budget = [], run.get("attempted") or [], run.get("budget")
    surface = run.get("surface") or []
    if not attempted:
        out.append("no path attempted — a run that visited nothing cannot report 'no crash'")
    if not surface:
        out.append("surface undeclared — coverage without a denominator is not coverage")
    elif len(attempted) > len(surface):
        out.append(f"surface smaller than the run — {len(attempted)} attempted, "
                   f"{len(surface)} declared")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
        out.append("budget undeclared — an unbounded run is not the run that was authorised")
    elif len(attempted) > budget:
        out.append(f"budget exceeded — {len(attempted)} attempted, budget {budget}")
    return out + [f"finding without {', '.join(gap)} — an unnamed failure has no stable "
                  "identity, so it would file twice"
                  for gap in ([k for k in REQUIRED_FINDING if not str(f.get(k) or "").strip()]
                              for f in run.get("findings") or []) if gap]


def verdict(run: dict, open_issues: list[dict] | None = None) -> tuple[int, list[str]]:
    """(exit code, report lines) for one run record."""
    bad = _refusals(run)
    if bad:
        return 1, ["REFUSED — a run that cannot be believed files nothing:"] + \
            [f"  - {b}" for b in bad]
    attempted, surface = run["attempted"], run["surface"]
    head = [f"target: {run.get('target', '<undeclared>')} · coverage "
            f"{len(attempted)}/{len(surface)}", "paths attempted: " + ", ".join(map(str, attempted))]
    findings, open_issues = run.get("findings") or [], open_issues or []
    if not findings:
        return 0, head + ["NO CRASH FOUND — the list above is the whole basis of that claim."]
    return 3, head + proposal_lines(proposal(findings, open_issues))


def load_run(path: Path) -> tuple[dict | None, str]:
    """The run record, or None with the reason. `None` is the ONLY failure signal: callers
    branch on the record, never the message, so unusable input cannot reach `verdict`."""
    if not path.is_file():
        return None, f"run record not readable: {path} — a gate that cannot read never approves"
    try:
        data = json.loads(path.read_text(errors="replace"))
    except json.JSONDecodeError as exc:
        return None, f"run record is not JSON ({exc}) — unusable input is exit 2"
    if not isinstance(data, dict):
        return None, "run record must be a JSON object with attempted/budget/findings"
    return data, ""


HANG = {"route": "/generate", "klass": "gen_hang", "domain": "gates",
        "symptom": "no result after 421s"}


def _selfcheck_identity() -> None:
    """A crash keeps one identity across noise, and splits on route and on class."""
    assert title_of(HANG) == title_of(dict(HANG, symptom="no result after 388s")), \
        "timing noise must not mint a second issue for one crash"
    assert title_of(HANG) not in (title_of(dict(HANG, route="/chat")),
                                  title_of(dict(HANG, klass="console"))), "route/class split"
    assert fingerprint(HANG) in title_of(HANG), "the tracker searches the title"
    twin = [{"number": 9, "state": "OPEN", "title": title_of(HANG)}]
    entries = proposal([HANG, dict(HANG, symptom="no result after 388s"),
                        dict(HANG, route="/chat", repro="cmd")], twin)
    assert [e["fingerprint"] for e in entries] == [fingerprint(HANG), fingerprint(dict(HANG, route="/chat"))]
    assert entries[0]["twin"] == "#9 (open)" and entries[1]["twin"] is None, "the open twin is named"
    assert (entries[0]["afk_human"], entries[1]["afk_human"]) == ("yes", "no"), "repro is claimable"
    assert not any("gh issue create" in ln for ln in proposal_lines(entries)), "nothing is filed"


def selfcheck() -> int:
    """Every refusal branch, offline: no browser, no network, no tracker."""
    _selfcheck_identity()
    ok = {"budget": 4, "surface": ["/", "/a"], "attempted": ["/"], "findings": []}
    code, lines = verdict(ok)
    assert code == 0 and "NO CRASH FOUND" in "\n".join(lines) and "1/2" in "\n".join(lines)
    assert verdict(dict(ok, attempted=[]))[0] == 1, "nothing visited is not 'no crash'"
    assert verdict(dict(ok, surface=[]))[0] == 1, "coverage with no denominator is not coverage"
    assert verdict(dict(ok, attempted=["/", "/a", "/b"], budget=9))[0] == 1, "surface too small"
    assert verdict(dict(ok, budget=None))[0] == 1, "an unbounded run is not authorised"
    assert verdict(dict(ok, attempted=["/", "/a"], budget=1))[0] == 1, "over budget refuses"
    assert verdict(dict(ok, findings=[{"klass": "x"}]))[0] == 1, "unnamed failures refuse"
    assert verdict(dict(ok, findings=[{k: v for k, v in HANG.items() if k != "domain"}]))[0] == 1
    assert verdict(dict(ok, findings=[HANG, dict(HANG, route="/chat")]))[0] == 3
    assert load_run(Path("/nonexistent/x.json"))[0] is None, "absent is exit 2, never green"
    print("SELFCHECK OK — 16 branches: identity, in-run dedup, open twin, afk routing, no filing "
          "command, coverage, seven refusals, unusable input")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="verdict on one crasher run record")
    parser.add_argument("--run", type=Path, help="record: target budget surface attempted findings")
    parser.add_argument("--open-issues", type=Path,
                        help="gh issue list --state all --json number,title,state output")
    parser.add_argument("--unattended", action="store_true",
                        help="write the proposal into the run record; print nothing to file")
    parser.add_argument("--selfcheck", action="store_true")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if not args.run:
        parser.error("--run FILE is required (or --selfcheck)")
    data, err = load_run(args.run)
    if data is None:   # branch on the record, never on the message: pyright, and the truth
        print(err or f"run record unusable: {args.run}", file=sys.stderr)
        return 2
    open_issues: list[dict] = []
    if args.open_issues:
        try:
            open_issues = json.loads(args.open_issues.read_text())
            if not isinstance(open_issues, list):
                raise ValueError("not a JSON list")
        except (OSError, ValueError):
            print(f"open-issue list unusable: {args.open_issues} — a twin search that cannot read "
                  "never reports 'none open'", file=sys.stderr)
            return 2
    code, lines = verdict(data, open_issues)
    if code == 3 and args.unattended:
        data["proposal"] = proposal(data.get("findings") or [], open_issues)
        args.run.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        lines = lines[:2] + [f"UNATTENDED — {len(data['proposal'])} finding(s) proposed in "
                             f"{args.run} under 'proposal'; nothing filed, a person picks later."]
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
