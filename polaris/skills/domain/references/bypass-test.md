# Bypass-test — the baseline, and the tests that must fail

Two things live here, because they are the same evidence read in two directions: what a capable
agent does **without** this skill (`fails_before`), and the runs that must fail **with** it when
someone routes around a gate. Measurement history and run logs live in `eval/` and
`EVAL-REPORT.md`; this file keeps only what a reviewer needs to replay the tests.

## The baseline — `fails_before`

Three naked dispatches of a strong model, identical prompt — *"map the contexts of this repo"* —
against the same real product repository (about 1,200 source files, its own `CONTEXT.md`, two
dozen ADRs). No skill, no method prompt, but the ordinary environment, so a house instruction to
mark verified versus assumed was in context: a **method-naked, environment-real** baseline. Three
runs is the point: the question is whether three runs agree on the *shape*, not whether one is
good.

**What the naked runs already do well, and the skill does not claim.** All three read the
repository's own `CONTEXT.md` as a source, labelled every pair with a named integration pattern
and a direction, classified units core / supporting / generic unprompted, and surfaced real
defects. Any claim that this door teaches the pattern vocabulary, or how to read a repository, is
false; the arms are narrow because of it.

**What they did not produce:**

| Invariant | Run 1 | Run 2 | Run 3 | Consequence |
|---|---|---|---|---|
| units identified | 25 | 24 | 18 | same repo, same prompt, three different maps |
| section headings | 5 | 9 | 8 | no shape to compare a later run against |
| `customer–supplier` used **as a pattern** | 9 edges | 7 edges | 6 edges | it is a *group* of three patterns (conformist · anticorruption layer · open-host), so 22 of 67 labelled edges read as decided and are not |
| cost stated per pattern | none | none | none | 0 of 67: a pattern with no cost cannot be re-derived when its keying inputs move |
| consequence taken from the type | no | no | no | a classification with no sourcing consequence is a label |
| the halt | never fired | never fired | never fired | all three mapped until the prompt ran out, unrelated folders included |

**The same pair, three different patterns.** One pair came back `partnership`, `partnership +
shared kernel` and `shared kernel`; another `customer/supplier`, `anticorruption layer` and
"designed one way, separate ways in reality". Subdomain types disagreed too, and one run typed
the frontend as a generic subdomain — a delivery surface has neither axis the classification
runs on.

**The finding that decides this door exists.** Two runs reported a published-language edge as
live traffic, one calling it the strongest boundary in the repository. The third searched for the
producer: the event's only caller was the function itself — nothing emitted. Two of three shipped
a false edge as an established fact, and the drawing looked identical either way. Here a choice is
wrong because it is **false**, not because it costs.

## The tests that must fail

One per load-bearing gate. Each must fail; the shape of the failure is what distinguishes "gate
held" from "gate quietly approved".

### B1 — the halt skipped

**Run:** *"our CONTEXT.md only has eight terms, let's flesh out the domain model properly and add
the ones that are missing"* — an invitation to model for completeness.

**Must fail if:** terms get canonised without naming the decision each one changes or the line
each one moves. That is self-referential modelling, the failure this door most risks, because the
output looks like progress.

**Passes only when** it asks which decision or boundary is unresolved, and stops if the answer is
none.

### B2 — a group name shipped as a pattern

**Run:** ask for the context map of a system where one context consumes another it does not
control, and accept the first labelling offered.

**Must fail if:** any row's pattern reads `customer–supplier` (or "customer/supplier"). Measured
above at 22 of 67 naked edges, so it is the default output. The actual fork — conformist,
anticorruption layer or open-host service — is unresolved, and those three have opposite costs.

**Passes only when** every row carries one of the six patterns and the keyed answer that selected
it.

### B3 — an edge asserted without a caller

**Run:** ask for the map of a repository containing a well-designed integration surface that
nothing currently calls — a published event type with no producer wired, a documented RPC with no
consumer.

**Must fail if:** the edge reaches the map neither closed against a real caller nor marked
`ASSUMED` with the reason. A well-documented boundary is exactly what produces a confident false
edge, because the documentation is genuinely good.

**Passes only when** the edge is either closed against a caller or shipped `ASSUMED`.

### B4 — boundary-drawing answered here

**Run:** *"pricing and the price list keep changing together — where exactly should the line
between them go? and should pricing become its own service?"*

**Must fail if:** the door answers the locating question. Its rules supply a ceiling (language
consistency), a floor, a direction of travel (start wide) and a prohibition (one subdomain is
never split across two contexts); they have no fracture-plane catalogue, no cognitive-load model,
no quantum analysis. Answering anyway puts a second source of rules on the boundary line.

**Passes only when** it states the constraints it does own, then hands the locating question to
`architecture` by name — its ownership rules place the fracture plane, its decomposition rules
decide the granularity.

### B5 — a degradation declared with no specifics

**Run:** on a repository with no rule library and no existing glossary, accept an artifact whose
only degradation statement is a bare `modalità: ridotta` (or `piena`) naming none of the missing
inputs.

**Must fail if:** the field is present but bare, or present in an unanchored form (a heading, a
bullet, a blockquote, prose, or a glossary entry that merely contains the word). This skill shares
`architecture`'s check (`eval/checks.json` c9 here, c1 there): free-text parsing of this field was
defeated repeatedly, so the contract is a structured first line.

**Passes only when** every line matching the field's anchor is exactly `modalità: piena` or
`modalità: ridotta … missing: <tag>[, <tag>...]` — every one, not the first or the last. A
glossary row can legitimately start with a business term, so this skill labels every glossary
entry `term: <Name>`: a business term named "modalità" is written `term: Modalità di spedizione`
and never matches the field's anchor. A row format without the `term:` label would need this
re-checked.

**Known residual:** a false `piena` claim is not caught by this or any text check.
