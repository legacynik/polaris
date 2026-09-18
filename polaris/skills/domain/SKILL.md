---
name: domain
description: ◇ Name the domain and place its boundaries. Fires when a term is overloaded, when two words are used for one thing, when a subdomain must be typed core, supporting or generic, or when two contexts with different models must integrate or be mapped. Not for where a service boundary falls, nor for interface, schema or framework commitments.
version: 0.3.3
user-invocable: true
auto: true
job: settle one question of domain language or domain boundary — the canonical term with the aliases it kills, the subdomain type with its sourcing consequence, the integration pattern with what it costs, or the context map with one labelled row per pattern — and halt the moment the modelling stops resolving a decision or a line
when_not: deciding WHERE a boundary line falls or how granular a unit should be (fracture planes and quanta — `architecture`, which loads Team Topologies 1 · 12 · 13 · 15 and Hard Parts 10 · 11 · 20 · 23 · 24 · 26 · 30 by name); committing to an interface, a data contract, a schema, a framework or a hot path (`architecture`); choosing what the company should build at all (strategy); implementing an aggregate, value object, repository or event-sourced model (nobody — write the code)
lifecycle: one settled question per invocation — a `CONTEXT.md` row per canonised term, a `CONTEXT-MAP.md` row per integrating pair and pattern, or a repository-root `DOMAIN.md` update for stable domain/component IDs; an ADR only when the three-condition test passes · files are created lazily, never in advance of the first thing to write in them · every halt is written into the artifact it interrupted · every edge not closed against a caller ships marked `ASSUMED`
invokes: []
invoked-by: [human, architecture]
io: "receives: a contested term, subdomain, integrating contexts, system to map, or proposed stable domain/component ID -> produces: the canonical term, sourcing consequence, integration pattern, context map, or current DOMAIN.md mapping; otherwise a halt naming who owns the question."
status: active
---

# domain

## Where this goes (host repository decides)

A skill decides **how** to produce a document, never **where** it lives. Before writing any spec,
plan, audit, review, validation receipt or diagram, read the host repository's output map and use
it; a document that lands where the repository does not look was never written.

```bash
sed -n '/^outputs:/,/^[^ ]/p' _polaris/config.yml 2>/dev/null || sed -n '/^outputs:/,/^[^ ]/p' config.yml
```

This skill produces: **domain, diagram (context map beside DOMAIN.md)**. Kinds: `spec` `plan` `audit` `review` `validation` `diagram` `decision` `archive` — each maps to a
documentation area `docs/modules/<area>/…` whose README is a generated map. Never invent a third
location; if the repository declares no map, say once where you wrote and why.

Settle **one** question of what the domain is called and where it divides. The sibling door
`architecture` decides what a change *costs*; this one decides what is *true* — a term that
does not describe the thing, a line that cuts where the domain does not divide. Two criteria
of correctness, two doors.

The rules travel with this skill: `references/decision-rules/khononov-learning-ddd.md`,
resolved from this skill's own directory, so they load on any repository — not only the one that
holds the library. Every step below names the rule ids it loads. **Load only what the step
names**; the file is a rule index, not a document to read whole. The `chapters/` files stay in
the vault library and are never decision input — study material only.

A run that cannot load it still settles the question from the repository's own evidence: the
term as the code uses it, the boundaries the census proves. What it may not do is present a
term shaped by this file's headings as rule-derived. Say so with a **structured first line** —
`modalità: ridotta — missing: <tag>[, <tag>...]`, tags from `rule-library` · `glossary` ·
`graph-verify` — with the free-text reason below it; `modalità: piena` when nothing degraded.
Checked on that one line by `eval/checks.json` c9, never across the whole artifact — the same
contract `architecture`'s SKILL.md carries, hardened after three rounds of a fresh critic
defeating a free-text parser (#78). An unnamed degradation is a defect, not a fallback.

## Step 0 — the halt, before any modelling

> **"può diventare modellazione autoreferenziale — fermati quando il linguaggio risolve una
> decisione o un confine."**

*(It can become self-referential modelling — stop when the language resolves a decision or a
boundary.)*

The founder's rule, verbatim, and stricter than anything the book says. It runs **first** and
it runs again at every step:

- A term earns a place only when naming it **changes a decision or moves a line**. A term that
  merely makes the model feel complete is noise.
- A session that has resolved neither has produced nothing, however much shared understanding
  it generated. Stop it; do not schedule the follow-up.
- Stop drilling when every finer child is the same type as its parent (rule 8).

## Three habits, absorbed from `domain-modeling`

`domain-modeling` is archived (`_archived/2026-08-18-domain-absorbed/`) but three
of its in-session habits run through every arm above and are not optional:

- **Challenge the term the moment it contradicts `CONTEXT.md`.** "Your glossary defines
  'cancellation' as X, you just said Y — which is it?" Called out on the spot, not batched
  into an end-of-session pass.
- **Sharpen the vague term by proposing the canonical one, right when it is said.** "You're
  saying 'account' — do you mean the Customer or the User? Those are different things."
- **Cross-check the glossary against the code, and surface the contradiction.** The load-bearing
  one: the only point in the suite where the glossary is verified against the real state
  instead of against itself. "Your code cancels entire Orders, but you just said partial
  cancellation is possible — which is right?"

## Which boundary is in play — the second question, always

**Subdomains are discovered; contexts are designed** (rule 11). A subdomain boundary is a
finding about the business — you may be wrong about it, you may not choose it. A context
boundary is a design decision you own. Get this backwards and the argument becomes circular.

The founder wears both hats, and the book names exactly that exception: when one head owns
both the software design and the business strategy, **say which hat is speaking**, because the
check that normally comes from the other party is gone.

## An edge is a claim about the code

Every map edge follows the census-then-verify mechanic exactly as `architecture`'s SKILL.md
defines it (its "Census, then verify" section — one definition, both doors): script finds the
candidates, the graph closes the ones that carry the decision, whatever does not close ships
marked `ASSUMED` with the reason. Its rule 5 travels too: **name the graph actually reached, or
declare `modalità: ridotta` with the verify leg missing** — an edge closed by grep alone is not
an edge closed by a graph, and the two read identically in the output. Measured on the baseline:
two of three naked runs reported a published-language edge as live traffic; the third checked
and found the producer had no caller at all.

## The arms — one row per question

| Question | loads | emits | halts when |
|---|---|---|---|
| **a term is overloaded, vague, or two words mean one thing** | rule **12** (language consistency is the *ceiling* on context width) | a `CONTEXT.md` row: canonical term · aliases to avoid · the boundary against its nearest neighbour | two experts use one word for two things → that is not a naming problem, it is the ceiling telling you where it is. Hand the width question to the map arm. **Never prefix** (`MarketingLead`, `CRMLead`) — the named anti-pattern: nobody says the prefix out loud |
| **how much engineering does this subdomain deserve** | rules **1**–**10**: 1 the fork · 2 side-business test · 3 integration-cost test · 4 advantage is not always technical · 5 the unrewritable ball of mud · 6 sourcing · 7 the reverse check · 8 distillation depth · 9 exclusions · 10 drift | the type (core · supporting · generic) **with its consequence taken**: build-best in-house · build-simple, corners allowed · buy or adopt | *"it's core because it's important"* — importance is not differentiation, every subdomain is required · the supporting/generic gray area with the integration cost unpriced → that is a two-hour spike, not a judgement call · the reverse check mismatches (rule 7) → stop building and open the business conversation; resolving it alone in either direction is the failure this check exists to prevent |
| **two contexts with different models must talk** | rule **18** (the three-step fork) → **19**–**24** admission per branch → **25** drift → **26**–**28** mechanics | the pattern · its direction · the keyed answer that selected it · **what it costs** | the two contexts are one subdomain split in two (rule 13) → no pattern saves that, and it is the book's own worst outcome · `separate ways` proposed over a **core** subdomain → hard out, no exception · the models are actually identical → you have one context, not two |
| **map the contexts of this system** | rules **29** required fields · **30** read across edges, not single ones · **31** an existing system: the five named findings | `CONTEXT-MAP.md` (contract below) | domain knowledge is missing → the review cannot proceed on code alone; the remedy is a conversation, and this door does not fake one · a finding is about **people** → hand off (ownership and load to Team Topologies via `architecture`, the conversation itself to the founder) and do not stage an organizational intervention from a diagram |
| **bind stable repository domains/components** | the settled terms and context boundaries above, then the repository census-and-verify pass | repository-root `DOMAIN.md`: stable `domain_id`, stable `component_id`, component paths and executable freshness frontmatter — **then regenerate the context map** with `scripts/arch_diagram.py`, whose regions ARE the contexts this arm just bound | a name is contested, a path cannot be verified, or a component crosses two unresolved contexts → halt before a Decision can name it |

When the map turns into work, rules **32**–**33** sequence it: align logical boundaries
(namespaces, modules, packages) before physical ones, and extract only on the two named
triggers — two teams in one codebase, or conflicting models in one component. **A logical
boundary with nothing checking it is a comment**; the enforcement is `architecture`'s field.
The migration *shape* — strangler versus in-place — is `architecture`'s migration arm too.

**Solo-operator collapse, recorded not filtered.** `partnership` and `shared kernel` both
reduce to *the same person edits both sides*, so the fork between them disappears. What
survives the reduction is the reason to keep an explicit contract anyway: ad hoc integration
between two contexts you both own *washes out their boundaries over time*. `conformist`,
`anticorruption layer` and `separate ways` survive intact, because there the upstream is a
vendor or your own legacy system, and that power imbalance is real at any headcount.

## What the artifacts must carry

**`CONTEXT.md` — a glossary and nothing else.** No implementation detail, no spec, no scratch
pad, no container for implementation decisions. Without that constraint it is a second README
within a month. Created **lazily**: no file until there is a first thing to write in it.

| Field | Means |
|---|---|
| term | the canonical name, the one people actually say — rendered as the literal label `term: <Name>`, never a heading naming the term directly (`## <Name>`) and never a bare `<Name>: <definition>` line, so a business term can never collide with this door's own structured fields |
| what it is here | one sentence, in the business's words |
| aliases to avoid | the losing terms, **listed** — this is what makes a glossary usable in review instead of decorative |
| boundary against the nearest term | 3–5 lines of dev/expert dialogue that separate them. If you cannot write it, the boundary is not understood and the row is not ready |
| flagged ambiguities | its own mandatory section: where the code and the language disagree, each naming which of the two is wrong |
| `modalità` | once per document, `piena` or `ridotta` naming the missing input — the rule library, the graph verify leg — same field, same contract as every other arm's |

Second pass has a protocol, not a vibe: re-read, incorporate, re-flag, rewrite the dialogue.

**`CONTEXT-MAP.md` — one row per pattern.**

| Field | Means |
|---|---|
| pair | the two contexts |
| pattern | `partnership` · `shared kernel` · `conformist` · `anticorruption layer` · `open-host service` · `separate ways`. **`customer–supplier` is a group name, never a label** — a row carrying it is an undecided row |
| direction | upstream → downstream, or symmetric for partnership and shared kernel |
| why this branch | the keyed answer from rule 18 that selected it: collaboration quality, where the power sits, or cost of integration versus duplication |
| what it costs | mandatory. A pattern with no stated cost is a defective row |
| `ASSUMED` | until the edge is closed against a real caller |
| `modalità` | once per document, `piena` or `ridotta` naming the missing input |

A pair that genuinely needs two patterns gets **two rows**. Forcing one label per pair is a
falsification, and the book says so.

**Where the repository keeps its language somewhere else, its convention wins.** Add the row where
that repository already keeps its terms, name that location in the free-text line below
`modalità` — never in the structured first line itself, which stays exactly `modalità: piena`
when nothing degraded — and never backfill an existing glossary into a shape this repository did
not ask for. A repository with no glossary at all is not a degraded run: it is the first row,
written lazily like any other.

**`DOMAIN.md` — the machine-readable repository map.** The frontmatter carries
`schema_version`, `document_type: domain`, `status: active`, `owner`, `snapshot_scope`, computed
`snapshot_ref`, `review_trigger`, `domains[]`, `components[]` and `modalità` (`piena` or `ridotta`
naming the missing input). Each component has one stable ID, one or more domain IDs and verified
repository paths. An unknown ID or missing path blocks Decision landing; prose below the
frontmatter may explain the language but cannot introduce a second map.

**An ADR only when all three hold** — hard to reverse · surprising without the context ·
the fruit of a real trade-off. Miss one and it is a dated line, not an ADR. This composes with
`metodologia`'s threshold; it is not a second copy of it.

## Two glossaries — the hard rule

The vocabulary of **design** — module, seam, depth, adapter-as-code-shape — is scaffolding for
the conversation and **never becomes an artifact**. The documents this door emits speak the
system's own domain language plus the named integration patterns, nothing else. A `CONTEXT.md`
row explaining what a seam is has drifted into the other door's job.

One name collides across the two and it matters: an **anticorruption layer** here is a
translation between two *models*, chosen because of a power relationship you cannot change.
The wrapper around a third-party library adopted just in time is a different pattern with the
same name, and it belongs to `architecture`.

## When NOT to use it

- **Where exactly the line goes, or how granular a unit should be.** This door supplies a
  ceiling, a floor, a direction and a prohibition — it has no fracture-plane catalogue, no
  cognitive-load model, no quantum analysis. That is `architecture`, loading Team Topologies
  and Hard Parts by rule id. A third provenance on the boundary line is the named failure mode
  of this door, not ordinary scope hygiene.
- **An architectural commitment** — an interface, a data contract, a schema change, a
  framework, a hot path. `architecture`. There a choice is wrong because it **costs**; here
  because it is **false**.
- **Tactical DDD** — aggregates, value objects, repositories, event-sourced models, layering.
  Nobody owns it and nobody needs to: write the code.
- **Whether to build the thing at all.** This door reads business strategy as an input; it
  identifies which subdomain carries the advantage, never whether the advantage is worth
  having.
- **Module depth, or where an interface seam goes.** Borrowed wholesale from Ousterhout by the
  book itself, and owned here by `architecture`.

## Quick reference

| step | what it produces | blocks? |
|---|---|---|
| Step 0, the halt | permission to continue, or a stop | yes — a session that resolves neither a decision nor a line ends |
| script pass over callers, then the graph on the survivors | the candidate edges, then the closed ones | no — whatever does not close becomes `ASSUMED` |
| the three-condition test | ADR, or a dated line | no |
| `python3 scripts/arch_diagram.py --from DOMAIN.md --out docs/modules/<area>/diagrams/<name>.architecture.json [--check-delivery]` | the context map: one region per `domain_id`, its components inside it, each tagged `esiste` · `parziale k/n` · `solo spec` from the paths, plus the WORST verdict the Decision register gives that component | no — but CI regenerates, diffs it and refuses an HTML rendered from older bytes, so a map edited by hand is red |

The map is one artifact shared with `architecture`: that door owns the boxes, this one owns the
regions. A separate contexts-only diagram was tried and dropped — four Polaris contexts share
components pairwise (a K4), and a K4 cannot be drawn on a grid without a crossing, which showcase
validation refuses. The regions carry the same fact without the crossing.

Bypass-test: [`references/bypass-test.md`](references/bypass-test.md).

## Clarify only what changes the model

Do not invoke a separate interview phase. Resolve repository facts first, then ask **one**
plain-language question only when its answer changes a term, boundary or consequence. State the
current hypothesis and recommendation, explain why a wrong answer matters, and offer at most
2–3 mutually exclusive options with one honest cost each. Skip anything already answered by the
user or evidence; if the user delegates a reversible choice, take the recommendation and proceed.
Stop only when the missing answer would make the domain artifact false.
