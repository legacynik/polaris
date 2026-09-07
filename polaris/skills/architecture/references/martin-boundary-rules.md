# Component and boundary rules — rewritten from scratch

Thirteen rules that decide **where a component boundary goes and when to build one**, a
question none of the four audited extracts fully own (see
[`routing.md`](routing.md#where-all-four-stop) — they stop at the *domain* boundary and at
cross-service coupling; this door is about the physical/component seam inside a single
codebase or deployable). Distilled from Robert C. Martin's *Clean Architecture* and its SOLID
predecessors, **written from scratch in this file's own words — no sentence here is copied
from the book or from any chapter file**; verified mechanically by
[`../scripts/shingle_check.py`](../scripts/shingle_check.py), which fails loud on any run of
12 or more shared words. Provenance recorded in `CHANGELOG.md`, never repeated
here — see [`design-bar.md`](../../skill-meta/references/design-bar.md) on why a fact belongs
in exactly one place.

Loads at Step 0 and at the `existing system judged` / `architectural decision` / `new feature
touching architecture` arms, whenever the question is a **component or module boundary**
rather than a service boundary (that's `routing.md`'s granularity fork) or a domain concept
boundary (that's the `domain` door).

## Contents

1. [The inflection point — when to build a boundary](#1-the-inflection-point--when-to-build-a-boundary)
2. [Partial boundaries decay without an owner](#2-partial-boundaries-decay-without-an-owner)
3. [Four physical forms and their chattiness budget](#3-four-physical-forms-and-their-chattiness-budget)
4. [The Kitty test, and why services alone aren't architecture](#4-the-kitty-test-and-why-services-alone-arent-architecture)
5. [Dependency direction, stated operationally](#5-dependency-direction-stated-operationally)
6. [Depend on volatility, not abstractness — and let violations collect in Main](#6-depend-on-volatility-not-abstractness--and-let-violations-collect-in-main)
7. [The REP/CCP/CRP tension, and why structure isn't designed top-down](#7-the-repccpcrp-tension-and-why-structure-isnt-designed-top-down)
8. [SRP is one actor, not one responsibility](#8-srp-is-one-actor-not-one-responsibility)
9. [The Humble Object as a testability delta](#9-the-humble-object-as-a-testability-delta)
10. [A framework is an asymmetric marriage](#10-a-framework-is-an-asymmetric-marriage)
11. [The database is a detail; the data model is not](#11-the-database-is-a-detail-the-data-model-is-not)
12. [The compiler enforces it, not the reviewer](#12-the-compiler-enforces-it-not-the-reviewer)

## 1. The inflection point — when to build a boundary

Two triggers, not one, and both are needed because either alone gets the timing wrong. Build a
boundary the moment you feel real friction from its absence — a change that should touch one
place keeps forcing you to touch two or three because nothing separates them yet. That is the
early trigger. The second is a standing comparison you should keep re-running rather than
answer once: the cost of building the boundary now versus the cost of continuing to live
without it. The boundary earns its construction at the point those two costs cross — build it
too early and you are maintaining a seam nothing yet needs; build it too late and every commit
since the friction started has been paying a tax the boundary would have cancelled. Re-run the
comparison often, because both costs move as the system grows — this is the one rule in the
set with an explicit stop condition on *timing*, and it is what keeps a boundary from being
either premature or a year overdue.

## 2. Partial boundaries decay without an owner

Between "no boundary" and "a fully separated component with its own deployment and its own
interface" sits a family of cheaper, weaker options: stop short of the final split and leave
the two sides in one deployable but already speaking through an interface (skipping only the
last, most expensive step); introduce a Strategy so the varying part is swappable without a
full seam; or wrap the dependency in a Facade so callers see one name instead of many. Each
buys some of the isolation a real boundary would give, at a fraction of the cost — with one
condition attached to every one of them: they only pay off if the anticipated need actually
materialises. A partial boundary built for a split that never happens is a permanent tax with
no matching benefit, and unlike a full boundary it has no natural pressure keeping it honest —
it quietly decays back toward coupling the moment nobody is watching it, because nothing forces
the two sides to keep respecting the shape. Treat a partial boundary as a bet with an
expiration date, not as insurance.

## 3. Four physical forms and their chattiness budget

The same logical separation can be realised as four different physical shapes, and each one
comes with a different price for a single call crossing it — knowing which shape you are in
tells you how much cross-seam chatter you can afford:

- **A monolith, or a component compiled into one deployable** — crossing the seam is a function
  call. Chattiness is free; design the interface for clarity, not for call count.
- **A component running in its own local process or thread** — crossing costs a local
  context switch: cheap, but no longer free, and now visible in a profiler.
  boundary — this is where the physical form starts constraining the interface shape.
- **A component addressed as a separate deployable, still on the same machine or over a fast
  local link** — costs climb into the low milliseconds; batch what you can, but occasional
  chatter is tolerable.
- **A true network service, addressed over a real network hop** — costs run from tens of
  milliseconds to full seconds under load, and every additional round trip is now a
  user-visible latency decision. This is the form where chattiness must be actively designed
  away: the interface has to be shaped for few, coarse calls, never for the same fine-grained
  method-call style that a monolith affords for free.

Choosing the physical form without pricing the chattiness it imposes is the mistake this rule
exists to stop — the same interface that is elegant as a monolith can be a performance
liability the moment it is redrawn as a network service.

## 4. The Kitty test, and why services alone aren't architecture

Splitting a system into services says nothing on its own about whether the system has good
architecture — a service boundary can just as easily freeze bad coupling in place as remove it.
The test: name one plausible feature that legitimately spans the whole system — a
cross-cutting concern like adding a new field to every user-facing record, or applying a new
compliance rule everywhere personal data is touched — and count how many separately deployable
services would need to change to ship it. A design that forces a change to nearly all of them
for a feature that conceptually belongs in one place has not achieved separation, only
distributed the same tangle across process boundaries, which is more expensive to change than
a tangle that at least lived in one deployable. Passing this test is a precondition for calling
a set of services an architecture at all, not evidence of a good one on its own.

## 5. Dependency direction, stated operationally

The abstract rule — dependencies should point toward what is more stable — becomes usable the
moment it is restated as a question about who is protecting whom: **if module A needs to be
shielded from changes happening in module B, then the dependency must run from B toward A, not
the other way around.** The arrow always points at the thing being protected. This turns "keep
dependencies pointing toward stability" from a slogan into a mechanical check you can run on
any two modules — pick the one you want insulated, and that is the one nothing may depend on
in the wrong direction. It is also what makes an open/closed violation legible: if changing B
routinely forces a change in A, the arrow was drawn backwards.

## 6. Depend on volatility, not abstractness — and let violations collect in Main

The Dependency Inversion Principle is often misread as "depend on abstract things, not concrete
ones", which produces a wall of interfaces with exactly one implementation each and no benefit.
The filter that actually matters is **volatility, not abstractness**: a concrete type that
essentially never changes — a string, an integer, a well-settled standard-library type — is
perfectly safe to depend on directly, because there is nothing left to insulate against. Reserve
the inversion for things that genuinely churn: a payment provider's SDK, a framework whose major
versions reshape its API, a vendor library still finding its shape. And no system fully obeys
the rule everywhere — some concrete, volatile dependency will always exist somewhere, because
somebody has to actually construct the objects the abstractions describe. The answer is not to
chase every violation to zero; it is to let them **collect in one place** — a composition root,
conventionally called Main — so the rest of the system stays clean and the volatility is priced
into exactly one file instead of scattered across every module that happens to need an object
built.

## 7. The REP/CCP/CRP tension, and why structure isn't designed top-down

Three cohesion principles pull a codebase's component structure in different directions at
once. The Reuse/Release Equivalence Principle wants a component to be a coherent, independently
releasable unit — nothing in it that a consumer might want without the rest. The Common Closure
Principle wants classes that change for the same reason to sit in the same component, so one
reason to change touches one place. The Common Reuse Principle wants a component to contain
only things that get reused together, so pulling in the component doesn't drag in unrelated
baggage. Optimising any one of the three in isolation degrades the other two, and which pair a
project should favour changes over its life: a young, single-team codebase sits closer to the
Common Closure side — the ability to make one change in one place while iterating fast matters
more than reuse nobody is asking for yet — and drifts toward reuse-favouring cuts only once
real external consumers show up and start depending on stable subsets. The practical
consequence is that **component structure is not something you draw once from a diagram before
writing code** — it is a map of what is actually buildable and releasable together, and it is
expected to be redrawn as the project's position on that tension shifts. A component structure
that has never been repartitioned since day one is a sign nobody has checked whether it still
fits.

## 8. SRP is one actor, not one responsibility

The Single Responsibility Principle is easy to mis-state as "a module should do one thing",
which is unfalsifiable — everything can be described as doing one thing at the right altitude.
The operative form is narrower: **a module should answer to one actor** — one person, role, or
stakeholder whose changing needs are the only reason that module should ever change. Two
concrete symptoms show the violation in practice rather than as a matter of taste. First,
**accidental duplication through a shared helper**: two actors' code happens to call the same
utility function today because the logic looked identical, and a change requested by one actor
silently breaks the other, because the helper was never actually shared business logic — it was
two different concerns that coincidentally matched. Second, **merge conflicts between people who
have no business coordinating**: if two contributors serving two unrelated stakeholders keep
colliding in the same file, that file is answering to more than one actor and needs splitting
along the actor line, not along whatever technical seam looked convenient.

## 9. The Humble Object as a testability delta

If a use case cannot be tested without spinning up a real web server, a real database, or the
full weight of a framework, that is not a fact about testing — it is evidence that the
framework, not the application, currently owns the architecture. The remedy pattern is the
**Humble Object**: split the hard-to-test logic away from the thing that is hard to test (a UI
element, a database call, a framework entry point) into two pieces — a rich piece holding all
the decisions, testable in isolation, and a deliberately "humble" thin piece that does nothing
but talk to the untestable thing, so thin there is nothing left in it worth testing. The seam
between those two pieces is very often exactly the seam the architecture needed anyway; treat a
class that is hard to test as a design smell pointing directly at where a boundary belongs,
rather than as a testing inconvenience to route around with more mocking.

## 10. A framework is an asymmetric marriage

Adopting a framework is not a neutral tool choice — it is a commitment with an unequal split of
risk. You commit fully: your code's shape, its lifecycle, and often its very language of
concepts bend to fit the framework's model. The framework's author commits nothing back to your
specific system, and the framework's own documentation and idioms actively steer toward the
tightest possible coupling — "the framework way" is almost always the most invasive way to use
it. The mitigation is not refusing frameworks; it is **containing the marriage to one place**:
wire the framework's objects together, and construct anything it demands, only inside the
composition root (`Main`, in the vocabulary of [rule 6](#6-depend-on-volatility-not-abstractness--and-let-violations-collect-in-main)).
Business logic should never carry a framework annotation or inherit from a framework base class
directly — if it does, the day the framework's major version reshapes its API, the reshaping
bill lands on every business rule instead of on the one file that was always expected to absorb
it.

## 11. The database is a detail; the data model is not

Which database engine a system uses — which vendor, which storage layer, whether it's a
relational store or a document store — is a plumbing decision, deferrable, and swappable
behind a clean seam without disturbing the business rules above it: a detail, in the sense that
almost nothing about the shape of the application should depend on it. The **data model** is a
different question entirely and does not get the same deferral: what the entities are, how they
relate, which invariants they carry, is a decision with the same weight as any other
architectural commitment, because getting it wrong reshapes the business rules that sit on top
of it. Conflating the two — treating "we haven't picked a database yet" as license to also defer
modelling the data — is how a system ends up with no data model at all, only whatever shape the
eventually-chosen database happened to make convenient.

## 12. The compiler enforces it, not the reviewer

A rule that lives only in a document, a convention, or a reviewer's memory is a rule that gets
violated the first time someone new touches the code, or the first time an experienced
contributor is in a hurry. The reliable form of any structural rule — dependency direction,
layer access, which module may import which — is one a build step can check and fail on,
because a compiler or a linter does not get tired, does not skip the check under deadline
pressure, and does not need onboarding. **This exact mechanism already lives in the suite and
is not re-derived here**: `directionality-of-imports` and `layer-access-rules-as-code`, both
loaded by the audit arm (`architecture/references/audit-arm.md:148`), are the
audited extract's answer to "make the rule mechanically checkable" — load those, never
reconstruct an equivalent from this file. What this rule adds on top is the framing: a finding
whose only proposed remedy is "add this to the review checklist" has not found an enforcement
mechanism, it has found a rule not yet worth automating, or a rule too vague to automate at all.
