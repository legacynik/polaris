# Domain-strategy rules

These rules decide five things: the type of a subdomain and the sourcing that follows from it, the
boundary of a context against the boundary of a subdomain, the integration pattern between two contexts
with different models, the context map as an emitted artifact, and the order in which boundaries enter a
system that already exists. Each rule reads condition → decision → why → check. A step loads only the
rule ids it names, never the whole file.

**Halt condition, binding on every rule here.** Modelling can turn self-referential. Stop the moment the
language resolves a decision or a boundary. Keep a term in the model only if giving it a name shifts a choice
or relocates a line; a term that merely makes the model feel fuller is noise. A modelling pass that
resolved neither has produced nothing, however much shared understanding it generated: close it and do not
schedule a follow-up. Rules 8 and 9 are this halt applied at the classification and analysis steps.

## Where these rules stop

These rules supply a ceiling (rule 12), a floor (rule 16), a direction of travel (rule 14) and a
prohibition (rule 13) for boundaries. They never locate a boundary.

| Question | Who decides it instead |
|---|---|
| Where exactly does the line between these two units go? | ownership rules 1, 12, 13 and 15 (capacity ceiling, fracture-plane choice and its validation, single owner) |
| Which of two candidate services absorbs the other; how granular? | decomposition rules 10 and 11 for the quantum count, 20 for the leftover test, 23 for fault-tolerance splits, 24 for the 30/70 workflow test, 26 for data relationships, 30 for write ownership |
| How do we cultivate, record or police the ubiquitous language; how do we recover lost domain knowledge? | the `domain` door. These rules keep one consequence of the language: consistency as the ceiling on context width (rule 12) |
| Module depth, and where an interface seam belongs | `architecture` |
| How do I implement an aggregate, value object, repository or event-sourced model? | nobody: write the code |
| Our strategy, or whether to build this in the first place | strategy — outside this skill. These rules take the strategy as an input and only locate which subdomain carries the advantage |
| How do I weigh two designs against each other? | the decomposition rules 86 `least-worst-not-best`, 87 `three-step-tradeoff-process`, 90 `mece-the-comparison-set` |
| Storage engines, replication, consistency models, transactions | the data-systems rules |
| Hiring, roles, cadence, accountability, decision rights | people and roles — outside this skill |
| How is a logical boundary enforced once drawn? | governance rules `directionality-of-imports`, `layer-access-rules-as-code` and `archunit-governable-relationships` |
| A threshold for any signal here (call volume, size, cost) | the governance rule `derive-thresholds-from-production-not-estimates`; these rules carry no numbers |

## Conditions that change a rule's footing

- **One person owns both sides.** The integration fork (rule 18) is keyed on the power relationship between
  two teams, which a solo operator does not have. What changes:
  - **Collapses into one.** Partnership (19) and shared kernel (20) both become the same person editing
    both sides; there is nothing left to choose between them, and their coordination and cascading-change
    costs vanish too. One-team-per-context (15) is trivially met. An explicit contract between your own contexts
    still pays: ad hoc integration between two contexts with one owner erodes their boundary over time,
    and the contract is what keeps them two contexts. Spend the shared-kernel discipline (minimal shared
    scope, integration tests on every change) on yourself.
  - **Survives intact.** Rules 21 (conformist), 22 (anticorruption layer), 24 (separate ways) and 26
    (translation), because the upstream is a third-party vendor or your own legacy system, and the power
    imbalance against a vendor is real at any headcount.
  - **Survives, re-keyed.** Open-host service (23) stops protecting other teams and starts protecting your
    future contexts and your published integration surface from your internal model: the versioning
    discipline you want anyway.
  - **Unaffected.** Sections A, D and E, which are keyed on business strategy and code, not headcount.
  - **Weakened.** Rule 7's reverse check and rule 11's two-hats exception both lose the counterpart that
    normally supplies the check. Argue against yourself explicitly and record which hat spoke.
- **Instrumentation.** Rule 17 needs cross-context call volume per operation. Without it the rule yields
  `ASSUMED` plus the instrument to build, never a fabricated reading.
- **Cost estimates.** Rules 3, 20 and 24 decide on integration, coordination and duplication cost and carry
  no method for estimating them. If you cannot price both sides, halt and price them (a short spike); do
  not decide by feel.
- **Map size.** Rule 30 reads a distribution across edges; a map with two or three pairs has none to read.
- **Generated code.** The buy side of the generic branch (rules 1, 3) presumed building a solved thing was
  expensive. That cost fell; re-derive the buy/build line per case.

---

# A. Subdomain classification — the anti-overengineering fork

Rule 1 is the fork. Rules 2–5 locate a candidate on it, 6–7 act on the placement, and 8–10 stop the
type from going stale.

### 1. subdomain-type-classification
- **condition:** a subdomain is known and the next step sets its engineering budget — the stack, the pattern, build-vs-buy or who staffs it.
- **decision:** place it using exactly two axes — does it give a competitive edge, and how complex is its business logic — and accept what the branch implies:
  - **complex + competitive advantage → core:** build in-house only (buying it would hand the advantage to anyone else who buys it), most advanced techniques, best people, expect high volatility.
  - **complex + no advantage + a solved problem others already sell → generic:** buy or adopt open source. Building it in-house is the failure.
  - **simple + no advantage → supporting:** build it yourself because nothing ready-made fits, with a rapid-development framework and no elaborate patterns.
  - Five-column profile, read per type. Core: advantage yes, complexity high, volatility high, built in-house, an interesting problem. Generic: advantage no, complexity high, volatility low, bought or adopted, a solved problem. Supporting: advantage no, complexity low, volatility low, built in-house or outsourced, an obvious problem.
- **why:** one decision prevents both overengineering (a rich domain model behind a form over a table) and under-engineering (a differentiating algorithm coded as transaction scripts). It costs a judgement about business strategy made by an engineer, which will sometimes be wrong in either direction, and a standing duty to revisit it: a type assigned once and never rechecked is worse than none, because the design keeps obeying a stale verdict (rule 10).
- **check:** you can say what this company does differently from competitors for this specific subdomain. Halt if the argument is that it is core because it is important — every subdomain is required, and importance is not differentiation. The supporting/generic overlap is a gray zone: resolve it with rule 3, not by argument. Re-verify the generic branch's economics before acting: generated code made a passable in-house build of a solved problem cheap, so the deciding reason to buy is now that a widely used product has been tested and hardened by many other users, not the build cost.

### 2. core-or-supporting-side-business-test
- **condition:** the subdomain's complexity is debatable and core versus supporting will not settle.
- **decision:** imagine selling it as a standalone product: if customers would buy it separately, it is core.
- **why:** it is a business-side test an engineer can run without a strategy session. It costs a bias toward core, because almost anything sounds saleable in the abstract; pair it with rule 1's complexity axis, which calls a subdomain core only when it needs complex algorithms or processes governed by complex rules and invariants.
- **check:** ask about this subdomain in isolation, not the product around it — a payment integration does not become saleable because the product around it sells. If the honest answer is that someone would pay, but not enough to matter, that is a strategy question (strategy — outside this skill); do not round up to core.

### 3. supporting-or-generic-integration-cost-test
- **condition:** a ready-made solution exists for a subdomain you build today, or you are about to adopt one.
- **decision:** compare the cost of building your own minimal version with the cost of integrating the external one. Cheaper to build → supporting, build the minimum. Cheaper to integrate → generic, adopt it.
- **why:** it settles the one boundary that rule 1 leaves gray. It costs stability: the verdict reverses whenever fresh open-source work lands or an adopted integration proves dearer than expected, so deciding it once and hard-coding the consequence is the failure.
- **check:** count every integration cost — adapter code, authentication, leakage of their model into yours (rule 22), upgrade churn — not just the licence. If you cannot estimate it because you have not read the vendor's contract shape, run a two-hour spike before deciding. Re-verify the buy/build economics: the build side got cheaper, which moves some former generic cases into supporting.

### 4. competitive-advantage-not-necessarily-technical
- **condition:** the business's edge is already known and the software serving it now needs a type.
- **decision:** the advantage and the software that serves it are separate subdomains with separate types. When the edge sits in people, design, relationships or contracts, the system supporting it is supporting and is built as such. An online jewellery seller: the jewellery design is core, the shop engine can be bought. A firm whose analysts detect fraud by hand: the analysts' work is core, the system that shows documents and tracks their comments is supporting.
- **why:** it prevents the most expensive mistake in this file — a business vertical whose profit came from existing relationships, declared core, then built as an event-sourced, CQRS, microservice system over logic that plain active records would have served. It costs a risk of misuse: used loosely it licenses under-building every system that has people in its loop, and rule 10 shows the opposite failure. A sophisticated AI model inside a domain does not make the domain core either.
- **check:** you have asked where the money actually comes from and got an answer more specific than the product name. If the business insists the software is core while you find the advantage only in the non-software half, do not overrule them silently: open rule 7's conversation.

### 5. legacy-ball-of-mud-as-core-tell
- **condition:** strategic analysis of an existing system, looking for its core subdomains.
- **decision:** treat the worst-designed component that the business refuses to rewrite, because of business risk, as a candidate core subdomain. Confirm with two tests: no ready-made product could replace it (else it is generic), and any change to it carries business risk.
- **why:** it locates core candidates by reading code when no expert can be asked, the normal state of a brownfield audit. It costs false positives: a component can also be untouchable merely because nobody documented or tested it, or because it carries weight by accident. Engineer sentiment signals volatility, not value — a rough supporting component draws few complaints because it rarely changes.
- **check:** the refusal to rewrite comes from business risk, not from missing tests or the seniority of whoever wrote it. If a ready-made replacement exists and nobody has priced it, price it first: the answer decides between core (keep, invest) and generic (buy, delete). Pair with rules 2 and 4 before acting.

### 6. staffing-and-sourcing-by-subdomain-type
- **condition:** deciding who implements a subdomain — senior in-house, junior in-house, contractor, or vendor.
- **decision:** derive it from the type:
  - **core** → in-house only, sitting next to whoever holds the domain knowledge, staffed with the strongest people. Outsourcing it is unwise: it is a strategic investment, and cutting corners there is risky now and can be fatal later.
  - **supporting** → needs no rare skill, is a good training ground for newer engineers, and outsources well.
  - **generic** → buy or adopt; nobody needs to be staffed on it.
- **why:** staffing follows a stated reason instead of seniority politics. It costs review attention: the least-reviewed, least-tested code goes to the least experienced people, which is exactly where supporting subdomains silently drift into core (rule 10) without anyone noticing.
- **check:** the type is settled and has survived rule 7's reverse check. A core subdomain implemented by an outsourced party is one of rule 31's five findings: halt and escalate instead of continuing quietly.

### 7. reverse-verify-type-from-the-pattern
- **condition:** a subdomain has been classified and an implementation pattern chosen, before building.
- **decision:** run the classification backwards. Pick the business-logic pattern from the requirements in front of you, with no speculation or gold plating; map that pattern to the subdomain type it implies; verify that type against the business vision. Two mismatches, two consequences:
  - **declared core, but a day's hack would do** → either look for finer-grained subdomains, or question the viability of that line of business.
  - **declared supporting, but only an advanced pattern fits** → either the requirements carry accidental business complexity and should be simplified, or the business has not yet realised it gains an edge from this subdomain.
- **why:** it is a falsifiable check on the softest judgement in the file, and its output is a business conversation rather than a design. It costs a willing business counterpart, a delay at the moment work feels ready, and in a one-person shop it is at its weakest because you must argue against yourself.
- **check:** the pattern was chosen without knowing the declared type; choosing the pattern to match the label makes the check worthless. On a mismatch stop building and open the conversation; settling it on your own, whichever way, defeats the purpose of the check.

### 8. subdomain-distillation-depth
- **condition:** you hold a coarse candidate subdomain (typically a department or org unit) and must decide whether to drill further.
- **decision:** start coarse, from the org chart's departments and units. Drill until the unit is a set of coherent use cases — same actor, same business entities, a closely related set of data — which is the most precise subdomain boundary. Distil core subdomains as far as possible, so every generic and supporting piece can be extracted and effort focused; for supporting and generic, stop when a further level yields no new design insight.
- **why:** it finds what a coarse classification hides, such as a core routing algorithm three levels inside a customer-service department that looked outsourceable. It costs unbounded analysis time if the stop is not enforced. It works at subdomain granularity, not deployment granularity: a finer subdomain does not imply a finer deployable (rule 16 and the decomposition rules decide that).
- **check:** apply the halt condition — drop any level that settles no choice and shifts no line. In practice, stop once all children at the next level down share their parent's type.

### 9. exclude-non-software-subdomains
- **condition:** enumerating an organisation's subdomains at the start of an analysis.
- **decision:** name the business functions that have nothing to do with software, record them as excluded, and focus on what touches the system in front of you. Do not try to identify every core subdomain; even in a mid-sized company that is neither practical nor possible.
- **why:** it bounds the analysis with an explicit finish line — the halt condition at the analysis step. It costs permanence: an excluded function can later acquire software of its own and arrive as a new core subdomain from off the map, so the list of exclusions feeds rule 10's recheck rather than being deleted.
- **check:** the exclusions are written down, because they are rule 4's evidence (the jewellery design and the analysts' judgement are excluded from the software and still core). The analysis is done when the subdomains touching the system are typed; mapping the rest of the company is the halt condition firing.

### 10. subdomain-type-drift
- **condition:** periodically, and at once whenever changing a subdomain becomes disproportionately painful.
- **decision:** treat the type as mutable. Primary signal: the existing design can no longer support current business needs — that pain is the call to reassess. Secondary signal: complexity growing in a supposedly simple domain; if it does not raise profit it is accidental business complexity, if it does, a supporting subdomain is becoming core. Act by direction:
  - **supporting → core:** bring it in-house, move to a richer pattern, end any outsourcing.
  - **core → generic** (a vendor now sells the solution): cease investing; only heavy research spending could still win an edge there.
  - **generic → core** (you choose to out-build the market, as a retailer did when it turned its own infrastructure into a cloud business): bring it in-house with your best people.
  - **core → supporting** (the complexity does not pay): cut to the minimum logic; outsourcing becomes permissible.
  - **supporting or generic → core** also voids separate ways (rule 24): duplicated implementations consolidate under customer–supplier.
- **why:** static classification cannot catch a supporting subdomain correctly built as transaction scripts whose simple flags grow into real rules and invariants until it is core with its design unchanged — a big ball of mud and a rewrite a year later. It costs a standing review whose only natural trigger is pain, and pain lags: once it is undeniable, rewriting has usually become the cheapest move. Rule 17 is the only leading indicator these rules offer.
- **check:** the original type was recorded somewhere findable (an ADR linked to the code); drift is undetectable against an unwritten baseline. Complexity that grows without a link to profit gets simpler requirements, not a richer pattern.

---

# B. Context boundaries against subdomain boundaries

These give a ceiling, a floor, an ownership split and a default direction; none of them finds where a
line goes. Locating it belongs to the ownership and decomposition rules (see Where these rules stop).

### 11. subdomains-discovered-contexts-designed
- **condition:** a boundary change is proposed, or two people dispute where a boundary lies.
- **decision:** first establish which kind of boundary is in play. Subdomains are discovered: the business strategy defines them, and you can be wrong about one but cannot choose it. Bounded contexts are designed: they are your decision, shaped to the project's context and constraints.
- **why:** it ends a whole class of circular argument and makes rule 7 meaningful (a type cannot be verified against the business vision if the type is itself a design choice). It costs a dependency on business knowledge you may lack, and in a one-person shop the two-hats exception below swallows the rule unless enforced by hand.
- **check:** no precondition; this is the first move in any boundary conversation. Halt if someone is designing a subdomain — that changes the business strategy under the guise of a refactor, and the decision is not theirs. When one person is in charge of both engineering and business development, name the hat you are wearing, since no second party is there to push back.

### 12. context-ceiling-by-language-consistency
- **condition:** proposing a context boundary, or challenging one as too wide.
- **decision:** a context may extend only as far as its ubiquitous language stays consistent. Consistency is mechanical: every term has exactly one meaning, with no ambiguous terms and no synonyms. A boundary wider than that holds inconsistent models. Two domain experts using one word for two things (lead as a single notification in marketing and as a whole lifecycle in sales) is not a communication problem to fix; it is the ceiling showing where it is.
- **why:** it gives a falsifiable ceiling — the only tool here that can veto a proposed boundary — and it is why one model for the whole enterprise is illegal rather than merely clumsy. It costs scope: it is only a ceiling and says nothing about anything narrower, where most real decisions live. It also costs access to domain experts, which the `domain` door governs.
- **check:** you listened to actual domain experts, not to a schema. Halt if the response to a term collision is prefixing (`MarketingLead`, `CRMLead`): prefixes add cognitive load (which model, when?) and split the code from the spoken language, since nobody says the prefixes aloud.

### 13. never-split-a-subdomain-across-contexts
- **condition:** a proposed decomposition would put parts of one subdomain in two contexts.
- **decision:** refuse it. A context may contain several subdomains, never part of one. Use cases that belong together and touch the same data stay in one context; split, the same requirement changes both contexts and forces simultaneous deployment.
- **why:** it detects a decomposition that would produce permanent lockstep deployment and duplicated rules that drift apart at once — one entity split across an implicit boundary by moving logic into stored procedures leads to two teams with two vocabularies, years of hidden production defects corrupting the data, and a full rewrite. It costs width: obeying it can force a context wider than you want, and that is the correct price. It is a prohibition, not a locator: it removes candidates and never proposes one.
- **check:** distil to coherent use cases first (rule 8); until then, one subdomain is not a defined unit. No exception applies.

### 14. start-wide-decompose-on-knowledge
- **condition:** first-time context boundaries in a domain still poorly understood.
- **decision:** start wide and narrow later, keyed on domain knowledge and volatility, never on a size target: the context's size follows from the model it holds. Wide boundaries spanning several subdomains make it safer to be wrong, because refactoring logical boundaries costs far less than refactoring physical ones. The dial: the less you know about the domain, the wider the first boundaries. It applies mainly to core subdomains; generic and supporting ones are more formulaic and far less volatile.
- **why:** it buys reversibility where uncertainty is highest and is the answer to premature microservices (the modular-monolith-first default). It costs a wide context you will split later, with shared-codebase coordination while it lasts, and the risk that later never comes and the ineffective boundaries pile up debt. It conflicts with ownership rule 1 (`Domain-capacity ceiling per unit`), which caps a unit by cognitive load: when one team must own the wide context, ownership rule 1 governs and caps the width; when the wide context is a single owner's own code, this rule's asymmetry governs. State which you invoked; do not average them.
- **check:** say honestly how much of the domain you understand; your own ignorance is what this rule runs on, and it is what people misreport most. Halt if you are chasing small contexts: every extra small context adds integration cost. Halt if the width is being picked to reach some number of services or teams; size is one of the least useful boundary heuristics.

### 15. one-team-per-context
- **condition:** assigning ownership of a context, or discovering two parties editing one.
- **decision:** one team implements, evolves and maintains a context; no two teams work on the same one. The relation runs one way: a team may own several contexts. Separate ownership removes implicit assumptions about each other's models and forces explicit integration protocols. The operative statement is ownership rule 15 (`Single-owner rule`), which is stricter and also governs access, pull requests and temporary grants; this rule is kept for the reason it gives a shared kernel the status of an exception.
- **why:** it puts explicit contracts where implicit assumptions were, the mechanism behind every rule in section C. It costs architectural stability: adding teams splits wide contexts so each team gets its own, so headcount changes become boundary changes, which rule 14 calls expensive. This rule and rule 14 are in tension by construction.
- **check:** no precondition. Two teams on one context is a finding to escalate (rule 31), not a situation to manage. The only deliberate exception is a shared kernel admitted under rule 20.

### 16. context-microservice-validity-bracket
- **condition:** validating a proposed physical decomposition — before committing, and whenever someone asks whether something should be a microservice.
- **decision:** check the proposal against a bracket, not a target. A microservice is always a bounded context; the converse does not hold. At the wide end sits the bounded context: the largest valid monolith, a viable design and not a ball of mud. The aggregate is the narrow end: the narrowest possible boundary. Anything inside is legal; failing to decompose into proper contexts yields a big ball of mud, decomposing past the aggregate yields a distributed one. Inside the bracket the default is subdomain alignment, the safest service boundary. What should be small in a microservice is the domain knowledge it exposes through its public interface, not its lines of code or its team.
- **why:** it is a cheap veto on both failure modes at once; shallow services are a main reason microservice projects fail. It costs completeness: a bracket is not a decision, and reporting it as one would make these rules a third voice on the boundary line. Explaining why the narrow end fails needs module-depth reasoning, which `architecture` owns.
- **check:** both ends of the bracket come from rule 8's distillation and rule 12's language ceiling, so run those first. Stop the moment the question becomes where exactly inside the bracket: hand off to decomposition rules 10, 11, 24, 26, 30 and ownership rules 1, 12, 13.

### 17. chatty-contexts-signal-a-wrong-model
- **condition:** monitoring an existing decomposition, especially one that has grown.
- **decision:** read heavy cross-context calling as a flaw in the model rather than a speed issue. Contexts that cannot complete an operation without calling another context are a strong signal of an ineffective model: redesign their boundaries to raise autonomy.
- **why:** it is a leading indicator of a wrong boundary, the only one here that fires before rule 10's pain; ignored, services drawn around aggregates grow chattier until each needs all the others, and the decoupled system becomes a distributed monolith. It costs false alarms: chattiness also has legitimate causes (a genuine cross-context workflow, an integration pattern doing its job), and acting on it alone can trigger a boundary rewrite that separate ways (24) or an aggregating translation layer (26) would have resolved for far less.
- **check:** cross-context call volume per operation is observable; without it the rule yields `ASSUMED` plus the instrument to build. No threshold is given here — derive one with governance rule `derive-thresholds-from-production-not-estimates`. Do not respond by caching, batching or co-locating: they hide the signal.

---

# C. Integration-pattern selection between two contexts

Six patterns sit in three groups, one per style of team collaboration. The cooperation group holds
partnership and shared kernel. The customer–supplier group — a group name, not a pattern — holds
conformist, anticorruption layer and open-host service. Separate ways is a group of one. Rule 18 is the fork; 19–24 admit each branch; 25
handles drift; 26–28 make a chosen pattern real.

### 18. integration-pattern-selection
- **condition:** two bounded contexts must interact and you are choosing how.
- **decision:** select in three keyed steps, in order:
  1. **Is collaboration between the two owners good** — well-established communication, or dependent goals where each side's success needs the other's? → cooperation group: partnership (19) or shared kernel (20).
  2. **If not, where is the power?** Both sides can succeed independently, so one of them dictates the contract. Upstream holds power: take their model as it is → conformist (21), or translate it away → anticorruption layer (22). Downstream holds power and you, as supplier, protect your consumers → open-host service with a published language (23).
  3. **If integrating costs more than duplicating** → separate ways (24).
- **why:** it turns a vocabulary of six patterns into a selection with a test per branch. It costs portability: keyed on team power, it degenerates in a one-person shop (see Conditions that change a rule's footing). It also returns one answer per pair, while one pair of contexts can need two patterns at once, even when each context holds a single subdomain.
- **check:** you can state (a) the collaboration quality between the owners, (b) which side can dictate the contract, (c) whether the two models genuinely differ — social and model facts that the code cannot answer. Halt if the two contexts are one subdomain split in two: that is rule 13, and no pattern saves it. If the models are identical, you have one context, not two.

### 19. partnership-preconditions
- **condition:** considering ad hoc, two-way coordinated integration between two contexts.
- **decision:** admit partnership only where communication is truly strong, since nothing contractual backs it up. Coordination is ad hoc and symmetric: one side announces an API change, the other adapts without conflict, and neither dictates the contract language. Required: established collaboration practice, high commitment, frequent synchronisation between teams, and continuous integration of both sides' changes to keep the feedback loop short.
- **why:** it buys the lowest ceremony and the fastest change cycle of any option. It costs every safeguard: without a contract, translation or versions, each change needs a conversation, and when the relationship weakens the integration decays quietly rather than breaking a build. For a solo operator it is the default and the trap: ad hoc integration between two contexts you own erodes their boundary over time, which is the argument for spending rule 20's discipline on yourself.
- **check:** both owners can and will synchronise often; geographically distributed teams are a poor fit. The moment synchronisation degrades, leave it (rule 25); staying is how integration failures accumulate.

### 20. shared-kernel-admission
- **condition:** two contexts would each need to implement some or all of one model.
- **decision:** admit a shared kernel only when the cost of duplication exceeds the cost of coordination, and then in minimal scope: share only the part both contexts must implement, ideally just the integration contracts and data structures that cross the boundary. Mandatory: every change to the kernel triggers integration tests for every affected context, or contexts run stale copies and corrupt data or fail at runtime. Four legitimate uses: owners who cannot achieve partnership (geography, politics); stepwise legacy modernisation (temporary); a pair of contexts under one owning team, to keep their boundaries from washing out; and the most volatile subdomains — usually core — where frequent change makes duplication the costlier side.
- **why:** it removes duplicated volatile model code and, in the same-team case, keeps boundaries explicit that ad hoc integration would erode. It costs the strongest coupling in this section: the shared model couples the lifecycles of every participant, so one change hits all of them at once. It also costs a permanent CI obligation and, across teams, the one-owner principle itself. A monorepo makes the mechanism easy; it does not make it cheap.
- **check:** you can estimate both costs and the shared model's volatility (the more it changes, the more integration costs). Across different teams it contradicts rule 15 by construction, so it must be justified as a pragmatic exception. If you cannot write down which of the four uses applies, do not use it.

### 21. conformist-admission
- **condition:** an upstream context dictates the contract and you are deciding whether simply to accept it.
- **decision:** conform — adopt the upstream model — when the power imbalance is real (the upstream has no motive to serve its clients and offers its contract as take-it-or-leave-it) and their model is tolerable: an industry standard, or good enough for your needs. That is a positive judgement about their model, not resignation.
- **why:** it is the cheapest integration: nothing to translate, no separate model to keep up, and alignment with a standard at no cost if theirs is one. It costs independence: their concepts live in your code and every change they make lands on you; a context that conforms to a mess becomes one.
- **check:** their model was assessed against your needs; calling it adequate must be a result, never an assumption. Go to rule 22 if any ACL trigger holds, above all if your side is a core subdomain: conforming gives up autonomy, and a core subdomain's autonomy is not yours to give.

### 22. anticorruption-layer-admission
- **condition:** you are downstream, cannot conform, and must translate.
- **decision:** build an anticorruption layer that translates the upstream model into one tailored to your needs when any of three triggers holds:
  1. **your side holds a core subdomain** — its model needs extra care, and the supplier's model would impede modelling the problem;
  2. **the upstream model is inefficient or awkward for your needs** — conforming to a mess makes you one, common with legacy systems;
  3. **the supplier's contract changes often** — with the layer, their changes reach only the translation.
- **why:** it buys a clean model on your side, one blast radius for their changes, and a simpler ubiquitous language free of foreign concepts. It costs a permanent translation layer: each new upstream field forces a mapping choice, in code with no business value that must still be tested and maintained. Do not confuse it with governance rule `jit-anticorruption-layer`, which is a wrapper around a third-party dependency whose interface you own, adopted just in time; this layer translates between two models because of a power relationship you cannot change — same name, different trigger, different cost. For a solo operator this is the highest-value rule here, since the vendor and legacy case survives every team-keyed collapse.
- **check:** the upstream really holds the power and that will not change; where negotiation is possible, partnership or a negotiated contract fits and the layer is over-engineering. If translating would cost more than duplicating the functionality, the models are too far apart: go to separate ways (24).

### 23. open-host-service-admission
- **condition:** you are the upstream context, power is skewed toward your consumers, and you want to protect them.
- **decision:** decouple your public interface from your implementation model and publish it as a published language — an integration-oriented protocol convenient for consumers, deliberately not your ubiquitous language. That lets internals and public model evolve at different rates, and lets you expose several versions of the published language at once so consumers migrate gradually. Exposing your data for analysis in a model distinct from the operational one is the same pattern: the analytical model is one more published language.
- **why:** it buys freedom to change internals without a consumer migration, gradual multi-version migration, and a smaller public surface. It costs an extra published model that someone designs, maintains, translates and versions: it is the anticorruption layer reversed, with the supplier taking on the consumers' translation cost on purpose. It also costs rule 28's discipline, where this pattern usually fails.
- **check:** you have more than one consumer, or one whose breakage you cannot accept; with a single consumer you control, this is ceremony. If an internal change has no expression in today's published language, halt and release a new version instead of leaking it.

### 24. separate-ways-admission
- **condition:** integration is being assumed by default and nobody has asked whether it is worth it.
- **decision:** duplicate instead of integrating when integration costs more than duplication, for three reasons: owners who cannot collaborate or agree; a generic subdomain easy to adopt locally (a logging framework — exposing it as a service adds more complexity than duplicating saves); and models too different to bridge, where conformist is impossible and an anticorruption layer would cost more than duplicating.
- **why:** it removes a coordination cost that was buying nothing, and it balances the habit of turning each shared concept into a service. It costs duplicated logic that drifts, and the standing risk that the duplicated thing becomes core while nobody watches, at which point a consolidation is owed. Being forced into it by politics is a diagnosis, not a design (rule 30).
- **check:** you priced both sides; this is the only rule in the section whose answer is to build it twice. Hard out on core subdomains: duplicating them defeats the strategy of implementing them in the most effective way. Once a duplicated subdomain turns core (rule 10), separate ways no longer applies: integrate under customer–supplier, with one team implementing the core.

### 25. integration-drift-on-organizational-change
- **condition:** the organisation shifts (teams relocate, divide, grow, or fall out) or two contexts start failing to integrate often.
- **decision:** re-derive the pattern, because rule 18's inputs have changed. Two transitions:
  - **partnership → customer–supplier** (conformist, anticorruption layer or open-host service) when strong collaboration lapses, for instance when one context's work moves to a distant development centre;
  - **customer–supplier → separate ways** when communication problems make duplicating cheaper than chasing each other.
  - Read the inverse as a diagnostic: a shift to separate ways tells you the teams could not cooperate, and that what they duplicated is not core.
- **why:** it keeps the design tracking the organisation, not a diagram of a company that no longer exists. It costs real work each time (building a layer, versioning a published language, writing a duplicate), and it makes integration patterns short-lived choices, awkward for anything recorded as an ADR. The documented drift runs only toward less collaboration; no upgrade path back is described.
- **check:** the current pattern is recorded on the context map (rule 29); drift is invisible without a baseline. If the duplicated functionality is core, separate ways is unavailable however bad the collaboration (rule 24): escalate as an ownership consolidation (ownership rule 15; people and roles — outside this skill), not as architecture.

### 26. translation-stateless-or-stateful
- **condition:** an anticorruption layer or open-host service has been chosen and must be built.
- **decision:** one fork, keyed on whether translation needs memory.
  - **Stateless** — translate on the fly as requests arrive (open-host service) or leave (anticorruption layer), as a proxy. Synchronous: embed the transform in the context's code, or put it in an API gateway, which also helps manage and serve several API versions. Asynchronous: a message proxy that subscribes, transforms and forwards, and can filter out messages irrelevant to the target.
  - **Stateful** — needs its own database, required when translation aggregates (batching, merging many fine-grained messages into one) or unifies several sources (a backend-for-frontend, or a context fronted by a layer that aggregates from all others to keep integration complexity out of its business logic). Aggregating transformation cannot run in an API gateway.
  - A shared translation layer consumed by several downstream contexts becomes a context of its own: an interchange context.
- **why:** stateless buys a part that stores nothing, raises no consistency question and needs no operations; it costs aggregation, and with a gateway part of your integration semantics lives in vendor configuration outside your repository. Stateful buys aggregation and multi-source unification; it costs its own database — backups, migrations, consistency semantics, failure modes — and a new component that can go stale. An interchange context costs a context nobody owns by default.
- **check:** establish whether some consumer needs data merged across messages or sources; that answer, not the transport, chooses the branch. Before building custom stateful translation, check off-the-shelf stream-processing platforms (Kafka, Kinesis) and batch tools (NiFi, Glue, Spark): by rule 1 a translation-and-batching engine is generic, and building it in-house is the failure. The fork holds; the named products (gateways such as Kong, KrakenD, AWS API Gateway, Apigee, Azure API Management, and the tools above) are a dated list — re-verify against current tooling before acting.

### 27. event-type-selection-for-cross-context-integration
- **condition:** two contexts integrate asynchronously and you are designing the message.
- **decision:** choose among three event types by the consumer's consistency need:
  - **event notification** — announces a change without carrying everything needed to react; the consumer follows a link or queries;
  - **event-carried state transfer** — carries all the changed state, an asynchronous replication mechanism;
  - **domain event** — models the business, useful even with no external consumer.
  - Selection: eventual consistency acceptable → state transfer; consumer must read the producer's latest write → notification followed by a query for current state; domain events go outward sparingly, as a dedicated set of public domain events.
  - Secondary reasons to prefer notification: security (forcing an explicit query keeps sensitive data off the messaging bus and adds a permission check on each subscriber) and concurrency (state-transfer data can be stale on arrival; with competing consumers the query can take a pessimistic lock).
- **why:** notification buys a thin public interface, keeps sensitive data off the wire and always reads fresh; it costs a synchronous dependency on the producer at read time, which gives back the fault tolerance asynchronous integration was bought for. State transfer buys consumer autonomy (consumers keep working while the producer is down) and removes repeated queries; it costs a permanently eventually-consistent replica in every consumer and turns every field you ship into contract. Domain events buy domain fidelity; published outward they cost implementation coupling (rule 28).
- **check:** you can state the consumer's consistency requirement; everything follows from it, and it is the question nobody asks. The message type is what couples or decouples the system: halt if publishing convenience, not the consumer's need, is driving the choice (rule 28).

### 28. never-expose-private-domain-events
- **condition:** publishing events out of a context, especially an event-sourced one.
- **decision:** treat events as part of the context's public interface and keep private events private; under an open-host service, published events belong to the published language. The common mistake is designing a published language for the model's objects while letting domain events out as they are, which exposes the implementation model. Translate through rule 26's asynchronous proxy. When several consumers derive the same view from your raw events, move that projection into the producer as a consumer-driven contract: an integration-specific model, decoupled from the internal one.
- **why:** it buys freedom to add or reshape internal events without breaking subscribers, and removes a failure seen in real systems: a schema change breaks every subscriber's projection, and a new internal event that subscribers ignore leaves their projections inconsistent. It costs a second event model and the translation to it, and the producer now owns a projection shaped by consumer needs — the same deliberate trade an open-host service already makes.
- **check:** separate the events that drive your own state from those meant for consumers; when all events are public there is no published language. If two consumers build the same projection from your events, stop and move it upstream: identical derivation logic in two places must change together.

---

# D. The context map as an emitted artifact

The output contract: the same artifact, the same shape, every time.

### 29. context-map-required-fields
- **condition:** a system's integration patterns are chosen, or one of them changes.
- **decision:** emit a context map — the contexts of the system drawn with every integration between them — with fixed fields per integrating pair: which two contexts, which pattern, which direction (upstream/downstream, or symmetric for partnership and shared kernel). It must yield three things: the high-level design (the components and the models they implement), the communication patterns (who collaborates closely and who chose less intimate patterns such as anticorruption layer and separate ways), and organisational issues (rule 30). Introduce it from the start and update it with every new or changed context; maintenance is shared, each owner updating its own integrations. It can be kept as code, for instance with Context Mapper. A pair with two patterns gets two rows.
- **why:** it buys form constancy — the same shape every time — and it composes with the `domain` door's `CONTEXT-MAP.md`. It costs a maintained artifact, and a stale map is worse than none because rule 25 reads drift against it. Derive it from code and configuration where possible, and mark it `ASSUMED` until resolved against the repositories.
- **check:** every integrating pair went through rule 18; edges without a pattern label make a plain dependency diagram, which delivers none of the three yields. When a context holds several subdomains, or one subdomain's modules need different strategies, several patterns are at play: forcing one label per pair falsifies the map. Re-verify Context Mapper's currency and maintenance against current tooling before adopting it.

### 30. context-map-as-organizational-diagnostic
- **condition:** reading an existing context map, as opposed to drawing one.
- **decision:** read patterns across edges, not single edges, as organisational findings. Every consumer of one upstream builds an anticorruption layer → the upstream's model is the problem; the fix is an open-host service there, not more layers elsewhere. All separate-ways edges cluster on one team → the duplication routes around a collaboration failure, not an engineering one, tolerable only while none of the duplicated subdomains is core (rule 24).
- **why:** it is the highest-leverage output of the map — an architecture diagram that surfaces an organisational cause. It costs an over-reading risk: several layers against one upstream may only show that it is an outside vendor, where translating is right and there is nothing to repair. Ask these as questions, not conclusions.
- **check:** the map covers enough pairs for a pattern to show; two edges have no distribution to read. The findings are about people: ownership and load go to ownership rules 1 and 15, decision rights and the conversation itself to people and roles — outside this skill. Do not stage an organisational intervention from a diagram.

### 31. context-map-of-an-existing-system
- **condition:** judging a system someone else designed: an inherited codebase, a brownfield audit, due diligence.
- **decision:** map the existing high-level components as if they were bounded contexts, then run a fixed finding list. Identify components by decoupled lifecycle: even in a monorepo or a single monolithic codebase, check which parts can be evolved, tested and deployed independently. Label every relation with an integration pattern. Report against five findings:
  1. several teams changing one high-level component;
  2. duplicate implementations of core subdomains;
  3. a core subdomain implemented by an outsourced company;
  4. friction from frequently failing integration;
  5. awkward models spreading from external services and legacy systems.
  - For each component, test the tactical fit as well: does the solution fit the problem's complexity; where are more elaborate patterns needed; where can corners be cut or an off-the-shelf solution used?
- **why:** it buys a repeatable review with a fixed output, driven by a list rather than by whatever the reviewer happened to notice. It costs coverage: all five findings are strategic and social, so it says nothing about correctness, performance, security or data — route those to the data-systems rules, the decomposition rules §J and the governance rules' detectors. Treating it as a complete architecture review is a serious under-read.
- **check:** run section A before this, because three findings depend on knowing which subdomains are core. If domain knowledge has been lost — widespread and acute in core subdomains — the review cannot proceed on code alone: halt, and recover the knowledge through the `domain` door or by talking to the people who hold it. The halt condition applies: stop mapping once each component's type and relations are settled.

---

# E. Brownfield sequencing

The order in which boundaries enter a system that already exists; turns rule 31's map into work.

### 32. logical-boundaries-before-physical
- **condition:** modernising an existing system after rule 31's review.
- **decision:** align logical boundaries first — namespaces, modules, packages, whatever the stack offers — with the subdomains, and only then consider physical ones. Moving types between modules is a relatively safe refactor because business logic does not change. Make it complete across platforms: logic in stored procedures, serverless functions and other codebases gets the same boundary, for instance by renaming procedures after their module or moving them into a dedicated database schema.
- **why:** it is the cheapest possible correction of a wrong boundary and the operational form of rule 14's asymmetry (logical refactors cost far less than physical ones). It costs enforcement: any later commit can reach across a namespace, and without a check the boundary erodes unseen. Enforce with governance rules `archunit-governable-relationships`, `layer-access-rules-as-code` and `directionality-of-imports`; unchecked, a logical boundary is only a comment.
- **check:** the subdomains are identified and typed (section A), since this reorganises toward that map. Before declaring the move safe, verify that references by full type name — dynamically loaded modules, reflection and the like — do not break; they make a safe move unsafe.

### 33. physical-extraction-triggers
- **condition:** whether to turn a logical boundary into a physical one — a separate service, project or deployable.
- **decision:** extract on two triggers: several teams changing one codebase → decouple their lifecycles with a context per team; conflicting models in different components → move them into separate contexts. Further legitimate reasons: forming new teams, or a non-functional requirement such as separating development lifecycles or scaling one functionality independently. Otherwise, extract only where turning a logical boundary physical gains the most value; decomposing early into the smallest possible contexts is risky.
- **why:** it buys independent lifecycles, independent scaling and enforced model separation. It costs an integration pattern from section C, another deployable, and cheap refactoring — a rename has become a migration, and ineffective physical boundaries tend to be left alone and accumulate debt.
- **check:** rule 32 is done for this component; extracting before the logical boundary is clean extracts the mess. With no trigger and no named non-functional requirement, do not extract. If the extraction breaches rule 16's bracket or splits a subdomain (rule 13), stop regardless of trigger. Finer granularity goes to decomposition rules 10, 11, 24, 26, 30.

### 34. strangler-or-in-place-refactor
- **condition:** a component has been chosen for modernisation and you must pick the migration shape.
- **decision:** a fork between replacing whole components gradually and refactoring the existing solution gradually.
  - **Strangler:** a new context implements new requirements and gradually absorbs the legacy context's functionality, while the legacy context stops evolving except for hotfixes and emergencies. A thin façade acts as the public interface and routes each request to legacy or new; it is removed when migration completes. One-database-per-context may be relaxed here, with an expiry: the legacy context is retired, sooner rather than later, and the database then belongs to the new implementation alone.
  - **In-place refactor:** small incremental steps, never one leap — a transaction script or active record never jumps directly to event sourcing; go through state-based aggregates first.
  - Either way, protect both edges: an anticorruption layer shields the new code from old models (rule 22), and an open-host service with a published language shields consumers from legacy changes (rule 23).
- **why:** strangler buys a fresh context and a cutover that can be undone slice by slice; it costs a façade to build and delete, a frozen legacy codebase, and a temporarily violated invariant (the shared database). In-place buys no new deployment surface and no dual-run; it costs a long stretch where the code is neither the old design nor the new, plus an ordering constraint — moving from state-based to event-sourced aggregates is far safer than discovering wrong transactional boundaries inside an event-sourced aggregate.
- **check:** domain knowledge and an effective model of the domain exist first; without them you re-implement behaviour you do not understand. Never a big rewrite in either branch: rewrites from scratch rarely succeed and rarely keep management support. Think big, start small, and accept that parts of a large system stay imperfect, so decide deliberately where to invest. Stop if the shared-database relaxation has no retirement date: that is governance rule `no-shared-database-integration` violated, not a strangler. Pair with governance rule `strangler-fig-with-a-fitness-function`, which adds the check that the legacy context is actually shrinking.
