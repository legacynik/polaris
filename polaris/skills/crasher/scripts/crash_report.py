#!/usr/bin/env python3
"""crash_report — the two things a crasher run can lie about, made mechanical.

"No crash found" is worth nothing unless the run names the paths it visited against the surface
it was meant to cover, so a run with no attempted list, no declared surface, or more paths than
its budget is refused rather than believed. "Here is a crash" is worth nothing if the same crash
files again next week, so a finding's identity is a fingerprint over route + failure class + a
symptom with its numbers collapsed: a 421s hang and a 388s hang are ONE finding. Filing stays at
`issue-contract`, which dedups at apply time (`build_issue.py:apply_gate`), and the fingerprint
rides in the title so that search finds the twin.

    crash_report.py --run RUN.json      verdict on one run record
    crash_report.py --selfcheck         every refusal branch, offline

Exit: 0 no crash (accepted) · 1 run refused · 2 unusable input · 3 finding(s) to file. Stdlib
only, no network, no browser — the run record is produced by the drive, not here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path

DIGITS = re.compile(r"\d+")
IDENTITY = ("route", "klass", "symptom")     # what makes a failure THIS failure
# `domain` labels the issue rather than naming the failure, so it is required for filing but kept
# out of the fingerprint. B12 rejects a label outside the host glossary: never guess one.
REQUIRED_FINDING = IDENTITY + ("domain",)
# Addressed absolutely: the invocation is printed to be run from wherever the reader is.
BUILD_ISSUE = Path(__file__).resolve().parents[2] / "issue-contract" / "scripts" / "build_issue.py"


def fingerprint(finding: dict) -> str:
    """Stable identity of a failure: route + class + de-numbered symptom."""
    seed = [DIGITS.sub("#", " ".join(str(finding.get(k, "")).lower().split())) for k in IDENTITY]
    return hashlib.sha256("|".join(seed).encode()).hexdigest()[:8]


def title_of(finding: dict) -> str:
    """The fingerprint rides in the title because that is what the tracker searches."""
    return f"crasher: {finding.get('klass', 'unknown')} on {finding.get('route', '?')} [{fingerprint(finding)}]"


def _payload(finding: dict) -> dict:
    """The founder contract (B9-B16). The second adversarial test is always the dedup promise."""
    repro, route = str(finding.get("repro") or "").strip(), finding.get("route")
    fp = fingerprint(finding)
    if repro:
        ac = f"{repro} — exit 1 on the current deployment, exit 0 once fixed"
        first = f"{repro} — re-run cold from a clean session, exit 1 reproduces the finding"
    else:
        ac = (f"no assertion exists for class {finding.get('klass')!r} yet: the fix is accepted "
              f"when a cold re-drive of {route} returns status 200 with 0 console errors")
        first = (f"re-drive {route} cold: the same symptom must appear, exit 0 means the "
                 "finding was flaky and the issue is void")
    dedup = (f"run the crasher again on the same target: the finding must print fingerprint "
             f"{fp} once more and the tracker must refuse the second issue — 0 new, exit 1")
    return {"ac": ac, "domain": str(finding.get("domain") or ""), "advs": [first, dedup],
            "afk": "yes" if repro else "no", "priority": str(finding.get("priority") or "p2"),
            "exec": (f"Il crasher ha trovato un problema su {route}: "
                     f"{finding.get('symptom')}").replace("`", ""),
            "dedup": f"Searched: tracker for '{fp}'. Found: none."}


def issue_argv(finding: dict, slug: str) -> list[str]:
    """The issue-contract invocation for one finding — never a raw `gh` call. The `--field`
    pairs repeat the values under the ids the Polaris issue forms use; an id a template does
    not have is ignored, and one it needs and lacks is named by `build_issue.py` itself."""
    p = _payload(finding)
    argv = ["python3", str(BUILD_ISSUE), "--repo-slug", slug,
            "--repo-path", str(finding.get("repo_path") or "."), "--type", "bug",
            "--title", title_of(finding), "--ac", p["ac"], "--exec", p["exec"],
            "--dedup", p["dedup"], "--domain", p["domain"],
            "--priority", p["priority"], "--afk", p["afk"]]
    argv += [a for adv in p["advs"] for a in ("--adv-test", adv)]
    for key, value in (("not-a-duplicate", p["dedup"]), ("repro", p["ac"]),
                       ("adversarial-verification", " · ".join(p["advs"])),
                       ("domain", p["domain"]), ("priority", p["priority"]), ("afk", p["afk"])):
        argv += ["--field", f"{key}={value}"]
    return argv


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


def verdict(run: dict) -> tuple[int, list[str]]:
    """(exit code, report lines) for one run record."""
    bad = _refusals(run)
    if bad:
        return 1, ["REFUSED — a run that cannot be believed files nothing:"] + \
            [f"  - {b}" for b in bad]
    attempted, surface = run["attempted"], run["surface"]
    head = [f"target: {run.get('target', '<undeclared>')} · coverage "
            f"{len(attempted)}/{len(surface)}", "paths attempted: " + ", ".join(map(str, attempted))]
    findings = run.get("findings") or []
    if not findings:
        return 0, head + ["NO CRASH FOUND — the list above is the whole basis of that claim."]
    slug = str(run.get("repo_slug") or "<owner>/<repo>")
    return 3, head + [f"{len(findings)} finding(s) — file each through issue-contract:"] + [
        "  " + " ".join(shlex.quote(a) for a in issue_argv(f, slug)) for f in findings]


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
    argv = issue_argv(HANG, "o/r")
    claimable = issue_argv(dict(HANG, repro="cmd"), "o/r")
    assert argv[argv.index("--afk") + 1] == "no" and "no assertion" in " ".join(argv)
    assert claimable[claimable.index("--afk") + 1] == "yes", "a repro command is claimable"
    assert "gh" not in argv and Path(argv[1]).is_absolute(), "one door, addressed absolutely"
    assert sum(1 for a in argv if a == "--adv-test") == 2, "B9 refuses fewer than two"
    assert fingerprint(HANG) in argv[argv.index("--adv-test", argv.index("--adv-test") + 1) + 1]
    bare = issue_argv({k: v for k, v in HANG.items() if k != "domain"}, "o/r")
    assert bare[bare.index("--domain") + 1] == "", "a domain is never guessed for the glossary"


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
    print("SELFCHECK OK — 18 branches: identity, afk routing, one absolute door, two adversarial "
          "tests, dedup promise, no guessed domain, coverage, seven refusals")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="verdict on one crasher run record")
    parser.add_argument("--run", type=Path, help="record: target budget surface attempted findings")
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
    code, lines = verdict(data)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
