# bypass-test — critic

Every case is reproducible with one command. The criterion is single: **before the gate it passed, now
it must fail.** Cases 1-3 are the three failures measured in the field, not hypotheses.

```bash
mkdir -p /tmp/critic-artifact
printf 'actual artifact line\n' > /tmp/critic-artifact/a.md
```

## The baseline these cases reproduce

Three identical runs of bare Opus on the same artifact (one skill-census row), 2026-08-21,
identical prompt and no format hint. All three found the real defects. None
passed the cases below.

## Case 1 — report without an account (0/3 passed it)

A report with real findings and no `ledger`: the critic does not say what it opened or what it
accepted on trust.

```bash
cat > /tmp/bypass-1.json <<'JSON'
{"artifact":"census-row","contract":"row must match the file it measures",
 "findings":[{"claim":"the row describes a file it does not measure","severity":"important",
 "evidence":{"path":"plan-eng-review/SKILL.md","line":1015,"quote":"Read sections/review-sections.md"}}]}
JSON
python3 scripts/critic_gate.py --validate /tmp/bypass-1.json   # atteso: exit 1, "ledger: missing"
```

## Case 2 — plausible finding never falsified (3/3 produced it)

Complete ledger, quote present, but no counter-argument attempted. It is the exact shape of the three
bare runs.

```bash
python3 - <<'PY' > /tmp/bypass-2.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"c","ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[{"claim":"x","severity":"minor","contract_quote":"c","evidence":{"path":"a.md","line":1,"quote":"actual artifact line"}}],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-2.json   # atteso: exit 1, "falsification: missing"
```

## Case 3 — unquoted finding, downgraded instead of discarded

This is the defect **verified in the donor**: the donor skill forces an unquoted finding to confidence `4-5`
claiming it is suppressed, but its table shows `5-6` «with caveat», so a finding at 5 reaches
the user anyway. Here there is no band.

```bash
python3 - <<'PY' > /tmp/bypass-3.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"c","ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[{"claim":"x","severity":"critical","contract_quote":"c","evidence":{"path":"a.md","line":1,"quote":"  "},
   "falsification":{"counter":"maybe fine","survived":True,"why":"checked"}}],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-3.json   # atteso: exit 1, "unquoted is not a finding"
```

## Case 4 — silent zero findings

«Looks fine» without saying so. It is the loophole the donor skill leaves open: all the specialists can
return `NO FINDINGS` and the run proceeds to `clean` without anyone declaring it.

```bash
python3 - <<'PY' > /tmp/bypass-4.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"c","ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-4.json   # atteso: exit 1, "zero findings must be declared"
```

Zero **declared** findings do pass instead, and that is intended: non-empty `halt.reason` → exit 0.

## Case 5 — finding that did not survive its own counter-argument

The critic attempts falsification, the counter-argument holds, and it reports the finding anyway.

```bash
python3 - <<'PY' > /tmp/bypass-5.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"c","ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[{"claim":"x","severity":"minor","contract_quote":"c","evidence":{"path":"a.md","line":1,"quote":"actual artifact line"},
   "falsification":{"counter":"the section is inlined elsewhere","survived":False,"why":"and it is"}}],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-5.json   # atteso: exit 1, "did not survive"
```

## Case 6 — unreadable input that must not pass as green

Missing file, empty file, or broken JSON: **exit 2**, never exit 0. A gate that cannot read does not approve.

```bash
python3 scripts/critic_gate.py --validate /tmp/does-not-exist.json   # atteso: exit 2, "UNUSABLE"
printf '   ' > /tmp/bypass-6.json && python3 scripts/critic_gate.py --validate /tmp/bypass-6.json
printf '{nope'  > /tmp/bypass-6.json && python3 scripts/critic_gate.py --validate /tmp/bypass-6.json
```

## Case 7 — invented quote or contract clause

The gate rereads both `evidence.path:line` and `contract_quote`. A plausible sentence that is absent
from the artifact or the contract must fail.

```bash
python3 - <<'PY' > /tmp/bypass-7.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"must preserve the exact line",
   "ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[{"claim":"x","severity":"important","contract_quote":"invented requirement",
   "evidence":{"path":"a.md","line":1,"quote":"invented artifact line"},
   "falsification":{"counter":"maybe present","survived":True,"why":"claimed"}}],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-7.json   # exit 1, both quotes rejected
```

## B8 — relative artifact resolved from the caller's cwd

The selfcheck writes report and artifact together, then invokes the gate from an empty sibling cwd. The
previous version looks for `artifact/` in the cwd and fails; the current gate resolves it from the report.

## What this gate does NOT block — declared

- **A lied-about ledger.** `opened` can list a file the critic did not really read: the
  script verifies the presence of the field, not the reading. Closing this half requires
  instrumenting the tool calls, out of scope for a gate that decides in milliseconds.
- **A façade falsification.** A non-empty `counter` and `survived: true` can be written even
  without having thought. The gate imposes that the step exists and is visible to the reader, not that it was
  done well — that is judged by T3, not by a script.
- **Lied-about runtime provenance.** The gate verifies files and lines, it cannot prove that the model
  really executed the declared tool calls; the fresh T3 remains the authority on that step.

```bash
python3 scripts/critic_gate.py --selfcheck   # 24 branches, including ignorance and relocation
```
