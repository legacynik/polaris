# The design bar — what makes a skill predictable

Load this before writing or editing the text of a `SKILL.md`. It is the bar the prose is
graded against; `eval-protocol.md` is the bar the behaviour is graded against.

**What a skill is for**, and the criterion every other rule here serves: to put simple
guardrails and direction on the **crucial steps**. Not to document a domain. A skill that
explains where it should constrain has failed even when every sentence in it is true — and
that failure is the default one, because explaining is easier than deciding what must not
vary. The test is not *short*: it is *nothing that does not change behaviour*. Those are
different, and confusing them cuts the parts that work (measured 2026-08-19: the longest
description in the suite, 1,978 characters, is also the one measuring 100% rank-1, while the
shortest was measuring 66.7% — for a reason that turned out to be its corpus, not its length).

## Contents

- [Invocation — the two loads](#invocation--the-two-loads)
- [The description is the trigger](#the-description-is-the-trigger)
- [Information hierarchy](#information-hierarchy)
- [Completion criteria and legwork](#completion-criteria-and-legwork)
- [When to split](#when-to-split)
- [Leading words](#leading-words)
- [Pruning](#pruning)
- [The six failure modes](#the-six-failure-modes)
- [Match the form to the failure](#match-the-form-to-the-failure)
- [The frontmatter contract](#the-frontmatter-contract)
- [Layout, and how far down things go](#layout-and-how-far-down-things-go)
- [Script or prose — match the freedom to the fragility](#script-or-prose--match-the-freedom-to-the-fragility)
- [Body style](#body-style)
- [Before it ships](#before-it-ships)

A skill exists to wrangle determinism out of a stochastic system. **Predictability** — the
agent taking the same *process* every run, not producing the same output — is the root
virtue, and every lever below serves it. A brainstorming skill should predictably diverge:
its tokens vary, its behaviour does not.

## Invocation — the two loads

Two choices, each spending a different budget.

| | Reached by | Pays | Pick it when |
|---|---|---|---|
| **model-invoked** (keeps `description`) | agent, other skills, and the human | **context load** — the description sits in the window every turn | the agent must find it on its own, or another skill must call it |
| **user-invoked** (`disable-model-invocation: true`, or `auto: false` in this suite) | only the human typing its name | **cognitive load** — the human is the index that must remember it exists | it only ever fires by hand |

Cognitive load is not a cost to minimise: it is the price of human agency. Spend it where
judgement matters. When user-invoked skills outgrow what one head holds, the cure is a
**router skill** that names the others and when to reach for each — not a description
bolted onto each of them.

## The description is the trigger

Two jobs only: say what the skill is, and list the **branches** that should fire it.

- **Front-load the leading word.** The description is where it does its invocation work.
- **One trigger per branch.** Synonyms renaming a single branch are duplication — "build
  features using TDD … asks for test-first development" is one branch written twice.
- **Cut identity already in the body.** Triggers, plus a "when another skill needs…"
  reach clause. Nothing else.
- **State when to use it, never what it does.** A description that summarised its own
  workflow made an agent run one review where the skill's flowchart called for two;
  removing the summary fixed it. Two vendor sources disagree here — one advises a "pushy"
  description that gestures at the process. The house sides with the evidence-backed rule,
  which is also what SPEC-MADRE Fase 5.2 already says: *la description è il trigger, non
  un riassunto*. Every word costs context load on every turn, so a description earns
  harder pruning than the body.
- **Weight the trigger by what a false positive costs.** The vendor advice above is tuned
  against *under*-triggering, where firing wrongly costs a skill read for nothing. A
  write-side skill sits in the opposite regime: firing wrongly appends to a ledger, ticks a
  plan or commits. Measured 2026-08-19: `update` fired on *"prendi il checkpoint"* — a
  request to **read** one — because its description carried the bare noun `checkpoint`
  among the triggers. Name the action by its verb and its destination ("write a checkpoint
  into the session log") and the read intent stops matching without a single exclusion.
- **Never list what it must not do.** Exclusions belong to "when NOT to use it" in the body.
  In the description they are paid on every turn of every session, and they still do not
  discriminate — the verb does.

## Information hierarchy

Content is **steps** (ordered actions) and **reference** (definitions, rules, facts), and
they mix freely — a skill can be all steps, all reference, or both. The ladder ranks how
immediately the agent needs each piece:

1. **In-skill step** — the primary tier. Each step ends on a **completion criterion**.
2. **In-skill reference** — consulted on demand. Often a legitimately flat peer-set (every
   rule of a review on one rung); that is an arrangement, not a smell.
3. **External reference** — pushed out of `SKILL.md` into a file, reached by a **context
   pointer**, loaded only when the pointer fires.

Push too little down and the top bloats; push too much and you hide what the agent needs.
That tension is the whole decision. **Progressive disclosure** is the move down the ladder,
and **branching** licenses it: inline what every branch needs, disclose what only some
branches reach. A **context pointer's wording**, not its target, decides whether the agent
gets there — a must-have behind a weak pointer is a variance bug, so sharpen the wording
first and pull the material back inline only if that fails.

Where the ladder decides how far down a piece sits, **co-location** decides what sits
beside it: a concept's definition, rules and caveats under one heading, so reading one part
brings its neighbours.

## Completion criteria and legwork

A completion criterion has two axes, and they do different work:

- **Clarity** — can the agent tell done from not-done? A vague bound ("understanding
  reached") lets attention slip to *being done*. Needs steps to bite.
- **Demand** — how much it requires. "Every modified model accounted for" forces
  **legwork**; "produce a change list" does not. This axis binds flat reference too, which
  is how a skill with no steps still carries an exhaustiveness bar ("every rule applied").

The strongest criteria are both checkable and exhaustive.

## When to split

Each cut spends one of the two loads, so split only when the cut earns it.

- **By invocation** — split off a model-invoked skill when a distinct leading word should
  fire it, or another skill must reach it. You pay context load forever.
- **By sequence** — split a run of steps when the steps still ahead tempt the agent to
  rush the one in front. Hiding works only across a real context boundary (a hand-off or a
  subagent dispatch); an inline call leaves the later steps in context and clears nothing.

## Leading words

A **leading word** is a compact concept already in the model's pretraining that the agent
thinks with while running the skill — *lesson*, *red*, *tight*, *fog of war*, *tracer
bullets*. Repeated as a token, never as a sentence, it accumulates a distributed definition
and anchors a whole region of behaviour in the fewest tokens, by recruiting priors the
model already holds. Coining your own works only if you define it, and a made-up word
recruits nothing — you pay in definition tokens what a pretrained word gives free.

It serves predictability twice: in the body it anchors execution, in the description it
anchors invocation. When the same word lives in the founder's prompts, the docs and the
code, the agent links that shared language to the skill and fires it more reliably.

Assume every skill is carrying restatements a leading word retires, and go find them:
"fast, deterministic, low-overhead" → *tight*; "a loop you believe in" → *red*.

## Pruning

- **Single source of truth** — each meaning in exactly one authoritative place, so
  changing behaviour is a one-place edit.
- **Relevance** — does the line still bear on what the skill does? A line loses relevance
  by never bearing on the task, or by going stale.
- **No-op hunt, sentence by sentence** — not line by line. When a sentence fails the
  no-op test, delete the whole sentence rather than trim words from it. Be aggressive:
  most prose that fails should go, not be rewritten.

## The six failure modes

Diagnose with these; each names the lever that cures it.

| Mode | What it is | Cure |
|---|---|---|
| **Premature completion** | ending a step before it is done, attention slipping to *being done* | sharpen the completion criterion first (cheap, local); only if it is irreducibly fuzzy *and* you observe the rush, hide the later steps by splitting |
| **Duplication** | the same meaning in more than one place | one source of truth; it also inflates that meaning's rank on the ladder past its real place |
| **Sediment** | stale layers that settle because adding feels safe and removing feels risky | a pruning discipline; it is the default fate of any skill without one |
| **Sprawl** | simply too long, even when every line is live and unique | the ladder: disclose reference, split by branch or sequence |
| **No-op** | a line the model already obeys by default, so you pay load to say nothing | the test is *does it change behaviour versus the default?* A weak leading word (*be thorough*) is a no-op; the fix is a stronger word (*relentless*), not another technique |
| **Negation** | steering by prohibition; *don't think of an elephant* names the elephant and makes it more available | prompt the positive, so the banned behaviour is never spoken; keep a prohibition only as a guardrail you cannot phrase positively, and pair it with the target |

The no-op verdict is model-relative, not reader-relative: two people disagreeing over
whether a line is a no-op disagree about the default, and settle it by running the skill,
not by debate. That is what T3 is for.

## Match the form to the failure

The shape of the fix follows the shape of what broke — writing a rule where a recipe was
needed is the commonest miss.

| Baseline failure | Right form | Wrong form |
|---|---|---|
| skips a rule under pressure (knows better, does it anyway) | prohibition + rationalization table + red flags | soft guidance ("prefer…", "consider…") |
| complies, but the output has the wrong shape | positive contract: state what the output IS, its parts, in order | a prohibition list ("don't restate", "never narrate") |
| omits a required element from something already produced | structural: a REQUIRED field or slot in the template | prose reminders near the template |
| behaviour should depend on a condition | a conditional keyed to an observable predicate | an unconditional rule plus exemption clauses |

Two rules hold whichever form you pick. **No nuance clauses**: one "unless it matters"
degraded a working recipe from consistent to noisy. **Exemption clauses do not scope**: an
exemption for code blocks still suppressed code blocks — restructure instead.

When a rule *does* get rationalised away under pressure, the fix has a known shape: a
two-column table, `Excuse | Reality`, holding the agent's actual words in the left column and
the one-line rebuttal in the right — plus a short red-flags list of the phrases that mean
"stop and start over". Both are filled from the baseline transcript, never invented: the
excuses that matter are the ones the agent really produced.

## The frontmatter contract

The suite contract is in `_standard/SKILL-STANDARD.md` and enforced by `validate_suite.py`.
The platform limits on top of it:

| Field | Limit | Notes |
|---|---|---|
| `name` | 64 characters, kebab-case, equals the directory name | verb-first or gerund reads best (`writing-docs`, not `doc-writer`); never `helper`, `utils`, `tools` |
| `description` | 1024 characters | third person, never first or second — it is injected into the system prompt, and a mixed point of view degrades discovery |

Only `name` and `description` are pre-loaded for every installed skill, which is why they
carry the whole discovery burden among hundreds of candidates. Everything else in the
frontmatter is read after the skill has already been chosen.

## Layout, and how far down things go

```
<slug>/
  SKILL.md            the flow — under 500 lines, and the house aims far lower
  scripts/            deterministic work; runs without entering context
  references/         tables, matrices, catalogues; loaded only when a pointer fires
  eval/               prompts.json + checks.json — the stored corpus
```

- **Keep references one level deep from `SKILL.md`.** A pointer that leads to another pointer
  loses the reader: agents commonly preview a file with a partial read, so anything reachable
  only through a second hop may never be seen. Link every reference directly from the top.
- **A reference over 100 lines opens with a table of contents**, so a partial read still shows
  the full scope of what is inside.
- **Name files for what they hold** — `form_validation_rules.md`, never `doc2.md`. For a
  multi-domain skill, split by domain (`references/finance.md`, `references/sales.md`) so an
  unrelated question never drags in the wrong schema.
- **Say whether a script is to be run or read.** "Run `analyze.py` to extract the fields" and
  "see `analyze.py` for the extraction algorithm" are different instructions; ambiguity here
  wastes a turn. For utility scripts, execution is almost always what you want.

## Script or prose — match the freedom to the fragility

The question is not "can the agent do this?" but "how much variation survives here?"

| Freedom | Use when | Form |
|---|---|---|
| high | several approaches are valid, the choice depends on context, heuristics guide it | numbered prose steps, judgement left open |
| medium | a preferred pattern exists, some variation is fine, configuration matters | a parameterised template to adapt |
| low | the operation is fragile, consistency is critical, the sequence is exact | one specific command: "run exactly this, do not add flags" |

The image that settles most cases: a narrow bridge with cliffs on both sides gets low freedom
(a database migration); an open field gets high freedom (a code review).

**Prefer a script for anything deterministic.** Ship `validate_form.py` rather than asking the
agent to generate validation code each time — pre-written code is more reliable than generated
code, costs no tokens to produce, and behaves the same on every run. And a script must
**solve, not punt**: handle the missing file and the permission error inside the script with a
sensible fallback, rather than letting a raw traceback surface for the agent to interpret.

For anything batched or destructive, use **plan, validate, execute**: analyse, write the plan
to a file, validate the plan with a script, only then execute, then verify. It catches errors
while they are still cheap and keeps the planning reversible.

## Body style

- **One term per concept, everywhere.** Not "API endpoint" here and "URL" or "route" there.
- **Steps are numbered and explicit.** For a long workflow, give a checklist the agent can
  copy and tick off; for a fork, write the branch as an observable question ("*Creating new
  content?* → creation workflow below") with each branch spelled out separately.
- **Examples are concrete input/output pairs**, not descriptions of what a good output would
  be like. Two or three beat a paragraph of adjectives.
- **Templates state their own strictness.** Either "always use this exact structure" or "a
  sensible default, adjust as needed" — never leave the reader guessing which one it is.
- **No time-bombs.** "If you are doing this before August 2025…" goes stale silently. State
  the current method plainly and put superseded material under an explicit old-patterns
  heading.
- **One default, one named escape hatch.** Listing five libraries makes the agent choose;
  naming one plus the single condition that overrides it does not.
- **Forward slashes in every path**, and fully qualified `Server:tool` names for MCP tools.
- **Justify every constant.** `TIMEOUT = 47` with no reason is a value nobody can safely
  change; say why 30 is 30.
- **Do not explain what the model already knows.** A paragraph defining what a PDF is costs
  tokens and buys nothing — that is the no-op test applied to exposition.

## Before it ships

- description is specific, and says both what the skill does and when to fire it
- `SKILL.md` under its declared ceiling, details pushed into `references/`
- references one level deep, long ones with a table of contents
- consistent terminology, concrete examples, no time-sensitive phrasing
- every workflow has steps with checkable completion criteria
- scripts solve rather than punt, handle their errors, justify their constants, list the
  packages they need, and carry a `--selfcheck` that proves the ignorance branch
- validation or verification step present for anything destructive
- at least three eval cases exist and the baseline was measured before the text was written
- tried on a small model as well as a large one: what a big model infers, a small one needs
  spelled out, and the gap between them is usually a missing completion criterion
