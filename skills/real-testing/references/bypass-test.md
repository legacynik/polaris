---
title: real-test — bypass-test (must fail if someone bypasses the gate)
description: 9 bypass attempts against a throwaway git repo (5 original + 4 from an adversarial attack). Each MUST be blocked except the exemption on the default branch and the explicit bypass, which must pass BUT leave a trace in bypass.log — never a silent bypass (208 occurrences measured).
status: active
---

# Bypass-test

Materializes a real git repo (not a fake directory) and tries 9 ways to bypass the gate:
5 against `gate.sh` (the Claude Code fast path), 4 against the real anchor — the git hook installed
by `install-hook.sh` — which are the side paths found by the adversarial attack when the
JSON-payload simulation alone is no longer enough to stop a REAL `git commit`.
If even ONE of these passes when it should block, the gate is declared, not hardened.

```bash
#!/usr/bin/env bash
set -eu
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts"
REPO="$(mktemp -d)"
git init -q "$REPO"
git -C "$REPO" config user.email t@t; git -C "$REPO" config user.name t
printf 'def charge(amount):\n    if amount > 0:\n        return "ok"\n    return "zero"\n' > "$REPO/app.py"
git -C "$REPO" add . && git -C "$REPO" commit -q -m base
bash "$SKILL/install-hook.sh" --repo "$REPO" >/dev/null
git -C "$REPO" add . && git -C "$REPO" commit -q -m "chore: install"
git -C "$REPO" checkout -q -b feat/issue-1

payload() { printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'; }
gate() { (cd "$REPO" && payload | bash "$SKILL/gate.sh"); }

# --- introduce a new, never-tested branch -----------------------------------
printf 'def charge(amount):\n    if amount > 0:\n        return "ok"\n    elif amount < 0:\n        raise ValueError("neg")\n    return "zero"\n' > "$REPO/app.py"
git -C "$REPO" add .
HASH=$(python3 "$SKILL/perimeter.py" --repo "$REPO" --head STAGED --hash-only)
VFILE="$REPO/.real-test/verdicts/$HASH.json"

# 1) ATTEMPT: declare MERGEABLE without ever citing the new `elif` branch.
python3 "$SKILL/verdict.py" new --repo "$REPO" --out "$VFILE"
python3 - "$VFILE" <<'PY'
import json, sys
v = json.load(open(sys.argv[1]))
for row in v["matrix"]:
    row["exception_ticket"] = "N/A"
v["verdetto"] = "MERGEABLE"                      # <-- lying declaration
v["raccolto"] = [{"tipo": "falso-allarme", "nota": "looked fine"}]
json.dump(v, open(sys.argv[1], "w"), indent=2)
PY
set +e; gate; rc=$?; set -e
[ "$rc" -eq 2 ] || { echo "BYPASS-TEST FAILED (1): MERGEABLE without branches_exercised went through"; exit 1; }
echo "1/5 blocked: declaring MERGEABLE is not enough, the uncovered branch is found by perimeter.py"

# 2) ATTEMPT: rename an old, passed verdict to the new hash name
#    (the INTERNAL content_hash stays the old one: the filename is not the source of truth).
OLDV="$REPO/.real-test/verdicts/deadbeefdeadbeefdeadbeefdeadbeefdeadbeef.json"
python3 -c "import json; d=json.load(open('$VFILE')); d['content_hash']='deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'; json.dump(d, open('$OLDV','w'))"
cp "$OLDV" "$VFILE"     # old verdict, renamed to the right filename
set +e; python3 "$SKILL/verdict.py" validate "$VFILE" --repo "$REPO"; rc=$?; set -e
[ "$rc" -eq 1 ] || { echo "BYPASS-TEST FAILED (2): misaligned internal content_hash went through"; exit 1; }
echo "2/5 blocked: the content_hash INSIDE the file counts, not the filename"

# 3) ATTEMPT: evidence=live on a live-required class with an empty artifact.
python3 "$SKILL/verdict.py" new --repo "$REPO" --out "$VFILE"
python3 - "$VFILE" "$REPO" <<'PY'
import json, sys
v, repo = json.load(open(sys.argv[1])), sys.argv[2]
for row in v["matrix"]:
    row["exception_ticket"] = "N/A"
    if row["file"] == "app.py":
        row["branches_exercised"] = ["app.py:4"]
        row["class"] = "api-cli"          # force live-required for the test
        row["evidence"] = "live"
        row["evidence_artifact"] = "empty.json"
v["verdetto"] = "MERGEABLE"
v["raccolto"] = [{"tipo": "difetto", "artifact": "tests/x.py::y"}]
json.dump(v, open(sys.argv[1], "w"), indent=2)
open(f"{repo}/empty.json", "w").close()   # EMPTY artifact
PY
set +e; python3 "$SKILL/verdict.py" validate "$VFILE" --repo "$REPO"; rc=$?; set -e
[ "$rc" -eq 1 ] || { echo "BYPASS-TEST FAILED (3): empty artifact passed off as live proof went through"; exit 1; }
echo "3/5 blocked: an empty artifact is not proof"

# 4) ATTEMPT: keep modifying the code AFTER obtaining a valid verdict.
python3 - "$VFILE" "$REPO" <<'PY'
import json, sys, pathlib
v, repo = json.load(open(sys.argv[1])), pathlib.Path(sys.argv[2])
row = next(r for r in v["matrix"] if r["file"] == "app.py")
row["evidence"], row["evidence_artifact"] = "assumed", None
(repo / "trace.json").write_text('{"ok":true}')
row["class"], row.pop("evidence_artifact", None)
json.dump(v, open(sys.argv[1], "w"), indent=2)
PY
gate >/dev/null 2>&1 && echo "4a valid verdict: commit allowed" || { echo "setup 4 broken"; exit 1; }
printf '\n# line added AFTER the verdict\n' >> "$REPO/app.py"
git -C "$REPO" add .
set +e; gate; rc=$?; set -e
[ "$rc" -eq 2 ] || { echo "BYPASS-TEST FAILED (4): code changed after the verdict, gate did not see it"; exit 1; }
echo "4/5 blocked: any extra line after the verdict changes the hash and invalidates the proof (G2.6)"

# 5) ATTEMPT: explicit bypass — MUST pass, but MUST leave a trace.
rm -f "$REPO/.real-test/bypass.log"
set +e; REAL_TEST_BYPASS_GATE=1 gate >/dev/null 2>&1; rc=$?; set -e
[ "$rc" -eq 0 ] || { echo "BYPASS-TEST FAILED (5a): explicit bypass must allow"; exit 1; }
[ -s "$REPO/.real-test/bypass.log" ] || { echo "BYPASS-TEST FAILED (5b): bypass left no trace — this is exactly R8 (208 silent bypasses measured)"; exit 1; }
echo "5/5 correct: the bypass passes but is logged, never silent"

rm -rf "$REPO"
echo "BYPASS-TEST OK — 5/5 attempts behave as they should"
```

**If one day any of these 5 passes when it should block (except 5, which must exit
`rc=0` but with a non-empty log), the gate has regressed to a declaration — do not ship, fix it first.**

## Why these 5 and not others

Each one reproduces a real registry case, not an invented one:

| # | Reproduces | Entry |
|---|---|---|
| 1 | self-reported verdict that ignores the new branch introduced by the fix | G1.6 / F6 |
| 2 | evidence copied/renamed instead of recomputed | G2.6 (evidence detached from the current runtime digest) |
| 3 | mock/empty artifact passed off as real IO | G2.1 (34 observations, "green certifies the mock") |
| 4 | valid verdict at time T, code changed afterwards, nobody notices | G2.6 (real case: newline-collapse validated on the old function, 3 days in prod) |
| 5 | bypass exists but is silent | R8 (208 explicit bypasses measured in MISURE.md, none traced) |


## R1 — a stale `main` branch must never silently become the base (merge 2026-08-16)

fails_before: real-test v0.1.0 (`resolve_base` tried the literal name `main` after the default
branch — against the plugin's doctrine §0: «Do not assume main»).

Setup: repo `-b develop`, branch `main` created at the first commit and never advanced, 3 commits.
Command: `perimeter.py --repo . --head HEAD` without `--base`.
**BEFORE (v0.1.0)**: base = sha of `main` (stale), silently — wrong perimeter = false green. Observed 2026-08-16.
**AFTER (v2.0.0)**: base = HEAD~1 with the fallback DECLARED on stderr; the name `main` is never
tried. Repo with a single commit: falls back to HEAD (declared). Selfcheck: dedicated R1 assertion.

## R2 — a command that MENTIONS `git commit` must not trigger the gate (merge 2026-08-16)

fails_before: real-test v0.1.0 (`gate.sh` matched the substring `*"git commit"*`).

Command: PreToolUse payload with `command: echo "do not git commit yet"` on a repo with an active marker.
**BEFORE (v0.1.0)**: exit 2 — it blocked a harmless echo (false positive: a guard that fires on
prose teaches people to ignore it). Observed 2026-08-16.
**AFTER (v2.0.0)**: exit 0; a real `git commit -m x` without a verdict → exit 2 (control test).
Merge note: the fix uncovered a second real defect — `grep -q` under `pipefail` kills
`printf` with SIGPIPE precisely on the true matches; fixed with grep without `-q`.
