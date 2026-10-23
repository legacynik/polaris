# Ownership rules

These rules decide who owns a surface: how much one unit can carry, where a responsibility splits,
which interaction mode two units run, what each unit publishes for others, and which symptoms send a
boundary back for redesign. A unit can be a human team, one specialist, one agent, or a swarm of agents.
Each rule reads condition → decision → why → check. A step loads only the rule ids it names, never the
whole file.

## Where these rules stop

| Question | Who decides it instead |
|---|---|
| Pay, rewards, hiring, letting someone go, individual performance | people and roles — outside this skill |
| Legal employment structure, which person fills a role | people and roles — outside this skill |
| Vendor selection, project cost estimates, product direction | strategy — outside this skill |
| Naming the bounded contexts a split follows (rule 12) | the `domain` door |
| Which service boundary or interface a component exposes once ownership is set | the component-boundary rules and the decomposition rules |
| An arrangement that already works and a rule here argues against it | inspect the arrangement first; the rule prompts a review, it does not overrule observed success |

When a question falls in the first three rows, say these rules do not cover it. Reasoning by analogy
from a team-design rule to a people or money question produces a confident wrong answer.

## Conditions that change a rule's footing

- Every number in rules 1, 6, 10, 17 and 21 was calibrated on human teams of five to nine people. For an
  agent unit, keep the structure and the ordering, derive the number from the unit's real context and
  attention budget, and record the number you used. An unvalidated cap falls back to the human figure,
  never to no cap.
- Rule 2 rests on human trust limits. It gives no size limit for an agent unit; take that unit's numeric
  limit from rules 22, 23 or 24, and if none of them yields one, record the limit as unresolved.
- Rule 12 lists team location as a split line. Location has no meaning for agents; drop it from the
  candidates for an agent unit.
- Rules 21 and 22 need visible signal: stable communication paths and an enumerable dependency list.
  Without them, the first deliverable is making the signal visible, not the verdict.
- Rule 23 needs enough usage for a service-level objective to mean something. Below that, the builder
  keeps the thing and the rule does not fire.
- All other rules describe information flow, ownership and boundaries; they apply to any kind of unit as
  written.

### 1. Domain-capacity ceiling per unit
- **condition:** a domain, subsystem or responsibility area is about to be assigned to a unit.
- **decision:** classify the domain as simple (a known procedure), complicated (needs analysis and
  iteration) or complex (needs experiments to discover). A unit holds two or three simple domains, or at
  most one complicated domain, or exactly one complex domain and nothing else; a domain too big for one
  unit splits into subdomains, and two units never co-own one domain.
- **why:** the cap keeps the unit's working attention on its owned work, and the split keeps ownership
  single. It costs more units and more handoffs between them.
- **check:** the complexity class was assessed honestly, without being talked down to fit the plan. For
  an agent unit, keep the ordering (complex crowds out everything, complicated costs more than simple)
  and derive the counts from its context budget, recording them. If the unit reports overload while its
  output still looks fine, stop assigning and escalate to a boundary redesign.

### 2. Group-size ceiling triggers a split
- **condition:** a human team, or a group of human teams, grows in headcount.
- **decision:** cap a team at 5–8 people (about 15 where trust is high), a group of teams at 50 (150 with
  high trust), and a larger division at 150–500. Crossing a limit is the signal to carve out a new,
  semi-independent unit.
- **why:** staying under the limit keeps coordination by personal trust workable. It costs a split, a new
  boundary and the work of drawing it.
- **check:** the group coordinates through interpersonal trust; confirm the limit is actually crossed,
  then act. For an agent unit this rule yields no size limit: take the numeric limit from rules 22–24.

### 3. Architecture-vs-org-structure tiebreaker
- **condition:** a documented target architecture conflicts with how the organisation actually
  communicates and reports.
- **decision:** the real communication structure wins by default. The target architecture wins only if
  unit boundaries are redrawn to match it before the build starts.
- **why:** systems take the shape of the paths their builders talk along, so redrawing units first is the
  only way to get the planned shape. It costs a reorganisation ahead of any delivery.
- **check:** the target architecture is written down, not aspirational. If redrawing units is not
  approved, accept the architecture the current structure will produce, or escalate the redesign to
  whoever owns organisation design. This holds for any kind of unit.

### 4. Architecture fitness test for team-scoped flow
- **condition:** a set of unit boundaries is about to be committed, and on every later review of the
  system those units own.
- **decision:** the boundary set passes only if the architecture shows four properties: loose coupling
  between components, high cohesion inside each, clear and fitting version compatibility, and clear and
  fitting testing across units. Treat a draft org chart as a draft architecture, and turn it down for
  architectural reasons when it fails.
- **why:** it catches a wrong boundary before coordination overhead piles up around it. It costs a
  standing review instead of a one-time sign-off.
- **check:** the intended architecture is known before units are drawn; otherwise the test runs on an
  architecture nobody chose. If a property fails and cannot be fixed inside one unit's remit, redraw the
  boundary (rule 12) instead of adding coordination process.

### 5. Unexpected friction on a service boundary signals a defect
- **condition:** two units declared a low-touch service relationship, yet need heavy ongoing
  back-and-forth to make it work; or a planned close collaboration produces almost no interaction.
- **decision:** treat the friction as a defect in the API, the boundary or the providing unit's
  capability, and investigate before adding meetings or process. Treat the silent collaboration as a
  skill gap in the consuming unit or a boundary too ambitious to bridge.
- **why:** reading the mismatch as a signal finds the defect early. It costs an investigation each time
  the observed mode departs from the declared one.
- **check:** the intended mode was declared in advance; without it nothing counts as unexpected. Check the
  providing unit's published interface first (rule 16). If friction persists after one investigation
  cycle, escalate to a boundary redraw or to fixing the provider's missing capability.

### 6. Collaboration-mode partner cap
- **condition:** a unit is asked into close collaboration (shared responsibility, blurred boundary) with
  other units.
- **decision:** one close-collaboration partner at a time. Service mode (X-as-a-Service) scales to many
  partners; facilitating sits between, bounded by real mentoring bandwidth. A second simultaneous close
  collaboration converts to service or facilitating mode.
- **why:** close collaboration is the expensive mode and does not scale, so capping it protects the unit's
  capacity. It costs slower discovery on the interfaces pushed to service mode early.
- **check:** the relationship is truly close collaboration, not service or facilitating. For an agent
  unit, keep the ordering (collaboration costs most, service least) and derive the cap from its budget,
  recording it; with no derivation, the cap stays at one.

### 7. Indefinite collaboration signals a wrong boundary
- **condition:** two units stay in close collaboration on one interface for an open-ended period without
  settling a stable API.
- **decision:** treat it as a defect: wrong domain boundary, wrong split of responsibility or wrong skill
  mix. Redraw the boundary or fix the skills; collaboration is the exploring phase and service mode the
  exploiting phase that should follow.
- **why:** it stops a relationship that never found its boundary from passing as good teamwork. It costs
  a redesign while the collaboration still feels productive.
- **check:** the collaboration was started to discover a boundary, not as joint ownership by design. This
  rule is itself the halt: when it fires, stop and redesign.

### 8. Default role type is stream-aligned
- **condition:** any new team, role or unit is being created.
- **decision:** make it stream-aligned, owning one valuable stream of work end to end. Make it enabling,
  complicated-subsystem or platform only for a specific, stated reason of offloading load from
  stream-aligned units.
- **why:** end-to-end ownership keeps delivery flowing without handoffs. It costs each stream-aligned
  unit some breadth it must carry itself.
- **check:** none needed; this is the default. If a role fits none of the four types, redesign its remit
  rather than inventing a fifth type.

### 9. Complicated-subsystem role justification test
- **condition:** someone proposes a dedicated complicated-subsystem unit for a component.
- **decision:** create it only when the component needs specialist knowledge beyond what a stream-aligned
  unit can reasonably hold; potential sharing or reuse is not a reason. Expect one or two such units in a
  whole organisation.
- **why:** it keeps specialist units rare and justified by necessity. It costs the owning stream the
  burden of a component it would rather hand off.
- **check:** an honest load assessment of the component exists. If the stated reason is reuse, not need,
  give the component to the stream-aligned unit that owns it, or to a platform.

### 10. Enabling relationships must have a planned end
- **condition:** an enabling relationship is being set up between two units.
- **decision:** declare its end condition when it starts; for human units the expected span is a few weeks
  to a few months. A relationship that becomes a permanent daily dependency is reclassified as an
  unmanaged platform or silo and fixed as such.
- **why:** success means the served unit grows more autonomous, and a declared end makes that testable. It
  costs a re-plan when the gap closes slower than planned.
- **check:** the relationship exists to close one named capability gap. For an agent unit, tie the end to
  the gap closing, not to calendar time. When the relationship outlives its plan without the served unit
  becoming self-sufficient, halt and re-plan.

### 11. Platform investment sizing (Thinnest Viable Platform)
- **condition:** someone proposes investing in a dedicated platform unit.
- **decision:** start with the thinnest version that works, which may be a documented list of reliable
  dependencies. Grow it into a dedicated platform unit only when the underlying substrate needs an ongoing
  management layer: tracking new and retired APIs, custom integration work.
- **why:** a thin start avoids building platform nobody asked for. It costs consuming units some
  integration work until the platform grows.
- **check:** none needed; this is the starting posture. If platform scope keeps growing without demand or
  complexity evidence from consumers, halt the expansion: the platform has drifted from real need.

### 12. Fracture-plane selection order
- **condition:** a monolithic responsibility or system is being split, or a new boundary drawn between
  units.
- **decision:** split along business-domain bounded contexts first. Add a secondary line (change cadence, risk, regulatory
  compliance, user personas, technology, performance isolation, team location) only
  when the domain split alone does not give an independently ownable, capacity-sized unit; split by
  technology layer only when that technology is genuinely foreign to the rest of the stack.
- **why:** domain splits produce units that deliver on their own. It costs mapping the domain well before
  splitting, and early splits will need revision.
- **check:** the domain has been mapped with enough business and technical knowledge to find a bounded
  context. For agent units, drop team location from the candidates. If no line or combination gives an
  ownable unit, escalate and accept cross-boundary coordination as a deliberate cost; across incompatible
  substrates, name one side the platform for the others.

### 13. Fracture-plane validation — two tests, in order
- **condition:** a candidate boundary is about to be committed.
- **decision:** run two tests in order. First the screen: can this unit consume or provide the
  responsibility as a service? A no kills the candidate. Then the binding test: does the result give units
  that are both more autonomous (fewer dependencies) and lighter (fewer unrelated responsibilities)? Both
  must improve; gaining one by losing the other fails.
- **why:** two tests stop splits that trade dependencies for load or the reverse. It costs a trial period,
  since a boundary rarely proves itself before it runs.
- **check:** if the two tests disagree, the second one governs. A passing boundary is provisional and
  enters the periodic re-check of rule 21.

### 14. Regulatory/risk carve-out
- **condition:** a part of the system is subject to its own regulation, or its risk profile differs
  materially from the system around it.
- **decision:** give it its own boundary and owner even when it would otherwise sit inside a larger
  unit's domain.
- **why:** it limits audit and compliance blast radius and lets legal and compliance stakeholders attach
  to exactly one owner. It costs one more unit and one more interface.
- **check:** the regulation or risk profile differs in a demonstrable way, not merely by feeling sensitive.
  Verify by naming the regulation or the risk metric that differs.

### 15. Single-owner rule
- **condition:** ownership of any running service, subsystem or deliverable is being assigned.
- **decision:** exactly one unit owns it. Other units propose changes (pull requests, suggestions) and the
  owner applies them; the owner may grant temporary access, and access never transfers ownership.
- **why:** one owner means one place that answers for the thing and its changes. It costs other units
  waiting on the owner for every change.
- **check:** no exception exists. Verify that every surface lists exactly one owner; two owners, or none,
  is a defect to fix before work proceeds.

### 16. Every role publishes a Team API
- **condition:** a unit is created, or another unit needs to interact with it.
- **decision:** the unit publishes seven things or it cannot be consumed: (1) code: runtime endpoints,
  libraries, clients and UI it produces; (2) versioning: how it announces change, such as SemVer used as
  a commitment to keep dependents working; (3) documentation: guides showing how to use what it owns;
  (4) the practices and principles it works by; (5) communication: channels and tools that reach it; (6) work information: what
  it does now, what comes next, its near-term priorities; (7) anything else another unit needs to work with
  it. Usability by other units is a design criterion.
- **why:** a published contract makes the unit usable without meetings, and for an agent unit the contract
  is literally its interface. It costs keeping seven items current.
- **check:** the unit has a stable identity and a single owner (rule 15). If another unit cannot say what
  this unit's API is, define it before assigning work; investigate interaction friction (rule 5) as an API
  defect before treating it as a boundary defect, because the API fix is cheaper.

### 17. Accountability routes to the durable unit, not a transient assignee
- **condition:** work, a KPI, a reward or a budget is being assigned.
- **decision:** assign it to the durable unit (team or role), which allocates internally; never to an
  individual person or a single execution inside the unit.
- **why:** a durable assignee keeps ownership alive after the individual or the run is gone. It costs
  visibility into who inside the unit did what.
- **check:** the unit is stable and identifiable, not an ad hoc pool. For agent units the rule binds
  harder: a task given to one agent invocation has no owner once it ends, so route it to the durable role.
  The human motivation argument behind team rewards does not apply to agents; apply the routing only.

### 18. New work, support and BAU all stay with the owning stream
- **condition:** deciding who runs live support, maintenance or business-as-usual work for a stream.
- **decision:** the unit that builds a stream also supports it and maintains it, legacy included. No unit
  exists only for business-as-usual work, and support is never pooled across streams; cross-unit swarming
  is reserved for incidents that truly cross stream boundaries.
- **why:** keeping build and run together preserves the feedback from operations into design and gives the
  builder a reason not to repeat its mistakes. It costs builder capacity spent on support.
- **check:** if support is being centralised to save cost, reject it on feedback-loop grounds (rule 25 is
  the same failure in budgets). Staff frontline and operational roles with experienced members, because
  the rest of the organisation steers on the signal they report.

### 19. Decision rights over "who builds what" are architecture decision rights
- **condition:** deciding which unit builds or owns which service.
- **decision:** treat the assignment as an architecture decision. Whoever assigns units to services shapes
  the system's architecture, so technical input is required at that decision.
- **why:** it puts architecture choices where technical judgement can reach them. It costs an extra voice
  in organisational decisions.
- **check:** verify technical input was recorded before the assignment is final. If a purely
  administrative or budget-holding party made it without that input, flag a governance defect before
  finalising.

### 20. Platform roadmap decision rights stay with the platform, not consumers
- **condition:** a platform unit receives feature requests from the units that consume it.
- **decision:** the platform owns its roadmap. It curates toward consumers' longer-term needs, using
  feature-usage measurements to rank work; consumers influence the roadmap and do not direct it.
- **why:** it keeps the platform coherent for all consumers rather than shaped by the loudest one. It
  costs individual consumers waiting for features they want now.
- **check:** the platform really runs in service mode with several consumers. If one consumer effectively
  sets the roadmap alone, the relationship has slid back into unmanaged collaboration: investigate.

### 21. Periodic boundary re-check, triggered by named symptoms
- **condition:** a periodic review of whether an existing unit's boundary still fits; for human units the
  interval is several months.
- **decision:** redesign the boundary, instead of adding process or headcount, when any of these shows:
  (a) the unit crossed a size or coordination limit, or one member or sub-part is routinely the bottleneck
  for a component; (b) delivery cadence is slowing; (c) the unit struggles to integrate a growing set of
  shared dependencies, where the fix is a thin platform wrapper. For (b), first tell a new hard dependency
  or silo apart from accrued technical debt, since each needs a different fix; when planning the change,
  publish the expected timeline up front, knowing it will slip.
- **why:** named symptoms turn a vague unease into a redesign trigger, and a published timeline keeps a
  transitional structure from setting into a permanent one. It costs redesign work and a period of
  instability.
- **check:** communication paths are stable enough to give real signal; skip the check during constant
  reorganisation. Reorganise no more often than the interval allows. For an agent unit, the bottleneck
  reads as an unacknowledged single routing point, and the interval may be much shorter but must still be
  long enough to accumulate signal: derive it and record it.

### 22. Every unit declares a dependency-count threshold
- **condition:** a unit is created (declare the threshold) and from then on (read the count).
- **decision:** count the unit's dependencies on other units, classed as knowledge, task or resource;
  declare a threshold and an alert on that count. Crossing the threshold triggers a boundary redesign,
  never more coordination; a dependency inside the unit's own group is acceptable, one crossing into
  another group warns that the role or the work assignment is wrong.
- **why:** the count is the structural numeric limit any unit can carry, human or agent, and it catches
  creeping coupling. It costs maintaining the dependency inventory.
- **check:** dependencies are visible; if nobody can list them, the list is the first deliverable. When the
  threshold is crossed and the proposed answer is a meeting, a liaison or a process step, reject it and go
  to rule 12.

### 23. Shared or transferred ownership is gated by a declared SLO and error budget
- **condition:** a specialist unit is about to run, or co-run, something a different unit built, or to
  hand it back.
- **decision:** transfer only once the owner declares a service-level objective with an error budget.
  Responsibility moves to the specialist when scale warrants it and the objective is agreed; it returns to
  the builder when operability falls below the budget or usage drops, and may move again once the budget is
  met.
- **why:** the agreed number, not the org chart, decides who runs the thing, in both directions. It costs
  instrumenting and tracking the objective.
- **check:** usage is high enough for an objective to mean something; below that the builder keeps it and
  no transfer arises. Refuse any transfer proposed without a declared objective and error budget, because
  an ungated transfer turns the specialist relationship into a silo.

### 24. Role-type mix ratio check
- **condition:** reviewing a whole portfolio of units, not a single one.
- **decision:** aim for roughly 6:1 to 9:1 stream-aligned units against all other types, so about one unit
  in seven to ten is not stream-aligned. A materially lower ratio signals over-specialisation and triggers
  a review of every non-stream-aligned unit against rules 9, 10 and 11.
- **why:** it flags unit sprawl cheaply at portfolio level and applies to any kind of unit. It costs a
  coarse signal that cannot judge any single unit.
- **check:** every unit is already typed as exactly one of the four types (rule 8). Use the ratio to choose
  what to re-examine; keep a justified platform unit even when removing it would improve the ratio.

### 25. Funding must not split build from run
- **condition:** budget categories are being set up for a stream's work, or an existing budget structure is
  read while naming a surface's owner.
- **decision:** reject a build-versus-run budget split that pays one unit to build a thing and another to
  operate it. Fund units, not individuals, and avoid project-driven deadlines and large-batch budgets.
- **why:** it stops the build/run split of rule 18 from returning through money even when the unit design
  is right. It costs giving up the budgeting categories finance may prefer.
- **check:** the funding structure is visible; if it is not, that is the finding. If the money forces the
  builder and the operator apart, record the conflict on the owner rather than naming an owner the budget
  contradicts. When a sound unit design fails to deliver, check funding before blaming the design.
