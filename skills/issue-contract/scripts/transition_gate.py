#!/usr/bin/env python3
"""State-transition gate for `triage`. One function — `decide()` — makes
every decision; the CLI (`run()`/`main()`) is a thin wrapper around it and a
direct `import transition_gate` gets the exact same checks (closes the
corpus-audit finding: a gate that only fires through `main()`). There is no
lower-privilege path to a label: the old checks-free `resolve_label()` is
gone, folded into `decide()` as a private helper nothing public can reach
without going through the checks first.

Blocks a promotion to ready-for-agent/wontfix without a well-formed
redundancy-check (G9#7: prior-art ignored, 15 observations) — a `Searched:`
under 10 chars is treated as no search at all.
Blocks ready-for-agent when eligibility can't be verified at all (no
--issue-json, or the json is missing the 'assignee'/'linked_active_workstream'
keys) — missing data is not the same as a verified null, and this gate fails
closed, not open (daily-triage free-pick collision, incident #441).
Blocks wontfix with no --reason, and cross-checks a rejected-bug/
rejected-enhancement reason against a *verified* `category` field from
--issue-json instead of trusting the caller's flag — a self-declared reason
proves nothing.
Blocks writing .out-of-scope/ for an already-implemented wontfix (poisons
dedup); requires it (Decision:/Prior requests:) for every rejected-* reason.
Blocks a new tracked issue whose --concept matches the title of an issue
already open in --open-issues-json (F10) unless --override states why it's
different — a real, mechanized dedup check on real data, not prose.

With --apply (+ --issue-number, --repo): after an ALLOW this process itself
calls `gh issue edit` — the only way to reach `gh` through this tool is a
decision that returned ALLOW first. Without --apply: decision-only as before
(prints ALLOW/BLOCK, caller applies) for dry runs / CI.

    transition_gate.py --to <state> [--issue-json F] [--redundancy-file F]
                        [--reason R] [--out-of-scope-file F] [--label-map F]
                        [--apply --issue-number N --repo O/R [--from-label L]]
    transition_gate.py --to new-issue --concept "C" --open-issues-json F [--override "why"]
    transition_gate.py --selfcheck

Exit: 0 = ALLOW (label printed on stdout) · 1 = BLOCKED (reasons on stderr)
      2 = usage error (unknown state / --apply missing its required flags)
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

STATES = {"needs-triage", "needs-info", "ready-for-agent", "ready-for-human", "wontfix", "new-issue"}
CANONICAL_LABELS = {s: s for s in STATES}  # self-contained default — no
# external role-map skill required (sanes the broken /setup-matt-pocock-skills dependency)
CATEGORY_FOR_REASON = {"rejected-bug": "bug", "rejected-enhancement": "enhancement"}


def load_json(path):
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def load_json_list(path):
    if not path:
        return []
    data = json.loads(Path(path).read_text())
    return data if isinstance(data, list) else []


def _field(text, key):
    m = re.search(rf"^{key}\s*:\s*(.+)$", text, re.I | re.M)
    return m.group(1).strip() if m else ""


def check_redundancy(path):
    if not path or not Path(path).exists():
        return ["BLOCKED: redundancy-check file missing — search codebase + open backlog first (G9#7)"]
    text = Path(path).read_text()
    searched, found = _field(text, "searched"), _field(text, "found")
    errs = []
    if len(searched) < 10:
        errs.append("BLOCKED: redundancy-check 'Searched:' missing or too short to be a real search (G9#7)")
    if not found:
        errs.append("BLOCKED: redundancy-check missing 'Found:' — state yes/no + detail")
    return errs
    # NOTE (honest limit, not hidden — see update-gate.md): this proves the FORM of a
    # search happened, never that it happened truthfully. No text field can.


def check_eligibility(issue, has_issue_json):
    if not has_issue_json:
        return ["BLOCKED: --issue-json required for ready-for-agent — cannot verify assignee/workstream, fails closed"]
    errs = []
    if "assignee" not in issue:
        errs.append("BLOCKED: issue-json missing 'assignee' key — absent key is not a verified null")
    elif issue["assignee"] not in (None, "", "null"):
        errs.append(f"NOT-ELIGIBLE: already assigned to {issue['assignee']} — do not free-pick (daily-triage incident #441)")
    if "linked_active_workstream" not in issue:
        errs.append("BLOCKED: issue-json missing 'linked_active_workstream' key — absent key is not a verified false")
    elif issue["linked_active_workstream"]:
        errs.append("NOT-ELIGIBLE: linked to an active workstream/epic — leave it to the owner")
    return errs


def check_out_of_scope(reason, oos_path, issue, has_issue_json):
    if not reason:
        return ["BLOCKED: --reason required for wontfix (already-implemented|rejected-bug|rejected-enhancement)"]
    errs = []
    if reason == "already-implemented":
        if oos_path:
            errs.append("BLOCKED: reason=already-implemented must NOT write .out-of-scope/ — poisons dedup")
        return errs
    if not oos_path or not Path(oos_path).exists():
        errs.append(f"BLOCKED: {reason} requires an .out-of-scope/<concept>.md file")
    else:
        oos_text = Path(oos_path).read_text()
        if "Decision" not in oos_text or "Prior requests" not in oos_text:
            errs.append("BLOCKED: .out-of-scope file missing Decision:/Prior requests: fields")
    want_category = CATEGORY_FOR_REASON[reason]
    if not has_issue_json or "category" not in issue:
        errs.append(f"BLOCKED: --reason {reason} needs --issue-json with a verified 'category' field — a self-declared reason alone is not trusted")
    elif issue["category"] != want_category:
        errs.append(f"BLOCKED: --reason {reason} implies category={want_category}, verified issue-json says category={issue['category']!r}")
    return errs


def check_dedup(concept, has_open_issues, issues, override):
    errs = []
    if not concept:
        errs.append("BLOCKED: --concept required for new-issue — state what this is about, in a few words")
    if not has_open_issues:
        errs.append("BLOCKED: --open-issues-json required for new-issue — cannot dedupe against a bucket you never checked (F10)")
    if errs:
        return errs
    words = set(re.findall(r"[a-z0-9]{4,}", concept.lower()))
    hits = [it for it in issues if words & set(re.findall(r"[a-z0-9]{4,}", it.get("title", "").lower()))]
    if hits and not override:
        listing = ", ".join(f"#{h.get('number')} '{h.get('title')}'" for h in hits[:5])
        errs.append(f"BLOCKED: possible duplicate of open issue(s) {listing} — dedupe first, or pass --override 'why this is different' (F10)")
    return errs


def _resolve_label(to, label_map):
    """Private: a label string, not a decision. Only `decide()` calls this,
    and only after every applicable check_* above returned clean."""
    return label_map.get(to, CANONICAL_LABELS.get(to, to))


def decide(to, *, issue_json=None, redundancy_file=None, reason=None,
           out_of_scope_file=None, label_map=None, concept=None,
           open_issues_json=None, override=None):
    """The single decision surface — CLI and direct import both call this.
    Returns (exit_code, label_or_None, errors_list)."""
    if to not in STATES:
        return 2, None, [f"unknown state '{to}' — one of {sorted(STATES)}"]
    issue = load_json(issue_json) if issue_json else {}
    errs = []
    if to in ("ready-for-agent", "wontfix"):
        errs += check_redundancy(redundancy_file)
    if to == "ready-for-agent":
        errs += check_eligibility(issue, bool(issue_json))
    if to == "wontfix":
        errs += check_out_of_scope(reason, out_of_scope_file, issue, bool(issue_json))
    if to == "new-issue":
        errs += check_dedup(concept, bool(open_issues_json), load_json_list(open_issues_json), override)
    if errs:
        return 1, None, errs
    return 0, _resolve_label(to, load_json(label_map) if label_map else {}), []


def mutate(label, from_label, issue_number, repo):
    """Only reachable from run() after decide() returned ALLOW — see run()."""
    cmd = ["gh", "issue", "edit", str(issue_number), "--repo", repo, "--add-label", label]
    if from_label and from_label != label:
        cmd += ["--remove-label", from_label]
    subprocess.run(cmd, check=True)


def run(args):
    if args.apply:
        if args.to == "new-issue":
            print("BLOCK: --apply is not valid for --to new-issue — no tracker label to write, hand off to issue-contract on ALLOW", file=sys.stderr)
            return 2
        if not args.issue_number or not args.repo:
            print("BLOCK: --apply requires --issue-number and --repo", file=sys.stderr)
            return 2
    code, label, errs = decide(
        args.to, issue_json=args.issue_json, redundancy_file=args.redundancy_file,
        reason=args.reason, out_of_scope_file=args.out_of_scope_file, label_map=args.label_map,
        concept=args.concept, open_issues_json=args.open_issues_json, override=args.override,
    )
    if code != 0:
        for e in errs:
            print(e, file=sys.stderr)
        return code
    print(f"ALLOW {label}")
    if args.apply:
        mutate(label, args.from_label, args.issue_number, args.repo)
    return 0


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--to", required=True)
    p.add_argument("--issue-json")
    p.add_argument("--redundancy-file")
    p.add_argument("--reason", choices=["already-implemented", "rejected-bug", "rejected-enhancement"])
    p.add_argument("--out-of-scope-file")
    p.add_argument("--label-map")
    p.add_argument("--concept")
    p.add_argument("--open-issues-json")
    p.add_argument("--override")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--issue-number")
    p.add_argument("--repo")
    p.add_argument("--from-label", default="needs-triage")
    return p


def main():
    return run(build_parser().parse_args())


def selfcheck():
    """Every real branch, proven to fail when it must — including the
    direct-import path (no lower-privilege shortcut) and the decision/
    mutation coupling under --apply (proven by monkeypatching `mutate`,
    never by trusting stdout)."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        red_ok = d / "red_ok.md"; red_ok.write_text("Searched: codebase + open issues for X\nFound: no\n")
        red_bad = d / "red_bad.md"; red_bad.write_text("Searched: X\n")
        red_short = d / "red_short.md"; red_short.write_text("Searched: x\nFound: no\n")
        issue_ok = d / "issue_ok.json"; issue_ok.write_text('{"assignee": null, "linked_active_workstream": false}')
        issue_taken = d / "issue_taken.json"; issue_taken.write_text('{"assignee": "bob", "linked_active_workstream": false}')
        issue_noassignee = d / "issue_noassignee.json"; issue_noassignee.write_text('{"linked_active_workstream": false}')
        issue_bug = d / "issue_bug.json"; issue_bug.write_text('{"category": "bug"}')
        issue_enh = d / "issue_enh.json"; issue_enh.write_text('{"category": "enhancement"}')
        oos_ok = d / "oos.md"; oos_ok.write_text("# X\n**Decision:** reject\n**Prior requests:**\n- #1\n")
        open_issues = d / "open.json"; open_issues.write_text(
            '[{"number": 7, "title": "Dark mode support"}, {"number": 8, "title": "Export to CSV"}]'
        )

        a = build_parser()

        def run_args(argv):
            return run(a.parse_args(argv))

        # -- 1-7: the original 7 branches (redundancy / eligibility / out-of-scope shape) --
        assert run_args(["--to", "ready-for-agent", "--issue-json", str(issue_ok), "--redundancy-file", str(red_ok)]) == 0, \
            "well-formed redundancy + eligible issue must ALLOW"
        assert run_args(["--to", "ready-for-agent", "--issue-json", str(issue_ok)]) == 1, \
            "missing redundancy-check must BLOCK"
        assert run_args(["--to", "ready-for-agent", "--issue-json", str(issue_ok), "--redundancy-file", str(red_bad)]) == 1, \
            "malformed redundancy-check (no Found:) must BLOCK"
        assert run_args(["--to", "ready-for-agent", "--issue-json", str(issue_taken), "--redundancy-file", str(red_ok)]) == 1, \
            "already-assigned issue must BLOCK (free-pick collision)"
        assert run_args(["--to", "wontfix", "--redundancy-file", str(red_ok), "--reason", "already-implemented", "--out-of-scope-file", str(oos_ok)]) == 1, \
            "already-implemented + out-of-scope-file must BLOCK (poisoning)"
        assert run_args(["--to", "wontfix", "--redundancy-file", str(red_ok), "--reason", "rejected-enhancement",
                          "--out-of-scope-file", str(oos_ok), "--issue-json", str(issue_enh)]) == 0, \
            "rejected-enhancement with a valid out-of-scope file + verified category must ALLOW"
        assert run_args(["--to", "bogus-state"]) == 2, "unknown state must be a usage error"

        # -- 8-9: L5, fail closed on unverifiable eligibility data --
        assert run_args(["--to", "ready-for-agent", "--redundancy-file", str(red_ok)]) == 1, \
            "ready-for-agent with NO --issue-json at all must BLOCK, not fail open"
        assert run_args(["--to", "ready-for-agent", "--issue-json", str(issue_noassignee), "--redundancy-file", str(red_ok)]) == 1, \
            "issue-json missing the 'assignee' key must BLOCK — absent is not verified-null"

        # -- 10-12: L3/L4, --reason required and cross-checked against a verified category --
        assert run_args(["--to", "wontfix", "--redundancy-file", str(red_ok)]) == 1, \
            "wontfix with NO --reason at all must BLOCK"
        assert run_args(["--to", "wontfix", "--redundancy-file", str(red_ok), "--reason", "rejected-bug",
                          "--out-of-scope-file", str(oos_ok), "--issue-json", str(issue_enh)]) == 1, \
            "reason=rejected-bug on a verified category=enhancement issue must BLOCK (self-declared reason contradicted)"
        assert run_args(["--to", "wontfix", "--redundancy-file", str(red_ok), "--reason", "rejected-bug",
                          "--out-of-scope-file", str(oos_ok)]) == 1, \
            "reason=rejected-bug with NO --issue-json must BLOCK — unverified self-declared category"
        assert run_args(["--to", "wontfix", "--redundancy-file", str(red_ok), "--reason", "rejected-bug",
                          "--out-of-scope-file", str(oos_ok), "--issue-json", str(issue_bug)]) == 0, \
            "reason=rejected-bug with a verified category=bug issue + oos file must ALLOW"

        # -- 13: L6, a trivially short 'Searched:' is treated as no search --
        assert run_args(["--to", "ready-for-agent", "--issue-json", str(issue_ok), "--redundancy-file", str(red_short)]) == 1, \
            "a 1-char 'Searched:' must BLOCK — raises the floor on form (truth still unverifiable, see update-gate.md)"

        # -- 14-17: F10, mechanized dedup against real open-issue data --
        assert run_args(["--to", "new-issue", "--concept", "dark mode support",
                          "--open-issues-json", str(open_issues)]) == 1, \
            "a concept matching an already-open issue title must BLOCK without --override"
        assert run_args(["--to", "new-issue", "--concept", "dark mode support",
                          "--open-issues-json", str(open_issues), "--override", "different: this is API dark-mode, not UI"]) == 0, \
            "the same match with an explicit --override must ALLOW (audited escape hatch)"
        assert run_args(["--to", "new-issue", "--concept", "dark mode support"]) == 1, \
            "new-issue with NO --open-issues-json must BLOCK, not dedupe against nothing"
        assert run_args(["--to", "new-issue", "--concept", "rate limiter backoff",
                          "--open-issues-json", str(open_issues)]) == 0, \
            "a concept with no title overlap must ALLOW"

        # -- 18: L2, direct import gets the same checks as the CLI (no lower-privilege path) --
        code, label, errs = decide("ready-for-agent", issue_json=str(issue_ok))  # no redundancy_file
        assert code == 1 and label is None and errs, \
            "calling decide() directly (bypassing argparse/run entirely) must still BLOCK — same checks as the CLI"
        assert not hasattr(sys.modules[__name__], "resolve_label"), \
            "the old checks-free public resolve_label() must not exist as a shortcut"

        # -- 19-20: --apply only ever reaches `gh` through an ALLOW --
        this = sys.modules[__name__]
        calls = []
        original_mutate = this.mutate
        this.mutate = lambda label, frm, num, repo: calls.append((label, frm, num, repo))
        try:
            blocked = run_args(["--to", "wontfix", "--redundancy-file", str(red_ok), "--apply",
                                 "--issue-number", "1", "--repo", "o/r"])  # no --reason -> BLOCK
            assert blocked == 1 and calls == [], \
                "a BLOCKed decision + --apply must NEVER call the mutation function"
            allowed = run_args(["--to", "ready-for-agent", "--issue-json", str(issue_ok), "--redundancy-file", str(red_ok),
                                 "--apply", "--issue-number", "42", "--repo", "o/r"])
            assert allowed == 0 and calls == [("ready-for-agent", "needs-triage", "42", "o/r")], \
                "an ALLOWed decision + --apply must call the mutation function exactly once, with the decided label"
        finally:
            this.mutate = original_mutate
        assert run_args(["--to", "ready-for-agent", "--apply"]) == 2, \
            "--apply without --issue-number/--repo must be a usage error, not a silent no-op"

    print("SELFCHECK OK — 24 branches proved, each fails/passes as it must")
    return 0


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        sys.exit(selfcheck())
    sys.exit(main())
