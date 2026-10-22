# Component-boundary rules

Twelve rules that decide **where a component boundary goes inside one codebase or deployable,
and when to build one at all**. The service-granularity fork belongs to the decomposition rules
and a domain concept boundary to the `domain` door ([routing.md](../routing.md) maps both); these
rules own the physical and component seam.

Loads at Step 0 and at the `existing system judged`, `architectural decision` and `new feature
touching architecture` arms whenever the question is a component or module boundary. A
Decision cites them as `component-boundary:<n>`, the number of the heading.

## 1. The inflection point — when to build a boundary

- **condition:** a change that should touch one place keeps forcing edits in two or three,
  because nothing separates them yet; or someone proposes a seam the code does not yet ask for.
- **decision:** build the boundary when both triggers fire: the friction is real and observed,
  and the cost of building it now has crossed below the cost of living without it. Treat that
  comparison as standing: re-run it as the system grows, never answer it once.
- **why:** this rule sets the timing. Too early, you maintain a seam nothing needs; too late,
  every commit since the friction began has paid a tax the boundary would have cancelled. The
  cost is the recurring re-check itself, and accepting some friction before you act.
- **check:** name the concrete changes that touched several places; with none, halt and leave
  the code unsplit. Verify by stating both costs side by side in the Decision.

## 2. Partial boundaries decay without an owner

- **condition:** a full boundary (separate deployment, own interface) looks too expensive, and a
  cheaper partial one is on the table.
- **decision:** pick one of three partial forms: keep both sides in one deployable but already
  talking through an interface, skipping only the final split; a Strategy that lets the varying
  part be swapped with no full seam; or a Facade so callers see one name instead of many. Record
  it as a bet with an expiry date and an owner, never as insurance.
- **why:** each form buys part of a real boundary's isolation at a fraction of its cost, but only
  if the anticipated need materialises. Otherwise it is a permanent tax, and with no pressure
  keeping the two sides honest it drifts back to coupling as soon as nobody watches it.
- **check:** name the split the partial boundary prepares for, its owner and its expiry. At
  expiry, either complete the split or remove the partial form; with no owner, halt.

## 3. Four physical forms and their chattiness budget

- **condition:** a logical separation is being given a physical shape, or an existing interface
  is being moved to a different shape.
- **decision:** name the form and shape the interface to its per-call price. In one deployable
  (monolith or compiled-in component) a crossing is a function call: design for clarity, not
  call count. In a local process or thread it is a context switch: cheap, visible in a profiler,
  and starting to constrain the interface. As a separate deployable on the same machine or a
  fast local link it costs low milliseconds: batch what you can, tolerate occasional chatter.
  As a true network service it costs tens of milliseconds up to seconds under load: design for
  few, coarse calls, since every round trip is a user-visible latency choice.
- **why:** the same interface that reads well in a monolith becomes a performance liability
  once redrawn as a network service. Pricing the form up front costs coarser, less elegant
  interfaces the further out you go.
- **check:** the Decision names the form and counts the crossings per user action. A
  fine-grained interface placed on a network hop is a halt: redesign the interface first.

## 4. The cross-cutting feature test, and why services alone aren't architecture

- **condition:** a set of services is offered as evidence of good architecture, or a split into
  services is proposed.
- **decision:** name one plausible feature that legitimately spans the whole system, such as a
  new field on every user-facing record or a new compliance rule wherever personal data is
  touched, and count the separately deployable services that must change to ship it. If nearly
  all of them change for a feature that belongs in one place, the split has distributed the
  tangle, not removed it.
- **why:** a service boundary can freeze bad coupling as easily as remove it, and a tangle spread
  across processes costs more to change than one inside a single deployable. Running the test
  costs one honest scenario walk-through.
- **check:** passing is a precondition for calling the services an architecture, never proof
  that it is a good one. Record the feature used and the count.

## 5. Dependency direction, stated operationally

- **condition:** two modules depend on each other in one direction and you must decide which way
  the arrow runs, or changes in one keep forcing changes in the other.
- **decision:** if module A must be shielded from changes in module B, the dependency runs from
  B toward A. The arrow always points at the thing being protected.
- **why:** it turns the stability slogan into a mechanical check on any pair, and it exposes an
  open/closed violation: when edits to B keep forcing edits to A, the arrow is backwards. The
  cost is often an interface owned by A that B must implement.
- **check:** name the protected module first; without a clear answer, halt and ask which side
  changes less. Verify that no import runs from the protected module to the other.

## 6. Depend on volatility, not abstractness — and let violations collect in Main

- **condition:** an interface or inversion is proposed for a dependency, or a review counts
  concrete dependencies as violations.
- **decision:** invert only what actually churns: a payment provider's SDK, a framework whose
  next major version rewrites its API, a vendor package still finding its shape. Depend directly on
  settled concrete types (strings, integers, mature built-in types). Accept the
  violations that remain and collect them in one composition root, conventionally `Main`, which
  constructs the objects the abstractions describe.
- **why:** reading the principle as "depend on abstract things" yields a wall of
  one-implementation interfaces with no benefit; zero violations is impossible because something
  must build the objects. Collecting them prices the volatility into one file, at the cost of
  that file knowing every concrete type.
- **check:** for each proposed interface, name the change history or roadmap that shows the
  target churning; with none, drop the interface. Verify that concrete construction of volatile
  types happens only in `Main`.

## 7. The REP/CCP/CRP tension, and why structure isn't designed top-down

- **condition:** deciding how to group classes into components, or a component layout that has
  never been revisited.
- **decision:** weigh three cohesion pulls. Reuse/release equivalence wants each component to be
  one coherent, independently releasable unit; common closure wants classes that change for the
  same reason in the same component; common reuse wants a component to hold only what is reused
  together. A young single-team codebase favours common closure; shift toward the reuse-oriented
  cuts only when real external consumers depend on stable subsets.
- **why:** optimising any one pull degrades the other two, and the right balance moves over the
  project's life, so structure is a map of what builds and releases together, expected to be
  redrawn. The cost is periodic repartitioning work.
- **check:** name the project's current position (single team, or external consumers present). A
  layout never repartitioned since day one is a prompt to re-check fit, not proof it is wrong.

## 8. SRP is one actor, not one responsibility

- **condition:** a module serves several stakeholders, or one of the two symptoms below appears.
- **decision:** give each module exactly one actor: one person, role or stakeholder whose
  changing needs are its only reason to change. Split along the actor line, not along whichever
  technical seam looks convenient. The two symptoms: a shared helper that two actors' code calls
  because the logic looked identical, where one actor's change silently breaks the other
  (accidental duplication); and repeated merge conflicts between contributors serving unrelated
  stakeholders in the same file.
- **why:** "does one thing" is unfalsifiable at any altitude; "answers to one actor" is
  testable. The cost is duplicating code that only looked shared, and more modules.
- **check:** name the actor for the module; if you cannot name one, or name two, it needs
  splitting. Verify that the duplicated helper copies may now diverge freely.

## 9. The Humble Object as a testability delta

- **condition:** a use case cannot be tested without a real web server, a real database or the
  full framework.
- **decision:** split the logic from the hard-to-test thing (a UI element, a database call, a
  framework entry point) into a rich piece holding every decision, testable in isolation, and a
  humble piece so thin it only talks to the untestable thing and holds nothing worth testing.
  Place the boundary at that seam.
- **why:** the need for real infrastructure shows the framework, not the application, owns the
  architecture, and the testability seam is very often the seam the design needed anyway. It
  costs an extra class per seam and replaces mocking with structure.
- **check:** verify the rich piece's tests run with no server, database or framework. Treat a
  hard-to-test class as a pointer to where a boundary belongs, never as a reason to add mocks.

## 10. A framework is an asymmetric marriage

- **condition:** adopting a framework, or business code that carries framework annotations or
  extends framework base classes.
- **decision:** contain the framework in one place: wire its objects and construct whatever it
  demands only in the composition root (`Main`, as in [rule 6](#6-depend-on-volatility-not-abstractness--and-let-violations-collect-in-main)).
  Business logic carries no framework annotation and inherits from no framework base class.
- **why:** you commit fully (code shape, lifecycle, vocabulary) while the framework commits
  nothing to your system, and its idiomatic usage is usually the most invasive one. Containment
  means the next breaking major version is paid in one file instead of every business rule; the
  cost is giving up some of the framework's conveniences.
- **check:** scan business modules for framework imports, annotations and base classes; each hit
  is a finding. Adopting frameworks stays allowed; this rule only decides where they live.

## 11. The database is a detail; the data model is not

- **condition:** the storage engine is undecided, or someone proposes deferring data modelling
  until it is.
- **decision:** defer the engine (vendor, storage layer, relational or document) behind a clean
  seam. Decide the data model now: the entities, how they relate and the invariants they carry,
  with the weight of any other architectural commitment.
- **why:** almost nothing in the application should depend on the engine, but a wrong data model
  reshapes the business rules above it. Merging the two deferrals leaves a system whose model is
  whatever the eventual engine made convenient. The cost is modelling work before storage is
  known.
- **check:** before deferring the engine, verify the entities, relations and invariants are
  written down. Data-system tuning of the chosen engine belongs to the data-systems rules.

## 12. The compiler enforces it, not the reviewer

- **condition:** a structural rule (dependency direction, layer access, which module may import
  which) exists only in a document, a convention or a reviewer's memory, or a finding's remedy
  is a review-checklist line.
- **decision:** make the rule something a build step checks and fails on. The mechanism is
  governance rules `directionality-of-imports` and `layer-access-rules-as-code`, which the
  audit arm loads; read them for how to build the check.
- **why:** a compiler or linter does not tire, skip the check under deadline or need onboarding;
  a documented rule breaks the first time a newcomer or a hurried expert touches the code. The
  cost is writing and maintaining the check.
- **check:** a finding whose only remedy is a checklist line has found no enforcement: either the
  rule is not yet worth automating or it is too vague to automate, so sharpen it or say which.
