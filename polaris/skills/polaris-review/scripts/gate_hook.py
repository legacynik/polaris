#!/usr/bin/env python3
"""PreToolUse hook: blocks `git commit` / `gh pr merge` unless a matching,
un-forged approval exists at `.review-gate/approvals/<staged-tree-hash>.json`.

Fixes the bug this mechanism inherits from parallel-issue-flow's
preCommitGate.sh/preMergeGate.sh: those parse the hook's JSON with
`sed -E ... \\s`, a GNU-only escape BSD sed (macOS) never matches, so
`tool_name` always comes out empty and the gate allows everything, always,
silently. This parses with the stdlib `json` module only — no sed, no regex
on JSON — so that bug class cannot recur here. It also carries no bypass
environment variable: `PARALLEL_FLOW_BYPASS_GATE=1` is the exact escape
hatch registro voice G2.5 names as the reason the old wall was discipline,
not a mechanical block.

Command detection is word-set based, not adjacency-regex, and applies to
ANY tool whose input carries a `command`/`cmd`/`script` string — not only
`tool_name == "Bash"`. Both hardenings close reproduced evasions
(EVAL-review-bypass.md 3c-3g): `git -c commit.gpgsign=false commit -m x`
(flag between the words), `CMD=git; SUB=commit; $CMD $SUB -m x` (shell
variable indirection — "git"/"commit" still appear as whole words next to
`=`/`$`), `gh --repo x/y pr merge N` (a flag before the subcommand), and a
non-Bash shell-capable tool (e.g. an MCP `execute_shell_command`) carrying
the identical command. A determined obfuscator (base64, an interpreter that
builds the argv list piecemeal at runtime with no literal "git"/"commit"
token in the command string at all) still defeats word-set matching — no
static-text classifier closes that without executing the shell, which is
out of scope for a hook that must return in milliseconds; see
`references/bypass-test.md`'s stated threat-model boundary.

Content-addressed, not positional (registro spec's own principle): the key
is `git write-tree`, recomputed fresh on every check, so restaging anything
after approval invalidates it automatically — no separate staleness check
needed. The approval alone is not trusted either: it must name the two
findings files it was built from and match their current SHA-256 digest, so
hand-writing `{"verdict":"PASS"}` (the G2.5 shortcut) is not sufficient —
see references/bypass-test.md for the reproduction.

Wire into settings.json:
  "hooks": {"PreToolUse": [{"matcher": "Bash",
    "hooks": [{"type": "command", "command": "python3 <path>/gate_hook.py"}]}]}

Contract (Claude Code PreToolUse hook): reads
{"tool_name":..,"tool_input":{"command":..},"cwd":..} on stdin.
Exit 0 = allow. Exit 2 = block, one-line reason on stderr.

    gate_hook.py              run as a hook (reads stdin)
    gate_hook.py --selfcheck  prove every branch blocks/allows as designed
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

PASSING_VERDICTS = {"PASS", "PASS-WITH-WAIVER"}
COMMAND_KEYS = ("command", "cmd", "script")
WORD_RE = re.compile(r"[A-Za-z][\w.\-]*")


def extract_command(tool_input: dict) -> str:
    """The command text, from whichever key a shell-capable tool used —
    Bash's `command`, or an equivalent on any other tool. A tool with none
    of these keys (Read, Grep, ...) yields "" and is never gated."""
    for k in COMMAND_KEYS:
        v = tool_input.get(k)
        if isinstance(v, str):
            return v
    return ""


def targets_gate(command: str) -> bool:
    """Word-set match, not adjacency-regex: "git" and "commit" (or
    "gh"+"pr"+"merge") need only both appear as whole words SOMEWHERE in
    the command, in any order, with anything between them — a `-c
    key=value` flag, a `;`-separated variable assignment, a quoted argv
    list. This deliberately over-blocks ambiguous cases (e.g. a `grep`
    quoting the phrase) rather than under-block a real merge — a gate that
    can't tell must not approve (registro G2 #8)."""
    words = {w.lower() for w in WORD_RE.findall(command)}
    return ("git" in words and "commit" in words) or \
           ("gh" in words and "pr" in words and "merge" in words)


def staged_tree_hash(cwd: str) -> str | None:
    """The content-addressed key. None if `cwd` isn't a usable git repo."""
    try:
        r = subprocess.run(["git", "write-tree"], cwd=cwd, capture_output=True, text=True, timeout=10)
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def load_approval(cwd: str, tree_hash: str) -> dict | None:
    path = pathlib.Path(cwd) / ".review-gate" / "approvals" / f"{tree_hash}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def findings_digest_ok(cwd: str, approval: dict) -> bool:
    """The approval must point at findings files that still hash to what it
    recorded — closes the "I'll just hand-write PASS" bypass (G2.5)."""
    digest = approval.get("findings_digest")
    paths = (approval.get("standards_path"), approval.get("spec_path"))
    if not digest or not all(paths):
        return False
    blob = b""
    for rel in paths:
        p = pathlib.Path(cwd) / rel
        if not p.exists():
            return False
        blob += p.read_bytes()
    return hashlib.sha256(blob).hexdigest() == digest


def decide(payload: dict, cwd: str) -> tuple[int, str]:
    """(exit_code, stderr_reason). (0, "") means allow."""
    command = extract_command(payload.get("tool_input") or {})
    if not targets_gate(command):
        return 0, ""
    tree_hash = staged_tree_hash(cwd)
    if tree_hash is None:
        return 2, "review gate: not a git repo here — cannot verify an approval"
    approval = load_approval(cwd, tree_hash)
    if approval is None:
        return 2, f"review gate: no approval on file for staged tree {tree_hash[:12]} — run `polaris-review` first"
    if approval.get("verdict") not in PASSING_VERDICTS:
        return 2, f"review gate: approval says {approval.get('verdict')!r} for {tree_hash[:12]}"
    if not findings_digest_ok(cwd, approval):
        return 2, f"review gate: approval for {tree_hash[:12]} doesn't match its own findings files"
    return 0, ""


def main() -> None:
    payload = json.load(sys.stdin)
    code, reason = decide(payload, payload.get("cwd") or ".")
    if reason:
        print(reason, file=sys.stderr)
    sys.exit(code)


def _repo(tmp: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    (tmp / "a.txt").write_text("x")
    subprocess.run(["git", "add", "a.txt"], cwd=tmp, check=True)


def _write_valid_approval(tmp: pathlib.Path, tree_hash: str, verdict: str) -> None:
    fd = tmp / ".review-gate" / "findings"
    fd.mkdir(parents=True, exist_ok=True)
    sp, spp = fd / "standards.json", fd / "spec.json"
    sp.write_text('{"axis":"standards","findings":[]}')
    spp.write_text('{"axis":"spec","findings":[]}')
    digest = hashlib.sha256(sp.read_bytes() + spp.read_bytes()).hexdigest()
    ad = tmp / ".review-gate" / "approvals"
    ad.mkdir(parents=True, exist_ok=True)
    approval = {"verdict": verdict, "findings_digest": digest,
                "standards_path": ".review-gate/findings/standards.json",
                "spec_path": ".review-gate/findings/spec.json"}
    (ad / f"{tree_hash}.json").write_text(json.dumps(approval))


def selfcheck() -> int:
    """Eleven branches, each must land on the exit code it's named for."""
    commit = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        _repo(tmp)
        cwd = str(tmp)
        assert decide(commit, cwd)[0] == 2, "no approval file must BLOCK"
        h = staged_tree_hash(cwd)
        _write_valid_approval(tmp, h, "FAIL")
        assert decide(commit, cwd)[0] == 2, "verdict FAIL must BLOCK"
        _write_valid_approval(tmp, h, "PASS")
        assert decide(commit, cwd)[0] == 0, "verdict PASS with matching digest must ALLOW"

        forged = tmp / ".review-gate" / "approvals" / f"{h}.json"
        forged.write_text(json.dumps({"verdict": "PASS"}))  # hand-written, no digest
        assert decide(commit, cwd)[0] == 2, "a hand-written approval with no findings digest must BLOCK"

        (tmp / "b.txt").write_text("y")
        subprocess.run(["git", "add", "b.txt"], cwd=cwd, check=True)
        assert decide(commit, cwd)[0] == 2, "restaging must invalidate the stale approval"

        h2 = staged_tree_hash(cwd)
        (tmp / ".review-gate" / "approvals" / f"{h2}.json").write_text("{not valid json")
        assert decide(commit, cwd)[0] == 2, "a malformed approval file must BLOCK"

        unrelated = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
        assert decide(unrelated, cwd)[0] == 0, "an unrelated Bash command must ALLOW"
        not_bash = {"tool_name": "Read", "tool_input": {"file_path": "git-commit-notes.md"}}
        assert decide(not_bash, cwd)[0] == 0, "a non-command-shaped tool input must ALLOW " \
            "(no 'command'/'cmd'/'script' key — a file path mentioning git/commit is not a command)"

        # 3c-3g: reproduced evasions of the old adjacency-regex / Bash-only gate.
        # All must BLOCK — no approval exists for the (unstaged-change-free) repo
        # state at this point, so any of these reaching the approval check at all
        # already proves targets_gate recognized them; a regression that made
        # targets_gate return False would instead ALLOW (exit 0) here.
        flag_between = {"tool_name": "Bash",
                         "tool_input": {"command": "git -c commit.gpgsign=false commit -m x"}}
        assert decide(flag_between, cwd)[0] == 2, "a config flag between git/commit must still BLOCK (3c)"

        var_indirect = {"tool_name": "Bash",
                         "tool_input": {"command": "CMD=git; SUB=commit; $CMD $SUB -m x"}}
        assert decide(var_indirect, cwd)[0] == 2, "shell variable indirection must still BLOCK (3d)"

        embedded = {"tool_name": "Bash", "tool_input": {
            "command": "python3 -c \"import subprocess; subprocess.run(['git','commit','-m','x'])\""}}
        assert decide(embedded, cwd)[0] == 2, "git/commit embedded in another interpreter's argv must BLOCK (3e)"

        gh_flag = {"tool_name": "Bash",
                   "tool_input": {"command": "gh --repo acme/widgets pr merge 123 --squash"}}
        assert decide(gh_flag, cwd)[0] == 2, "a gh flag before the pr/merge subcommand must still BLOCK (3f)"

        non_bash_shell = {"tool_name": "mcp__serena-code-graph__execute_shell_command",
                           "tool_input": {"command": "git commit -m x"}}
        assert decide(non_bash_shell, cwd)[0] == 2, \
            "a non-Bash shell-capable tool with the same command must BLOCK too (3g)"
    print("SELFCHECK OK — 11 branches, each blocked/allowed as designed "
          "(incl. 3c-3g evasion reproductions)")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv[1:] else main())
