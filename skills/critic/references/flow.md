---
title: critic — the pass, the halt rules and the report schema
description: OPEN, ATTACK, QUOTE, FALSIFY, FILTER, EMIT; when to halt; the exact JSON the gate validates. Moved from SKILL.md 0.2.4 unchanged in substance.
status: active
---

# The critic pass

## Flow

1. **OPEN** — read the materialized artifact and every source it names. Record paths in
   `ledger.opened`; declare deliberate omissions and accepted-but-unverified claims.
2. **ATTACK** — seek contract violations, omissions, assumptions, edge cases, hidden coupling and
   broken conventions.
3. **QUOTE** — every candidate carries the exact `contract_quote` it violates plus an
   artifact-relative `path`, one-based `line`, and verbatim `quote`. Never infer aliases, best
   practices, or safety goals the contract does not state. If either quote cannot be verified, drop
   the candidate.
4. **FALSIFY** — state the strongest counter-argument, try to make it hold, and report only findings
   that survive. Record killed candidates in `dropped[]`.
5. **FILTER** — before emitting, move every candidate with `survived != true`, an unverifiable
   artifact quote, or an unverifiable `contract_quote` to `dropped[]`; never retain it at a lower
   severity. If no findings survive, set `halt` to `{"reason":"<concrete reason>"}`; otherwise set
   `halt` to `null`.
6. **EMIT** — write the JSON report and run `critic_gate.py --validate`; non-zero means the pass did
   not happen.

One invocation is one pass: never self-loop. Default to one root-cause finding; add another only
when it is independent and its `survived` value is literally `true`. A candidate appears in exactly
one of `findings[]` or `dropped[]`, never both. Emit at most three findings and one strongest dropped
candidate; keep each textual field under 25 words and the JSON under 500 output tokens. The caller
may open another pass, up to three total. If substantive findings remain after three, decompose the
artifact. If two passes produce substantive findings and the caller accepts none, stop: that is
validation theater.

## Halt

- Empty, unreadable, or non-materialized artifact: stop.
- Unclear contract: repair it before review.
- Zero findings: allowed only with a concrete `halt.reason`; never invent findings to fill a quota.
- Artifact too large for one read: decompose it; never review a slice as if it were the whole.

## Output

```json
{
  "artifact": "../materialized/bundle",
  "contract": "observable requirement",
  "ledger": {"opened": ["a.md"], "not_opened": [], "accepted_unverified": []},
  "findings": [{
    "claim": "discrete actionable defect",
    "severity": "critical|important|minor",
    "contract_quote": "verbatim contract clause",
    "evidence": {"path": "a.md", "line": 7, "quote": "verbatim excerpt"},
    "falsification": {"counter": "strongest objection", "survived": true, "why": "probe"}
  }],
  "dropped": [{"candidate": "...", "counter": "...", "why_it_died": "..."}],
  "halt": null
}
```

`artifact` must be a readable directory, either absolute or relative to the report file. Evidence
paths stay inside it; the gate rereads the cited line and rejects fabricated artifact or contract
quotes, missing files, invalid line numbers, placeholders, incomplete ledgers/falsification/dropped
entries, and silent zero-finding reports.

```bash
python3 scripts/critic_gate.py --validate <report.json>  # 0 pass · 1 invalid report · 2 unusable input
python3 scripts/critic_gate.py --selfcheck               # 24 adversarial branches
```

The gate proves report structure and quote/location integrity. Runtime provenance still owns whether
the declared files were genuinely opened; T3 judges whether falsification was substantive.
