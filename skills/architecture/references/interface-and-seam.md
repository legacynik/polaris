# Interface and seam — the OWNED side

Loads when Step 0 answered **`OWNED`**: every caller can still change in one commit. Optimise
for **depth** — behaviour per unit of interface — never for what you can no longer take back.
The other side is [contract-and-commitment.md](contract-and-commitment.md).

Name things with the terms below — module, interface, seam, adapter — so every finding and
design in this door uses one vocabulary.

## Contents

- [Vocabulary](#vocabulary)
- [Depth as leverage](#depth-as-leverage)
- [The deletion test](#the-deletion-test)
- [The two-adapter rule — and where it stops applying](#the-two-adapter-rule--and-where-it-stops-applying)
- [Internal seam vs external seam](#internal-seam-vs-external-seam)
- [Four dependency categories](#four-dependency-categories)
- [Replace, don't layer](#replace-dont-layer)
- [Rejected framings](#rejected-framings)

## Vocabulary

**Module** — anything with an interface and an implementation: a function, a class, a package,
a slice spanning tiers. Scale-agnostic on purpose.

**Interface** — everything a caller must know to use the module correctly: the type signature,
plus invariants, ordering, error modes, required configuration, performance characteristics.
Wider than "signature" or "API" — those name only the type-level surface.

**Seam** — where the module's interface lives, the place you can alter behaviour
without editing in that place. Where to put it is a decision distinct from what sits behind it.

**Adapter** — a concrete thing satisfying an interface at a seam. Names a *role*, not a
substance: a thin adapter can wrap a deep implementation (a Postgres repo) or a large adapter
can wrap almost nothing (an in-memory fake).

## Depth as leverage

Depth is **leverage at the interface**: how much behaviour a caller or a test can exercise per
unit of interface they had to learn. Not a ratio of implementation-lines to interface-lines —
see [Rejected framings](#rejected-framings) for why that measure is thrown out. A deep module
hides a lot behind a small interface; a shallow one exposes nearly as much surface as it
contains, which is a pass-through wearing a name.

Depth produces two things: **leverage** for callers (one implementation pays back across N call
sites and M tests) and **locality** for maintainers (a bug, a fix, a piece of knowledge
concentrates in one place instead of spreading across every caller).

## The deletion test

Imagine deleting the module. If the complexity it held simply vanishes, it was a pass-through —
it never earned its seam. If the complexity reappears, distributed back across every caller that
used to lean on it, it was earning its keep. This is the only *falsifiable* test of
architectural value on the OWNED side: it does not ask for a judgement call, it asks what
happens to the complexity when the module is gone.

## The two-adapter rule — and where it stops applying

**One adapter means a hypothetical seam. Two adapters means a real one.** Don't introduce a
port unless at least two adapters are justified — typically production plus test. A
single-adapter seam is indirection wearing an architecture diagram.

**Validity condition:** this rule holds only where you **own the
callers** — Step 0 answered `OWNED`. On a `PUBLISHED` surface it is actively harmful if copied
without this condition: there the correct seam count is **zero adapters** at commitment time,
because adding one later is a breaking change for consumers you cannot enumerate. A rule that is
discipline on one side of Step 0 is a bug on the other — see
[`contract-and-commitment.md`](contract-and-commitment.md#published-seams-build-at-zero-adapters)
for the PUBLISHED-side form.

## Internal seam vs external seam

A deep module can carry **internal seams** — private to its implementation, used only by its
own tests — in addition to the single **external seam** at its public interface. Without this
distinction, "deep module" reads as "monolith, untestable", which is the objection that sinks
the whole rule. A module is deep and thoroughly tested when its tests cross internal seams its
callers never see.

## Four dependency categories

When deepening a cluster of shallow modules, classify what it depends on — the category decides
how the deepened module gets tested across its seam:

1. **In-process** — pure computation, in-memory state, no I/O. Always deepenable: merge the
   modules, test through the new interface directly. No adapter needed.
2. **Local-substitutable** — a dependency with a real local stand-in (PGLite for Postgres, an
   in-memory filesystem). Deepenable if the stand-in exists; the seam stays internal, no port at
   the module's external interface.
3. **Remote but owned (ports & adapters)** — your own service across a network boundary. Define
   a port at the seam; the deep module owns the logic, the transport is injected as an adapter.
   Tests use an in-memory adapter, production uses HTTP/gRPC/queue.
4. **True external (mock)** — a third party (Stripe, Twilio) you do not control. The deepened
   module takes it as an injected port; tests supply a mock adapter.

## Replace, don't layer

Old unit tests written against the shallow modules become waste the moment tests at the
deepened module's interface exist — **delete them**, don't keep both. New tests assert on
observable outcomes through the interface, never on internal state, and should survive an
internal refactor: a test that must change when the implementation changes was testing past the
interface, not through it.

## Rejected framings

Kept as a section, not as trivia — the value is the precedent of a skill naming what it
considered and discarded:

- **Depth as the ratio of implementation-lines to interface-lines** — rewards padding the implementation. Depth-as-leverage above replaces it.
- **"Interface" as a language keyword or a class's public methods** — too narrow. Interface
  here is every fact a caller must know, including invariants and failure modes no type
  signature carries.
- **"Boundary"** — overloaded with the bounded context, a different correctness question
  (is the concept true here, not what it costs). Say **seam** or **interface**; where a concept
  boundary falls is the `domain` door's question.
