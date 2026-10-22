# bypass-test — crasher

One criterion: **it passed before this door existed, and now it must fail.** Every case is one
command. Run them from `crasher/`.

The baseline is the crasher as it stood on the abandoned `feat/crasher-skill` branch (closed): it drove the app and printed a transcript. Nothing in it refused a verdict, and nothing
gave a finding a stable identity — so both of the failures below were legal.

```bash
cd crasher
```

## Case 1 — "no crash found" after visiting nothing

The shape an unattended run degrades into: the driver dies at login, the loop finds nothing to
report, and the run announces a healthy app. The old crasher printed exactly this.

```bash
python3 - <<'PY' > /tmp/crasher-b1.json
import json; print(json.dumps({"target":"https://staging.example.invalid","budget":8,
 "surface":["/","/login","/items"],"attempted":[],"findings":[]}))
PY
python3 scripts/crash_report.py --run /tmp/crasher-b1.json   # expected: exit 1, "no path attempted"
```

## Case 2 — a run that ignored its own budget

The record's `budget` is what bounds an unattended run, written before the drive starts. A run that
visited more than it was authorised to visit is not the run that was authorised, and its verdict
does not stand.

```bash
python3 - <<'PY' > /tmp/crasher-b2.json
import json; print(json.dumps({"target":"https://staging.example.invalid","budget":2,
 "surface":["/","/a","/b","/c"],"attempted":["/","/a","/b","/c"],"findings":[]}))
PY
python3 scripts/crash_report.py --run /tmp/crasher-b2.json   # expected: exit 1, "budget exceeded"
```

## Case 2b — coverage with no denominator

The subtler half of case 1, and the one that reads as a pass: the run visited three paths and does
not say out of how many. An earlier version defaulted the surface to whatever was attempted and
printed `coverage 3/3` — a perfect score over a sample the run itself chose.

```bash
python3 - <<'PY' > /tmp/crasher-b2b.json
import json; print(json.dumps({"target":"https://staging.example.invalid","budget":8,
 "attempted":["/","/a","/b"],"findings":[]}))
PY
python3 scripts/crash_report.py --run /tmp/crasher-b2b.json  # expected: exit 1, "surface undeclared"
```

## Case 3 — the same crash filed twice

The duplicate this door exists to prevent. Two runs, one week apart, one hang: the only thing that
moved is the number of seconds. The old title carried the symptom verbatim, so the tracker search
found nothing and a second issue opened.

```bash
python3 - <<'PY'
import importlib.util, sys
s = importlib.util.spec_from_file_location("cr", "scripts/crash_report.py")
cr = importlib.util.module_from_spec(s); s.loader.exec_module(cr)
a = {"route": "/items/new", "klass": "gen_hang", "symptom": "no result after 421s"}
b = {"route": "/items/new", "klass": "gen_hang", "symptom": "no result after 388s"}
print(cr.title_of(a)); print(cr.title_of(b))
sys.exit(0 if cr.title_of(a) == cr.title_of(b) else 1)
PY
# expected: two identical titles -> issue-contract's apply gate blocks the second
```

## Case 4 — two different failures collapsed into one issue

The opposite error, and it must NOT happen: a hang and a console flood on the same route are two
findings. If this prints one title twice, the fingerprint is too coarse and the door is hiding a
bug.

```bash
python3 - <<'PY'
import importlib.util, sys
s = importlib.util.spec_from_file_location("cr", "scripts/crash_report.py")
cr = importlib.util.module_from_spec(s); s.loader.exec_module(cr)
a = {"route": "/items/new", "klass": "gen_hang", "symptom": "no result"}
b = {"route": "/items/new", "klass": "console", "symptom": "no result"}
sys.exit(0 if cr.title_of(a) != cr.title_of(b) else 1)
PY
# expected: exit 0, two distinct titles
```

## Case 5 — a nameless finding

A finding with no route or no symptom has no identity, so it files again on every run. Refused
before it reaches the tracker.

```bash
python3 - <<'PY' > /tmp/crasher-b5.json
import json; print(json.dumps({"target":"https://staging.example.invalid","budget":4,
 "surface":["/"],"attempted":["/"],"findings":[{"klass":"console"}]}))
PY
python3 scripts/crash_report.py --run /tmp/crasher-b5.json   # exit 1, "finding without route, symptom, domain"
```

## Case 6 — a transcript sold as a reproducing command

A finding with no `repro` must not be handed to an unattended agent. The old flow filed everything
the same way, so a transcript-only finding was claimable and the agent had nothing to run.

```bash
python3 - <<'PY' > /tmp/crasher-b6.json
import json; print(json.dumps({"target":"https://staging.example.invalid","budget":4,
 "surface":["/"],"attempted":["/"],"findings":[{"route":"/x","klass":"console","domain":"gates",
 "symptom":"twelve errors on load","evidence":"t.log"}]}))
PY
python3 scripts/crash_report.py --run /tmp/crasher-b6.json | grep -- "--afk no"
# expected: exit 3 from the report, and the printed invocation carries --afk no
```

## Case 6b — an invocation the tracker door would have rejected

The one the first version of this door shipped, and the one a grep could never catch. The printed
argv named `build_issue.py`, so the test passed; run it and the contract refused it, because B9
requires **two** adversarial tests and only one was emitted. The finding never reached the tracker.

```bash
python3 - <<'PY'
import importlib.util, sys, pathlib
s = importlib.util.spec_from_file_location("cr", "scripts/crash_report.py")
cr = importlib.util.module_from_spec(s); s.loader.exec_module(cr)
argv = cr.issue_argv({"route": "/x", "klass": "console", "symptom": "twelve errors on load",
                      "domain": "gates"}, "o/r")
print("adversarial tests:", sum(1 for a in argv if a == "--adv-test"))
print("domain:", repr(argv[argv.index("--domain") + 1]))
sys.exit(0 if sum(1 for a in argv if a == "--adv-test") >= 2 else 1)
PY
# expected: 2 adversarial tests. The executed proof is
# tests/test_crash_report.py::TheInvocationIsAcceptedByIssueContract, which runs build_issue.py.
```

## Case 6c — a domain invented to satisfy the label

`frontend` is not in every repository's glossary, and B12 refuses a label the glossary does not
hold. The first version defaulted to it, so an API finding filed as frontend wherever the label
happened to exist, and was rejected wherever it did not.

```bash
python3 - <<'PY' > /tmp/crasher-b6c.json
import json; print(json.dumps({"target":"https://staging.example.invalid","budget":4,
 "surface":["/"],"attempted":["/"],"findings":[{"route":"/x","klass":"console",
 "symptom":"twelve errors on load"}]}))
PY
python3 scripts/crash_report.py --run /tmp/crasher-b6c.json  # expected: exit 1, "finding without domain"
```

## Case 7 — unreadable input read as a green

Absent file, empty file, broken JSON, a JSON array instead of an object. A gate that cannot read
does not approve.

```bash
python3 scripts/crash_report.py --run /tmp/does-not-exist.json   # expected: exit 2
printf '   '   > /tmp/crasher-b7.json && python3 scripts/crash_report.py --run /tmp/crasher-b7.json
printf '{nope' > /tmp/crasher-b7.json && python3 scripts/crash_report.py --run /tmp/crasher-b7.json
printf '[]'    > /tmp/crasher-b7.json && python3 scripts/crash_report.py --run /tmp/crasher-b7.json
```

## What this door does NOT block — declared

- **A fabricated run record.** `attempted` can list paths the browser never opened; the script
  checks the claim's shape, not the browsing. Closing that means having the driver emit the record
  itself, which is a change to the driver, not to this gate.
- **A host template this door has never seen.** The invocation carries the founder contract and
  the `--field` ids the Polaris issue forms use. A repository whose template asks for other
  required fields is told which by `build_issue.py`, and the run adds them; nothing here reads
  that template in advance.
- **A badly classified finding.** Flaky-versus-real is judgement. The gate refuses a nameless or
  unbudgeted run; it cannot refuse a wrong one.
- **A finding invented outright.** Nothing here re-executes the reproducing command. `bugfix`'s own
  gate does that at the other end of the handover, and that is where it belongs.

```bash
python3 scripts/crash_report.py --selfcheck   # 13 branches, offline
```
