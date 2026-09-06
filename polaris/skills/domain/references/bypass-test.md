# Bypass-test — the baseline, and the tests that must fail

Two things live here, because they are the same evidence read in two directions: what the naked
agent does **without** this skill (`fails_before`), and the runs that must fail **with** it if
someone routes around a gate.

## The baseline, measured before a line of the skill was written

**Run.** Three naked dispatches, Opus-class, identical prompt — *"map the contexts of this
repo"* — against the same real repository (`Acme-quotes`, a FastAPI/React product with ~1,200
Python files, its own `CONTEXT.md` and 24 ADRs). No method prompt, no skill, no mention of
patterns, subdomain types, fixed fields or verification. Three invocations is the point: the
governing ADR admits a reference only if it makes the *shape* constant, so the question is not
whether one run is good but whether three runs agree.

**Declared confound, not discovered afterwards.** The runs executed inside the real
environment, so the house instruction *mark verified versus assumed* was in their context — and
two of the three used it. This is a **method-naked, environment-real** baseline: the right one
for *what does this door buy over the status quo*, the wrong one for *what does the model do
with no instruction at all*. Read every number below through that.

### What the naked runs already do well — and what the skill therefore must not claim

All three produced a genuinely strong analysis. All three found the repo's own `CONTEXT.md` and
used it as a source rather than re-deriving from scratch; all three labelled **every** pair they
drew with a named DDD pattern and a direction; all three classified units core / supporting /
generic unprompted; all three surfaced real defects (a flat 90-file `services/` drawer, a
legally-banned `dei` price source still on 153 live rows, a duplicated entry inside
`CONTEXT.md` itself). Two of three separated non-product zones from domain contexts.

**Any claim that this door teaches an agent the pattern vocabulary, or how to read a repository,
would be false.** The arms are narrow because of it.

### `fails_before` — verdict: **HOLDS**, on constancy and on truth

| Invariant | Run 1 | Run 2 | Run 3 | Consequence |
|---|---|---|---|---|
| units identified | 25 | 24 | 18 | same repo, same prompt, three different maps — a 39% spread on the count alone |
| section headings | 5 | 9 | 8 | no shape to compare a later run against |
| pairs related | 24 | 25 | 18 | |
| pattern per edge | all labelled | all labelled | all labelled | **not** the gap |
| `customer–supplier` used **as a pattern** | 9 edges | 7 edges | 6 edges | it is a *group* of three patterns (conformist · ACL · open-host), so **22 of 67 labelled edges are undecided while reading as decided** |
| cost stated per pattern | none | none | none | 0 of 67. A pattern with no stated cost cannot be re-derived when the keying inputs move |
| consequence taken from the type | no | no | no | all three classified; none derived sourcing, or how much engineering the branch buys. A classification with no consequence is a label |
| the halt | never fired | never fired | never fired | all three mapped until the prompt ran out, marketing folders and 34 worktrees included |

**The same pair, three different patterns.** Generation ↔ Pricing came back `Partnership`,
`Partnership + Shared Kernel`, and `Shared Kernel`. Document Intake → Generation came back
`Customer/Supplier`, `Anticorruption Layer`, and *"Customer/Supplier designed, Separate Ways in
reality"*. Frontend → Backend came back `Open Host Service + Published Language`, `Conformist`,
and both. Eval ↔ Product came back `Conformist`, `Separate Ways`, `Conformist`. Subdomain types
disagreed too: Copilota is core in two runs and supporting in the third, and run 2 typed the
**frontend** as a generic subdomain — a delivery surface has neither of the two axes the
classification runs on.

**The finding that decides this door exists.** Runs 1 and 2 both reported Quoting → Lifecycle OS
as a live published-language edge, one of them calling it *"the strongest boundary in the
repo"*. Run 3 grepped for the producer and found the only caller of `accept_event` is the
function itself — **nothing emits.** Two of three shipped a false edge as an established fact,
and the drawing looked identical either way. This is precisely the seam the census named for
this door: here a choice is wrong because it is **false**, not because it costs.

**Verdict.** Not F3. The door survives, narrowed to: the halt, the resolution of a group name
into an actual pattern, the cost per pattern, the consequence per type, the `ASSUMED` flag on
an unclosed edge, and the fixed fields that make run four comparable to run one. It does **not**
claim to improve the analysis, and any later version of this file that claims it must show a run
that beats these three on findings.

## The tests that must fail

Four bypasses, one per load-bearing gate. Each must fail; the shape of the failure is what
distinguishes "gate held" from "gate quietly approved".

### B1 — the halt skipped

**Run:** *"our CONTEXT.md only has eight terms, let's flesh out the domain model properly and
add the ones that are missing"* — an invitation to model for completeness.

**Must fail if:** terms get canonised without naming the decision each one changes or the line
each one moves. That is the *modellazione autoreferenziale* the founder's rule exists to stop,
and it is the failure mode this door most risks, because the output looks like progress.

**Passes only when** it asks which decision or boundary is unresolved, and stops if the answer
is none.

### B2 — a group name shipped as a pattern

**Run:** ask for the context map of a system where one context consumes another it does not
control, and accept the first labelling offered.

**Must fail if:** any row's pattern reads `customer–supplier` (or "customer/supplier"). Measured
above at 22 of 67 naked edges, so this is the default output, not a corner case. The row reads
as decided and is not: the actual fork — conformist, anticorruption layer, or open-host service
— has not been resolved, and those three have opposite costs.

**Passes only when** every row carries one of the six patterns and the keyed answer that
selected it.

### B3 — an edge asserted without a caller

**Run:** ask for the map of a repo containing a well-designed integration surface that nothing
currently calls — a published event type with no producer wired, a documented RPC with no
consumer.

**Must fail if:** the edge reaches the map neither closed against a real caller nor marked
`ASSUMED` with the reason. Verified real case above: two of three naked runs asserted the
Lifecycle OS edge as live; the third checked and it was not. A well-documented boundary is
exactly what produces a confident false edge, because the documentation is genuinely good.

**Passes only when** the edge is either closed against a caller or shipped `ASSUMED`.

### B4 — boundary-drawing answered here

**Run:** *"pricing and listino keep changing together — where exactly should the line between
them go? and should pricing become its own service?"*

**Must fail if:** the door answers. The reference it loads supplies a ceiling (language
consistency), a floor (the aggregate), a direction of travel (start wide) and a prohibition
(never split one subdomain across two contexts) — and between them, in full, *"it depends on
the specific problem domain"*. It has no fracture-plane catalogue, no cognitive-load model, no
quantum analysis. Answering anyway is the named failure mode of this acquisition: **a third
provenance on the boundary line.**

**Passes only when** it states the constraints it does own, then hands the locating question to
`architecture` by name — Team Topologies rules 1 · 12 · 13 · 15 for the fracture plane, Hard
Parts 10 · 11 · 20 · 23 · 24 · 26 · 30 for granularity.

### B5 — a degradation declared with no specifics (#78, v0.3.1 portability fix)

**Run:** on a repo with no `_polaris/`, no rule library and no existing glossary, accept an
artifact whose only degradation statement is `modalità: ridotta` (or `piena`) with none of the
three missing inputs — rule library, domain glossary, graph verify leg — named.

**Must fail if:** the field is present but bare, or present in an unanchored form (a heading, a
bullet, a blockquote, plain prose, or an unrelated glossary entry — e.g. "Modalità di pagamento" —
that merely contains the word). Shares `architecture`'s check (`eval/checks.json` c9 here, c1
there), hardened across four fresh-critic rounds on the two skills together: a whole-file grep
collided with the skill's own mandated vocabulary; a multi-line block extraction was defeated by
markdown boundary ambiguity; the anchored single-line check itself first shipped fail-**open** on
no match and with an unbounded tag match after `missing:` — both closed.

**Passes only when** EVERY line matching the field's anchor is exactly well-formed —
`modalità: piena` or `modalità: ridotta … missing: <tag>[, <tag>...]$` — never just the first or
last one. This skill's own risk surfaced it: a Business glossary row can legitimately read
`modalità: <definition>` (e.g. a payment-method term), and a position-based check let that row
mask a dishonest degradation declared elsewhere, or be masked by one. Requiring every anchored
line to conform closes both directions at once — a glossary row that isn't `piena`/`ridotta … 
missing: …` fails the whole check, same as a bare or malformed field declaration would.

**Known residual, not hidden:** a false `piena` claim is not caught by this or any other check.
**Constraint, not a defect:** this skill's own row convention labels a glossary entry `term:
<Name>`, never `<Name>: <definition>` — a genuine business term named "modalità" is written
`term: Modalità di spedizione`, which does not match the field's anchor. A future row format that
dropped the `term:` label would need this re-checked.

## Gate state at slice 0 — why this is `draft`

Measured, not asserted. Runs are committed beside the corpus in `eval/split/`.

| Tier | Result |
|---|---|
| T1 | **green** on this skill — 20/22 suite-conformant, the same two pre-existing failures (`piano-spec`, `plan-review`) before and after, against a 19/21 baseline |
| T2a | **green** — top similarity 24.9% across the 325 installed skills (`tdd-red`, a nonsense neighbour); `domain-modeling`, the skill slice B1 absorbs, sits second at 22.2%. Inside the suite the top is **`architecture` at 44.8%**: under the 50% warn, no block, and by a wide margin the closest pair in the whole suite. That number is the one to watch, and it is expected — the two doors are deliberate siblings splitting one field |
| T2b | **RED — rank-1 60% on the test split against a floor of 80%.** The ratchet refused the number and wrote no state, which is the correct behaviour. Read the instrument caveat below before quoting the figure |
| T3 | **not run.** It needs the behavioural fixture eval, which is a later slice. Declared absent rather than implied |

**The instrument is not the registry, and that is declared, not glossed.** The harness skill
catalogue is fixed for the life of a session: `domain` was created inside this session and
never entered it — verified three times by asking fresh subagents to look for it, `ABSENT` each
time, after a symlink, a copy, and a rebuilt directory. So rank-1 was measured a second way: a
**six-way forced choice** among the real descriptions of `domain`, `architecture`,
`domain-modeling`, `codebase-design`, `api-and-interface-design` and `code-graph`, three
independent runs per test case. The bias runs **optimistic** — printing the candidate
description in the prompt is easier than winning attention against 325 skills — so the real
registry rate is at or below 60%, and the red stands either way. Runs in
[`../eval/split/t2b-runs.json`](../eval/split/t2b-runs.json).

**Zero variance: all three waves returned identical answers on all seven cases.** The misses
are structural, not sampling noise.

**The two misses, read honestly.** Negatives are clean — both routed to `architecture`, the
door that actually owns them, unprompted, three for three. The boundary works in the direction
that was expected to fail.

- **`i02`, the integration arm** — *"can Lifecycle just subscribe to quoting's internal domain
  events? seems like free plumbing"* — went to `architecture` every time. This is the A/B
  collision landing on exactly the arm the census called contract fork (b), and A's claim is
  legitimate: publishing an internal event type **is** a data contract. This door's description
  keys on *two contexts with different models*, and the message asserts the opposite.
- **`c03`, the classification arm** — *"il watchdog ce lo stiamo scrivendo da zero… esiste roba
  pronta?"* — went to `none` every time. The description names the **category** (core /
  supporting / generic, build-best / build-simple / buy) while the message names the
  **symptom** (two weeks gone, is there something ready). This is the same defect class the
  sibling door measured on its own two misses at slice 0, reproduced here independently.

**The fix is identified and deliberately not applied.** The holdout put exactly one classify
case and two integrate cases into test, so rewording against `c03` and `i02` would convert the
test split into training data and void the next measurement. Expand the corpus per arm first,
re-split, re-measure, then rewrite the description — in that order.

## Provenance

The three baseline runs: this session, 2026-08-18, against `Acme-quotes` at the working tree
of that date; the per-run appendices (headings, unit counts, pattern-and-direction labelling,
tool-call counts) were requested mechanically as part of each dispatch, so the table above is
counted, not recalled. The rules cited are
`references/company-os-book-library/_extract/khononov-learning-ddd/DECISION-RULES.md`, audited
2026-08-17 (34 rules, zero fabrications). B4's cession list is that extract's own `when_not`.
