---
title: babysit — bypass-test (the status must never say READY for a PR an owner cannot trust)
description: Six inputs that must not read READY; an unreachable gh must exit 2. Runs pr_status.py on synthetic snapshots, no network.
status: active
---

# Bypass-test

CI runs this block as written: `tests/test_pr_status_b1.py::test_b2_the_bypass_test_reference_runs_and_holds`
extracts it and fails on any `BYPASS:` line or a non-zero exit. A declared proof nothing runs is no proof.

```bash
#!/usr/bin/env bash
set -u
D="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts"
python3 - "$D" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import pr_status as ps
head = "a" * 40
ok = {"state": "OPEN", "headRefOid": head, "mergeable": "MERGEABLE", "statusCheckRollup": [
      {"name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS", "startedAt": "2026-01-01T00:00:00Z"}]}
rec = {"user": {"login": "me"}, "body": f"<!-- real-test v1 sha={head} verdict=MERGEABLE -->\nambiente: staging"}
def v(**k):
    base = dict(pr=ok, threads=[], comments=[rec], reviews=[], viewer="me", now="2026-02-01T00:00:00Z", ignore={},
                label=None, body_errors=[], changed_since={}, inert=[], env="staging")
    return ps.summarize(**(base | k))["verdict"]
bad = {
 "no receipt": v(comments=[]),
 "receipt by someone else": v(comments=[rec | {"user": {"login": "bot"}}]),
 "receipt on another head": v(pr=ok | {"headRefOid": "b" * 40}),
 "red check undeclared": v(pr=ok | {"statusCheckRollup": [ok["statusCheckRollup"][0] | {"conclusion": "FAILURE"}]}),
 "label on an older head": v(label={"sha": "c" * 40}),
 "no checks reported": v(pr=ok | {"statusCheckRollup": []}),
}
leaks = [k for k, val in bad.items() if val == "READY"]
print("\n".join(f"BYPASS: {k}" for k in leaks))
sys.exit(1 if leaks or v() != "READY" else 0)
PY
r=$?
GH_HOST=nonexistent.invalid python3 "$D/pr_status.py" 999999 >/dev/null 2>&1
[ $? -eq 2 ] || { echo "BYPASS: no data did not exit 2"; r=1; }
exit $r
```
