# Bypass-test — must FAIL to bypass, every time

Three ways the old pre-commit/pre-merge gate this replaces was proven bypassable, each reproduced here and closed, **plus 7 more
found by an adversarial audit of this skill itself** (cases 3a-3g —
empty findings via the official path, a direct import instead of the CLI, and 5 variants that
bypass `targets_gate` by literal text). Run the whole block; every `echo exit=$?` MUST
print `2` (blocked) except the ones marked `exit=0`.

```bash
set -e   # setup steps below must hard-fail; expected-nonzero checks use the
         # `|| CODE=$?` idiom instead — a bare failing pipeline WOULD also
         # trigger set -e and silently truncate the whole run before the
         # "want N" line ever prints (verified empirically; not theoretical)
SCRIPTS="<review-skill-dir>/scripts"   # e.g. ~/.agents/skills/review/scripts
gate() { CODE=0; printf '%s' "$1" | python3 "$SCRIPTS/gate_hook.py" || CODE=$?; }
finalize() { CODE=0; python3 "$SCRIPTS/finalize_review.py" "$@" || CODE=$?; }

rm -rf /tmp/review-bypass-test && mkdir /tmp/review-bypass-test && cd /tmp/review-bypass-test
git init -q && git config user.email t@t.com && git config user.name t
echo "def add(a,b): return a+b" > app.py
git add app.py
COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m x"},"cwd":"'"$(pwd)"'"}'

# 1. Nothing has run `review` yet — the naive case. MUST block.
gate "$COMMIT"; echo "1) exit=$CODE (want 2)"

# 2. The G2.5 bypass this job exists to close: hand-write an approval
#    instead of running the review ("I already looked at it, just say PASS").
#    No `findings_digest` a real reviewer pass would have produced — MUST block.
mkdir -p .review-gate/approvals
H=$(git write-tree)
echo '{"verdict":"PASS"}' > ".review-gate/approvals/$H.json"
gate "$COMMIT"; echo "2) exit=$CODE (want 2)"

# 3. A step up: forge findings files too, but they don't match the digest
#    named in the approval (stale, edited after the fact, or copy-pasted
#    from a different review). MUST block.
mkdir -p .review-gate/findings
echo '{"axis":"standards","findings":[]}' > .review-gate/findings/standards.json
echo '{"axis":"spec","findings":[]}' > .review-gate/findings/spec.json
echo '{"verdict":"PASS","findings_digest":"0000","standards_path":".review-gate/findings/standards.json","spec_path":".review-gate/findings/spec.json"}' \
  > ".review-gate/approvals/$H.json"
gate "$COMMIT"; echo "3) exit=$CODE (want 2)"

# 4. The real path: run finalize_review.py against real findings files —
#    THIS is how a valid approval gets written. `scope` must be the real
#    output of --print-scope; a stale/wrong scope is case 7 below. MUST
#    allow (exit=0).
python3 "$SCRIPTS/finalize_review.py" --print-scope --cwd . > /tmp/rt-scope.json
python3 - <<'PY'
import json
scope = json.load(open("/tmp/rt-scope.json"))
for axis, path in (("standards", ".review-gate/findings/standards.json"),
                    ("spec", ".review-gate/findings/spec.json")):
    json.dump({"axis": axis, "findings": [], "scope": scope}, open(path, "w"))
PY
finalize .review-gate/findings/standards.json .review-gate/findings/spec.json --cwd .
gate "$COMMIT"; echo "4) exit=$CODE (want 0)"

# 5. Re-staging after approval without re-review (the "I'll just add one
#    more line" drift) invalidates the approval automatically — content
#    addressed, not positional. MUST block.
echo "def sub(a,b): return a-b" >> app.py
git add app.py
gate "$COMMIT"; echo "5) exit=$CODE (want 2)"

# 6. The old escape hatch does NOT exist here — setting it must have no
#    effect. MUST still block (same as case 1, env var ignored).
CODE=0; printf '%s' "$COMMIT" | PARALLEL_FLOW_BYPASS_GATE=1 python3 "$SCRIPTS/gate_hook.py" || CODE=$?
echo "6) exit=$CODE (want 2, env var must be a no-op — there is none to read)"

# 7. case 3a: two findings files typed by hand in two
#    seconds, "findings":[], with NO scope at all — indistinguishable from
#    "reviewed, clean" before this case existed. finalize_review.py must
#    refuse to write anything (exit 3), so gate_hook has nothing to approve.
echo "def add(a,b): return a+b" >> app.py
git add app.py
echo '{"axis":"standards","findings":[]}' > .review-gate/findings/standards.json
echo '{"axis":"spec","findings":[]}' > .review-gate/findings/spec.json
finalize .review-gate/findings/standards.json .review-gate/findings/spec.json --cwd .
echo "7) finalize_review exit=$CODE (want 3, nothing written)"
gate "$COMMIT"; echo "7b) exit=$CODE (want 2, no approval on file)"

# 8-13. case 3b-3g, driven directly against the importable
# functions (the same ones the CLI and the hook call) — this both closes
# the "direct import skips validation" gap (3b IS this pattern) and avoids
# fighting shell-quoting to embed adversarial command strings in JSON.
SCRIPTS="$SCRIPTS" python3 - <<'PY'
import os, subprocess, sys, json
sys.path.insert(0, os.environ["SCRIPTS"])
import finalize_review as fr
import gate_hook as gh

# 8 (3b): direct decide_verdict call, skipping the CLI, with a lowercase
# (invalid) severity that a real CRITICAL must not be able to hide behind.
scope = fr.real_scope(".")
bad = {"axis": "standards", "scope": scope, "findings": [
    {"file": "app.py", "line": 1, "severity": "critical",
     "summary": "command injection", "evidence": "os.system(x)"}]}
spec = {"axis": "spec", "scope": scope, "findings": []}
try:
    fr.decide_verdict(fr.Inputs(".", bad, spec, set()))
    print("8) BYPASSED (3b) — must not happen")
except ValueError as e:
    print(f"8) BLOCKED (3b, raised): {e}")

# 9-13 (3c-3g): five ways to write "git commit"/"gh pr merge" that a
# literal-adjacency regex misses, run through the real decide() the hook
# uses. All must return exit code 2 (no approval exists for this repo).
cases = [
    ("9 (3c, flag between git/commit)", "Bash", "git -c commit.gpgsign=false commit -m x"),
    ("10 (3d, shell variable indirection)", "Bash", "CMD=git; SUB=commit; $CMD $SUB -m x"),
    ("11 (3e, embedded in another interpreter's argv)", "Bash",
     "python3 -c \"import subprocess; subprocess.run(['git','commit'])\""),
    ("12 (3f, gh flag before the subcommand)", "Bash", "gh --repo acme/widgets pr merge 123 --squash"),
    ("13 (3g, non-Bash tool, same command)", "mcp__serena-code-graph__execute_shell_command",
     "git commit -m x"),
]
for label, tool_name, command in cases:
    code, _ = gh.decide({"tool_name": tool_name, "tool_input": {"command": command}}, ".")
    print(f"{label} exit={code} (want 2)")
PY

rm -rf /tmp/review-bypass-test
```

## What this does and does not defend against

Cases 1–3 and 5 close the **specific bypass this job's registro voices name**:
G2.5 (merge wall = self-reported discipline — closed by requiring an approval file at all,
and by rejecting a hand-written one without a matching findings digest), and the stale-hash
drift both `review` and `real-testing` inherited-and-fixed from the old gate
(content-addressed key recomputed fresh every check, not cached).

Cases 7–13 close the second round, found by an adversarial audit of this skill itself
 7/7b close "two empty findings files, typed in two seconds, zero
relation to the diff" passing as a genuine clean review (3a — `scope` must now name the real
staged files and line count); 8 closes a direct-import caller skipping the CLI's own
validation (3b — `decide_verdict` now validates itself, so the CLI and any importer are
gated identically); 9–13 close five `targets_gate` evasions that a literal-adjacency regex
missed — a config flag between `git`/`commit` (3c), shell-variable indirection (3d), the
command embedded in another interpreter's argv (3e), a `gh` flag before the subcommand (3f),
and a non-`Bash` shell-capable tool carrying the identical command (3g).

**Threat model boundary, stated plainly, including what stays open after this round**: this
is a local, unsigned, filesystem gate — same as the system it replaces. A determined attacker
with write access to the repo could, in principle, reconstruct the whole protocol (forge
findings files with a correct `scope`, hash them correctly, write a matching approval) by
hand — cases 7/8 raise the cost of that (you must know what's actually staged, and you can't
skip validation via import) but do not make it cryptographically impossible, and neither
`gate_hook.py` nor the donor gate it replaces (`preCommitGate.sh`) attempt to. `targets_gate`
is still text-based: an obfuscator who builds the argv with no literal "git"/"commit" word in
the command string at all (base64, a second script file with no gated word in its own
invocation) is not caught by cases 9–13's word-set match either — closing that needs a real
shell parser or execution tracing, out of scope for a hook that must decide in milliseconds.
Finally, `gate_hook.py` only fires where it is actually wired as a pre-commit hook; whether that
wiring exists on any given machine is an operational fact this document cannot test (see
the Portability section of `gate.md`) — a `git commit` typed in a plain
terminal, a different harness, or a machine where the hook was never installed never reaches
this script at all. What this closes is the **realistic bypass this project measured
happening and then re-measured after fixing it**: a lazy or rushed `{"verdict":"PASS"}`, an
approval written for a diff that has since changed, an env-var escape hatch nobody has to
type to use, an empty review with no link to the diff, a direct-import shortcut, and five
ways of writing the same shell command. That is the failure class the registro documents
(G2.5, G2.7, G3.7, G9.1), not nation-state tamper resistance or a guarantee that the hook is
even running on this machine right now.

## Running the three structural selfchecks

```bash
python3 <review-skill-dir>/scripts/gate_hook.py --selfcheck        # 11 branches, incl. 3c-3g
python3 <review-skill-dir>/scripts/finalize_review.py --selfcheck  # verdict + scope (3a/3b) + real git
python3 <review-skill-dir>/scripts/scan_blockers.py --selfcheck    # money-path correlation, secrets, mock-marker
```
All three print `SELFCHECK OK` and exit 0, or raise `AssertionError` naming exactly which
branch failed to hold.

## Second-opinion cases (absorbed from codex-review 1.0.0)

Run from the skill directory. Each command exits 0 when the skill is sound, 1 when the case it
guards has come back.

**S1 — a pinned model id recommended as runnable.** `fails_before:` codex-review 0.9.0, whose
guide carried `-m gpt-5.2-codex` in four runnable examples while its own warning said such ids
fail on a subscription login. The skill pins no model anywhere.

```bash
! grep -nE -- ' -m [a-z0-9.-]+|model[ =:"]+(gpt|claude|o[0-9])' SKILL.md references/second-opinion.md
! grep -niE '\b(haiku|sonnet|opus|gpt-[0-9])' SKILL.md
```

**S2 — an invocation without stdin closed or a timeout.** `fails_before:` the first Codex lens
of the PR sweep: no `< /dev/null`, no `timeout`, an hour blocked on stdin, zero-byte output.

```bash
python3 - <<'PY'
import re, sys
text = open("references/second-opinion.md").read()
blocks = [b for b in re.findall(r"```bash\n(.*?)```", text, re.S) if " exec " in b]
bad = [b for b in blocks if "< /dev/null" not in b or "timeout " not in b]
print(f"{len(blocks)} exec block(s), {len(bad)} without stdin closed and a timeout")
sys.exit(1 if bad or not blocks else 0)
PY
```
