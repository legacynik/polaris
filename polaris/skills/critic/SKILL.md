---
name: critic
description: "◇ Polaris — Attack one artifact from fresh context: a plan before it is accepted, a decision record, a claim, or a diff that needs more than review. Only quoted, falsified findings survive; blocking ones go back to the author, only taste reaches the human. Use before accepting a plan or decision, or before relying on a claim. Requires python3. Not routine code review (review), merge verdicts (real-testing) or mechanical edits."
version: 0.3.3
user-invocable: true
auto: false
lifecycle: one .critic/<artifact-hash>.json per pass → caller validates it with critic_gate.py and drains it at its own gate
invokes: []
invoked-by: [human, architecture, apex-curate]
io: receives a materialized ARTIFACT directory plus CONTRACT, never the author's claim/reasoning/transcript → emits a validated JSON ledger with only quoted, falsified findings, each blocking or taste
status: active
---

# critic

## What it does

A fresh-context adversarial pass with one invariant: a plausible finding nobody verified does not
exist. The caller hands over only `ARTIFACT + CONTRACT`, never the author's conclusion, reasoning
or transcript. Every candidate must quote the contract clause it breaks and the artifact line
that breaks it, then survive its strongest counter-argument. `critic_gate.py` rereads every quote.

## When

What it attacks, and when it is worth its cost (operating model §10):

| Artifact | When | Work size |
|---|---|---|
| plan file | once, at the end of define, before `status: accepted` | medium, large |
| decision record (DEC) | once per record, before `accepted` | large |
| claim | before anyone relies on it (a census row, a "verified" line, another skill's output) | any |
| diff | when a non-mechanical change must be falsified beyond `review`'s audit | any |

Tiny work never pays for a critic.

## Steps

1. **Materialize.** Copy the artifact and every source it cites into one directory. Write the
   CONTRACT from the artifact's own promises: a plan's outcome and DoD, a DEC's three ADR tests
   and its `probe`, a claim's exact sentence. Nothing of the author's reasoning goes in.
2. **Dispatch.** A fresh-context agent from your harness, on the strongest model it has, runs
   OPEN → ATTACK → QUOTE → FALSIFY → FILTER → EMIT (`references/flow.md`). One invocation is
   one pass; it never loops on itself.
3. **Validate.** `python3 scripts/critic_gate.py --validate <report.json>`: 0 pass, 1 invalid
   report, 2 unusable input. Non-zero means the pass did not happen.
4. **Route.** `critical` and `important` findings are **blocking**: the author fixes them, and a
   plan or DEC is not accepted until each is fixed. `minor` findings are **taste**: the only part
   that reaches the human, who decides; they never block.
5. **Stop.** A plan or DEC gets one pass; its fixes are checked by the caller against the
   findings, not by a new pass. A claim or diff: at most three passes, then decompose. Two passes
   with findings and none accepted by the caller: stop, it is validation theater.

## Output

`.critic/<artifact-hash>.json` in the schema of `references/flow.md`, accepted by
`critic_gate.py`, plus one line: blocking count, taste count, or the concrete `halt.reason`.
Zero findings are valid only with that reason.
**Next:** blocking findings → back to the author (`plan-area` for a plan); none → ask the founder to accept, the taste findings as options.

## Where this goes

This skill produces: **review** — at the path the host's `outputs:` map gives that kind; with
no map, say once where you wrote.

## Not for

- Routine or finished-PR code review: `review`. Merge or release verdicts: `real-testing`.
- Mechanical edits, broad repository sweeps (`sweep`), or confirming a decision already made.
