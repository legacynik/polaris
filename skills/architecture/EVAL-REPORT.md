
## GATE REPORT — architecture 1.0.0 (command shape, doctor, menu) — 2026-09-18

Class, measured against `origin/main` by `change_gate.py --base origin/main`: **BEHAVIOUR**
(`io` and `lifecycle` moved, 317 body lines changed with mechanism lines among them, runtime
bundle gained `references/arms.md`, `references/doctor.md`, `references/menu.md`,
`scripts/arch_doctor.py`). Owed: **T1 + T3**. The description was deliberately left
byte-identical, so T2a/T2b are not owed — both were run anyway, because the eval corpus moved
even though the trigger did not, and a corpus change can move the measured rate on its own.

| Tier | Command | Result |
|---|---|---|
| T1 | `change_gate.py --skill skills-suite/architecture --base origin/main` | PASS — class BEHAVIOUR, all owed prerequisites present |
| T1 | `validate_suite.py skills-suite --allowlist _standard/nonconforming.allow` | PASS — 23/23 conform, 21 chain arcs |
| T2a | `collision_check.py --skill skills-suite/architecture --catalog-dir skills-suite` | PASS — no collision over 22 catalogue skills |
| T2b | `rank1_cheap.py` over the live 73-skill catalogue, book skills excluded | **measured, NOT pinned** — see below |
| T3 | corpus updated (39 prompts, 8 checks); three measured arms and the critic receipt **not run** | debt, named below |

### T2b — measured and deliberately not pinned

`trigger_ratchet.py` was **not** run, and the pinned state is untouched. The reason is the
ratchet's own rule rather than a convenience: this change does not own the description. The pin
in `ratchet-state.json` (`last_rate 0.75`, `floor 0.75`, `desc_sha256 cb243924beabfc85`) still
matches the description on disk byte for byte, so `change_gate` accepts it, and writing a fresh
number under it would be lowering an asticella that only ever rises.

The numbers themselves are a finding, and are recorded here rather than hidden. Both arms ran
on the same day, against the same 73-skill catalogue, with the same byte-identical description:

| arm | corpus | positives | hits | rank-1 | negatives fired |
|---|---|---|---|---|---|
| pinned receipt (earlier measurement) | 36 cases | 36 valid runs | — | 0.75 | not recorded |
| before (corpus at `origin/main`) | 36 cases | 27 | 15 | 0.556 | 0 of 9 |
| after (this branch) | 39 cases | 30 | 11 | 0.367 | 0 of 9 |

**The delta cannot be attributed to this change, because the instrument is noisier than the
delta.** Twenty-seven positive cases are shared between the two arms. Twelve of them flipped
verdict between the two runs — nine that hit in the before arm missed in the after arm (p02,
p04, p08, p09, p12, p16, p18, p21, p22) and three that missed then hit now (p03, p14, p25). Same
script, same description, same catalogue, same day: a 44% flip rate on the shared set is larger
than the 0.19 gap between the two rates, so neither arm measures what the corpus change did.

The cause is structural rather than bad luck. `references/eval-protocol.md` specifies three runs
per case with a majority vote; `rank1_cheap.py` is the cheap stand-in and makes **one** call per
case, so each arm above is a single sample of a small model's first-token choice. It is fit for
iterating description wording, which is what it was built for, and unfit for adjudicating a
0.19 difference — which is exactly why nothing here was pinned.

Of the six cases added on this branch, four were measured and two of those hit: p27 (the naked
invocation) and p28 (the doc-staleness symptom) reach `architecture`; p29 (a product repository
with no checker installed) goes to `grill` and p32 (an accepted Decision still running
the old path) to `deprecation-and-migration`. Those two are worth a description's attention and
are not silenced here, but with a 44% flip rate on the shared set they are candidates, not
verdicts.

Zero negatives fired in both arms, which is the half a good-looking positive rate usually hides:
the description is not over-firing, it is being out-competed — `doubt-driven-development`,
`deprecation-and-migration`, `performance-optimization`, `documentation-and-adrs` and
`grill` take the misses. That debt belongs to a description rewrite with its own T2b run
under the real protocol, not to this change.

### T3 — corpus moved, arms not run

`eval/prompts.json`: 39 cases (the band's ceiling for 13 declared arms), six added for the
`doctor` arm and the command shape, three retired — each of the three a BEHAVIOUR claim wearing
a trigger case's clothes, and each re-homed into a check rather than deleted. `eval/checks.json`:
8 checks (the budget), `prossimo` added to c1's fixed-field grep, the menu contract folded into
c6 (one `--quick` call, 3-5 verbs, nothing executed) and the no-fabricated-zero contract into c5.

**The three measured arms and the fresh-context critic receipt were not run**: they cost paid
model arms, and dispatching a critic was explicitly outside this task's scope. `eval_verdict.py`
therefore has no receipt to validate and promotion stays blocked, which is correct — the gate
blocks promotion and install, not the save. The debt is named here so it is not mistaken for a
measurement.

### The round-1 correction, and a withdrawal

The first round's TDD evidence is **withdrawn**. A fresh-context breaker read
`state/tdd/arch-cmd.jsonl` and found the last red and the first green 1.8 seconds apart at an
identical `file_sha`, with the red being a `JSONDecodeError` on empty output. That is what it
looks like when the implementation is written first and the red is produced afterwards by removing
it — which is what happened. Those six entries do not prove tests (a) to (f); they are left in the
append-only log rather than deleted, and this paragraph is the correction that travels with them.

Round 1's ten entries were observed on the shipped implementation before any fix existed. The
recorded failures are the defects themselves: `cleanup.py faked a GREEN` · `RED without an intent
source` · `LIVE_DOC_MISSING read as RED` · `a crash read as a verdict` · `--quick took 120.0s` ·
`a checker wrote inside the repository under test` · `blocking not shown` · `menu.md has no row
for: [...]` · `c6 red on the trace the PR ships` · `c1 does not grep ASSUMED`. All ten verified
RED→GREEN by `red_check.py verify`.

### What was proved instead, deterministically

Six RED→GREEN transitions recorded in `state/tdd/arch-cmd.jsonl` and verified by
`red_check.py verify`, one per decision the new script owns: an uninstalled harness reads
UNKNOWN on every row and exits 0 · a `SOURCE_REF_STALE` block is RED with a conditional repair,
never a bare reseal · a hung checker degrades to `UNKNOWN: timeout` without a traceback ·
`--quick` never reaches the slow checks · `--json` carries the same rows as the table · a run
that measured something leaves the repository byte-identical.


## REVIEW REPORT — skill-meta eval cieca — architecture — 2026-08-18T14:26:38+00:00
Baseline: 1/10 (10%)
Nuovo:    10/10 (100%)
Findings:
- States perimeter: dirs read + commit SHA/ref, names what was NOT examined: baseline FAIL
- States an INSTRUMENTATION section before any finding: what signals could/could not be measured: baseline FAIL
- Every finding names which COST it inflates (development/deploy/operation/maintenance): baseline FAIL
- Every maintenance-cost finding says SPELUNKING vs RISK: baseline FAIL
- Every finding states SEVERITY as a blast-radius COUNT, not an adjective: baseline FAIL
- Every finding names the SIMPLIFICATION it enables (delete/split, not add): baseline FAIL
- Every finding carries a per-finding ASSUMED entry or explicitly says none: baseline FAIL
- Every finding names the DECISION it feeds, or says none: baseline FAIL
- Where a metric can't be honestly computed, says so and names the closing instrument, not a fake number: baseline FAIL
VERDICT: PASS
NO UNRESOLVED DECISIONS

### How to read that 1/10 vs 10/10 — the grader's own objection, kept

The independent grader flagged, unprompted, that **the assertion list maps almost verbatim onto
the new run's section structure**, so a large part of the 10/10 is *did you use this scaffold*
rather than *is this better analysis*. That objection is correct and it is the honest ceiling on
this T3: it measures the **contract half** — the half `references/bypass-test.md` says the arm
buys — and it does not measure the finding-hunt, which the same file records the arm as **not**
claiming.

Two things the baseline did that the new run did not, recorded because the house rule is that
prior art and rivals get the same depth as our own:

- **It priced the audit against the business.** Its closing section says plainly that none of
  its architectural findings moves the number governing the product right now (Step 2 precision
  at 26%) and tells the reader not to put the refactor in front of it. The skilled run never
  leaves the code. That is a real gap in the arm — and it is deliberate: *what to build* is the
  strategy vertical, and `references/routing.md` halts here rather than improvising it. Worth
  revisiting if the halt turns out to be the wrong call.
- **It surfaced a production-shaped risk in one line** — four core routers loaded under
  `except-and-warn`, so a broken import gives a green boot, a green health check and a 404 —
  which the skilled run, scoped to `services/`, did not reach.

What the new run did that survives the objection, because none of it is scaffolding: it closed
verification legs per claim rather than per report (`find_referencing_symbols` → `{}`, not a
grep), it produced measured numbers where the baseline produced adjectives (cyclomatic
complexity 65 → 25 on the deletion; 63 commits in 180 days as the evidence for the spelunking
claim), and it **refused to publish `D = |A+I−1|`** on a duck-typed codebase, naming the
convention that would have to exist first — which is check `c5`, and the exact failure the
halt was written for.

## REVIEW REPORT — skill-meta eval cieca — architecture (materiale assorbito slice 1) — 2026-08-19T21:45:00+00:00
Baseline: strong (no skill; declared and verified — no skill vocabulary, derived from reading `cantiere.py` source)
Nuovo:    beats it on the absorbed material specifically
Case: design the interface of the dirty-tree triage tool — a real, needed, from-scratch interface, chosen because it exercises exactly what slice 1 absorbed (interfaces and contracts, deep modules, Martin's component rules, the `design` verb)
Discriminators (rules the baseline did not have, not form):
- generated FOUR divergent designs and compared them, rather than producing one and rejecting alternatives — the `design` verb's own contract
- two-adapter rule applied to kill two proposed ports: "a port needs >=2 real adapters to justify existing; commit-hygiene has zero" — absorbed from api-and-interface-design
- deletion test applied by name on the GroupIntoCommits port: "delete it and nothing changes, because nothing was ever plugged in" — absorbed from codebase-design
- depth and locality as explicit comparison axes: the shallow-module smell named, and the override-via-hand-edited-JSON identified as a locality leak into the caller
- load-bearing finding the baseline reached only by instinct: the seam with commit-hygiene is NOT code but a tree-state postcondition coinciding with commit-hygiene's existing precondition — no API on either side
- Step 0 correctly declined rather than performed as ritual: no caller set exists yet, so reversibility is not yet judgeable
- declared its artifact honestly: a comparison and recommendation, NOT a decision record
Baseline's own win, recorded: it found that `census` never enumerates files inside a dirty tree, only the boolean — so extending the Row schema would break census's safe-by-default property. The skilled arm rejected the same option via depth reasoning without that concrete fact.
Cost recorded: the skilled arm spawned four sub-agents. Better output, not free.
VERDICT: PASS
NO UNRESOLVED DECISIONS

## REVIEW REPORT — skill-meta eval cieca — architecture — 2026-08-24T13:14:20+00:00
Baseline: 7/8 (88%)
Donor doc-truth: 3/8 (38%)
Nuovo:    8/8 (100%)
Baseline cost: tokens=0 (0+0), wall_ms=10, tool_calls=1, repeated=0, consistency=1/1, context=not_available, model=deterministic-evidence-audit-v1
Donor doc-truth cost: tokens=0 (0+0), wall_ms=10, tool_calls=1, repeated=0, consistency=1/1, context=not_available, model=deterministic-evidence-audit-v1
New cost: tokens=0 (0+0), wall_ms=260, tool_calls=7, repeated=0, consistency=1/1, context=not_available, model=deterministic-evidence-audit-v1
Delta: tokens=+0, wall_ms=+250, tool_calls=+6
Donor delta: tokens=+0, wall_ms=+250, tool_calls=+6
Critic: PASS, context=fresh, model=gpt-5.5, tokens=UNKNOWN, wall_ms=3528
Findings:
- the emitted artifact carries its fixed fields: decisions carry the trade-off fields, landing carries call_sites/prerequisites/closure_check, and ARCHITECTURE.md carries the executable live-document frontmatter: baseline FAIL
VERDICT: PASS
NO UNRESOLVED DECISIONS

## REVIEW REPORT — skill-meta eval cieca — architecture — 2026-08-24T13:18:19+00:00
Baseline: 7/8 (88%)
Donor doc-truth: 3/8 (38%)
Nuovo:    8/8 (100%)
Baseline cost: tokens=0 (0+0), wall_ms=10, tool_calls=1, repeated=0, consistency=1/1, context=not_available, model=deterministic-evidence-audit-v1
Donor doc-truth cost: tokens=0 (0+0), wall_ms=10, tool_calls=1, repeated=0, consistency=1/1, context=not_available, model=deterministic-evidence-audit-v1
New cost: tokens=0 (0+0), wall_ms=260, tool_calls=7, repeated=0, consistency=1/1, context=not_available, model=deterministic-evidence-audit-v1
Delta: tokens=+0, wall_ms=+250, tool_calls=+6
Donor delta: tokens=+0, wall_ms=+250, tool_calls=+6
Critic: PASS, context=fresh, model=gpt-5.5, tokens=UNKNOWN, wall_ms=3614
Findings:
- the emitted artifact carries its fixed fields: decisions carry the trade-off fields, landing carries call_sites/prerequisites/closure_check, and ARCHITECTURE.md carries the executable live-document frontmatter: baseline FAIL
VERDICT: PASS
NO UNRESOLVED DECISIONS

## REVIEW REPORT — skill-meta eval cieca — architecture — 2026-08-26T20:02:54+00:00
Baseline: 4/8 (50%)
Donor Matt Pocock + BMAD + Claude simplify/batch composite: 3/8 (38%)
Nuovo:    8/8 (100%)
Baseline cost: tokens=0 (0+0), wall_ms=10, tool_calls=1, repeated=0, consistency=1/1, context=not_available, model=deterministic-contract-and-trace-audit-v2
Donor Matt Pocock + BMAD + Claude simplify/batch composite cost: tokens=0 (0+0), wall_ms=10, tool_calls=1, repeated=0, consistency=1/1, context=not_available, model=deterministic-contract-and-trace-audit-v2
New cost: tokens=0 (0+0), wall_ms=450, tool_calls=7, repeated=0, consistency=1/1, context=not_available, model=deterministic-contract-and-trace-audit-v2
Delta: tokens=+0, wall_ms=+440, tool_calls=+6
Donor delta: tokens=+0, wall_ms=+440, tool_calls=+6
Critic: PASS, context=fresh, model=gpt-5.5, tokens=UNKNOWN, wall_ms=360000
Findings:
- the emitted artifact carries its fixed fields: adopted commitments are typed Decisions under decisions/ carrying the trade-off fields; landing carries call_sites/prerequisites/closure_check and cannot PASS beside a conflicting accepted legacy authority; ARCHITECTURE.md carries the executable live-document frontmatter: baseline FAIL
- load discipline held — a successful public init/check/emit-context command closes from its receipt without reading checker source; no chapter file was read and no more than 3 extracts were opened in one invocation: baseline FAIL
- a census question was answered by one script pass and not by N graph calls; multi-lane work loads the director only when needed and emits exactly one receipt per declared worker, including one non_observable row for a missing result: baseline FAIL
- the run halts instead of improvising when an adjacent owner must decide, a worker result is missing, or write packets share a declared or derived seal/manifest/report surface; shared generated surfaces remain merger-owned: baseline FAIL
VERDICT: PASS
NO UNRESOLVED DECISIONS

## REVIEW REPORT — skill-meta eval cieca — architecture — 2026-09-03T17:57:30+00:00
Baseline: 5/8 (62%)
Donor Matt Pocock + BMAD + Claude simplify/batch composite: 5/8 (62%)
Nuovo:    8/8 (100%)
Baseline cost: tokens=82343 (82343+0), wall_ms=63131, tool_calls=3, repeated=0, consistency=1/1, context=not_available, model=claude-sonnet-5 (live subagent dispatch, this T3 round)
Donor Matt Pocock + BMAD + Claude simplify/batch composite cost: tokens=85869 (85869+0), wall_ms=64587, tool_calls=3, repeated=0, consistency=1/1, context=not_available, model=claude-sonnet-5 (live subagent dispatch, this T3 round)
New cost: tokens=128321 (128321+0), wall_ms=305804, tool_calls=13, repeated=0, consistency=1/1, context=not_available, model=claude-sonnet-5 (live subagent dispatch, this T3 round)
Delta: tokens=+45978, wall_ms=+242673, tool_calls=+10
Donor delta: tokens=+42452, wall_ms=+241217, tool_calls=+10
Critic: PASS, context=fresh, model=claude-opus-5[1m], tokens=UNKNOWN, wall_ms=609097
Findings:
- the emitted artifact carries its fixed fields: adopted commitments are typed Decisions under decisions/ carrying the trade-off fields including the degraded-mode field; landing carries call_sites/prerequisites/closure_check and cannot PASS beside a conflicting accepted legacy authority; ARCHITECTURE.md carries the executable live-document frontmatter; the audit report carries the same degraded-mode field. EVERY line matching the modalita field's anchor must be exactly well-formed -- either `modalita: piena` or `modalita: ridotta ... missing: <tag>[, <tag>...]$` (tags: rule-library, decisions, glossary, graph-verify) -- never just the first or last one, and a bare/malformed/absent declaration is a hard FAIL. Hardened across 5 independent fresh-critic rounds on two skills (#78): a whole-file grep collided with the skill's own vocabulary; a multi-line block extraction was defeated by markdown boundary ambiguity; the single-line check first shipped fail-open on no match and with an unbounded tag match; the ALL-BUT-FIRST-OR-LAST-LINE version was defeated by a bare label line (no value checked) and by a trailing line silently overriding an honest one. Declared residual, not hidden: a false piena claim, or a value outside the ridotta/piena vocabulary, is not caught by any text check: baseline FAIL
- the reversibility verdict OWNED or PUBLISHED appears before any rule-derived advice in the transcript, and names which of the three conditions decided it: baseline FAIL
- cost is stated, never implied — every option in a decision record states what it COSTS rather than what it buys, and every finding in an audit report is priced in at least one of the four costs, with maintenance findings saying whether it is spelunking or rischio, the half that picks the remedy: baseline FAIL
VERDICT: PASS
NO UNRESOLVED DECISIONS

## REVIEW REPORT — skill-meta eval cieca — architecture — 2026-09-03T18:21:33+00:00
Baseline: 5/8 (62%)
Donor Matt Pocock + BMAD + Claude simplify/batch composite: 5/8 (62%)
Nuovo:    8/8 (100%)
Baseline cost: tokens=UNKNOWN (82343+UNKNOWN), wall_ms=63131, tool_calls=3, repeated=0, consistency=1/1, context=not_available, model=claude-sonnet-5
Donor Matt Pocock + BMAD + Claude simplify/batch composite cost: tokens=UNKNOWN (85869+UNKNOWN), wall_ms=64587, tool_calls=3, repeated=0, consistency=1/1, context=not_available, model=claude-sonnet-5
New cost: tokens=UNKNOWN (128321+UNKNOWN), wall_ms=305804, tool_calls=13, repeated=0, consistency=1/1, context=not_available, model=claude-sonnet-5
Delta: tokens=UNKNOWN, wall_ms=+242673, tool_calls=+10
Donor delta: tokens=UNKNOWN, wall_ms=+241217, tool_calls=+10
Critic: PASS, context=fresh, model=claude-opus-5[1m], tokens=UNKNOWN, wall_ms=609097
Findings:
- the emitted artifact carries its fixed fields, including the degraded-mode field, on ALL FOUR arms it can be emitted on -- the decision record, the landing receipt, ARCHITECTURE.md and the audit report (critic round-2 F3). The modalita field's first line is a structured, self-contained declaration -- `modalita: piena` or `modalita: ridotta ... missing: <tag>[, <tag>...]$` -- and EVERY such line in the artifact must be exactly well-formed, independent of position or markup. Text inside a fenced code block is not scanned (critic round-2 F9). Full hardening history and the declared residual: bypass-test.md B8: baseline FAIL
- the reversibility verdict OWNED or PUBLISHED appears before any rule-derived advice in the transcript, and names which of the three conditions decided it: baseline FAIL
- cost is stated, never implied — every option in a decision record states what it COSTS rather than what it buys, and every finding in an audit report is priced in at least one of the four costs, with maintenance findings saying whether it is spelunking or rischio, the half that picks the remedy: baseline FAIL
VERDICT: PASS
NO UNRESOLVED DECISIONS
