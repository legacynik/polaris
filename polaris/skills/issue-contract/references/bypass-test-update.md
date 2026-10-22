# Bypass-test — must FAIL

Adversarial attempts to promote an item, close it, or open a new one without doing the work the
gate requires. Every one of these **must exit non-zero** (BLOCKED). If any prints `ALLOW` or
exits 0, the gate is decorative — G2 (122 observations: "required-but-structural", `|| true`,
approves-when-unsure) reproduced inside this skill.

Run from `issue-contract/`:

```bash
# No `set -e`: every call below is EXPECTED to return non-zero — that's what's under test.
T=$(mktemp -d)
fail() { echo "GATE FAILED — $1"; exit 1; }

# 1) Skip the redundancy-check entirely, promote straight to ready-for-agent.
printf '{"assignee": null, "linked_active_workstream": false}' > "$T/issue.json"
python3 scripts/transition_gate.py --to ready-for-agent --issue-json "$T/issue.json"
[ "$?" -eq 0 ] && fail "bypass #1 (no redundancy-check) succeeded"

# 2) Fake compliance: a redundancy-check file that has 'Searched:' but no 'Found:'.
printf 'Searched: nowhere in particular\n' > "$T/fake.md"
python3 scripts/transition_gate.py --to ready-for-agent --issue-json "$T/issue.json" \
  --redundancy-file "$T/fake.md"
[ "$?" -eq 0 ] && fail "bypass #2 (malformed redundancy-check) succeeded"

# 2b) A near-empty 'Searched:' (one char) — the floor a trivial non-answer can't clear.
printf 'Searched: x\nFound: no\n' > "$T/toothin.md"
python3 scripts/transition_gate.py --to ready-for-agent --issue-json "$T/issue.json" \
  --redundancy-file "$T/toothin.md"
[ "$?" -eq 0 ] && fail "bypass #2b (1-char Searched:) succeeded"

# 3) Free-pick collision: issue already assigned, try to promote anyway.
printf 'Searched: codebase + open issues\nFound: no\n' > "$T/red.md"
printf '{"assignee": "someone-else", "linked_active_workstream": false}' > "$T/taken.json"
python3 scripts/transition_gate.py --to ready-for-agent --issue-json "$T/taken.json" \
  --redundancy-file "$T/red.md"
[ "$?" -eq 0 ] && fail "bypass #3 (free-pick on assigned issue) succeeded"

# 3b) Skip --issue-json entirely — "eligible" via absence of any data to check.
python3 scripts/transition_gate.py --to ready-for-agent --redundancy-file "$T/red.md"
[ "$?" -eq 0 ] && fail "bypass #3b (no --issue-json at all) succeeded"

# 3c) --issue-json present but missing the 'assignee' key — not the same as a verified null.
printf '{"linked_active_workstream": false}' > "$T/noassignee.json"
python3 scripts/transition_gate.py --to ready-for-agent --issue-json "$T/noassignee.json" \
  --redundancy-file "$T/red.md"
[ "$?" -eq 0 ] && fail "bypass #3c (assignee key absent) succeeded"

# 4) Poisoning: close as already-implemented but still hand it an out-of-scope
#    file — must be refused, or future dedup checks would carry a false rejection.
printf '# X\n**Decision:** reject\n**Prior requests:**\n- #1\n' > "$T/oos.md"
python3 scripts/transition_gate.py --to wontfix --redundancy-file "$T/red.md" \
  --reason already-implemented --out-of-scope-file "$T/oos.md"
[ "$?" -eq 0 ] && fail "bypass #4 (poisoned already-implemented) succeeded"

# 5) wontfix with NO --reason at all — used to ALLOW silently and skip every
#    check below it (no .out-of-scope requirement, no category cross-check).
python3 scripts/transition_gate.py --to wontfix --redundancy-file "$T/red.md"
[ "$?" -eq 0 ] && fail "bypass #5 (wontfix with no --reason) succeeded"

# 6) Reason auto-declared, never verified: close an ENHANCEMENT as rejected-bug
#    to dodge the .out-of-scope requirement rejected-enhancement carries.
printf '{"category": "enhancement"}' > "$T/enh.json"
python3 scripts/transition_gate.py --to wontfix --redundancy-file "$T/red.md" \
  --reason rejected-bug --out-of-scope-file "$T/oos.md" --issue-json "$T/enh.json"
[ "$?" -eq 0 ] && fail "bypass #6 (reason=rejected-bug contradicts verified category=enhancement) succeeded"

# 6b) Same trick without even a --issue-json to contradict — unverifiable, must still BLOCK.
python3 scripts/transition_gate.py --to wontfix --redundancy-file "$T/red.md" \
  --reason rejected-bug --out-of-scope-file "$T/oos.md"
[ "$?" -eq 0 ] && fail "bypass #6b (rejected-bug with no issue-json to verify against) succeeded"

# 7) F10 — open a new issue that duplicates one already open, no acknowledgment.
printf '[{"number": 7, "title": "Dark mode support"}]' > "$T/open.json"
python3 scripts/transition_gate.py --to new-issue --concept "dark mode support" \
  --open-issues-json "$T/open.json"
[ "$?" -eq 0 ] && fail "bypass #7 (duplicate concept, no --override) succeeded"

# 7b) Skip --open-issues-json entirely — "no duplicate" via never having looked.
python3 scripts/transition_gate.py --to new-issue --concept "dark mode support"
[ "$?" -eq 0 ] && fail "bypass #7b (new-issue with no --open-issues-json) succeeded"

# 8) Call the module directly in Python, bypassing argparse/run()/main() altogether —
#    the exact shape of the corpus finding ("a gate that only fires through main()").
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import transition_gate as t
code, label, errs = t.decide('ready-for-agent', issue_json='$T/issue.json')  # no redundancy_file
assert code != 0 and label is None, 'direct decide() call let a promotion through with no redundancy-check'
assert not hasattr(t, 'resolve_label'), 'checks-free resolve_label() shortcut still exists'
print('direct-import path: still BLOCKED, as required')
" || fail "bypass #8 (direct function-call bypass) succeeded"

rm -rf "$T"
echo "BYPASS-TEST OK — all 14 adversarial attempts were blocked, as required"
```

Equivalent (and wider) coverage lives in `scripts/transition_gate.py --selfcheck` (24 branches,
including all of the above plus the 6 legitimate-ALLOW paths and the `--apply`/mutation-coupling
proof, which needs Python-level monkeypatching of `mutate()` and so can't be a portable shell
one-liner — this file is the standalone, readable version any harness can run without trusting
the script's own self-report).

## What would make this pass for the wrong reason

If someone "fixes" a failing bypass attempt by adding a `--force`/`--skip-check` flag to
`transition_gate.py`, or by having the calling skill apply the label via `gh` regardless of the
script's exit code (reading `ALLOW`/`BLOCK` as advisory text instead of the exit code as the
gate), this test still catches it: the assertions above are on **process exit status**, not on
stdout content, and the SKILL.md instructs `--apply` as the only sanctioned path from decision to
mutation (never "read ALLOW off stdout and run `gh` yourself"). A skip-flag is a new attack
surface — if one is ever added, extend this file with a case that exercises it. There is no
`--force`/`--skip-check`/env-var backdoor in the script today (checked: `grep -n
"environ\|getenv" scripts/*.py` → 0 hits) — keep it that way.

## What this file does NOT close, on purpose, and why

- **Calling `gh issue edit` directly, never invoking this script at all.** `--apply` fuses
  decision and mutation *inside this tool*, so using it is safe by construction — but nothing in
  `issue-contract/` can force an agent to use the tool instead of typing the `gh` command by
  hand. Closing that needs a `PreToolUse`-style hook watching `gh issue edit` outside this skill's
  boundary (and a Claude-Code-only hook would break the self-contained/4-harness rule in
  `SKILL-STANDARD.md`). Documented as a known limit in `update-gate.md`, not silently declared fixed.
- **Whether a `Searched:`/`Found:`/`--concept` field is truthful, not just well-formed.** Case 2b
  raises the floor on trivial one-word non-answers; no text field can prove a search actually
  happened. Disclosed in `update-gate.md`, same limit the codebase-search half of G9#7 already lives
  with elsewhere in this suite.
