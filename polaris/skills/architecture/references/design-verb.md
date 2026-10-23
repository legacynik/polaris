# The `design` verb — greenfield, no commitment yet

Fires **before** Step 0 has anything to answer: there is no existing interface and no caller
set to judge as `OWNED` or `PUBLISHED` — the module doesn't exist yet. Generate several
genuinely different shapes for it, compare them on the vocabulary in
[interface-and-seam.md](interface-and-seam.md), and recommend one.

The premise: the first shape a designer reaches for is rarely the best one, and the fix is never
to think harder about that first shape — it is to generate a second, third and fourth shape that
are actually different, then compare.

## Contents

- [When this fires](#when-this-fires)
- [Step 1 — frame the problem space](#step-1--frame-the-problem-space)
- [Step 2 — spawn sub-agents with divergent constraints](#step-2--spawn-sub-agents-with-divergent-constraints)
- [Step 3 — present and compare](#step-3--present-and-compare)
- [Step 4 — synthesize](#step-4--synthesize)
- [Anti-patterns](#anti-patterns)

## When this fires

- "I'm starting from scratch on X, what shape do I give it?" — the symptom-phrased trigger this
  verb exists for, distinct from the arms above because there is no existing interface to judge.
- A new module, service, or component with no prior implementation to react to.
- The user explicitly wants alternatives compared, not a single proposal defended.

Not this verb: a module already exists and needs deepening — that's `interface-and-seam.md`
directly, no sub-agents. A caller set already exists and the question is what it can commit to —
that's Step 0 and `contract-and-commitment.md`.

## Step 1 — frame the problem space

Before spawning anything, write a short, user-facing statement of:

- the constraints any new interface would have to satisfy;
- the dependencies it would rely on, and which of the [four dependency
  categories](interface-and-seam.md#four-dependency-categories) each falls into;
- one rough, illustrative code sketch — not a proposal, just enough to make the constraints
  concrete for the reader.

Show this, then move immediately to Step 2: the reader can absorb the problem space while the
sub-agents work in parallel.

## Step 2 — spawn sub-agents with divergent constraints

Spawn at least 3 in parallel. Each must produce a **radically different** interface for the
same module — not a paraphrase of another's answer. Give each a separate technical brief (file
paths, coupling details, dependency category, what sits behind the seam), independent of the
user-facing framing from Step 1, plus a single divergent constraint, one of these four:

1. **Minimize the interface** — aim for 1 to 3 entry points maximum; maximise leverage per
   entry point.
2. **Maximize flexibility** — support many use cases and future extension.
3. **Optimize for the common case** — make the default caller's path trivial, even if rarer
   paths cost more.
4. **Take inspiration from a named precedent** — a specific library, paradigm, or existing
   module in this codebase, named explicitly in the brief.

Each sub-agent must output, in this order: (1) the interface — types, methods, parameters, plus
invariants, ordering, and error modes; (2) a usage example showing how a real caller uses it;
(3) what the implementation hides behind the seam; (4) its dependency strategy and adapters, per
the [four categories](interface-and-seam.md#four-dependency-categories); (5) trade-offs — where
its leverage is high, where it is thin. Give every sub-agent both this file's vocabulary and the
project's own `CONTEXT.md` domain vocabulary, so all four designs name things the same way.

## Step 3 — present and compare

Show designs one at a time so the reader absorbs each before comparing. Then contrast them by
**depth** (leverage at the interface), **locality** (where change will concentrate later), and
seam placement — the same three axes [`interface-and-seam.md`](interface-and-seam.md) defines,
never a fresh vocabulary invented for this comparison alone.

## Step 4 — synthesize

Give an opinionated recommendation — which design is strongest and why — never a menu with no
pick. If pieces of different designs would combine well, propose the hybrid explicitly rather
than leaving the reader to assemble it.

## Anti-patterns

- Sub-agents producing similar designs. If two come back close, the constraints weren't
  divergent enough — respawn, don't average them together.
- Skipping the comparison step. The value of this verb is the contrast, not the four designs in
  isolation.
- Implementing anything. This verb produces shapes to choose between, never code.
- Judging designs by estimated implementation effort — judge by leverage, locality, and seam
  placement, per Step 3.
