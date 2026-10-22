# Bypass-test — the test that must FAIL if a gate is worked around

Each block: the adversarial input, the exact command, and the outcome that
proves the gate held: without it, the skill is declared, not proofed. Every command below runs
from `pol-ship/`.

## 1. Redaction — a live-looking secret must block, a placeholder must not

```bash
echo 'AWS_KEY="AKIAABCDEFGHIJKLMNOP"' | python3 scripts/redact_scan.py --stdin
echo $?   # MUST be 1 (status BLOCKED)

echo 'AWS_SECRET_ACCESS_KEY="your-key-here"' | python3 scripts/redact_scan.py --stdin
echo $?   # MUST be 0 (status CLEAN) — a placeholder is not a false-positive block
```
If someone "fixes" a noisy scanner by widening the placeholder filter until it
swallows real secrets too, the first command starts returning 0. That is the
failure this test exists to catch — rerun it after any change to
`PLACEHOLDER_TOKENS` or the entropy filter in `redact_scan.py`.

## 2. Version bump — drift must stop the pipeline, not warn and continue

```bash
python3 scripts/version_bump.py --selfcheck
```
Asserts, among other branches, that a version file changed to a value
matching **neither** the last tag's value **nor** the value the conventional
commits since that tag imply exits `1` (`DRIFT_UNEXPECTED`), and that two
version files disagreeing with each other exits `1` (`DRIFT_STALE_PKG`). If
someone changes either branch to `return 0`, this selfcheck fails on the
`assert r["exit"] == 1` lines — that is the point.

## 3. Changelog — never a blind write

```bash
printf '# Changelog\nnothing here\n' > /tmp/CHANGELOG.md
python3 scripts/changelog_edit.py --file /tmp/CHANGELOG.md --bullet "- x"
echo $?                              # MUST be 2 (NO_ANCHOR)
diff /tmp/CHANGELOG.md <(printf '# Changelog\nnothing here\n')
echo $?                              # MUST be 0 — file byte-identical, untouched
```
A version of this script that falls back to appending at end-of-file "to be
helpful" when the anchor is missing passes silently and corrupts the
changelog's structure — this is exactly the failure mode `document-release`
was built to avoid ("never `Write`, only `Edit` at an exact match").

## 4. Merge safety — the flagship gate (closes G7#1)

```bash
echo '{"state":"OPEN","mergeable":"CONFLICTING","mergeStateStatus":"DIRTY"}' \
  | python3 scripts/merge_gate.py decide --pr-json -
# MUST report verdict "BLOCKED_CONFLICT", never "READY"

python3 scripts/merge_gate.py --selfcheck
```
The selfcheck's `r4`/`r5` cases are the ones that matter: a merge attempt
that returns non-zero is followed by exactly one requery and **zero**
further `gh pr merge` calls, in both the "actually merged" and "actually
still open" outcomes (`calls4["merge"] == 1`, `calls5["merge"] == 1`). A
version of `execute()` that retries on failure — the literal bug this gate
exists to prevent (cli/cli#3442, cli/cli#13380) — makes those assertions
fail because the fake `merge_fn` gets called twice.

**Adversarial variant to run by hand**: point `execute()`'s `merge_fn` at a
stub that always returns 1 and counts its own calls; confirm the count stays
at 1 no matter how many times `execute()` is invoked in the same process —
a caller-side retry loop wrapping `execute()` itself would defeat this at a
layer this script cannot see. That risk is structural, not closed by this
script: **the calling agent must not loop-retry `merge_gate.py execute`** —
document this constraint wherever `ship` Phase B is invoked from.

## 5. Canary — debounce must not swallow OR over-trigger

```bash
python3 scripts/canary_check.py --selfcheck
```
Proves: a single changed check does not alert (`consecutive_fail == 1,
alert == False`) — no page on a network blip. The second consecutive changed
check does alert (`consecutive_fail == 2, alert == True`) — a real outage is
not silently absorbed. A version that alerts on the first blip fails the
first assertion; a version that never alerts (debounce threshold raised
without bound, or comparison logic inverted) fails the second.

**Known residual bypass, not closed here**: `consecutive_fail` lives in
`.ship/canary-state.json`. Deleting that file between the two failing checks
resets the counter to 0 and the alert never fires, even though the outage is
real and ongoing. Mitigation direction (not built in this pass): commit
`.ship/canary-state.json` so its deletion shows up as a tracked diff that
`git-power`'s parked-work census would surface — out of scope for this skill
alone, and declared here instead of hidden.

## 6. Deploy drift — commits-behind must be counted, not asserted

```bash
python3 scripts/canary_check.py --selfcheck
```
Same run covers `drift`: two identical SHAs report `drift: false`; two SHAs
two commits apart in a real temp git repo report `commits_behind: 2` exactly
— not `null`, not `True`/`False` alone. A version that only reports the
boolean without the count would still pass casually but degrades exactly the
G4-voice-3 finding ("prod is stale" without a magnitude is not actionable) —
run the assertion, don't eyeball the JSON.

## The hook in front of `gh pr` (added 2026-10-18)

`python3 tests/hook_bypass.py` (from the skill folder, vault only) sends three payloads to `scripts/pre_tool_hook.py` inside a
throwaway git repo: a raw merge, an inline body no checker ever read, and a body file naming no
issue and no verdict. Each must exit 2; a `BYPASS:` line means the hook let it through.

**Declared limit, not a hole.** The hook is a tripwire on the default spelling of
`gh pr create|new|ready|edit|merge`, not a security boundary. It does NOT cover a `gh` call inside a
shell wrapper (`bash -c "gh pr create …"`, `sh -c`, `eval`, a subshell) nor `gh api` REST/GraphQL
calls other than the merge endpoints: those pass, and
`tests/test_pre_tool_hook_pr.py::test_declared_limit_a_wrapped_create_passes_and_is_documented`
keeps this paragraph and that behaviour together. The binding control is `pol-babysit` reading from
the PR the owner's label bound to the head SHA, plus branch protection on the server.

## Running everything at once

```bash
for f in scripts/*.py; do echo "== $f =="; python3 "$f" --selfcheck || echo "FAILED: $f"; done
python3 ../_standard/validate_suite.py .   # structural gate: frontmatter, bypass-test file, MAX_LINES, chain
```
Any `FAILED` line, or a non-zero exit from `validate_suite.py`, means this
skill is not blindata — it stays `status: draft`.

## 7. Verification window — a missing metric must never advance

`fails_before:` pol-ship 2.0.1 had no window: after the production deploy the canary watched
health only, so a doubled error rate on a healthy endpoint passed as ADVANCE by omission.

```bash
printf '{"health_ok":true,"error_rate":0.01,"p95_ms":400}' > /tmp/b.json
printf '{"health_ok":true,"error_rate":0.03,"p95_ms":400}' > /tmp/n.json
python3 scripts/canary_check.py verdict --baseline /tmp/b.json --now /tmp/n.json; echo "exit=$?"
# expected: ROLLBACK proposed — error_rate 0.01 -> 0.03 (3.00x, limit 2.0x) · exit=1
printf '{"health_ok":true,"error_rate":0.01}' > /tmp/n.json
python3 scripts/canary_check.py verdict --baseline /tmp/b.json --now /tmp/n.json; echo "exit=$?"
# expected: HOLD — UNKNOWN p95_ms · exit=3
```
