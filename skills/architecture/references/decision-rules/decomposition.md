# Decomposition rules

These rules decide when to break a system apart and how far: whether a split is justified, how big a service should be, who owns which data, how a distributed transaction converges, how contracts and coordination are shaped, when to reuse, how analytical data is served, and how a trade-off is analysed and governed.
Each rule reads condition → decision → why → check. Every decision has a cost; a rule applied without naming its cost has been applied wrong.
A step loads only the rule ids it names (number and slug), never the whole file.

## Where these rules stop

| Question | Who decides it instead |
|---|---|
| What is our strategy, what problem are we really solving, which business metric defines success, what should we build and how do we validate the need | strategy — outside this skill. These rules take the business driver as an input (rule 1) and never produce one. |
| Where the boundary between two teams goes, whether a team is overloaded, how teams interact | the ownership rules |
| Who is allowed to decide what, and how a decision is pushed down | people and roles — outside this skill |
| Role definitions, hiring, assessment, scorecards, compensation, performance management, 1:1s, coaching, accountability, operating cadence | people and roles — outside this skill |
| Legal exposure | a lawyer |
| What a term means, where a model's language changes, which subdomain is core | the `domain` door |
| Storage-engine internals, replication and partitioning mechanics, consistency models in depth | the data-systems rules |
| Dependency direction between components inside one deployable | the component-boundary rules |
| Whether a failing structural check stops the pipeline or only warns | the governance rules (governance rule `manual-stage-in-the-pipeline`) |
| Cloud spend and licence cost as a comparison dimension | these rules carry no cost model: price it yourself and add it as a row of the rule 88 matrix |
| The format, framework or code once the architecture decision is made | nobody: write the code (rules 59 and 87) |

## Conditions that change a rule's footing

- **Rules that presume several people** (1, 8, 9, 28, 37, 44, 63, 93, 99, 100, 101, 102): they assume a separate funder, product owner, data owner, security expert or tech lead. With one person holding every role, run them as a self-check: state the case from each role, answer each objection, and record which objection you overruled. The objection still has to be raised and answered.
- **Connection arithmetic** (rule 38): the specific figures presume many services with many instances. The mechanism binds at any scale: a per-instance pool multiplies by instance count, so recompute for your own numbers.
- **Consumer counts** (rules 11, 65): a breaking schema change costs coordination in proportion to its consumers, and the consumer nobody remembered is the real danger. This binds from two consumers.
- **Sidecar, mesh, platform team** (rules 17, 74, 77, 78, 80): presume enough teams that per-team implementations diverge. Below that, still give an orthogonal concern its own seam, even if the seam is a module; the platform-team ownership model is what does not transfer.
- **Full data mesh** (rules 82, 84): presumes several domain teams, a platform team and a federated governance group. What survives at any scale: analytical data belongs with the domain that owns the operational data, the analytical interface is asynchronous and eventually consistent, and a policy that must hold everywhere runs as code at the point of access.
- **A funder to convince** (rules 1, 2): solo, the sizing still runs; the output is proceed, defer or rewrite, decided by the person who will do the work, and the decision record is written for your future self.
- **Calibrated figures**: 30/70 (rule 24), ~40% shared domain code (rule 25), ~45% shared code as a feasibility signal (rule 3), 500MB replicated-cache ceiling (rules 39, 41), 15 total dependencies per component as an alert (rule 6), 1–2 standard deviations (rule 19), half the teams (rule 78), one-minute gap (rule 85). These are thresholds to set, calibrated on large enterprise codebases. Keep the constraint, recalibrate the figure, record which figure you used.
- **Instruments a rule needs before it can run**: rule 19 needs a statement counter that aggregates by component (most analysers count per file, so post-process); rule 2 needs afferent and efferent coupling per component; rule 6's dependency sizing needs a component-level graph with shared components filterable; rules 21 and 73 need change-frequency history per component from version control (nearly free, and the highest-leverage instrument here); rule 22 needs per-function throughput; rule 38 needs per-service connection-pool metrics streamed centrally; replicated-cache sizing (rules 39, 41) needs record count × record size × maximum expected instances; rule 14 needs runtime monitors, because static analysis cannot see dynamic coupling; rule 54 needs entry-point annotations and a code-walking tool; rule 85 needs message timestamps on the feed.
- **The general stop**: when a decision depends on a measurement you cannot take, say so and record the assumption you used instead. An unmeasured judgement is never presented as a measured one (rule 89).

---

# A. MIGRATION — whether to break something apart, and how

### 1. business-driver-gate
- **condition:** someone proposes breaking a monolithic system into parts.
- **decision:** decompose only for a clear business driver, and accept only two: speed-to-market and competitive advantage. Map each concrete business complaint to one of five characteristics — maintainability, testability, deployability (these give agility, hence speed-to-market), scalability and fault tolerance (these give competitive advantage) — and show that modularity moves it; a complaint that maps to none of the five is one modularity will not fix.
- **why:** it stops decomposition done for its own sake and ties every split to a result the business asked for. It costs weeks of evidence-gathering before any code moves, and it sometimes concludes with a justified no.
- **check:** the complaints are collected in the business's own words before mapping. If the only justification left is that nothing else has worked, stop and do not seek funding; that reason does not justify the cost.

### 2. decomposition-feasibility-gate
- **condition:** a decomposition is justified and you must decide whether the codebase can take it.
- **decision:** per component compute abstractness `A = Σmₐ/(Σm_c+Σmₐ)`, instability `I = Cₑ/(Cₑ+Cₐ)` and distance from the main sequence `D = |A + I − 1|`. If many components sit in the zone of uselessness (too abstract) or the zone of pain (too concrete and brittle), repairing the internal structure is not worth the time: do not decompose this codebase, consider a rewrite.
- **why:** it catches a codebase that will absorb months of shoring-up before it can split. It costs tooling and an analysis pass before any value ships, and can return a rewrite verdict that the metrics alone cannot fully justify.
- **check:** read A and I together — an I near zero means stable if mostly abstract and rigid if mostly concrete, and means nothing alone. No single metric decides; if the picture is ambiguous, get a second architect's reading instead of resolving it yourself.

### 3. decomposition-approach-selection
- **condition:** the codebase passed the feasibility gate and you must choose how to decompose.
- **decision:** largely unstructured source with no definable components → tactical forking (clone the whole monolith per target service, then delete what each does not need). Source that groups like functionality into well-defined or even loosely defined components → component-based decomposition.
- **why:** tactical forking starts at once with no up-front analysis, and costs latent dead code in every service, code no cleaner than the monolith's (only less of it), and inconsistent naming of shared code. Component-based decomposition gives emergent boundaries with no duplication, and costs significantly more elapsed time.
- **check:** look at the actual namespace and directory structure first. Measure the volume of shared code (shared infrastructure, a shared persistence layer) before choosing; around 45% shared code is the starting signal that forking's duplication will disqualify it even on an unstructured codebase. Forking also implies one team per fork.

### 4. service-based-stepping-stone
- **condition:** migrating a monolith toward microservices.
- **decision:** move to service-based architecture first — coarse-grained domain services over one shared database — and only then decide which domains need microservice granularity. It defers breaking the database, needs no operational automation or containers (each domain service ships as the same artefact type the monolith used), shows which domains really need finer grain, and is a purely technical move with no change to business involvement, org structure, or test and deploy environments.
- **why:** it avoids paying for data decomposition, distributed workflows, distributed transactions, automation and containers before any service needs them. It costs an extra migration stage that is easy to mistake for the destination, and you carry the single-database quantum (its scale, fault-tolerance and connection ceilings) for the whole intermediate period.
- **check:** the target really is microservices; if service-based is the end state, you are already done. If the required characteristic is fault tolerance or elasticity specifically, the shared database blocks it, so do not stop here and claim it.

### 5. build-services-from-components
- **condition:** forming services during any decomposition.
- **decision:** build services from components, never from individual classes. A component is a leaf-node namespace with a well-defined role, responsibility and set of operations.
- **why:** services built from components have explainable contents. It costs a component-refactoring phase before any service exists, which delays visible progress.
- **check:** components are identified and flattened first (the Flatten Components step of rule 6), with code living only in leaf namespaces. If you cannot name the component a class belongs to, stop and flatten; the service question is unanswerable until then.

### 6. decomposition-pattern-sequence
- **condition:** executing component-based decomposition.
- **decision:** apply six steps in order: Identify and Size Components → Gather Common Domain Components → Flatten Components → Determine Component Dependencies → Create Component Domains → Create Domain Services. After the first pass, apply them one at a time as ongoing maintenance touches the monolith during migration.
- **why:** service definitions emerge from the structure instead of being guessed. It is slower than opportunistic extraction and delays the first deployed service until late.
- **check:** if a later step shows an earlier one was wrong (a component domain that leaves components homeless), go back rather than proceed. Keep the steps alive as checks: store the prior list of component namespaces, walk the current structure, diff, alert on added and removed components, write the new list back; alert when a component's total dependencies pass ~15 (recalibrate).

### 7. domains-before-services
- **condition:** about to extract the first domain service.
- **decision:** extract no domain service until all component domains are identified and refactored.
- **why:** a component reassigned later to an already-extracted domain would force changes to a live service. It costs late delivery: nothing ships until the whole domain map is settled.
- **check:** the grouping has passed rule 8 `domain-grouping-needs-business-validation`. If domain assignment is still contested for any component, halt all extraction, not only that component's.

### 8. domain-grouping-needs-business-validation
- **condition:** grouping components into logical domains.
- **decision:** the grouping passes two tests: no component is left out, and cohesion inside each domain is good. If either fails — especially if some components belong nowhere — resolve it with the product owner or business sponsor, not with more technical reasoning.
- **why:** domains that the business recognises survive later change. It costs a dependency on a stakeholder's availability and opinion inside what looks like a technical step.
- **check:** components are sized, gathered and flattened first. Homeless components are the escalation trigger. Solo, name each domain in the business's vocabulary and see whether every component fits; the vocabulary question itself goes to the `domain` door.

### 9. architecture-story-not-tech-debt
- **condition:** a structural refactoring needs to be scheduled.
- **decision:** write it as an architecture story — the refactoring, then the characteristic or business need it serves — kept distinct from a technical-debt story. Tech debt is cleanup for later; an architecture story is a change needed soon to support a named characteristic or business need.
- **why:** structural work gets prioritised by what it supports instead of sinking with cleanup. It costs a second story type competing for the same capacity and a justification conversation for work that would otherwise pass unnoticed.
- **check:** the refactoring ties to a named characteristic or driver; if it does not, it is tech debt. Solo with no backlog, the distinction still sets the order of work.

---

# B. COUPLING — quantum, static, dynamic

### 10. quantum-count-by-bootstrap
- **condition:** you need to know how many architecture quanta a system really has.
- **decision:** for each candidate ask whether each dependency is needed to bootstrap the service: OS and container, every transitively resolved framework and package (read the build and container manifests), persistence, integration points needed to boot, any message broker. That set is the quantum's static coupling, and any shared coupling point — a shared database, a mediator or orchestrator, a tightly coupled UI — collapses the whole system to one quantum however many services are deployed.
- **why:** it gives an honest count of what can be deployed, scaled and fail independently. The honest count usually destroys a claimed benefit and forces either a data split or the admission that the system is one quantum; there is no cheap fix.
- **check:** count bootstrap dependencies, not call partners — services that only meet in a workflow are statically independent. If the count comes out at one when you believed many, stop and re-plan; the per-service characteristics you promised are not available.

### 11. shared-database-caps-quantum
- **condition:** designing or evaluating a distributed architecture with a shared database.
- **decision:** a shared database fails independent deployment unless the database is deployed in lock step with the application. If two services need different characteristics or independent fault tolerance, split the data; no amount of service decomposition substitutes.
- **why:** it stops promising per-service properties the data layer cannot deliver. Splitting costs every foreign key, view, trigger and stored procedure crossing the new line, loses referential integrity in the database, and turns joins into service calls.
- **check:** the database is genuinely shared, not merely co-located. If the data integrators of rule 37 `data-decomposition-balance` make the split infeasible, stop claiming per-service characteristics and design deliberately for one quantum.

### 12. ui-coupling-collapses-quantum
- **condition:** a distributed backend sits behind a single user interface.
- **decision:** a tightly coupled UI reduces the backend to one quantum, because the UI stops working when part of the backend is down and services cooperating in one UI cannot have different operational characteristics. To keep several quanta, make front and back asynchronous, usually with micro-frontends where each service emits its own UI elements onto a canvas that composes them through events.
- **why:** it preserves independent quanta end to end. It costs a composition layer, an event contract between UI fragments, and per-service UI ownership.
- **check:** test the UI's actual failure mode with one backend down. If micro-frontends are not viable, stop promising per-service scalability or elasticity and design UI plus backend as one quantum.

### 13. three-forces-chosen-together
- **condition:** deciding how two services interact at runtime.
- **decision:** choose communication (synchronous or asynchronous), consistency (atomic or eventual) and coordination (orchestrated or choreographed) together, as one point in a three-dimensional space, then read off the resulting pattern and coupling level from the eight-row table of rule 55. Transactions are easier in synchronous mediated designs; scale comes from eventual, asynchronous, choreographed ones.
- **why:** each choice pulls on the other two, so deciding them one by one lands on combinations nobody chose. It is slower than deciding each as it arises, and fixes the coupling level early, constraining later optimisation.
- **check:** all three dimensions are stated explicitly; an unstated one was chosen by default. If you land on asynchronous + atomic + choreographed (aac), stop and reopen the consistency requirement.

### 14. dynamic-coupling-needs-monitors
- **condition:** governing coupling.
- **decision:** govern static coupling at build time from manifests and dependency tools; govern dynamic coupling, which exists only at runtime, with continuous fitness functions, usually monitors. Build a call graph from consistent observability logs across every service: who calls whom, when, and how often.
- **why:** runtime coupling becomes visible and checkable. Continuous monitoring is ongoing operational cost and yields data nobody reads unless a fitness function acts on it.
- **check:** logging is consistent across services, since inconsistent logs produce a false graph. If you cannot observe the call graph, report the dynamic coupling as unknown. The principle applies at any scale; building dedicated tooling for it is a multi-team investment.

### 15. static-coupling-diagram-as-blast-radius
- **condition:** you need to know what a change will break, or you are learning a legacy architecture.
- **decision:** build the static quantum diagram as a reliability analysis that answers, for anything in architecture or operations, what might break if it changes. Its outputs are what must be tested when a service changes and where teams affect one another; generate it from container manifests, build files and package dependencies, and automate it into the build when environments are already generated.
- **why:** test scope and team impact come from evidence instead of memory. No off-the-shelf tool fits a specific mix, so it is a custom build, and it decays silently unless it is emitted by the same process that builds the system.
- **check:** pure workflow partners are left out; they are dynamically, not statically, coupled. Verify the diagram is regenerated by the build, not maintained by hand.

### 16. semantic-coupling-is-a-floor
- **condition:** any workflow must be modelled.
- **decision:** implementation can never reduce the domain's semantic coupling, only add to it. Model that coupling in one place — an orchestrator, the domain services or the contract — and align implementation partitioning with domain partitioning, because each technical layer imposed on top adds complexity to complexity you already had.
- **why:** it stops simplification effort aimed below the irreducible floor. Technical partitioning was often chosen for real savings (consolidated database connection pooling, for example), and aligning to domains gives those savings up; cost has often won that argument.
- **check:** the domain workflow is written down, or you cannot see the floor. If the business's semantics themselves are impractical or impossible, push back to the business instead of absorbing them in the architecture.

### 17. orthogonal-coupling-gets-its-own-seam
- **condition:** a capability must cut across the architecture's primary seams — operational concerns across domain services, or analytical data across operational services.
- **decision:** treat it as orthogonal coupling (two distinct purposes that must still intersect) and give it a separate, consistent layer instead of threading it through the domain seam. The sidecar is the pattern, a service mesh is a sidecar present everywhere, and the data product quantum (rule 82) is the same move for analytical data.
- **why:** domain services stay free of plumbing and the plumbing stays uniform. One sidecar per platform must be built and maintained, it can grow large, and every team pays its overhead, including teams that use none of it.
- **check:** the concern has no domain responsibility — logging, monitoring, service discovery, authentication and access control qualify; an `Address` or `Customer` class does not. When unsure, treat it as domain and keep it out; a shared technical utility is a genuine judgement call settled by rule 78. With few teams, the seam can be a module; the platform-team ownership model needs many teams.

---

# C. GRANULARITY — how big a service should be

### 18. granularity-equilibrium
- **condition:** deciding whether to split or merge services.
- **decision:** weigh six disintegrators — service scope and function, code volatility, scalability and throughput, fault tolerance, security, extensibility — against four integrators — database transactions, workflow and choreography, shared code, data relationships — and aim for equilibrium between them. A justification usually rests on several drivers, not one.
- **why:** it prevents both the distributed monolith and the unmaintainable coarse service. Walking both lists on every boundary decision is slow.
- **check:** both lists were actually walked; the common failure is running only the disintegrators. If the two sides genuinely balance, escalate with rule 28 `tradeoff-statement-to-the-business` instead of breaking the tie yourself.

### 19. size-by-statements-not-classes
- **condition:** measuring the size of a component or service.
- **decision:** measure statements (one complete action, usually ending in a semicolon or newline) and the number of public interfaces or operations exposed; never lines of code, class count or file count, which vary with each programmer's style. For components, target sizes within one to two standard deviations of the mean, with the share of code roughly even across components.
- **why:** the number measures what the unit does, not the writer's style. Statements still carry some subjectivity, and forcing an even spread can produce artificial splits that satisfy the metric and damage cohesion.
- **check:** a tool aggregates statements by component, not by file (post-process if it does not). A large outlier with no clear sub-domains stays as it is; size alone never licenses a split.

### 20. leftover-naming-test
- **condition:** any split, whatever the driver.
- **decision:** after any split, check that the leftover functionality forms a strongly cohesive unit with a good self-descriptive name. If the remainder can only be named by negation (other X, non-X), the split is wrong: do not split, or split further. Conversely, a service too hard to name because it does several things is a candidate to break apart.
- **why:** it is the cheapest cohesion test available. Honouring it often turns a two-way split into a three-way one, multiplying deployment units, contracts and operational surface beyond what the driver needed.
- **check:** write the actual proposed names down, not imagined ones. Always run it; it costs minutes.

### 21. volatility-based-split
- **condition:** parts of a service change at very different rates.
- **decision:** measure change frequency per functional area from version control and split so the frequently changing code is isolated. Example: two channels changing every ~6 months and a third changing weekly → one service for the stable pair, one for the volatile channel.
- **why:** smaller test scope and deployment risk, and stable functions stay available while the volatile one deploys. Each split adds a deployment unit, a contract and possibly inter-service calls; if the halves must then talk synchronously, the isolation is nullified.
- **check:** the remainder is nameable and cohesive (rule 20 `leftover-naming-test`). If volatility is asserted rather than measured, check the repository first; confident estimates of change rate are often wrong.

### 22. throughput-based-split
- **condition:** functions inside one service have very different scalability demands.
- **decision:** measure throughput per function and split when the spread forces low-demand functions to scale with high-demand ones. Example: 220,000 requests/min, 500/min and 1/min for three functions → three services, since consolidated the two quiet functions scale needlessly with the loud one, raising cost and hurting elasticity through mean time to start.
- **why:** each function scales at its own cost. It adds deployment units and operational surface and, if the functions shared code, either duplication or a new shared package with its own versioning burden.
- **check:** the figures are measured. If the resulting services must call each other to complete one request, re-check against rule 24 `workflow-integrator-30-70`.

### 23. fault-tolerance-split-requires-independence
- **condition:** splitting a service to isolate a crash-prone function.
- **decision:** the split buys fault tolerance only if the resulting services do not depend on each other synchronously. Services that must talk to each other gain nothing in fault tolerance from being separate.
- **why:** it stops paying for isolation that is not delivered. Real independence usually needs asynchronous communication, which costs eventual consistency, harder error handling and a broker in the static coupling.
- **check:** check the dependency in both directions, including error paths. If the pieces stay tightly coupled and dependent, keep the service together.

### 24. workflow-integrator-30-70
- **condition:** deciding whether services that talk to each other should be merged.
- **decision:** count requests needing inter-service workflow against purely atomic ones: about 30% workflow / 70% atomic → separate services are acceptable; reversed → merge them. Two overrides: where no end user is waiting (backend work) there is more leeway, and one critical request needing very fast response inside the minority can outweigh the majority.
- **why:** latency is paid per hop — price it at about 300 ms of network plus security latency per hop, so five hops cost 1,500 ms. Merging to fix latency gives back everything the split bought: independent scaling, independent deployment, isolated test scope.
- **check:** requests can be attributed to workflow or atomic, and the latency is priced. The percentages are ratios and hold at any scale. If criticality is contested, escalate as a trade-off statement (rule 28) instead of deciding on the percentage alone.

### 25. shared-domain-code-integrator
- **condition:** several candidate services would share code.
- **decision:** three conditions make shared code a reason to keep services together: shared domain functionality above a high share of the combined codebase (starting threshold: over 40%); frequent changes to that shared code, since versioning only defers the coordinated adoption; and defects that cannot be versioned because the fix must reach every service at once. Shared infrastructure code — logging, auditing, authentication, access control, monitoring — is not a reason to merge.
- **why:** it merges only where sharing really binds the services. A merged service has wider test scope, higher deployment risk and uniform scaling for functions with uneven demand.
- **check:** the shared code is classified as domain or infrastructure — that classification is the whole rule. If it encodes business logic, it is domain. Recalibrate the 40% for your codebase and record the figure used.

### 26. data-relationship-integrator
- **condition:** two candidate services would each need constant read access to the other's tables.
- **decision:** map functions to tables (owner writes and reads; accessor only reads). If every operation in one service would need the other's table and vice versa, merge them: the bounded context forbids direct cross-access, so the split guarantees permanent back-and-forth calls. This integrator carries the fewest trade-offs of the four, so weight it most when signals disagree.
- **why:** it avoids a split that pays for itself in chatter forever. Merging forfeits the disintegrator that motivated the split and yields a service that scales, deploys and fails as one.
- **check:** the function-to-table map is built, not estimated. Reorganising the table relationships to rescue the split is rarely feasible; propose it only with its own justification.

### 27. design-before-architecture
- **condition:** a characteristic, usually security, is being used to justify a service split.
- **decision:** check whether design can deliver the characteristic before spending an architectural split on it. Security can come from design (a shared encryption package, tokenised and encrypted data enforced at the API gateway and service mesh) instead of separate deployment units; namespaced components inside one service can satisfy a change-isolation demand without a second deployable.
- **why:** it avoids a deployment unit whose only job a mechanism already does. The design mechanism becomes a hard dependency to record in the decision, and the merged service still has wider test scope, higher deployment risk and uniform scaling.
- **check:** the design mechanism exists and is already in use; it is not a promise to build one. If it does not exist yet, the split is back on the table.

### 28. tradeoff-statement-to-the-business
- **condition:** a granularity decision, or any architecture decision, is genuinely balanced.
- **decision:** turn it into a trade-off statement: name both options and what each costs, then ask the product owner or sponsor which the business values more. Shape: we want X, but doing so loses Y; which matters more for the business, benefit A or benefit B? Then honour the answer.
- **why:** the people who carry the consequence choose it. It hands the decision to someone with less technical context, the answer may be one the architect disagrees with and still honours, and it spends stakeholder time on a decision they did not expect.
- **check:** both costs are stated in business language, not architecture vocabulary (rule 93 `bottom-line-not-evidence`). This rule is itself the escalation path. Solo, the shape still forces both costs into the open before choosing.

### 29. extensibility-driver-deferred
- **condition:** someone proposes a split because more of something will be added later.
- **decision:** use extensibility as a split driver only when the expansion is already known, planned or intrinsic to the domain (payment types keep growing; notification channels rarely do). Otherwise wait until a pattern of growth is established or confirmed.
- **why:** no speculative split. When the expansion does arrive, you pay for the split under time pressure instead of at leisure.
- **check:** the claim of future growth is checked with someone who would know; a sponsor expecting only two or three additions over a couple of years reverses the decision. If the pattern cannot be confirmed, defer.

---

# D. DATA OWNERSHIP AND ACCESS

### 30. writes-determine-ownership
- **condition:** assigning table ownership to services.
- **decision:** the service that writes to a table owns it, however many others read it. Resolve single ownership first, then common, then joint, so the simple cases clear the field before the hard ones.
- **why:** ownership follows the data's lifecycle, not its traffic. The owner is often not the heaviest user, so the busiest reader inherits a data-access problem with performance and fault-tolerance cost.
- **check:** read and write access are distinguished per service. If a read-heavy consumer says it cannot tolerate remote reads, keep ownership where it is and solve the read with rule 39 `data-access-pattern-selection`.

### 31. common-ownership-dedicated-owner
- **condition:** most or all services need to write to the same table (audit, logging-like data).
- **decision:** create a dedicated service as the sole owner; the others send it data to write. No return value needed → asynchronous fire-and-forget over a persisted queue (stored on disk by the broker, so delivery survives service or broker failure); a return value needed (a confirmation number, a key) → synchronous REST, gRPC or request-reply messaging.
- **why:** one writer keeps the bounded context intact. It costs a new service to build, deploy, scale and monitor, a queue in every writer's static coupling, and eventual consistency for the record.
- **check:** the shared-schema alternative has been rejected, because it brings back change control, connection starvation, scalability and fault-tolerance problems.

### 32. joint-ownership-four-techniques
- **condition:** two services in the same domain both write to one table.
- **decision:** evaluate all four and pick the one whose cost you can carry. **Table split**: each owns its part; costs restructuring, no ACID transaction across the halves, a permanent sync obligation, possible replication, and a forced CAP choice — availability (the creator proceeds when the partner is down) or consistency (creation fails when it is down). **Data domain (shared schema)**: both own it in a wider bounded context; costs schema changes touching several services, wider test scope, higher deployment risk, and write-responsibility governance added separately. **Delegate**: one owner, the other asks it to write; costs high coupling, slow non-owner writes, no atomic transaction for them, low fault tolerance for the non-owner. **Service consolidation**: merge the owners; keeps atomic transactions and costs coarser scaling, shared failure, higher deployment risk and wider test scope.
- **why:** joint ownership has no free option, so the choice is which cost to carry. Each technique's cost is stated with it.
- **check:** the two services really are in the same domain; otherwise it is common ownership or a boundary error. If a service already connects to another schema, the data-domain option is eliminated by constraint (one schema per service), not by preference.

### 33. data-domain-requires-rejustifying-the-split
- **condition:** choosing a shared data domain for joint ownership or for data access.
- **decision:** re-examine why separate services are needed at all when they share the data. Valid reasons: scalability differences, fault-tolerance needs, throughput differences, isolating code volatility; if none applies, the two services should be one.
- **why:** it catches two services that are one service on two deployables. The re-examination may invalidate a split already built and force an unbudgeted merge.
- **check:** name the reason in writing. If none can be named, merge rather than ship two services over one schema.

### 34. delegate-by-domain-priority
- **condition:** using the delegate technique and choosing which service owns the table.
- **decision:** two options: primary domain priority (the service doing most of the entity's CRUD owns it) or operational-characteristics priority (the service needing more performance, scale, availability or throughput owns it). Prefer domain priority, and fix the resulting performance and fault-tolerance problems with a replicated in-memory cache or a distributed cache.
- **why:** ownership stays with the domain that understands the data. The frequently updating non-owner pays a remote call on every write; synchronous delegation costs performance, asynchronous delegation costs consistency and integrity (the non-owner has no guarantee its write happened).
- **check:** identify both services — the CRUD-heavy one and the high-demand one are usually different. Operational priority makes the high-throughput service responsible for database work and error handling on data it does not own; if that is unavoidable, escalate it instead of absorbing it silently.

### 35. never-reach-into-another-database
- **condition:** a service needs data owned by another service.
- **decision:** get it through the service that owns the data domain, never by reaching into its database; each service connects to exactly one schema. Cross-schema synonyms are a temporary migration aid only — coupling points to break later, shifting integration out of the schema and into the services.
- **why:** schema changes stay local to their owner. Every removed cross-domain join becomes a runtime call with latency, availability and contract cost (a view that supplied a customer name becomes a call to the customer service).
- **check:** ownership is assigned. If the owner cannot serve the read volume, use rule 39 `data-access-pattern-selection`; a second schema connection is never the exception granted.

### 36. data-sovereignty-costs
- **condition:** committing to database-per-service.
- **decision:** accept three consequences in writing: performance problems when services need large data volumes; referential integrity no longer enforced by the database, so bad data can enter; and all database code touching other domains' tables (stored procedures, functions) moves to the service layer. If you cannot carry all three, do not claim data sovereignty.
- **why:** it buys teams that change their schemas without affecting other domains, and a database type suited to each service. The three consequences are its price.
- **check:** the cross-domain database artefacts are inventoried — foreign keys, views, triggers, functions, stored procedures. If referential integrity is a hard domain requirement, consider the data-domain technique (rule 32) instead.

### 37. data-decomposition-balance
- **condition:** deciding whether to break apart a database.
- **decision:** weigh six data disintegrators — change control, connection management, scalability, fault tolerance, architectural quanta, database-type optimisation — against two data integrators — data relationships (foreign keys, triggers, views, stored procedures, logical relationships) and database transactions (the single ACID unit of work). Adjudicate in explicit pairs: is change control worth more than this foreign key; is fault tolerance worth more than this materialised view?
- **why:** every disintegrator honoured costs an integrator — change control costs foreign keys, fault tolerance costs materialised views, and any split costs the single unit of work. The pairs make each loss a named choice.
- **check:** the data owner or DBA is in the conversation from the start. If they are unconvinced, do not proceed on architectural standing; gather evidence per driver (contention logs, connection projections from real traffic, outage blast radius) and return. Solo, argue the data owner's side through the pairs.

### 38. connection-wait-diagnostic
- **condition:** frequent request timeouts or tripped circuit breakers against a shared database.
- **decision:** check for connection waits first; they are the first sign the connection limit is reached and they show up disguised as timeouts and breaker trips. Then govern with connection quotas: start with even distribution, instrument concurrent use per service with fitness functions, keep quota values in an external configuration server adjustable by hand or program, and move to variable distribution as real needs emerge.
- **why:** it finds the real cause and buys time. Quota governance is ongoing work that only defers the split, and variable distribution needs knowledge of each service's function and scaling you may lack.
- **check:** per-service connection metrics are streamed centrally. A quota becomes invalid the moment services scale — five services tuned to exactly 100 connections can reach 242 once instances multiply; when scaling invalidates the quota, stop tuning and split the data.

### 39. data-access-pattern-selection
- **condition:** a service needs read access to data it does not own.
- **decision:** choose by which ceiling binds. **Inter-service communication**: simplest, no volume limit; costs network latency (30–300 ms) + security latency (20–400 ms) + data latency (10–50 ms), up to about a second, no fault tolerance, the owner scaling with the consumer, and a contract. **Column schema replication**: copy the column into the consumer; costs consistency, lost ownership governance (others can update data they do not own) and a sync mechanism to build; reserve it for aggregation, reporting, or when volume, responsiveness or fault tolerance rule out the rest. **Replicated caching**: in-memory per service, continuously synced, writable only by the owner; costs a consumer that cannot first start until the owner is up, volume × instances (feasibility falls fast above ~500MB — five instances of 500MB is 2.5GB), unsuitability for high update rates, and hard broadcast configuration in cloud and containers. **Data domain (shared schema)**: costs a wider bounded context, write governance, a consumer that sees everything in the domain, and a table schema that becomes the contract with nothing shielding consumers from change.
- **why:** each pattern trades a different ceiling, and only inter-service calls and replicated caching preserve ownership. The costs are stated per pattern.
- **check:** read frequency, data volume, update rate and consistency requirement are measured; each decides a different ceiling. If the service already connects to another schema, the data-domain option is out by constraint.

### 40. protocol-change-is-not-decoupling
- **condition:** someone proposes switching from REST to messaging to remove a synchronous dependency.
- **decision:** a protocol change does not change coupling. If the caller must wait for the answer to proceed, it is synchronously coupled whatever the transport.
- **why:** it closes off an apparent easy fix. It forces the harder conversation: caching, replication, merging, or accepting the dependency.
- **check:** ask whether the caller can proceed without the answer. Apply the correction immediately; no escalation needed.

### 41. distributed-cache-is-not-replicated-cache
- **condition:** considering an external caching server to share data between services.
- **decision:** a distributed cache does not solve distributed data access: it moves the fault-tolerance dependency from the owner to the cache server, breaks the bounded context because any service can update the shared cached data, and returns network latency because access is remote. Use a replicated cache (in-memory in each service, owner-writable, continuously synced), from a product that supports it, such as Hazelcast, Apache Ignite or Oracle Coherence.
- **why:** the owner stays the only writer and reads stay local. Replicated caching brings a licence cost and a team-capability risk, so price the licence and run a proof of concept first (rule 42).
- **check:** the product supports replication — re-verify against current tooling before acting. If no replicated-cache product is available, this pattern is out; never substitute a distributed cache and claim the same properties.

### 42. proof-of-concept-unfamiliar-technique
- **condition:** the chosen pattern uses a technique nobody on the team has used.
- **decision:** name it as a risk in the decision record and split the investigation: one person researches products and runs proofs of concept; another prices licensing and checks deployment-environment limits (availability-zone crossings, firewalls). Confirm feasibility on cost and on effort before the record is final.
- **why:** unfamiliarity is surfaced before commitment. The proof of concept delays the decision and consumes capacity on work that may be thrown away.
- **check:** the team was asked directly whether anyone has done it. If the proof fails on cost or environment, return to pattern selection rather than proceed on optimism. Solo, run both halves yourself.

### 43. database-type-selection
- **condition:** choosing a database type for a newly separated data domain.
- **decision:** rate candidates on seven characteristics — learning curve, ease of data modelling, scalability and throughput, availability and partition tolerance, consistency, language support with product maturity, SQL support and community, and read/write priority — and know each type's expensive operation: key-value (changing the aggregate means rewriting all data; queryable only by key), document (sharding-key choice as volume grows; ACID only within a collection), column family (row-key design takes several iterations), graph (changing a relationship type means recreating every edge, visiting both nodes; hard to shard, so write throughput is limited), NewSQL (sharding design including geographic placement), cloud-native (learning curve varies by product; the scaling trade-off is price), time-series (not general purpose; append-only).
- **why:** the store fits the data's shape. Polyglot persistence multiplies operational surface, required skills and hiring difficulty, which is why a data architect's default refusal is legitimate.
- **check:** the data is characterised (relational, aggregate, time-stamped, graph-shaped) instead of assumed relational. Products within one type differ on availability and consistency tuning, so evaluate the product, not the category; re-verify against current tooling before acting.

### 44. polyglot-needs-a-business-justification
- **condition:** proposing a different database type for one data domain.
- **decision:** developer or UI convenience is not enough; obtain a business justification. Valid evidence looks like changes that take days, a business unit asking for flexibility and responsiveness, or change requests being withheld because people expect frustration and unplanned cost.
- **why:** the migration is paid for by a business result. The search costs stakeholder meetings and may show the change is not worth it, and the migration itself usually means downtime for the affected function.
- **check:** the data owner had the chance to refuse, and a refusal on convenience grounds was accepted as legitimate. With no business justification, drop the proposal. Solo, name the business consequence of not changing, in the business's terms.

### 45. model-both-aggregates
- **condition:** choosing an aggregate boundary in a document database or any aggregate-oriented store.
- **decision:** model both options concretely and compare them side by side — one aggregate with children embedded, or split aggregates with references — and let a cardinality or change-pattern fact break the tie, not either party's convenience. Example: with only five parent types and most changes adding or removing children, duplication is cheap and reuse is worth little, so embed.
- **why:** the choice rests on a fact about the data. Whichever wins, its cost goes in the decision record — embedding means a common child change must be applied to several documents.
- **check:** both models are written out, not described. If no cardinality or change-pattern fact is available, gather one before deciding.

### 46. schema-migration-downtime-choice
- **condition:** moving schemas to separate physical database servers.
- **decision:** choose between backup and restore (back up each schema, stand up servers, restore, repoint services, drop originals) and replication (stand up servers, replicate, switch connections, drop originals). Backup and restore usually needs downtime; replication avoids it.
- **why:** the trade is downtime against setup work. Replication costs more setup and more coordination; there is no option that costs neither.
- **check:** data domains are already separated and each service already accesses only its own schema.

### 47. use-an-existing-message-before-adding-a-call
- **condition:** a service must get data to another service it can no longer write to directly.
- **decision:** before designing a new call or ownership arrangement, check whether a message already flows between the two services and whether its payload can carry the data. If an event already starts the downstream work, let the needed data ride along, and the sender needs no access to the receiver's table.
- **why:** no new coupling point is added. The payload grows (a mild stamp coupling), and an operation that was atomic in the monolith becomes two operations in two services; the decision record must say so.
- **check:** the existing message flows are known — the call graph of rule 14 `dynamic-coupling-needs-monitors` is what makes this possible.

### 48. validate-ownership-against-workflows
- **condition:** table ownership has been assigned across all services.
- **decision:** ownership assignment is not finished until it is validated against the business workflows and their transaction requirements. A map that is locally sensible can be globally unworkable once a workflow needs atomicity across it.
- **why:** it catches broken guarantees before they ship. It often reopens ownership decisions that felt settled, costing rework late.
- **check:** the business workflows are written down. If a workflow needs atomicity across an ownership line, escalate to rule 18 `granularity-equilibrium` or to the saga choice of rule 55 `name-the-saga-by-its-three-dimensions`; never accept the broken guarantee silently.

---

# E. TRANSACTIONS AND CONSISTENCY

### 49. acid-properties-must-be-known-before-trading-them
- **condition:** any decision that would move a business request across service boundaries.
- **decision:** name which ACID properties you give up and how each fails: atomicity binds to the service, not the business request; consistency breaks because one failure desynchronises tables and relational constraints cannot span service commits; isolation disappears, since committed data is visible to other services and requests before the business transaction completes; durability holds only per service. Without this you cannot judge when a distributed transaction is acceptable.
- **why:** the trade is made knowingly. Knowing the cost does not remove it; the honest analysis often shows the split you wanted is unavailable or needs saga machinery nobody budgeted.
- **check:** the business request is traced across every service it touches. If the business states an absolute all-or-nothing requirement (a record must never exist without its companion records), stop distributing that request and consolidate.

### 50. eventual-consistency-pattern-selection
- **condition:** a business request spans services and the data must converge.
- **decision:** pick one of three by what you can give up. **Background synchronisation** (an external process periodically reconciles sources): couples every data source, breaks every bounded context (it needs write access to all tables), ties schema changes to an external batch job, duplicates business logic into it, and is slowest to converge; use it only for closed heterogeneous systems that do not communicate or share data. **Orchestrated request-based** (sync during the request while the user waits): slowest responsiveness, hardest error handling, usually needs compensating transactions. **Event-based** (asynchronous pub/sub of events or commands): complex error handling through a dead-letter queue and eventual human intervention, and needs durable subscribers or a broker that keeps messages in the topic long enough.
- **why:** convergence speed and architecture damage trade against each other: background sync is cheapest to build and most destructive; event-based preserves the architecture and pushes the cost into error handling.
- **check:** you know how long the business tolerates inconsistency for this data (leftover records after a cancellation may be fine until a nightly run). In an architecture that needs tight bounded contexts, such as microservices, background synchronisation is excluded outright.

### 51. compensating-transaction-is-not-a-rollback
- **condition:** designing error handling for an atomic distributed transaction.
- **decision:** treat a compensating update as an operation that can itself fail, not as a rollback, and price four hazards before choosing an atomic saga: no isolation (other services may already have acted on the data being compensated); compensation failure (the reverse operation errors, the data is truly out of sync, and usually only a human can repair it); confusing end-user state (a retry after a failed compensation can produce a second, different error); and responsiveness (the user waits for all corrective action before hearing about the error).
- **why:** compensation does buy data restored to its prior state and the ability to retry and restart. The four hazards are its price and better engineering does not remove them.
- **check:** the downstream consumers of committed-then-compensated data are listed; compensating them may need compensation of its own, recursively. When a compensation fails, escalate to human repair; no automated layer sits beneath it.

### 52. prefer-state-management-over-compensation
- **condition:** an error occurs mid-workflow and the business allows eventual convergence.
- **decision:** instead of compensating, change the saga's state, answer the user successfully, and resolve behind the scenes: retries and error analysis first, then escalation to an administrator or supervisor for manual repair if unresolved. The end user does not carry the failed step; the orchestrator does.
- **why:** the user sees no failure for a step that can converge later. Data may be out of sync while errors are open and convergence can take time; a visible, immediate failure becomes an invisible, delayed one.
- **check:** the business genuinely tolerates the temporary inconsistency for this data; if not, this rule does not apply. Someone actually watches the error queue, and the manual-repair path is designed, with a person to escalate to.

### 53. saga-state-machine-required
- **condition:** a distributed transaction has more than a trivial number of steps.
- **decision:** whatever the error technique, make the transaction's state known and managed: model it as an explicit state machine with a start and an exit node, then produce a transition table (initiating state → transition state → action) that developers implement directly, in the orchestrator or in each service if choreographed. Model waiting as staying in a state, not as failure.
- **why:** every error path has a defined destination. It is up-front design work, a second artefact to keep in sync with code, and it exposes how many error states exist, which can stall a decision that was moving on optimism.
- **check:** every state's possible outcomes are enumerated, including which states have exactly one. A state whose error path has no destination is unfinished; do not implement it.

### 54. saga-scope-from-annotations
- **condition:** you need to know which services take part in a business transaction, for test scope or change impact.
- **decision:** declare all sagas in one enum, tag each service's entry point with the sagas it joins (annotations in Java, custom attributes in C#), and write a small code-walking CLI that answers which services are in saga X. Distributed transactions are designed, coded and maintained by the team, so this replaces the visibility a transaction manager would give.
- **why:** test scope and change impact are answerable on demand. The annotations are metadata with no runtime behaviour, so they drift silently and are worthless once wrong, and the tool is a custom build nobody owns unless assigned.
- **check:** service entry points are identifiable (a marker annotation on each entry point, itself a legitimate case of code replication). Assign an owner for the tool and verify the tags against the real call graph (rule 14).

### 55. name-the-saga-by-its-three-dimensions
- **condition:** any discussion of how a distributed transaction should work.
- **decision:** before arguing, name the combination — communication (s synchronous / a asynchronous) × consistency (a atomic / e eventual) × coordination (o orchestrated / c choreographed) — and read its properties off the table:

  | Code | Combination | Coupling | Complexity | Responsiveness | Scale/elasticity |
  |---|---|---|---|---|---|
  | sao | sync · atomic · orchestrated | Very high | Low | Low | Very low |
  | sac | sync · atomic · choreographed | High | High | Low | Low |
  | seo | sync · eventual · orchestrated | High | Very low | Medium | High |
  | sec | sync · eventual · choreographed | Medium | Low | Medium | High |
  | aao | async · atomic · orchestrated | High | High | Low | Low |
  | aac | async · atomic · choreographed | Medium | Very high | Low | Medium |
  | aeo | async · eventual · orchestrated | Low | Low | High | High |
  | aec | async · eventual · choreographed | Very low | High | High | Very high |
- **why:** the table is the trade-off statement. Two structural facts: coupling and complexity move in opposite directions (aec is least coupled and highly complex; sao is most coupled and simple), and atomic consistency caps scale in every row where it appears.
- **check:** all three dimensions are stated for the workflow. If the combination is aac, stop and reopen the atomicity requirement; its complexity is the worst of all eight.

### 56. dont-default-to-epic-saga
- **condition:** a stakeholder demands that state changes synchronise, or an architect reaches for the familiar transaction model.
- **decision:** the sao pattern (synchronous, atomic, orchestrated — the classic epic saga) is the most tightly coupled of the eight and very low on scale and elasticity; familiarity from monoliths and a stakeholder's demand for synchronised state, regardless of technical constraints, do not justify it. Consider seo first (synchronous, eventual, orchestrated — the lowest complexity of all eight) or aeo (asynchronous, eventual, orchestrated — low coupling, low complexity, high responsiveness, high scale).
- **why:** sao does buy transactional coordination that mimics the monolith, a clear workflow owner, and low complexity, since synchronous calls remove race conditions and deadlocks. It costs coupling, responsiveness and scale.
- **check:** confirm whether the atomicity demand is a real business constraint or an inherited assumption. If the business genuinely needs all-or-nothing, honour it by consolidating the services (rule 32, service consolidation) instead of building sao across them.

### 57. never-optimize-one-dimension-in-isolation
- **condition:** you are about to change one of the three dynamic-coupling dimensions to fix a problem.
- **decision:** asynchronous communication improves performance only when considered alone; entangled with consistency and coordination, it can make things worse. Starting from sao, seeing slow performance, adding asynchrony and choreography while keeping atomicity lands on aac, the worst pattern; keeping atomicity while only going asynchronous lands on aao, which is common for exactly this reason.
- **why:** it prevents locally correct steps from summing to the worst combination. It is slower than a targeted fix, and the honest answer is often that performance cannot improve without giving up the consistency guarantee — a harder conversation than a protocol change.
- **check:** you can name all three current values and all three proposed ones. If the change keeps atomic consistency while loosening the other two, stop; the atomicity requirement is what must be re-examined.

### 58. dont-lock-participating-services
- **condition:** a mediator coordinates a multi-service transaction and a second request reaches a service mid-workflow.
- **decision:** keep participating services open to other calls during a workflow; having the mediator make them refuse calls guarantees a valid transaction and destroys performance and scalability, and is worse when the calls are asynchronous.
- **why:** throughput and scale survive concurrency. The cost is that a second request may act on data the first workflow later compensates — the isolation problem, unmitigated.
- **check:** the concurrent-request case was recognised at all; sagas are easy to design for one workflow at a time. If concurrent contingent requests truly cannot be tolerated, escalate to consolidation instead of locking.

---

# F. CONTRACTS

### 59. contract-type-before-contract-format
- **condition:** someone proposes an integration technology because it is fast or fashionable.
- **decision:** decide strict versus loose first; that is the architecture decision. The format (gRPC, REST, GraphQL, JSON, messaging) is implementation and can be delegated, provided it passes the fitness functions.
- **why:** the decision that shapes coupling is made deliberately. It defers a concrete, motivating technology choice behind an abstract discussion, which can read as bureaucracy to whoever proposed it.
- **check:** the fitness functions that bound the delegation are actually built; without them the delegation is unbounded. Apply the reframing immediately.

### 60. need-to-know-contract-level
- **condition:** defining what a contract carries.
- **decision:** include only what the consumer needs. Fields added just in case are an anti-pattern: if a consumer needs only a name but the contract carries the whole profile, an unrelated profile change breaks the contract and forces coordination.
- **why:** it balances semantic coupling against needed information without needless fragility. Minimal contracts must be revised when a consumer's needs really grow — rare planned changes instead of frequent unplanned breakages, a trade worth taking.
- **check:** you know what the consumer actually uses; ask or measure.

### 61. strictness-by-rate-of-change
- **condition:** choosing contract strictness between two specific parties.
- **decision:** tight where the two parts are highly semantically coupled and change together; loose where their information changes at different rates. An orchestrator and the service that must stay in sync with every new type it manages get a tight contract; an orchestrator and a slow-changing notification or survey service get a loose one.
- **why:** strict contracts buy fidelity, build-time verification, versioning and clear documentation, and cost tight coupling plus a mandatory deprecation strategy. Loose contracts buy decoupling and cross-platform evolution, and cost contract management that fitness functions must replace.
- **check:** the change rates are observed or reasoned about explicitly, per pair.

### 62. deployment-cadence-overrides-strictness
- **condition:** one party to a contract cannot deploy on demand.
- **decision:** deployment cadence overrides the semantic argument: a party gated by a slow external release process (an app-store review, a client-controlled deployment window) gets a loose contract plus an extension mechanism for short-term flexibility, even where semantics call for tight. Record the external condition that would reverse the decision.
- **why:** the slow party is not blocked by every change. More validation logic must live on both sides; the cost moves, it does not disappear.
- **check:** the deployment constraint is real and imposed from outside, not an internal process choice you could fix.

### 63. consumer-driven-contracts
- **condition:** you want loose coupling and contract fidelity together.
- **decision:** invert push to pull: the consumer writes the contract for what it needs, and the provider runs that contract test in its own build and keeps it green at all times. Each consumer specifies as strictly as it needs, including constraints schemas cannot express, such as acceptable value ranges.
- **why:** fidelity where each consumer wants it, without a global strict contract. It costs two interlocking mechanisms instead of one (name/value pairs plus contract tests) and a hard dependency on team discipline that no tool enforces.
- **check:** engineering maturity exists: teams run contract tests promptly and fix failing builds. If failing builds are routinely ignored, use stricter contracts and accept the coupling. Solo, the mechanism becomes ordinary integration tests, still worth having.

### 64. stamp-coupling-legitimate-vs-accidental
- **condition:** a large data structure passes between services that each touch only a small part.
- **decision:** stamp coupling is legitimate in two cases — an industry-standard document passed around and updated in sections, and workflow state carried through a choreographed solution. It is an anti-pattern when it comes from over-specification or future-proofing; ask whether the extra fields serve this interaction.
- **why:** used for workflow state it saves a mediator, since the semantic coupling must live somewhere. It can create artificially high coupling between collaborators and bandwidth problems at scale.
- **check:** run the bandwidth arithmetic before accepting a large payload: 2,000 requests/second × 500 KB is 1,000,000 KB/second; carrying only a 200-byte field makes it 400 KB/second. Bandwidth is finite, and the monolith's natural barriers are gone; the arithmetic scales with your own request rate.

### 65. contract-abstracts-the-schema
- **condition:** a schema owned by one service must change while other services consume that data.
- **decision:** the contract, not the schema, is the unit of compatibility; let the contract differ from the schema deliberately in field names and types (a `DATE` column exposed as an epoch-milliseconds number under another name). A breaking schema change then changes the owner but not the consumers, and not at the same time; the owner can emit a placeholder until the contract is renegotiated.
- **why:** consumers are shielded from schema change. The schema-to-contract mapping is permanent work, and placeholder values (a far-future date, a zero) are a deliberate lie in the data that must be tracked and removed.
- **check:** the bounded context is real and consumers cannot reach the schema. Where consumers read the schema directly (the data-domain pattern of rule 39), this rule is unavailable: there the schema is the contract.

---

# G. ORCHESTRATION AND WORKFLOW COORDINATION

### 66. model-both-coordination-options
- **condition:** choosing between orchestration and choreography for a workflow.
- **decision:** model both solutions before comparing them, then walk the likely scenarios — the concrete problems the business has raised — and build a two-column credit table issue by issue. Credit both columns where both satisfy a requirement; it is not zero-sum, and both or neither may work.
- **why:** the comparison rests on modelled behaviour, not preference. Modelling twice costs time and produces one artefact that will be discarded.
- **check:** the workflow's steps are enumerated, including who starts and who completes it. No obvious winner after modelling is the normal case and the signal to run the trade-off table, not to defer.

### 67. complexity-selects-orchestration
- **condition:** the workflow's semantic complexity is known.
- **decision:** the more complex the workflow, the more an orchestrator pays off. Choreography fits workflows needing responsiveness and scale whose error scenarios are simple or rare; orchestration fits complex workflows with boundary and error conditions.
- **why:** coordination matches what the workflow demands. Orchestration costs responsiveness (everything goes through the mediator), fault tolerance (a single point of failure, mitigable with redundancy and more complexity), scalability (less parallelism) and coupling to the orchestrator; choreography costs distributed workflow ownership, state management, error handling and recoverability.
- **check:** error and boundary paths are enumerated, not only the happy path.

### 68. judge-coordination-by-error-paths
- **condition:** comparing coordination styles.
- **decision:** compare on error paths, not happy paths, and count the new communication links each error scenario adds. Orchestration handles even elaborate errors over links that already exist; choreography makes domain services talk to each other on each error, adding links the happy path never needed.
- **why:** the real cost of each style becomes visible. This criterion systematically favours orchestration, so applying it means consciously accepting orchestration's scalability ceiling for tractable error handling.
- **check:** at least two distinct error scenarios are drawn — an early failure (a payment rejected) and a late one (a backorder after several steps committed).

### 69. one-orchestrator-per-workflow
- **condition:** introducing an orchestrator.
- **decision:** one orchestrator per workflow, never a global one such as an enterprise service bus, which becomes the coupling point decoupling was meant to remove. The orchestrator holds no domain behaviour beyond the workflow it mediates.
- **why:** no system-wide coupling point. N workflows mean N orchestrators to build, deploy, monitor and scale — duplication accepted deliberately.
- **check:** the workflow's boundary is defined. If two workflows seem to need the same orchestrator, check whether they are really one workflow before sharing it.

### 70. synchronicity-per-call
- **condition:** designing the individual calls inside an orchestrated workflow.
- **decision:** choose synchronous or asynchronous per call, from that step's timing dependency, not as a blanket policy: payment verification is time-sensitive; fulfilment that runs a few times a day is not. Keep a call synchronous deliberately when it simplifies errors — running the first step serially means its failure needs no reversal anywhere else.
- **why:** each step pays only for the coupling it needs. The workflow becomes heterogeneous and harder to reason about and debug, and the deliberate serial first step buys simpler error handling with response time — consistency over responsiveness.
- **check:** each step's timing dependency is known.

### 71. choreography-state-owner-must-be-chosen
- **condition:** using choreography for a workflow with any transient state.
- **decision:** choose the state owner explicitly from three: **front controller** (the first service in the chain owns workflow state; status queries become trivial, but a domain service carries workflow state, communication overhead grows, and performance and scale suffer); **stateless choreography** (no transient state; rebuild a snapshot by querying every service; high performance and scale, but complexity rises fast with complex workflows); **stamp coupling** (state travels in the message contract; no front controller needed, but contracts grow and there is no just-in-time status query).
- **why:** someone owns the state by decision, not by accident. None of the three matches an orchestrator's state management; that gap is the price of choreography.
- **check:** confirm transient state exists at all; some workflows have none. If one queryable status point is a business requirement and stamp coupling cannot provide it, that is evidence for orchestration.

### 72. no-absolutes-in-coordination
- **condition:** someone proposes a blanket policy, such as choreography everywhere to stay decoupled.
- **decision:** reject the absolute; architecture has no absolutes except about absolutes. Decide coordination style per workflow; a decision record mandating one style system-wide is the wrong artefact.
- **why:** each workflow gets the style its error and scale profile needs. Different workflows in one system then coordinate differently, which costs a uniform mental model and onboarding time.
- **check:** each workflow's style is recorded with its own reason (rules 66–68).

---

# H. REUSE

### 73. reuse-requires-slow-rate-of-change
- **condition:** identifying something as a reuse candidate.
- **decision:** abstraction finds the candidate; a slow rate of change decides whether reuse is worth it. What is reused successfully everywhere — operating systems, open-source frameworks — changes slowly and on a predictable cadence; internal domain capabilities and fast-changing technical frameworks are poor coupling targets. Measure the rate from version control before deciding.
- **why:** reuse happens where it stays cheap. Rejecting reuse on volatility means accepting duplication with its sync and semantic-drift problems — sometimes still better than coupling between services.
- **check:** the change history has actually been looked at; a confident claim that shared logic changes constantly is often wrong once the repository is checked.

### 74. reuse-technique-selection
- **condition:** shared code exists across services.
- **decision:** choose among four by environment homogeneity and volatility. **Code replication**: only for simple static code (annotations, attributes, small utilities) that is one-off or unlikely to change; costs hard change propagation, inconsistency, no versioning across services. **Shared package** (compiled dependency): for homogeneous environments with low-to-moderate change; compile-time binding leaves performance, scale and fault tolerance untouched; costs dependency management, duplication across heterogeneous codebases, hard deprecation and communication. **Shared service**: for highly polyglot environments where shared functionality changes often; costs hard versioning (endpoint versioning is subjective and breaks across protocols), latency, a service that must scale with its consumers, and a fault-tolerance dependency; it requires composition, not inheritance. **Sidecar or service mesh**: operational coupling only (rule 77).
- **why:** the fundamental trade is compile-time risk (a package change forces coordinated redeploys) against runtime risk (a service change can break consumers in production). Each option's cost is stated with it.
- **check:** the shared code is classified as domain or infrastructure, and you know whether the environment is polyglot. If a simple change to a shared service could take consumers down at runtime and you cannot version it, use a shared package instead. Sidecars and meshes presume many teams.

### 75. fine-grained-shared-libraries
- **condition:** structuring shared code packages.
- **decision:** prefer small, functionally partitioned shared packages over large coarse-grained ones, choosing change control over easy dependency management. Carve relatively static functionality (formatters, authentication and access control) into their own packages; never build one package of miscellaneous shared things.
- **why:** a change touches only the consumers of that function. The dependency matrix grows fast — picture 200 services and 40 shared packages — so you buy change control with dependency-management pain, deliberately.
- **check:** each package has one functional purpose you can name.

### 76. always-version-never-latest
- **condition:** publishing a shared package.
- **decision:** always version, so one consumer needing an urgent change can adopt and ship immediately with no impact on the others; never let consumers pin to `LATEST`, which breaks quick fixes and emergency hot deployments. Prefer a deprecation policy per package (a rarely changing security package needs 2–3 versions; a weekly changing calculation package ~10) over one global policy, which causes churn and slows every team.
- **why:** consumers move at their own pace. Versioning is far from simple, and communicating a version change across teams is itself an unsolved coordination problem that tooling does not remove.
- **check:** someone owns deprecation tracking per package; custom policies are a real maintenance load. Serious defects or breaking changes override any deprecation policy, because every consumer must adopt at once; when that happens often, it is evidence for rule 25 `shared-domain-code-integrator`.

### 77. sidecar-carries-operational-coupling-only
- **condition:** deciding what goes into a sidecar.
- **decision:** the sidecar carries operational coupling — logging, monitoring, service discovery, authentication, access control, circuit breakers: plumbing with no domain responsibility. Domain shared components (an `Address` or `Customer` class) stay out, since placing them there adds exactly the coupling distribution tries to avoid; handle them with contracts.
- **why:** operational behaviour is uniform without coupling domains. A sidecar must exist per platform, can grow large and complex, and weighs on every service, including those needing none of it.
- **check:** the classification is honest; if it encodes business logic, keep it out. A shared technical utility is a genuine judgement call — decide it with rule 78. This pattern presumes many teams and a platform owner.

### 78. shared-utility-in-sidecar-threshold
- **condition:** deciding whether a shared utility belongs in the sidecar.
- **decision:** weigh how many teams need it against the overhead it adds to every service, especially those that do not. If fewer than half the teams use it (for example five of 16–17), leave it out and reassess later.
- **why:** the sidecar stays light for the majority. The teams that do use it each wire the dependency themselves, duplicating configuration and risking version divergence.
- **check:** the actual usage count is known. The threshold needs teams to count; at smaller scale ask the same question of any shared substrate: does the benefit to some justify the cost to all?

### 79. no-universal-entity-service
- **condition:** someone proposes consolidating the organisation-wide view of a key entity (Customer, Product, Employee) into a single service.
- **decision:** do not build it. Universality forces complexity — one entity that must serve every domain and scenario becomes too complex for simple uses — and brittleness — when every domain reads it from one place, any change there breaks everything, and adding a capability for one domain can affect all others. Let each domain keep its own bounded-context representation and pass information in loose contracts.
- **why:** domains evolve independently. Duplicated representations bring sync issues and semantic drift, accepted deliberately; the answer depends on style — in microservices prefer duplication, in service-based architecture prefer coupling.
- **check:** if a regulatory or master-data requirement demands one record of truth, treat it as a data-ownership problem (rule 31 `common-ownership-dedicated-owner`), not as a universal service. The failure mode presumes several divisions each holding a partial view.

### 80. platform-as-the-reuse-target
- **condition:** an organisation wants reuse at scale.
- **decision:** build a platform per distinguishable domain capability, behind a well-defined API that hides the implementation. A loosely coupled API lets the implementation change fast internally without breaking callers.
- **why:** reuse lands where the rate of change is slow — the API. Encapsulation limits breaking change but does not protect against changes in the meaning of what domains exchange, and the word platform drifts toward meaning anything.
- **check:** the capability is genuinely a distinguishable domain capability, and the term platform is defined for this case. This presumes many teams.

---

# I. ANALYTICAL DATA

### 81. no-warehouse-or-lake-for-distributed-architectures
- **condition:** deciding how to serve reporting and analytics from a distributed architecture.
- **decision:** reject both the data warehouse and the data lake: both are technically partitioned and both strip data from its domain context. The warehouse fails on integration brittleness (transform-on-ingest ties schema changes to import logic), domain knowledge split across four roles, a separately maintained yet tightly coupled ecosystem, and business value below its cost. The lake fails on discovery (relationships inside a domain are lost), PII reconstruction risk (many jurisdictions restrict data that can be combined to identify a person), quality problems pushed into downstream pipeline bottlenecks, and staleness from batch coupling.
- **why:** analytical data keeps its domain meaning. You give up the warehouse's real advantages — centralised consolidation and a dedicated analytics silo that isolates the load — and a data mesh pushes both back onto the domain teams.
- **check:** the architecture really is distributed and domain-partitioned; for an older monolithic architecture a warehouse may still fit. The alternative (rule 82) presumes many teams.

### 82. data-product-quantum-per-domain
- **condition:** a domain's data is needed for reporting, BI or ML.
- **decision:** build a data product quantum next to the service, run and maintained by the team that owns the operational data. Choose its type: source-aligned (its own domain's analytical data), aggregate (combines several inputs, synchronously or asynchronously), or fit-for-purpose (built for one need — a report, a BI view, an ML model). Add them gradually as needs appear, not up front.
- **why:** analytical data stays with the people who understand it. It needs contract coordination with the data product and asynchronous, eventually consistent communication, and each domain team now runs two deployables instead of one.
- **check:** the domain team can carry the second deployable. If analytical and operational data must stay in sync at all times, this pattern becomes very hard — surface that requirement before committing. At small scale keep the principle (rule 83) and skip the platform machinery.

### 83. data-sidecar-never-transactional
- **condition:** designing the coupling between a service and its data product quantum.
- **decision:** the data sidecar is always asynchronous and eventually consistent — the aeo or aec pattern of rule 55 — and never has to keep operational and analytical data transactionally in sync, which would defeat the orthogonal decoupling it exists for. Communication to the data plane is asynchronous so the domain service's operational characteristics are barely touched; and the data product quantum belongs to the quantum's static coupling, so like a broker it must be available.
- **why:** analytics cannot degrade operations. Analytical data lags operational data by an unbounded amount, and the data product becomes one more thing that must be up for the architecture to be complete.
- **check:** analytical consumers accept eventual consistency. If one demands transactional consistency between the two, escalate; never satisfy it inside the sidecar.

### 84. federated-governance-embedded-as-code
- **condition:** organisation-wide requirements (compliance, security, privacy, data quality, interoperability) must hold across decentralised data ownership.
- **decision:** form a federated governance group of domain data-product owners, security, legal, risk and compliance experts, and platform product owners; it decides what must be standard — data-sharing contracts, asynchronous transport modes, access control. Automate those policies as code in the sidecar of every data product, executed at the point of read or write, with the platform team upgrading sidecars uniformly.
- **why:** policies hold everywhere without relying on each team's memory. A standing cross-functional body is recurring cost, and uniform upgrades mean every domain inherits policy changes it did not choose.
- **check:** a platform team exists that can build and uniformly upgrade sidecars. Without that scale, keep the core: a policy that must hold everywhere runs as code at the access point, never as written guidance.

### 85. daily-completeness-contract
- **condition:** an analytical product does trend analysis over time periods fed by several sources.
- **decision:** require complete data for a period or none at all: an absent period can be exempted honestly, while a partial one silently corrupts the trend by looking like less activity. Ship the rule with a fitness function that checks message timestamps on arrival and, at typical volume, treats any gap over one minute as a processing gap that marks the period exempt. Keep contracts between source feeds and the aggregating product loose to prevent brittleness.
- **why:** the check refuses bad data instead of reporting it, so the output stays trustworthy. You deliberately discard partial but real data, shrinking the sample, and the one-minute threshold is calibrated to one message volume.
- **check:** message timestamps exist on the feed; recalibrate the gap for your volume. Watch the exemption rate: when exemptions become common, the trends are no longer accurate — escalate.

---

# J. METHOD AND GOVERNANCE

### 86. least-worst-not-best
- **condition:** comparing designs where several architecture characteristics compete.
- **decision:** stop looking for the best design; best would mean every competing factor maximised at once, which never happens. Name the competing characteristics, accept that none will excel as it would alone, and choose the combination whose losses you can live with — the least worst.
- **why:** the decision is honest about what it gives up. You lose the ability to present it as unambiguously right, which is harder to sell and defend; you defend a ranking of losses instead.
- **check:** each competing characteristic is named individually, and the record states what each loses.

### 87. three-step-tradeoff-process
- **condition:** any non-trivial architecture decision.
- **decision:** (1) find which parts are entangled; (2) analyse how they are coupled; (3) assess trade-offs by the impact of change on the interdependent parts. In step 3 fix the fundamental dimension first — the choice that most constrains the others — and iterate on the decisions it forces until only unentangled decisions remain; those are design.
- **why:** effort goes to the decisions that are actually hard. Iterative modelling costs time before commitment, and fixing the fundamental dimension early forecloses options a later insight might favour.
- **check:** step 1 is genuinely done; trade-off analysis fails when concerns have not been separated. Stop when the remaining decisions are unentangled: write the code.

### 88. rate-in-isolation-consolidate-at-the-end
- **condition:** building your own trade-off analysis over several candidate solutions.
- **decision:** rate each option in isolation first, then combine into one matrix at the end. Correlations appear only in the consolidated view — typically that coupling falls as scale and elasticity rise, and that more coupling means lower responsiveness and availability, since the more services a workflow involves, the likelier one failure fails the whole.
- **why:** patterns across options surface that pairwise comparison hides. Rating in isolation is slower and the ratings mean little until the end.
- **check:** the same rating dimensions are applied to every option. Add cost as a row yourself when it matters; these rules supply no cost dimension.

### 89. qualitative-not-quantitative
- **condition:** comparing architectures or patterns.
- **decision:** expect qualitative analysis; two architectures always differ too much for true quantitative comparison. Make it defensible with representative examples, inside your organisation or from localised spikes that test the theory, and convert what you can into quantitative results by building and testing it.
- **why:** judgement rests on evidence instead of opinion. Qualitative ratings are contestable and carry no proof, so they are harder to defend against a confident opinion; tests with objective outcomes are the way from speculation to engineering.
- **check:** representative examples exist, not just intuition. Mark each rating as measured, evidenced or assumed, and never present an assumed one as measured.

### 90. mece-the-comparison-set
- **condition:** comparing candidate technologies or approaches.
- **decision:** make the set MECE. Mutually exclusive: no capability overlap — a message queue and a whole enterprise service bus are not the same category of thing. Collectively exhaustive: no live option left out — comparing high-performance queues while omitting Kafka fails. For long-lived decisions, recheck that no new capability has arrived that changes the criteria.
- **why:** the answer is not wrong because the option space was. Exhaustiveness widens scope and delays the decision.
- **check:** list the categories and confirm each option sits in one and every live option is present; re-verify against current tooling before acting.

### 91. find-the-narrow-context
- **condition:** a generic trade-off matrix appears to favour one option.
- **decision:** do not decide from the generic matrix; generic solutions rarely survive situation-specific context. Keep researching the actual context — the criteria often change once it is clear — because the right narrow context leaves far fewer options and simplifies the decision. This is the working method behind keeping designs simple.
- **why:** the decision fits this situation, not an average one. It costs a second research round after the first already produced an answer, and may overturn a decision the team began acting on.
- **check:** you can tell generic findings from context-specific ones in your own research, and the record names the context that decided.

### 92. model-the-hard-scenario
- **condition:** using scenario modelling to decide between architectures.
- **decision:** model relevant domain scenarios and make at least one a complex workflow, since complex workflows expose the difficult parts. Easy scenarios (update a service, add a variant) often all favour one design while the complex one (a single request spanning several variants) reveals the real trade-off — extensibility and agility against performance and data consistency.
- **why:** the deciding scenario gets modelled before commitment. It is design work with no shipped output, and the hard scenario often overturns what the easy ones supported.
- **check:** the scenarios are real domain cases, not invented ones. If the easy scenarios all agree, you have not yet modelled the deciding one; keep going.

### 93. bottom-line-not-evidence
- **condition:** presenting a trade-off to non-technical stakeholders.
- **decision:** reduce it to a few key points, sometimes aggregates of individual trade-offs, phrased as business outcomes rather than mechanisms — not synchronous REST against asynchronous queues, but whether a guaranteed immediate start of a process matters more than responsiveness and fault tolerance.
- **why:** stakeholders judge outcomes instead of drowning in mechanism. Aggregation discards nuance some of which was decision-relevant, and the architect owns what was collapsed.
- **check:** the full analysis is done first; this is a presentation rule, not a shortcut through the work. Keep the full analysis in the decision record.

### 94. no-evangelism-no-foil
- **condition:** you or someone else advocates a tool, technique or approach with enthusiasm.
- **decision:** do not evangelise, and do not accept the opposing-foil role when someone else does, since an argument needs two real sides. Force an honest assessment of the good and the bad and bring it back to trade-offs; when adopting something contested, adopt it with a fitness function aimed at its specific known failure mode (a monorepo adopted together with checks against accidental coupling between its projects).
- **why:** the decision rests on analysis, and the feared failure is guarded from day one. The argument does not resolve socially, so you must do the modelling; and solutions rarely transfer beyond their original problem space, your own past successes included.
- **check:** you can name the specific failure mode, or there is nothing for the guard to check. If the claimed advantages need a discipline the team has never shown, name that as a condition of the decision instead of accepting it as given.

### 95. fitness-function-vs-unit-test
- **condition:** you are about to write an automated check and are unsure what kind it is.
- **decision:** ask whether executing it needs domain knowledge. Yes → unit, functional or acceptance test; no → fitness function (elasticity needs none; validating a mailing-address format does). Fitness functions are atomic (one characteristic alone, such as no component cycles) or holistic (a combination, because characteristics interact — security affects performance; scalability and elasticity can conflict).
- **why:** each check lands in the right suite with the right owner. Fitness functions are ongoing maintenance and can be overused into an interlocking set that only frustrates teams.
- **check:** the characteristic has an objective, measurable value; high performance with no number is not checkable. The split is not purely binary, so do not force a check that spans both into one category.

### 96. decompose-unmeasurable-characteristics
- **condition:** a required architecture characteristic cannot be measured objectively.
- **decision:** treat it as a composite and decompose it until each piece is measurable — agility becomes deployability, testability and cycle time. Inability to measure a characteristic usually means its definition is too vague.
- **why:** the requirement becomes checkable. Decomposition can lose what the stakeholder meant: all three metrics can pass while the business still feels slow.
- **check:** confirm the pieces with whoever stated the requirement. If a characteristic resists decomposition into anything measurable, it is not yet a requirement; escalate for clarification.

### 97. govern-structure-automatically-not-by-review
- **condition:** a structural principle is defined by someone who will not implement it personally.
- **decision:** automate the check into the build; code review comes too late, after a week of unchecked violations has already done the damage. Wire structural checks — component cycles, layer access rules, forbidden dependencies, component size, namespace restrictions — into the CI/CD pipeline, one fitness function per rule.
- **why:** violations are caught as they are written. Each check is code to write and maintain, false positives need exclusion files that themselves need governing, and overuse breeds frustration rather than quality.
- **check:** the rule can be expressed objectively. Checks that must stay human (a lawyer reviewing changes to legally sensitive code) go in a manual pipeline stage run as often as reasonably possible, since a check that never runs validates nothing (governance rule `manual-stage-in-the-pipeline`).

### 98. adr-with-alternatives-and-consequences
- **condition:** any consequential architecture decision is made.
- **decision:** record it as an ADR in the format of [writing.md](../writing.md): a short numbered title; Context with the forces; Decision in full sentences; Consequences with what happens after it is applied and the trade-offs weighed, the bad with the good; the alternatives considered under Rejected. Where an external condition could reverse it (scalability needs change, a release-gating policy relaxes), name that condition in Consequences as its trip-wire.
- **why:** the reasoning outlives the memory of whoever made it and the decision declares what would make it stale. It costs writing time on every decision for documents that may go unread — yet written justifications are often what keeps a sponsor's trust.
- **check:** the alternatives were genuinely considered; a record with one option documents an assumption, not a decision. Issues found later are amended in place when they are drift and superseded when they reverse it — never appended as dated updates; when the named trip-wire fires, reopen it.

### 99. the-three-habits
- **condition:** asking how to sustain good architecture beyond one project.
- **decision:** three habits, not a framework: trade-off tables for all decisions, decision records to document and communicate them, and collaboration with other teams on problems and solutions. When challenged as extra process, the answer is that this is the architecture work itself.
- **why:** decisions stay visible, reasoned and shared. The habits are recurring overhead on every decision and look like bureaucracy to anyone who has not seen the failure they prevent; their defence is results, not theory.
- **check:** each consequential decision has its table and its record. Solo, the collaboration habit becomes arguing the other teams' side yourself.

### 100. cross-discipline-collaboration-is-a-precondition
- **condition:** a decision spans application architecture and data architecture.
- **decision:** bring the data team into the conversation before the decision, not after; breaking apart data needs close work with whoever runs the database. Separate application and data teams each doing their own thing is the failure this prevents.
- **why:** data constraints shape the design from the start. Collaboration is slower than deciding alone and means accepting constraints you would not have chosen (one schema per service; polyglot persistence only with business justification), which turn out to be load-bearing.
- **check:** the data owner was consulted before the decision. If not, stop, acknowledge it to them, and bring them in before proceeding. Solo, argue the data owner's case against yourself first.

### 101. developer-confusion-is-a-design-signal
- **condition:** developers come back confused about how to implement a workflow or error path.
- **decision:** treat the confusion as evidence about the design, not about the developers; they are good detectors of incomplete or confusing solutions, such as a compensation failure with no defined user-facing outcome.
- **why:** undefined cases get found before they ship. Treating every confusion as a design flaw risks redesigning around unfamiliarity instead of real ambiguity.
- **check:** decide whether the confusion points at an undefined case (fix the design) or merely a new one (explain it). Solo, the signal is your own hesitation when writing the error path.

### 102. hypothesis-based-analysis
- **condition:** two people hold opposing positions on an architecture decision.
- **decision:** state a hypothesis in favour of one option — preferably the one you expect to reject — and have the group attack it; the goal is analysing trade-offs, not trading opinions. After the negatives, solicit the positives deliberately, then check the claim the whole argument rests on against real data.
- **why:** the decision rests on tested claims, not on who argued harder. It is slower than an architect ruling, and it can show the architect's own preference was unfounded.
- **check:** participants engage rather than defend; the method works through questions, not assertions. If the deciding claim cannot be checked against data, say so and decide under a stated assumption. Solo, argue for the option you like least and see what survives.
