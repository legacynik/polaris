# Decision Rules — Learning Domain-Driven Design (Khononov, O'Reilly Early Release)

**Extracted against a contract.** This book was acquired to fill exactly two holes that eleven prior
extracts left open (`_polaris/audit/2026-08-17-libri-mancanti-architettura.md`, gaps 3 and 4):

1. **What kind of domain is this** — core / supporting / generic, with a *consequence per branch*.
2. **How do two contexts with different models talk** — the integration-pattern fork.

Everything outside those two fields, plus the boundary of a context vs the boundary of a subdomain, the
context map as an emitted artifact, and the brownfield sequencing that produces one, is either ceded by
name in `when_not` or listed in SCARTATI with a reason. **34 rules.**

## The thesis this extract must not invert

> *"'It depends' is the correct answer to almost any question in software engineering, but not really
> practical. In this chapter, we will explore what 'it' depends on."* (Ch 10)

And the author's own guard against his method:

> *"A heuristic is not a hard rule that is guaranteed and mathematically proven to be correct in 100% of
> cases. Rather, it's a rule of thumb: not guaranteed to be perfect, yet sufficient for one's immediate
> goals."* (Ch 10)

The book's decisions are **strategic, not technical**: the type of a subdomain decides how much
engineering it deserves, and the *power relationship between the two teams* decides how two contexts
integrate. An extract that lists the six integration patterns without the condition that selects one has
produced a vocabulary list, which is precisely what decision 4 of `adr/2026-08-13` excludes.

## How to read the fields

| Field | Meaning |
|---|---|
| **when** | The recognizable situation that triggers the rule. **Rules are counted by this field, not by headers.** |
| **rule** | The decision rule — resolves a fork, does not summarize |
| **decides** | `subdomain type` · `sourcing` · `context boundary` · `integration pattern` · `context map` · `modernization sequence` |
| **precondition** | What must be true before it is safe to apply |
| **stop** | When the actor halts and escalates instead of deciding |
| **trade-off named** | What the rule COSTS, not only what it buys. **Mandatory. A rule with no stated cost is a defective rule.** |
| **still-true-in-2026** | `yes` · `check` (the field has plausibly moved; re-verify before acting) · `superseded` |
| **source** | Chapter / section, and page-level location in `_raw/full_text.txt` where the quote is verbatim |

---

## `when_not` — where this reference must not be used

### Hard out — never use this book to answer these

The first two rows are the **named failure mode of this acquisition**, not ordinary scope hygiene. The
verdict that bought this book (§"Cost of being wrong") states it: *"The failure mode is not wasted money,
it is a third provenance on the boundary line."* Khononov is loaded at the **classification** step and at
the **integration** step. He is not loaded at the boundary-drawing step.

| Do not use it to answer | Why not | Who owns it |
|---|---|---|
| **"Where exactly does the line between these two units go?"** | This book supplies **no method for finding a boundary**. It supplies a *ceiling* (rule 12: the language must stay consistent), a *floor* (rule 16), and a *default direction of travel* (rule 14: start wide). Between the ceiling and the floor it says, in full: *"it depends on the specific problem domain"* (Ch 3). It has no fracture-plane catalogue, no capacity model, no litmus test. | **Team Topologies** — `_extract/skelton-pais-team-topologies/`, rules **1** (`Domain-capacity ceiling per unit`), **12** (`Fracture-plane selection order`), **13** (`Fracture-plane validation — two tests, in order`), **15** (`Single-owner rule`) |
| **"Which of these two candidate services should absorb the other / how granular?"** | The book explicitly declines the mechanics: *"the decision for how big your bounded contexts should be depends on the specific problem domain"* (Ch 3). It never maps functions to tables, never counts quanta, never asks who writes. | **Hard Parts** — `_extract/ford-richards-hard-parts/`, rules **10** (`quantum-count-by-bootstrap`), **11** (`shared-database-caps-quantum`), **20** (`leftover-naming-test`), **23** (`fault-tolerance-split-requires-independence`), **24** (`workflow-integrator-30-70`), **26** (`data-relationship-integrator`), **30** (`writes-determine-ownership`) |
| **"How do I cultivate, document, or police a ubiquitous language?"** | Chapter 2 is the canonical statement of the practice and the vault **already owns a working implementation of it**: the installed `~/.claude/skills/domain-modeling/` skill (`CONTEXT.md` per context, root `CONTEXT-MAP.md`, challenge-the-term discipline, three-condition ADR gate). Loading a second provenance on the same practice buys nothing. This extract keeps only the *one* consequence of Ch 2 that the skill does not carry: language consistency as the **ceiling on context width** (rule 12). | **installed skill** `domain-modeling` |
| **"Is this module deep or shallow / where does the interface seam go?"** | Ch 14 borrows Ousterhout's depth heuristic wholesale and cites him by name. The vault owns that field as an installed skill. | **installed skill** `codebase-design` |
| **"How do I implement an aggregate / value object / repository / event-sourced model?"** | Deliberately out of scope — see SCARTATI §1. Four of the book's sixteen chapters, extracted to zero rules. | Nobody. Not needed; write the code. |
| **"What is our strategy / should we build this at all?"** | The book takes the business strategy as an **input** (Ch 1: *"The subdomains and their types are defined by the company's business strategy"*) and never produces one. It identifies which subdomain carries the competitive advantage; it cannot tell you whether the advantage is worth having. | **Rumelt** — `_extract/rumelt-strategy/` · **Working Backwards** — `_extract/bryar-carr-working-backwards/` |
| **"How do I weigh two designs against each other?"** | Zero adjudication method. The book's answer is a decision *tree* with the branches pre-assigned, which is the opposite of a trade-off analysis. | **Hard Parts** — rules 86–94 (`least-worst-not-best`, `three-step-tradeoff-process`, `mece-the-comparison-set`) |
| **Storage engines, replication, consistency models, transactions** | Chapter 16 touches analytical data and stops at the architecture. Nothing on mechanism. | **DDIA** — `_extract/kleppmann-ddia/` |
| **Hiring, roles, cadence, accountability, decision rights** | Absent. Teams appear only as the *variable that selects an integration pattern*, never as objects of design. | **Scaling People** · **Grove** · **Marquet** · **Mochary** |

### The halt condition — the founder's own stopping rule, verbatim

> **"può diventare modellazione autoreferenziale — fermati quando il linguaggio risolve una decisione o un
> confine."**

*(It can become self-referential modelling — stop when the language resolves a decision or a boundary.)*

This is the binding halt for every rule in this file, and it is stricter than anything the book itself
says. Operationally:

- **A term earns a place in the model only when naming it changes a decision or moves a line.** A term that
  merely makes the model feel more complete is noise. Rule 8 is the book's own version of the same halt
  (*"If drilling down further doesn't unveil any new insights that can help you make software design
  decisions, it can be a good place to stop"*) and rule 9 is its analysis-step twin.
- **A modelling session that has not resolved a decision or a boundary has produced nothing**, however
  much shared understanding it generated. Stop it; do not schedule the follow-up.
- **The book will not enforce this.** Ch 2's *"cultivation of a ubiquitous language is an ongoing
  process… constantly validated and evolved"* has no terminating condition at all, and Ch 12's event
  storming has ten steps and no exit criterion. Both are ceded above.

### Solo-operator collapse — what happens when there is one person

Recorded rather than filtered, following the `assumes-scale` stance of `ford-richards-hard-parts`. **The
integration-pattern fork (rule 18) is keyed on a variable the founder does not have: the power relationship
between two teams.** With one operator, several branches degenerate:

- **Collapses entirely.** `partnership` (rule 19) and `shared kernel` (rule 20) both reduce to "the same
  person edits both sides", so the fork between them disappears — and with it their whole cost model
  (coordination cost, cascading-change cost, the CI-on-every-change obligation). The book anticipates
  exactly this case and answers it: a shared kernel between two contexts *"owned and implemented by the
  same team"* is still worth having, because ad hoc partnership *"can 'wash out' the contexts' boundaries
  over time"* (Ch 4). **That sentence is the one that survives reduction**, and it is the argument for
  keeping explicit contracts between your own contexts.
- **Survives intact.** `conformist` (21), `anticorruption layer` (22), `separate ways` (24) and the
  translation mechanics (26) all survive unchanged, because the upstream is a **third-party vendor or a
  legacy system of your own**, and the power imbalance against a vendor is real whether you are one person
  or a hundred. This is where the book pays for itself in this vault.
- **Survives, re-keyed.** `open-host service` (23) stops being about protecting other teams and becomes
  about protecting **your own future contexts and your published integration surface** from your internal
  model — i.e. the versioning discipline you would want anyway.
- **Unaffected.** All of section A (subdomain classification), all of section D (context map), all of
  section E (brownfield). These are keyed on business strategy and code, not on headcount.

### Early-Release conditional

This is an O'Reilly **Early Release** draft, not the published 2021 first edition. Chapter numbering shifts
mid-file (the raw text opens with a Ch 2 fragment before the front matter), Ch 11 cross-references Ch 2 for
material that is in Ch 1, figures are referenced but absent, and the GitHub repo is declared inactive.
Where a rule depends on a figure, the field says so. See `EXTRACTION-NOTES.md`.

---

# A. Subdomain classification — the anti-overengineering fork

**10 rules.** This is contract fork (a). Rule 1 is the fork; rules 2–5 are the tests that place a candidate
on it; 6–7 are what you do once placed; 8–10 keep the classification honest over time.

### 1. subdomain-type-classification
- **when:** any subdomain has been identified and you are about to decide how much engineering it gets — before choosing a stack, a pattern, a build-vs-buy, or a person.
- **rule:** classify on **two axes only — competitive advantage and business-logic complexity** — and take the branch's consequence with it:
  - **Complex + provides competitive advantage → core.** *"Core subdomains have to be implemented in-house. They cannot be bought or adopted; that would undermine the notion of competitive advantage."* Most advanced techniques, best people, expect high volatility.
  - **Complex + no competitive advantage + a solved problem others already sell → generic.** *"It's more cost-effective to buy an off-the-shelf product or adopt an open source solution than invest time and effort into implementing a generic subdomain in-house."* **Building it in-house is the named failure.**
  - **Simple + no competitive advantage → supporting.** No ready-made solution exists, so *"a company has no choice but to implement supporting subdomains itself"* — but *"the simplicity of the business logic and infrequency of changes make it easy to cut corners"*. A rapid-application-development framework suffices; *"supporting subdomains do not require elaborate design patterns or other advanced engineering techniques."*
- **decides:** subdomain type · sourcing
- **precondition:** you can answer *what does this company do differently from its competitors* for this specific subdomain. Table 1-1 is the whole rule in five columns (competitive advantage · complexity · volatility · implementation · problem): core = Yes/High/High/In-house/Interesting · generic = No/High/Low/Buy-adopt/Solved · supporting = No/Low/Low/In-house-or-outsource/Obvious.
- **stop:** the supporting/generic overlap is explicitly a gray area and the book says so: *"The intersection between the supporting and generic subdomains is a gray area: it can go either way."* Resolve it with rule 3, not by argument. Also halt if the answer is *"it's core because it's important"* — importance is not differentiation; every subdomain is required (*"take one away and the whole structure may fall down"*).
- **trade-off named:** BUYS the single decision that prevents both overengineering (a domain model for a CRUD screen) and under-engineering (transaction scripts under a competitive algorithm). PAYS: the classification is a **judgement about business strategy made by an engineer**, and it will be wrong sometimes — the book's own case study got its flagship project wrong in both directions (Appendix A, marketing hub: business declared it core, *"it had no technical complexity"*). It also PAYS a standing obligation: a type assigned once and never revisited is worse than no classification, because the design keeps obeying a stale verdict (rule 10).
- **still-true-in-2026:** check — the *axes* are unchanged, but the **generic branch's economics moved**. In 2021, "solved problem → buy" was near-absolute because building a solved thing was expensive. With code generation, the cost of a passable in-house implementation of a generic subdomain has fallen far enough that the buy/build line must be re-derived per case, and the book's reason for buying (*"a solution is likely to be more reliable and secure since it has already been tested by many other companies"*) is now the load-bearing half of the argument, not the cost.
- **source:** Ch 1 · Types of Subdomains; Comparing Subdomains; Solution strategy; Table 1-1 (repeated as Table E-1 in Closing Words) · raw lines 419–479, 3839–3844

### 2. core-or-supporting-side-business-test
- **when:** a subdomain is complex enough to argue about and you cannot tell core from supporting.
- **rule:** apply the book's named discriminator: *"Ask whether the subdomain in question can be turned into a side business. Would someone pay for it on its own? If so, this is a core subdomain."*
- **decides:** subdomain type
- **precondition:** you are asking about *this* subdomain in isolation, not about the product it sits inside. A payment-gateway integration inside a product people pay for does not inherit the product's answer.
- **stop:** if the honest answer is *"someone would pay for it, but not enough to matter"*, you have a strategy question, not a classification question — escalate to Rumelt's diagnosis, do not resolve it here by rounding up to core.
- **trade-off named:** BUYS a business-side test an engineer can actually run without a strategy offsite. PAYS a systematic bias toward **core**: almost anything sounds saleable in the abstract, and the test has no price attached, so it inflates unless paired with the complexity check in rule 1 (*"the latter is a typical core subdomain"* only when you must *"implement complex algorithms or business processes orchestrated by complex business rules and invariants"*).
- **still-true-in-2026:** yes
- **source:** Ch 1 · Complexity · raw line 456

### 3. supporting-or-generic-integration-cost-test
- **when:** a ready-made solution exists for a subdomain you currently build, or you are about to adopt one.
- **rule:** *"would it be simpler and cheaper to hack your own implementation, rather than integrating an external one? If so, this is a supporting subdomain."* Cheaper to integrate → generic, adopt it. Cheaper to hack → supporting, build the minimum.
- **decides:** subdomain type · sourcing
- **precondition:** "cost of integrating" is the **full** cost — the adapter, the auth, the vendor's model leaking into yours (rule 22), the version treadmill — not the sticker price.
- **stop:** you cannot estimate the integration cost because you have not read the vendor's contract shape. That is a two-hour spike, not a judgement call; do it before deciding.
- **trade-off named:** BUYS the correct verdict on the one boundary the book calls a gray area. PAYS that the answer is **not stable** — Ch 11's `Supporting to Generic` and `Generic to Supporting` transitions are both this test flipping when a new open-source project appears or when an integration turns out to cost more than it saved. Deciding it once and hard-coding the consequence is the failure.
- **still-true-in-2026:** check — same reason as rule 1's generic branch: the "hack your own" side of the comparison got materially cheaper, which moves cases that were generic in 2021 into supporting.
- **source:** Ch 1 · Complexity; Figure 1-1 discussion · Ch 11 · Supporting to Generic; Generic to Supporting · raw lines 456, 458, 2817–2826

### 4. competitive-advantage-not-necessarily-technical
- **when:** you are about to classify the **software you are building** for a business whose advantage you have already located.
- **rule:** the advantage and the software that serves it are **separate subdomains, and they get separate types**. If the advantage lives in people, design, relationships or contracts, then the system supporting it is *not* core — it is supporting, and it must be built as such. The book's two cases: for a jeweller selling online, *"The jewelry design is [the core subdomain]. The company can use an existing off-the-shelf online shop engine, but it cannot outsource the design of its jewelry"*; for a manual fraud-detection firm, *"The core subdomain is the work the analysts are doing. The system you are building has nothing to do with fraud analysis, it just displays the documents and tracks the analysts' comments. As a result, the software is a supporting subdomain."*
- **decides:** subdomain type
- **precondition:** you have asked *where does the money actually come from* and got an answer more specific than the product name.
- **stop:** if the business insists the software is core while you can only find advantage in the non-software half, do not overrule them silently — that mismatch is rule 7's dialogue, and it is the highest-value conversation in the book.
- **trade-off named:** BUYS the single most expensive mistake in the file. Appendix A's marketing hub is exactly this rule violated: management declared a new profit vertical core, engineering answered with *"event-sourced domain model and CQRS"* plus microservices, and *"behind that complex architecture stood a very simple business logic, one so simple that it could have been implemented using plain active records"* — because *"the businesspeople were looking to profit by leveraging our existing relationships with other companies, and not through the use of clever algorithms."* PAYS: applied carelessly it becomes an excuse to under-build anything with a human in the loop, and the same appendix shows the opposite failure (event crunchers, rule 10).
- **still-true-in-2026:** yes — and sharper, since the AI-era version of the same error is inferring that a domain is core because the *model* is sophisticated.
- **source:** Ch 1 · Sources of competitive advantage · Appendix A · The real problem; Subdomains · raw lines 431–433, 3995–3996, 4013

### 5. legacy-ball-of-mud-as-core-tell
- **when:** doing strategic analysis on an existing system and looking for its core subdomains.
- **rule:** treat the **worst-designed component the business refuses to rewrite** as a candidate core subdomain: *"Another powerful yet unfortunate heuristic for core subdomains is identifying the worst-designed software components—those big balls of mud that all engineers hate but the business is unwilling to rewrite from scratch because of the accompanying business risk."* Then apply the discriminator that stops this from being a rule about ugly code: *"the legacy system cannot be replaced with a ready-made system—it would be a generic subdomain—and any modification to it entails business risks."*
- **decides:** subdomain type
- **precondition:** the refusal to rewrite is driven by **business risk**, not by the absence of tests or the seniority of its author.
- **stop:** if a ready-made replacement does exist and nobody has priced it, stop and price it. The answer decides between core (keep, invest heavily) and generic (buy, delete) — opposite ends of the fork.
- **trade-off named:** BUYS a way to find core subdomains from the code alone, when no domain expert is available — which is the normal condition in a brownfield audit. PAYS a real false-positive rate: components are also unrewritable because they are undocumented, untested, or load-bearing by accident, and this heuristic will label all of those core. Pair it with rules 2 and 4 before acting; and note the complement in the same passage — a supporting subdomain in rough shape *"triggers less emotional response from software engineers since it changes infrequently"*, so engineer sentiment is a signal about **volatility**, not value.
- **still-true-in-2026:** yes
- **source:** Ch 13 · Strategic Analysis · Core subdomains; Supporting subdomains · raw lines 3203, 3207

### 6. staffing-and-sourcing-by-subdomain-type
- **when:** deciding who implements a subdomain — in-house senior, in-house junior, contractor, or vendor.
- **rule:** derive it from the type, in both directions:
  - **core** → in-house only, *"as close as possible to the sources of domain knowledge"*, and *"The organization's most skilled talent should be assigned to work on its core subdomains."* Outsourcing is named unwise: *"It is a strategic investment. Cutting corners on a core subdomain is not only risky in the short term but can have fatal consequences in the long run."*
  - **supporting** → *"do not require highly skilled technical aptitude and provide a great opportunity to train up-and-coming talent"*, and *"the simplicity of the business logic makes supporting subdomains a good candidate for outsourcing."*
  - **generic** → buy or adopt; there is no staffing decision to make.
- **decides:** sourcing
- **precondition:** the type is settled and has survived rule 7's reverse check. Staffing on a wrong type is how the book's worst outcomes happened.
- **stop:** if a core subdomain is currently implemented by an outsourced party, that is one of the five findings rule 31 tells you to surface on the context map — halt and escalate rather than quietly continuing.
- **trade-off named:** BUYS a defensible answer to *who works on what* that is not seniority politics. PAYS: it hands juniors the code with the least review attention and the fewest tests, which is where unnoticed drift accumulates — and rule 10's whole point is that supporting subdomains are exactly the ones that silently become core. Cheap staffing on supporting work is correct *and* it is the mechanism by which type drift goes undetected.
- **still-true-in-2026:** yes
- **source:** Ch 1 · Solution strategy · Ch 11 · Strategic Design Concerns · raw lines 466–472, 2832

### 7. reverse-verify-type-from-the-pattern
- **when:** a subdomain has been classified and an implementation pattern has been chosen — before building.
- **rule:** run the classification **backwards** as a check. The author states it as a deliberate technique: *"Here is a trick I came up with at Marketnovus to foolproof the identification of subdomains: reverse the relationship between subdomains and tactical design decisions. Choose the business logic implementation pattern. No speculation or gold plating; simply choose the pattern that fits the requirements at hand. Next, map the chosen pattern to a suitable subdomain type. Finally, verify the identified subdomain type with the business vision."* The two mismatches have separate, named consequences:
  - **Declared core, but the fitting pattern is trivial** → *"If they think something is a core business, but you can hack it in a day, then it is either a sign that you need to look for finer-grained subdomains or that questions should be raised about the viability of that business."*
  - **Declared supporting, but only an advanced pattern fits** → either *"the businesspeople may have gotten overly creative with their requirements and ended up with accidental business complexity… the requirements can, and probably should, be simplified"*, or *"the businesspeople don't yet realize they employ this subdomain to gain an additional competitive edge."*
- **decides:** subdomain type
- **precondition:** the pattern was chosen from the requirements in front of you, **without** knowing the declared type. If you pick the pattern to match the label, the check is worthless.
- **stop:** on a mismatch, stop building and open the conversation. *"Reversing this relationship creates an additional dialogue between you and the business."* Resolving a mismatch alone, in either direction, is the failure this rule exists to prevent.
- **trade-off named:** BUYS a falsifiable check on the softest judgement in the file, and it is the only rule here whose output is a **business conversation rather than a design**. PAYS: it requires a business counterpart who will engage, and a founder wearing both hats must adversarially argue against himself, which is the condition under which the check is weakest. It also costs a delay at exactly the moment work feels ready to start.
- **still-true-in-2026:** yes
- **source:** Ch 10 · Business Logic Implementation Patterns (*"an excellent opportunity to revisit your assumptions"*) · Appendix A · Mapping design decisions to subdomains · raw lines 2746, 4021–4026
- **provenance note:** stated as a principle in **two** places — as a heuristic in Ch 10 and as a named technique in Appendix A. Not a case study promoted to a rule.

### 8. subdomain-distillation-depth
- **when:** you have a coarse-grained candidate subdomain (typically a department or an org unit) and must decide whether to keep drilling.
- **rule:** drill until the unit is **a set of coherent use cases** — *"subdomains resemble sets of interrelated, coherent use cases. Such sets of use cases usually involve the same actor, the business entities, and they all manipulate a closely related set of data"* — and stop there: *"These are the most precise boundaries of the subdomains."* Then apply the asymmetry: distillation *"is definitely necessary for core subdomains… It's essential that we distill them as much as possible since that will allow us to extract all generic and supporting functionalities and invest the effort on a much more focused functionality."* For the other two, *"If drilling down further doesn't unveil any new insights that can help you make software design decisions, it can be a good place to stop."*
- **decides:** subdomain type
- **precondition:** you started coarse. The book's named entry point is the org chart: *"A good initial heuristic is the company's org chart: its departments and other organizational units."*
- **stop:** *"we cannot drill down indefinitely, looking for insights at lower and lower levels of granularity."* The terminating condition is the founder's halt: a level that resolves no decision and moves no boundary is a level you do not need. Concretely — stop when all finer-grained children are the same type as the parent.
- **trade-off named:** BUYS the thing a coarse classification cannot: the book's worked case finds a **core** routing algorithm hidden three levels inside what looked like an outsourceable customer-service department. PAYS unbounded analysis time if the stop condition is not enforced, and this is precisely the *modellazione autoreferenziale* the founder flagged. Note also that this rule is doing **subdomain-granularity** work, not service-boundary work — a finer subdomain does not imply a finer deployment unit (rule 16 and the ceded Hard Parts rules decide that).
- **still-true-in-2026:** yes
- **source:** Ch 1 · Identifying Subdomain Boundaries; Distilling subdomains; Subdomains as coherent use cases · Ch 11 · Subdomains · raw lines 480–497, 2980–2985

### 9. exclude-non-software-subdomains
- **when:** enumerating an organization's subdomains at the start of an analysis.
- **rule:** identify the business functions that have **nothing to do with software**, name them as such, and drop them from the design: *"it's important to identify business functions that are not related to software, acknowledge them as such, and focus on aspects of the business that are relevant to the software system you are working on."* And do not attempt completeness: *"You don't have to identify all of the core subdomains. It won't be practical or even possible to do so, even for a medium-sized company."*
- **decides:** subdomain type
- **precondition:** you have written down the excluded ones. Dropping silently loses rule 4's evidence — the jeweller's design and the analysts' judgement are *excluded from the software design and are still the core subdomain*.
- **stop:** the analysis is done when the subdomains touching the system in front of you are typed. Continuing to map the rest of the company is the halt condition triggering.
- **trade-off named:** BUYS a bounded analysis with an explicit finish line — the operational form of the founder's stopping rule at the analysis step. PAYS: an excluded non-software subdomain can later acquire a software component (this is the *Supporting to Core* transition arriving from outside the map), so the exclusion list is an input to rule 10's periodic recheck, not a permanent deletion.
- **still-true-in-2026:** yes
- **source:** Ch 1 · Focus on the essentials · Ch 13 · Strategic Analysis · raw lines 499–501, 3208

### 10. subdomain-type-drift
- **when:** periodically, and immediately whenever changing a subdomain becomes disproportionately painful.
- **rule:** treat the type as **mutable** and read the drift off two signals, then act per direction. The primary signal is stated flatly: *"The main indicator of a change in a subdomain's type is the inability of the existing technical design to support current business needs… This 'pain' is an important signal. Use it as a call to reassess the business domain and design choices."* The secondary is complexity growth in a supposedly simple domain: *"if the business logic becomes more complicated over time, there should be a reason for the additional complexity. If it doesn't affect the company's profits, why would it become more complicated? That's accidental business complexity. On the other hand, if it enhances the company's profitability, it's a sign of a supporting subdomain becoming a core subdomain."* Consequences by direction:
  - **supporting → core:** move the implementation in-house, upgrade the pattern, stop outsourcing.
  - **core → generic** (a vendor solved it): stop investing; *"Without massive investments in research and development, [you] can no longer gain a competitive advantage"*.
  - **generic → core** (you decide to out-build the market): bring in-house, best people. Amazon/AWS is the book's named case.
  - **core → supporting** (complexity not justified, i.e. not profitable): *"cut the extraneous complexity, leaving the minimum logic needed"*; outsourcing becomes permissible.
  - **supporting/generic → core** also **voids `separate ways`** (rule 24) — duplicated implementations of a now-core subdomain must be consolidated into customer–supplier.
- **decides:** subdomain type · sourcing · integration pattern
- **precondition:** the original type was recorded somewhere you can find. Drift is undetectable against an unwritten baseline — which is exactly what an ADR linked to the code is for.
- **stop:** if complexity is growing and you **cannot** tie it to profit, do not upgrade the pattern — that is accidental business complexity and the correct action is to simplify the requirements, not to model them better.
- **trade-off named:** BUYS the one thing static classification cannot: Appendix A's event crunchers were correctly typed supporting, correctly built as transaction scripts, and then *"those simple flags evolved into a real business logic, with complex rules and invariants. What started out as transaction scripts evolved into a full-fledged core business subdomain"* — with the design unchanged, producing *"a very big ball of mud"* and a rewrite a year later. PAYS a standing review obligation with no natural trigger other than pain, and pain is a **lagging** indicator: by the time it is unmistakable, the rewrite is already the cheapest option. The book offers no leading indicator, and this is a real gap.
- **still-true-in-2026:** yes
- **source:** Ch 11 · Changes in Domains (all six transitions); Strategic Design Concerns; Tactical Design Concerns · Appendix A · Subdomains; Don't ignore pain · raw lines 2796–2837, 4011–4028

---

# B. The boundary of a context vs the boundary of a subdomain

**7 rules.** Scope item 2. These set a **ceiling**, a **floor**, an **authority split** and a **direction of
travel** — never a method for locating a line. The method is ceded in `when_not`.

### 11. subdomains-discovered-contexts-designed
- **when:** anyone proposes changing a boundary, or two people disagree about where one is.
- **rule:** first establish **which kind of boundary is in play**, because they have different owners. *"It's crucial to remember that subdomains are discovered and bounded contexts are designed. The subdomains are defined by the business strategy. However, we can design the software solution and its bounded contexts to address the specific project's context and constraints."* A subdomain boundary is a **finding about the business** — you may be wrong about it, but you may not choose it. A context boundary is a **design decision you own**.
- **decides:** context boundary
- **precondition:** none. This is the first move in any boundary conversation.
- **stop:** if someone is *designing* a subdomain, halt — they are changing the business strategy under the guise of a refactor, and that decision is not theirs. The book flags exactly one exception, and it is the founder's situation: *"Depending on the organization you are working in, you may be wearing two hats and be in charge of both software engineering and business development. As a result, you have the ability to affect both the software design (bounded contexts) and the business strategy (subdomains)."* When both hats are on one head, **say which one is speaking**, because the check that normally comes from the other party is gone.
- **trade-off named:** BUYS the end of a whole class of circular argument, and it is what makes rule 7's reverse check meaningful (you cannot verify a type against a business vision if the type is itself a design choice). PAYS: it makes the subdomain map a dependency on business knowledge you may not have, and in a solo shop the exception above swallows the rule unless the discipline is enforced by hand.
- **still-true-in-2026:** yes
- **source:** Ch 3 · Bounded Contexts Versus Subdomains; footnote 1 · raw lines 651–667, 738

### 12. context-ceiling-by-language-consistency
- **when:** proposing a context boundary, or challenging one as too wide.
- **rule:** the **widest legal boundary is where the ubiquitous language stops being consistent**, and consistency has a mechanical test: *"each term of the ubiquitous language should have one and only one meaning"* — no ambiguous terms, no synonyms. *"The consistency of the ubiquitous language only helps to identify the widest boundary of that language. It cannot be any larger, because then there will be inconsistent models and terminology."* Two domain experts using one word for two things is not a communication problem to fix; it is **the ceiling telling you where it is**.
- **decides:** context boundary
- **precondition:** you have listened to actual domain experts, not read a schema. The book's canonical case is *lead*, meaning a notification in marketing and a whole lifecycle in sales.
- **stop:** if the response to a term collision is to **prefix** the terms (`MarketingLead`, `CRMLead`), stop — that is the named anti-pattern, on two grounds: *"it induces cognitive load. When should each model be used?"* and *"the implementation of the model won't be aligned with the ubiquitous language. No one would use the prefixes in conversations."* Appendix A is this failure observed live: *"we were adding awkward prefixes to those 'aggregates'' names… Interestingly, we never used those prefixes in our conversations with the domain experts."*
- **trade-off named:** BUYS a **falsifiable ceiling** — the one thing in this book that can rule a proposed boundary out, and the reason a single enterprise-wide model is not merely inelegant but illegal. PAYS: it is only a ceiling. It says nothing about anything narrower, which is the entire space where real decisions live, and the space this extract cedes. It also PAYS a dependency on access to domain experts, which the ceded `domain-modeling` skill governs.
- **still-true-in-2026:** yes
- **source:** Ch 3 · Inconsistent Models; Scope of a Bounded Context · Ch 2 · Consistency · Appendix A · More "aggregates"! · raw lines 611–643, 63–72, 3931

### 13. never-split-a-subdomain-across-contexts
- **when:** a proposed decomposition would put parts of one subdomain in two different contexts.
- **rule:** **don't.** *"One thing to beware of is splitting a coherent functionality into multiple bounded contexts. Such division will hinder the ability to evolve each context independently. Instead, the same business requirements and changes will simultaneously affect the bounded contexts and require simultaneous deployment of the changes."* The test is rule 8's: *"identify sets of coherent use cases that operate on the same data and avoid decomposing them into multiple bounded contexts."* A context may contain **several** subdomains; it may never contain **part** of one.
- **decides:** context boundary
- **precondition:** the subdomains have been distilled to coherent-use-case granularity (rule 8). Without that, "one subdomain" is not a defined quantity and this rule cannot be applied.
- **stop:** hard out, no exception offered. The book's own worst outcome is this violation: the CRM's `Lead` was dissected across an implicit boundary when business logic was offloaded to stored procedures, producing *"two teams working on the same business component… each team had its own vocabulary"*, then *"Nasty production issues that had flown under the radar for years corrupted our most precious asset: our data"*, and finally a full rewrite *"a couple of years later"*. Appendix A files it under **"Suicidal boundaries… Never try this at home, okay?"**
- **trade-off named:** BUYS the detection of a decomposition that will produce permanent lockstep deployment and duplicated rules that *"went out of sync immediately"*. PAYS: obeying it can force a context wider than you want it — which is a real cost and the correct one to pay. Note it is a **prohibition, not a locator**: it removes candidate boundaries and never proposes one.
- **still-true-in-2026:** yes
- **source:** Ch 3 · Scope of a Bounded Context · Appendix A · Tower of Babel 2.0; Boundaries of Bounded Contexts · raw lines 649, 3946–3950, 4034

### 14. start-wide-decompose-on-knowledge
- **when:** designing context boundaries for the first time, in a domain you do not yet fully understand.
- **rule:** **start wide and narrow later**, keyed on domain knowledge and volatility, not on size. *"Rather than making the model a function of the desired size—optimizing for small bounded contexts—it's much more effective to do the opposite: treat the bounded context's size as a function of the model it encompasses."* The reason is an asymmetry in the cost of being wrong: *"Broad bounded context boundaries, or those that encompass multiple subdomains, make it safer to be wrong about the boundaries or the models of the included subdomains. Refactoring logical boundaries is considerably less expensive than refactoring physical boundaries. Hence, when designing bounded contexts, start with wider boundaries. If required, decompose the wide boundaries into smaller ones as you gain domain knowledge."* The dial: *"the less you know about the business domain, the wider the initial boundaries."* And it applies **mainly to core subdomains**, since *"both generic and supporting subdomains are more formularized and much less volatile."*
- **decides:** context boundary · modernization sequence
- **precondition:** you can state honestly how well you know the domain. This rule's input is your own ignorance, and it is the one input people misreport.
- **stop:** *"striving for small bounded contexts can backfire too. The smaller they are, the more integration overhead the design induces."* Also stop if you are choosing a width to hit a service count or to match a team count — Nick Tune, quoted: *"There are many useful and revealing heuristics for defining the boundaries of a service. Size is one of the least useful."*
- **trade-off named:** BUYS reversibility exactly where uncertainty is highest, and it is the book's answer to premature microservices. PAYS a wide context you will have to split later, with all the coordination that a shared codebase implies while it lasts, and it PAYS the risk that "later" never arrives — *"refactoring bounded context boundaries is an expensive undertaking, and in many cases, the ineffective boundaries remain unattended and end up accumulating technical debt."* **Named conflict with a sibling, do not average it:** Team Topologies rule 1 caps a unit by cognitive load, and a deliberately wide initial context can exceed that cap. The two are not reconcilable in general — Khononov optimizes for cheap boundary correction, TT for sustainable ownership. **When one team must own the wide context, TT rule 1 governs and the width is capped**; when the wide context is a single owner's own code, Khononov's asymmetry governs. Say which one you invoked.
- **still-true-in-2026:** yes — and the industry has moved toward it since 2021 (the modular-monolith-first default).
- **source:** Ch 10 · Bounded Contexts · Ch 11 · Domain Knowledge · Appendix A · Boundaries of Bounded Contexts · raw lines 2724–2732, 2971, 4035–4036

### 15. one-team-per-context
- **when:** assigning ownership of a context, or discovering that two parties are editing one.
- **rule:** *"A bounded context should be implemented, evolved, and maintained by one team only. No two teams can work on the same bounded context."* The relation is **one-directional**: *"a bounded context should be owned by only one team. However, a single team can own multiple bounded contexts."* The stated mechanism: *"This segregation eliminates implicit assumptions that teams might make about one another's models. Instead, they have to define communication protocols for integrating their models and systems explicitly."*
- **decides:** context boundary
- **precondition:** none.
- **stop:** two teams on one context is a **finding to escalate**, not a situation to manage — it is one of the five items rule 31 makes you surface. The book names exactly one deliberate exception, and prices it: a shared kernel *"contradicts the principle that a single team should own a bounded context"* and is admissible only under rule 20's conditions.
- **trade-off named:** BUYS explicit contracts in place of implicit assumptions, which is the mechanism behind every rule in section C. PAYS: it makes team growth a **forcing function on architecture** — *"adding new development teams can cause the existing wider bounded context boundaries to split into smaller ones so that each team can work on its own bounded context"* — so headcount changes now trigger boundary changes, which rule 14 just told you are expensive. This rule and rule 14 are in tension by construction. **Duplicate provenance, deliberately not re-derived here:** this is Team Topologies rule 15 (`Single-owner rule`) arriving from a different direction (model consistency rather than ownership clarity). TT's version is stricter and better specified — it governs access, pull requests and temporary grants. **Use TT rule 15 as the operative statement**; this rule is kept only because it supplies the *reason* a shared kernel is an exception rather than a normal option.
- **still-true-in-2026:** yes
- **source:** Ch 3 · Ownership Boundaries · Ch 4 · When to use shared kernel · Ch 11 · Organizational Changes · raw lines 677–681, 777, 2961

### 16. context-microservice-validity-bracket
- **when:** validating a proposed physical decomposition — before committing, and whenever "should this be a microservice" is asked.
- **rule:** check the proposal against a **bracket, not a target**. *"Although microservices are bounded contexts, not every bounded context is a microservice."* The bounded context is the **wide** end — *"bounded contexts… denote the boundaries of the largest valid monolith. Such a monolith should not be confused with a big ball of mud; it's a viable design option"*. The aggregate is the **narrow** end — *"the aggregate's boundary is the narrowest boundary possible."* Anything inside the bracket is legal: *"if the system is not decomposed into proper bounded contexts or is decomposed past the microservices threshold, it will result in a big ball of mud or a distributed big ball of mud, respectively."* Within the bracket, the book's **default** is subdomain alignment: *"All of these things make subdomains the safest boundary for designing microservices."*
- **decides:** context boundary
- **precondition:** the subdomains are distilled (rule 8) and the language ceiling is known (rule 12). Both ends of the bracket are computed from those.
- **stop:** **the moment the question becomes "where exactly inside the bracket".** That is the ceded question — go to Hard Parts rules 10, 11, 24, 26, 30 for the disintegrator/integrator analysis and to Team Topologies rules 1, 12, 13 for the fracture plane and the litmus test. This rule's entire job is to say which candidates are *illegal*. It also stops any decomposition argued from size: the book's own exercise answer to "what part of a microservice should be micro" is *"The knowledge of the business domain and its intricacies exposed across the service's boundary and reflected by its public interface"* — not lines of code, not team size.
- **trade-off named:** BUYS a cheap veto on both failure modes at once, and it is why *"Shallow services are also the reason why so many microservices-oriented projects fail."* PAYS: a bracket is not a decision, and reporting one as if it were is how this extract would become the third provenance on the boundary line. It also PAYS a dependency on Ousterhout's depth heuristic to explain *why* the narrow end fails — and depth is owned by the installed `codebase-design` skill, so do not re-derive it here.
- **still-true-in-2026:** yes
- **source:** Ch 14 · Domain-Driven Design and Microservices' Boundaries; Bounded Contexts; Aggregates; Subdomains; Conclusion; Exercises · raw lines 3405–3431, 3445, 3454–3463
- **judgment call:** flagged in `EXTRACTION-NOTES.md` §3. Ch 14 is the chapter closest to the ceded boundary field, and this is the single rule extracted from it. It is admitted as a **validity check with an explicit hand-off**, not as a locator.

### 17. chatty-contexts-signal-a-wrong-model
- **when:** monitoring an existing decomposition, particularly one that has grown.
- **rule:** treat **call frequency between contexts as a model defect**, not a performance problem. *"you may notice that a number of bounded contexts become increasingly 'chatty' over time, unable to complete any operation without calling another bounded context. That can be a strong signal of an ineffective model and should be addressed by redesigning the bounded contexts' boundaries to increase their autonomy."*
- **decides:** context boundary
- **precondition:** you can observe cross-context call volume per operation. Without that, this rule is unusable — it is the one rule here with an instrumentation dependency.
- **stop:** do not respond by caching, batching, or co-locating. Those hide the signal. The named endpoint of ignoring it is in Appendix A: services drawn around aggregates *"became more and more chatty. Eventually, almost each service required data from all the other services to complete some of its operations. The result? What was intended to be a decoupled system ended up being a distributed monolith: an absolute nightmare to maintain."*
- **trade-off named:** BUYS a **leading** indicator of a wrong boundary — the only one in this file that fires before the pain of rule 10. PAYS: chattiness has legitimate causes too (a genuine workflow across contexts, an integration pattern doing its job), so acting on it alone can trigger a boundary rewrite that a `separate ways` or an aggregating ACL (rule 26) would have resolved for far less. The book gives no threshold; deriving one is out of its competence — see Evolutionary's `derive-thresholds-from-production-not-estimates`.
- **still-true-in-2026:** yes
- **source:** Ch 11 · Bounded Contexts · Appendix A · Micro what? · raw lines 2989, 3992

---

# C. Integration-pattern selection between two contexts

**11 rules.** This is contract fork (b). Rule 18 is the fork; 19–24 are the admission test per branch;
25 handles drift; 26–28 are the mechanics that make a chosen pattern real.

**Correction to the acquisition brief, and it matters for routing.** The brief lists *"shared kernel ·
customer–supplier · conformist · anti-corruption layer · open-host service + published language · separate
ways"* as six peers. The book's taxonomy is **three groups containing six patterns**, and
`customer–supplier` is a **group name**, not a pattern: *"We will divide the patterns into three groups,
each representing a type of team collaboration: cooperation, customer–supplier, and separate ways."*
Cooperation = **partnership** + **shared kernel**. Customer–supplier = **conformist** + **anticorruption
layer** + **open-host service**. Separate ways stands alone. **Partnership is the pattern the brief's list
omits**, and it is the one a solo operator will reach for by default — so it is extracted (rule 19) with
its cost stated.

### 18. integration-pattern-selection
- **when:** two bounded contexts must interact and you are choosing how.
- **rule:** select in **three keyed steps**, in this order.
  1. **Is collaboration between the two owners good?** *"Cooperation patterns relate to bounded contexts implemented by teams with well-established communication… This also applies to teams with dependent goals, where one team's success depends on the success of the other, and vice versa. Again, the main criterion here is the quality of the teams' communication and collaboration."* → **cooperation group**: `partnership` (rule 19) or `shared kernel` (rule 20).
  2. **If not — where is the power?** *"Unlike in the cooperation case, both teams (upstream and downstream) can succeed independently. Consequently, in most cases we have an imbalance of power: either the upstream or the downstream team can dictate the integration contract."* → **customer–supplier group**: power upstream and you accept their model → `conformist` (21); power upstream and you refuse their model → `anticorruption layer` (22); power **downstream**, you are the supplier with consumers to protect → `open-host service` + published language (23).
  3. **If integration costs more than duplication** → `separate ways` (24).
- **decides:** integration pattern
- **precondition:** you can state, out loud, (a) the collaboration quality between the two owners, (b) which side can dictate the contract, and (c) whether the two models genuinely differ. **All three are social or model facts, not technical ones** — this fork is not resolvable from the code.
- **stop:** if the two contexts are **the same subdomain split in two**, stop: you are in rule 13's territory and no integration pattern will save it. If the models are actually *identical*, you have one context, not two.
- **trade-off named:** BUYS the thing the vocabulary alone cannot — a *selection* rule with a test per branch, which is the falsifiable success criterion this acquisition was judged against. PAYS: it is keyed on **team power relationships**, so it degenerates in a one-person shop (see `when_not` → Solo-operator collapse: partnership and shared kernel collapse; conformist, ACL and separate ways survive intact because the upstream is a vendor or a legacy system). It also PAYS a blind spot the book admits: *"even if bounded contexts are limited to a single subdomain, there still can be multiple integration patterns at play"* — one pair of contexts can need two patterns at once, and this fork returns one answer.
- **still-true-in-2026:** yes
- **source:** Ch 4 · the whole chapter; Cooperation; Customer–Supplier; Separate Ways; Conclusion · Ch 9 · Model Translation (restated) · raw lines 753–756, 781–785, 813, 842–854, 2355–2357

### 19. partnership-preconditions
- **when:** considering ad hoc, two-way coordinated integration between two contexts.
- **rule:** admissible only with **genuinely strong communication**, because there is no contract to fall back on: *"the integration between bounded contexts is coordinated in an ad hoc manner. One team can notify a second team about a change in the API, and the second team will cooperate and adapt—no drama or conflicts."* Its defining property is symmetry: *"The coordination of integration here is two-way. No one team dictates the language that is used for defining the contracts."* Required, not optional: *"Well-established collaboration practices, high levels of commitment, and frequent synchronizations between teams are required for successful integration in this manner. From a technical perspective, continuous integration of the changes applied by both teams is needed to further minimize the integration feedback loop."*
- **decides:** integration pattern
- **precondition:** both owners can and will synchronize frequently. *"This pattern might not be a good fit for geographically distributed teams since it may present synchronization and communication challenges."*
- **stop:** the moment synchronization degrades — that is rule 25's first transition, and staying in partnership past that point is the named path to accumulating integration failures.
- **trade-off named:** BUYS the lowest ceremony of any option and the fastest change cycle. PAYS: **no protection whatsoever.** There is no contract, no translation layer, no versioning; every change is a conversation, and the pattern fails silently as the relationship degrades rather than at a build break. For a solo operator this is the default and the trap — the book's own warning is that ad hoc integration between two contexts you both own *"can 'wash out' the contexts' boundaries over time"*, which is the argument for spending rule 20's ceremony on yourself.
- **still-true-in-2026:** yes
- **source:** Ch 4 · Partnership; When to use shared kernel · raw lines 758–763, 780

### 20. shared-kernel-admission
- **when:** the same model, or part of it, would have to be implemented in two contexts.
- **rule:** admissible only under a **cost comparison**, and then only in a minimized scope. The criterion: *"The overarching applicability criterion for the shared kernel pattern is the cost of duplication versus the cost of coordination. Since the pattern introduces a strong dependency between the participating bounded contexts, it should be applied only when the cost of duplication is higher than the cost of coordination."* The scope: *"the overlapping model should be limited, exposing only that part of the model that has to be implemented by both bounded contexts. Ideally, the shared kernel will consist only of integration contracts and data structures that are intended to be passed across the bounded contexts' boundaries."* The mandatory mechanism: *"each change to the shared kernel must trigger integration tests for all the affected bounded contexts"*, because *"Not propagating shared kernel changes to all related bounded contexts leads to inconsistencies in a model: bounded contexts may rely on stale implementations of the shared kernel, leading to data corruption and/or runtime issues."* Its four named legitimate uses: teams that cannot achieve partnership (geography, politics); **gradual modernization of a legacy system** (temporary); two contexts owned by the **same** team, to stop the boundaries washing out; and — by the volatility argument — *"the shared kernel will naturally be applied for the subdomains that change the most: the core subdomains."*
- **decides:** integration pattern
- **precondition:** you can estimate both costs, and the volatility of the shared model, since *"The difference between the integration and duplication costs depends on the volatility of the model. The more frequently it changes, the higher the integration costs will be."*
- **stop:** it **violates rule 15 by construction** and the book says so: *"If the participating bounded contexts are not implemented by the same team, introducing a shared kernel contradicts the principle that a single team should own a bounded context."* Therefore *"the use of a shared kernel has to be justified. It's a pragmatic exception that should be considered carefully."* If you cannot write down which of the four named uses applies, do not use it.
- **trade-off named:** BUYS the elimination of duplicated volatile model code and — in the same-team case — explicit boundaries that ad hoc integration would erode. PAYS the most expensive coupling in the chapter: *"The overlapping model couples the lifecycles of the participating bounded contexts. A change made to the shared model has an immediate effect on all the bounded contexts."* It also PAYS a permanent CI obligation, and it PAYS the ownership principle itself.
- **still-true-in-2026:** yes — the mono-repo mechanism it describes is now the common case rather than the alternative.
- **source:** Ch 4 · Shared Kernel; Shared scope; Implementation; When to use shared kernel · raw lines 764–780

### 21. conformist-admission
- **when:** an upstream context dictates the contract and you are deciding whether to simply accept it.
- **rule:** accept the upstream model — become conformist — when the imbalance is real and the model is tolerable. The situation: *"the balance of power favors the upstream team, which has no real motivation to support its clients' needs. Instead, it just provides the integration contract, defined according to its own model—take it or leave it."* The admission test is a **positive judgement about their model**, not resignation: *"the contract exposed by the upstream team may be an industry-standard, well-established model, or it may just be good enough for the downstream team's needs."*
- **decides:** integration pattern
- **precondition:** you have actually evaluated their model against your needs. "Good enough" is a finding, not a default.
- **stop:** stop and go to rule 22 if any of the three ACL triggers holds — most sharply if **your** side is a core subdomain. Conforming is a decision to give up autonomy (*"The downstream team's decision to give up some of its autonomy"*), and a core subdomain is the one place that is not yours to give.
- **trade-off named:** BUYS the cheapest possible integration: no translation layer, no model of your own to maintain, and free alignment with an industry standard if that is what you conformed to. PAYS your model's independence — their concepts are now in your code, and their changes are now your changes. The failure mode is stated as a rule in the next entry: *"If a bounded context conforms to a mess, it risks becoming a mess itself."*
- **still-true-in-2026:** yes
- **source:** Ch 4 · Conformist · raw lines 786–791

### 22. anticorruption-layer-admission
- **when:** you are downstream, cannot conform, and must translate.
- **rule:** build an ACL — *"it can translate the upstream bounded context's model into a model tailored to its own needs"* — when **any** of the book's three named triggers holds:
  1. *"When the downstream bounded context contains a core subdomain — A core subdomain's model requires extra attention, and adhering to the supplier's model might impede the modeling of the problem domain."*
  2. *"When the upstream model is inefficient or inconvenient for the consumer's needs — If a bounded context conforms to a mess, it risks becoming a mess itself. That is often the case when integrating with legacy systems."*
  3. *"When the supplier's contract changes often — The consumer wants to protect its model from frequent changes. With an anticorruption layer, the changes in the supplier's model only affect the translation mechanism."*
- **decides:** integration pattern
- **precondition:** the power imbalance is genuinely upstream and unchangeable. If you can negotiate, you are in partnership or customer–supplier proper, and an ACL is over-engineering.
- **stop:** if translating would cost more than duplicating the functionality, stop — that is `separate ways` (rule 24): *"The models may be so different that a conformist relationship is impossible, and implementing an anticorruption layer would be more expensive than duplicating the functionality."*
- **trade-off named:** BUYS a clean model on your side plus a single blast radius for their changes, and it *"isolates the downstream consumer from foreign concepts that are not relevant to its bounded context. Hence, it simplifies the consumer's ubiquitous language and model."* PAYS a translation layer you own forever: every field they add is a mapping decision, and the layer is code with no business value that must nevertheless be tested and maintained. **Name collision, stated explicitly:** this is *not* the `jit-anticorruption-layer` of `ford-parsons-evolutionary-architectures` (Evolutionary's is a wrapper around a **third-party library** whose interface you own, adopted *just in time*; a UI/backend proxy also gets called an anticorruption layer there). Khononov's ACL is a translation layer between **two models**, chosen because of a **power relationship you cannot change**. Same name, different pattern, different trigger, different cost — see `glossary.md`.
- **still-true-in-2026:** yes — and this is the highest-value rule in the file for a solo operator, since the vendor-and-legacy case survives the collapse of every team-keyed branch.
- **source:** Ch 4 · Anticorruption Layer · raw lines 792–803

### 23. open-host-service-admission
- **when:** you are the **upstream** context and have consumers whose interests you must protect.
- **rule:** when *"the power is skewed toward the consumers"* and *"The supplier is interested in protecting its consumers and providing the best service possible"*, **decouple your public interface from your implementation model** and publish the former as a **published language**: *"the upstream supplier decouples the implementation model from the public interface. This decoupling allows the supplier to evolve its implementation and public models at different rates."* The published language is deliberately **not** your ubiquitous language: *"The supplier's public interface is not intended to conform to its ubiquitous language. Instead, it is intended to expose a protocol convenient for the consumers, expressed in an integration-oriented language."* And it buys a specific capability: *"the integration model's decoupling allows the upstream bounded context to simultaneously expose multiple versions of the published language, allowing the consumer to migrate to the new version gradually."*
- **decides:** integration pattern
- **precondition:** you have more than one consumer, or one consumer you cannot afford to break. With a single consumer you control, this is ceremony.
- **stop:** *"that's only possible if the modified implementation model can be translated into the published language the consumers are already using."* When an internal change cannot be expressed in the current published language, the version boundary is the decision point — stop and version, do not leak the change through.
- **trade-off named:** BUYS freedom to change your internals without a consumer migration, plus gradual multi-version migration, plus a smaller public surface (which is what makes the service "deep" in Ch 14's terms). PAYS a **second model to design, maintain, translate and version** — *"the open-host service pattern is a reversal of the anticorruption layer pattern: instead of the consumer, the supplier implements the translation"* — so you have taken on your consumers' translation cost, deliberately. It also PAYS the discipline of rule 28, which is where teams usually fail this pattern.
- **still-true-in-2026:** yes
- **source:** Ch 4 · Open-Host Service · Ch 14 · Open-Host Service · Ch 16 · Combining Data Mesh and Domain-Driven Design · raw lines 804–812, 3434–3438, 3795

### 24. separate-ways-admission
- **when:** integration is being assumed by default and you have not asked whether it is worth it.
- **rule:** **duplicate instead of integrating** when integration costs more than duplication. Three named reasons: **communication difficulties** (*"When teams have a hard time collaborating and agreeing, it may be more cost-effective to go their separate ways and duplicate functionality in multiple bounded contexts"*); **a generic subdomain that is easy to integrate locally** (*"An example is a logging framework; it would make little sense for one of the bounded contexts to expose it as a service. The added complexity of integrating such a solution would outweigh the benefit of not duplicating the functionality. Duplicating the functionality would be less expensive than collaborating"*); and **model differences too large to bridge** (see rule 22's stop).
- **decides:** integration pattern
- **precondition:** you have priced both sides. This rule is a comparison, and it is the only rule in the section whose answer is "build it twice".
- **stop:** **hard out on core subdomains.** *"The separate ways pattern should be avoided when integrating core subdomains. Duplicating the implementation of such subdomains would defy the company's strategy to implement them in the most effective and optimized way."* And when a duplicated subdomain **becomes** core (rule 10), separate ways is void: *"If the subdomain morphs into a core subdomain, duplicating its functionality by multiple teams is no longer acceptable. Hence, the teams have no choice but to integrate their implementations. The customer–supplier relationship will make the most sense in this case, since the core subdomain will only be implemented by one team."*
- **trade-off named:** BUYS the removal of a coordination cost that was buying nothing, and it is the section's only anti-integration rule — the direct counterweight to the reflex that every shared concept must become a service. PAYS duplicated logic that will drift, and it PAYS the standing risk that the duplicated thing becomes core while nobody is watching, at which point you owe a consolidation. Being *forced* into it by politics is also a diagnosis, not a design: rule 30 reads clustered separate-ways as an organizational signal.
- **still-true-in-2026:** yes
- **source:** Ch 4 · Separate Ways; Note · Ch 11 · Strategic Design Concerns · Ch 13 · Separate ways · raw lines 813–822, 2831, 3247

### 25. integration-drift-on-organizational-change
- **when:** the organization changes — a team moves, splits, grows, or relations sour — or integration failures between two contexts are becoming frequent.
- **rule:** **re-derive the integration pattern**, because rule 18's inputs have changed. The two named transitions:
  - **partnership → customer–supplier.** *"The partnership pattern assumes there is strong communication and collaboration among teams. As time goes by, that might cease to be the case; for example, when work on one of the bounded contexts is moved to a distant development center… it may make sense to move away from the partnership pattern toward a customer–supplier relationship"* — i.e. to conformist, ACL, or open-host service.
  - **customer–supplier → separate ways.** *"it's not uncommon for teams to have severe communication problems… At some point, it may become more cost-effective to duplicate the functionality instead of continuously chasing one another's tails."*
  Read the inverse too, as a diagnostic: a shift **to** separate ways implies both that the teams struggled to cooperate **and** that the duplicated functionality is not a core subdomain (Ch 11 exercise 2, answers A and B).
- **decides:** integration pattern
- **precondition:** the current pattern was recorded — on the context map (rule 29). Drift is invisible without the baseline.
- **stop:** if the duplicated functionality **is** core, `separate ways` is unavailable no matter how bad the collaboration is (rule 24's hard out). The escalation is organizational, not architectural: consolidate ownership.
- **trade-off named:** BUYS a design that tracks the organization instead of a diagram that describes a company that no longer exists. PAYS: every re-derivation is real work — an ACL to build, a published language to version, a duplicate to write — and it means integration patterns are **not** long-lived decisions, which is uncomfortable for anything documented as an ADR. Note the asymmetry: the drift direction the book documents is always **toward less collaboration**; it never describes an upgrade path back.
- **still-true-in-2026:** yes
- **source:** Ch 11 · Organizational Changes; Partnership to Customer–Supplier; Customer–Supplier to Separate Ways; Exercises · Ch 13 · Customer–supplier relationships · raw lines 2959–2967, 3005–3015, 3240

### 26. translation-stateless-or-stateful
- **when:** an ACL or OHS has been chosen and must be built.
- **rule:** one fork, keyed on whether translation needs memory. *"The model's translation logic can be either stateless or stateful. Stateless translation happens on the fly, as incoming (OHS) or outgoing (ACL) requests are issued, while stateful translation involves a more complicated translation logic that requires a database."*
  - **Stateless** → the proxy pattern. **Synchronous:** embed the transform in the context's codebase, or offload to an API gateway (which *"can alleviate the process of managing and serving multiple versions of the bounded context's API"*). **Asynchronous:** a message proxy that subscribes, transforms and forwards — and which *"can also reduce the noise on the target bounded context by filtering out irrelevant messages."*
  - **Stateful** → required when the translation must **aggregate** (batching, unifying many fine-grained messages into one) or **unify multiple sources** (backend-for-frontend; a context fronted by an ACL that aggregates from all others *"to decouple the integration and business logic complexities"*). Hard constraint: *"Model transformation that aggregates incoming data cannot be implemented using an API gateway, and thus requires more elaborate, stateful processing… the translation logic requires its own persistent storage."*
  - A shared ACL consumed by several downstream contexts becomes a context in its own right: *"Such bounded contexts, which are mainly in charge of transforming models for more convenient consumption by other components, are often referred to as interchange contexts."*
- **decides:** integration pattern
- **precondition:** you know whether any consumer needs data combined across messages or sources. That question, not the transport, decides the branch.
- **stop:** if you are building custom stateful translation, first check the off-the-shelf route — *"you can avoid implementing a custom solution for a stateful translation by using off-the-shelf products; for example, a stream-process platform (Kafka, AWS Kinesis, etc.), or a batching solution (Apache NiFi, AWS Glue, Spark, etc.)"*. By rule 1, a translation-and-batching engine is a **generic** subdomain and building it in-house is the named failure.
- **trade-off named:** Stateless BUYS a component with no storage, no consistency question and no operational footprint; PAYS the inability to aggregate, and — via an API gateway — a piece of your integration semantics living in vendor configuration outside your repo. Stateful BUYS aggregation and multi-source unification; PAYS **its own database**, which means its own backups, migrations, consistency semantics and failure modes, plus a new component that can be stale. The interchange context PAYS a context nobody owns by default.
- **still-true-in-2026:** check — the fork and the constraint are structural and hold; the **named products** (Kong, KrakenD, AWS API Gateway, Apigee, Azure API Management, Kafka, Kinesis, NiFi, Glue, Spark) are a 2021 list and their relative fit has moved. Re-verify tooling, not the rule.
- **source:** Ch 9 · Model Translation; Stateless Model Translation; Stateful Model Translation · raw lines 2354–2392

### 27. event-type-selection-for-cross-context-integration
- **when:** two contexts integrate asynchronously and you are designing the message.
- **rule:** choose among the **three** event types by consistency requirement, then compress. The taxonomy: **event notification** (*"the notification shouldn't carry all the information needed for the subscribers to react to the event"* — the consumer follows a link or queries); **event-carried state transfer** (*"ECST messages include all the data reflecting the change in the state"* — *"Conceptually, using event-carried state transfer messages is an asynchronous data replication mechanism"*); **domain event** (*"intended to model and describe the business domain"*, useful *"even if no external consumer is interested in them"*). The selection rule:
  - *"If the components can settle for eventually consistent data, use the event-carried state transfer message."*
  - *"If the consumer needs to read the last write in the producer's state, issue an event notification message, with a subsequent query to fetch the producer's up-to-date state."*
  - *"sparingly use domain events for communication with external bounded contexts. Consider designing a set of dedicated public domain events."*
  Secondary criteria for preferring notification: **security** (*"Enforcing the recipient to explicitly query for the detailed information prevents sharing sensitive information over the messaging infrastructure and requires additional authorization of the subscribers to access the data"*) and **concurrency** (stale-on-arrival data; and with competing consumers, the query *"can be integrated with pessimistic locking"*).
- **decides:** integration pattern
- **precondition:** you can state the consumer's consistency requirement. Everything else follows from it, and it is the question nobody asks.
- **stop:** *"Choosing the correct type of event message is what makes (decouples) or breaks (couples) a distributed system."* If the choice is being made by what is convenient to publish rather than what the consumer needs, halt — that is rule 28.
- **trade-off named:** Notification BUYS a minimal public interface, no sensitive data in transit, and always-fresh reads; PAYS a synchronous dependency on the producer at read time, which forfeits the fault tolerance async integration was bought for. ECST BUYS consumer autonomy — *"the consumers can continue functioning even if the producer is not available"* — and removes repeated queries; PAYS a replica in every consumer, permanently eventually-consistent, plus every field you ship becoming part of your contract. Domain events BUY domain fidelity; PAY implementation coupling when published outward (rule 28).
- **still-true-in-2026:** yes — Fowler's 2017 taxonomy the chapter cites is still the standard vocabulary.
- **source:** Ch 15 · Types of Events; Event-Driven Design Heuristics; Evaluate consistency requirements; Use public and private events · raw lines 3515–3582, 3654–3662
- **judgment call:** flagged in `EXTRACTION-NOTES.md` §3. Ch 15 is nominally a Part IV "other methodologies" chapter, but its subject is explicitly *"designing a bounded context's public interface"* — the async form of contract fork (b) — so it is admitted. The chapter's coupling taxonomy is **not** extracted; coupling is Hard Parts' field.

### 28. never-expose-private-domain-events
- **when:** publishing events out of a context, especially an event-sourced one.
- **rule:** treat events as **part of the published language**, and keep private events private. *"Be wary of exposing implementation details when publishing domain events, especially in event-sourced aggregates. Treat events as an inherent part of the bounded context's public interface. Therefore, when implementing the open-host service pattern, ensure that the events are reflected in the bounded context's published language."* The mechanism is rule 26's async proxy: *"It's a common mistake to design and expose a published language for the model's objects and allow domain events to be published as they are, thereby exposing the bounded context's implementation model."* When several consumers each project the same view from your raw events, **move the projection into the producer**: *"the CRM can follow the consumer-driven contract pattern: project the model needed by the consumers and make it a part of the bounded context's published language—an integration-specific model, decoupled from the internal implementation model."*
- **decides:** integration pattern
- **precondition:** you can distinguish which of your events exist for your own state transitions and which exist for consumers. If every event is public, you have no published language.
- **stop:** if two consumers are building the same projection from your events, stop and move the projection upstream. Two consumers with identical derivation logic is duplicated business logic *"that has to change simultaneously"*.
- **trade-off named:** BUYS the freedom to add or reshape internal events without breaking subscribers, and it removes the failure the chapter documents at length — subscribers coupled to a producer's event schema, where *"if an event's schema changes, the subscribers' projection logic will fail"* and *"if a new domain event is added to the CRM's model, it can potentially affect the projected models, and thus, ignoring it will lead to projecting an inconsistent state."* PAYS a second event model plus the translation to it (rule 26's async proxy), and it PAYS the producer owning a projection driven by consumer needs — which is deliberate, and is the same trade the open-host service already made. The book's warning that this is not hypothetical: *"You may assume that this is an unrealistic example, but unfortunately, this example is based on a true story."*
- **still-true-in-2026:** yes
- **source:** Ch 15 · Distributed Big Ball of Mud; Implementation Coupling; Refactoring the Event-Driven Integration; Use public and private events · Ch 9 · Asynchronous · raw lines 3615–3658, 2376–2377
- **judgment call:** same flag as rule 27.

---

# D. The context map as an emitted artifact

**3 rules.** Scope item 2. This is the **output contract** — the thing that makes the extract produce the
same artifact twice, which is the ADR's stated basis for admission.

### 29. context-map-required-fields
- **when:** the integration patterns for a system have been selected, or any of them changes.
- **rule:** emit a **context map** with fixed fields — *"a visual representation of the system's bounded contexts and the integrations between them"* — and record, per integrating pair: **which two contexts**, **which pattern**, and **which direction** (upstream/downstream, or symmetric for partnership and shared kernel). The book names the three things the artifact must yield: **high-level design** (*"an overview of the system's components and the models they implement"*), **communication patterns** (*"which teams are collaborating and which prefer 'less intimate' integration patterns, such as the anticorruption layer and separate ways patterns"*), and **organizational issues** (rule 30). Maintenance is distributed and continuous: *"a context map should be introduced into a project right from the get-go, and be updated to reflect additions of new bounded contexts and modifications to the existing one"*, and *"since the context map potentially contains information originating from the work of multiple teams, it's best to define the maintenance of the context map as a shared effort: each team is responsible for updating its own integrations with other bounded contexts."* It can be *"managed and maintained as code, using a tool like Context Mapper."*
- **decides:** context map
- **precondition:** rule 18 has been run for every integrating pair. A map with unlabelled edges is a dependency diagram, not a context map, and carries none of the three insights.
- **stop:** the book states the artifact's own limit and it must be carried into the output rather than hidden: *"charting a context map can be a challenging task. When a system's bounded contexts encompass multiple subdomains, there can be multiple integration patterns at play"*, and *"even if bounded contexts are limited to a single subdomain, there still can be multiple integration patterns at play—for example, if the subdomains' modules require different integration strategies."* **A pair with two patterns gets two rows.** Forcing one label per pair is a falsification.
- **trade-off named:** BUYS **form constancy** — the same shape every time, which is the difference the governing ADR was written to reward, and it composes directly with the installed `domain-modeling` skill's `CONTEXT-MAP.md`. PAYS a maintained artifact, which is the vault's known failure mode (a map that is stale is worse than absent, because rule 25 reads drift against it). Mitigation: derive it from code and configuration where possible; note that the vault's own rule applies — *recall ≠ stato attuale*, so a context map is `ASSUMED` until resolved against the repos.
- **still-true-in-2026:** check — the **artifact** and its fields are unchanged; **Context Mapper**'s currency and maintenance status should be verified before adopting it as the tool.
- **source:** Ch 4 · Context Map; Maintenance; Limitations · raw lines 823–840

### 30. context-map-as-organizational-diagnostic
- **when:** a context map exists and you are reading it, rather than drawing it.
- **rule:** read **patterns across edges, not single edges**, as organizational findings. The book poses the two named readings as questions to be asked of the finished map: *"what does it mean if a certain upstream team's downstream consumers all resort to implementing an anticorruption layer, or if all implementations of the separate ways pattern are concentrated around the same team?"* Translated into findings: **every consumer of one upstream builds an ACL** → the upstream's model is the problem, and the fix is an open-host service there, not more ACLs elsewhere. **All separate-ways edges cluster on one team** → the duplication is buying around a collaboration failure, not an engineering one (and by rule 24 it is only tolerable while none of the duplicated subdomains is core).
- **decides:** context map
- **precondition:** the map covers enough pairs for a pattern to be visible. Two edges have no distribution to read.
- **stop:** these findings are about **people**, and this book has no method for acting on them. Hand off: unit ownership and load to Team Topologies (rules 1, 15), decision rights to Marquet, the conversation itself to Mochary. Do not attempt an organizational intervention from a diagram.
- **trade-off named:** BUYS the single highest-leverage output of the whole artifact — an architectural diagram that surfaces an organizational cause, which no other extract in the library produces. PAYS a real over-reading risk: three ACLs against one upstream may equally mean the upstream is a **third-party vendor**, in which case the pattern is correct and there is nothing to fix. The book poses these as questions, not conclusions, and this rule must be applied the same way.
- **still-true-in-2026:** yes
- **source:** Ch 4 · Context Map · Organizational issues · Ch 11 · Exercises · raw lines 831–832, 3010–3015

### 31. context-map-of-an-existing-system
- **when:** reviewing a system you did not design — a brownfield audit, an inherited repo, a due-diligence pass.
- **rule:** produce the map **as if** the existing components were bounded contexts, then run the fixed finding list. Procedure: *"start with the high-level components. These are not necessarily bounded contexts in the DDD sense, but rather boundaries used to decompose the business domain into subsystems"*; identify them by **decoupled lifecycle** — *"The characteristic property to look for is the components' decoupled lifecycles. Even if the subsystems are managed in the same source control repository (mono-repo) or if all the components reside in a single monolithic codebase, check which can be evolved, tested, and deployed independently from the others"*; then *"Use the knowledge of the high-level components to chart the current design's context map, as though these high-level components were bounded contexts. Identify and track the relationships between the components in terms of bounded context integration patterns."* Then report against the book's **five named suboptimal findings**, verbatim: *"Multiple teams working on the same high-level component · Duplicate implementations of core subdomains · Implementation of a core subdomain by an outsourced company · Friction because of frequently failing integration · Awkward models spreading from external services and legacy systems."* Per component, also check the tactical fit: *"Does the solution fit the complexity of the problem? Are there areas where more elaborate design patterns are needed? Conversely, are there any subdomains where it's possible to cut corners or use existing, off-the-shelf solutions?"*
- **decides:** context map · modernization sequence
- **precondition:** section A has been run first — three of the five findings are stated in terms of **core subdomains**, so the classification must exist before the review can produce them.
- **stop:** if domain knowledge is missing, the review cannot proceed on code alone: *"look for lost domain knowledge… The problem is widespread and acute in core subdomains, where the business logic is both complex and business critical."* The book's remedy is an event storming session, which is **ceded** (SCARTATI §4) — the halt is real, and the resolution comes from the installed `domain-modeling` skill or from talking to people, not from this file.
- **trade-off named:** BUYS a **repeatable review with a fixed output**, driven by a five-item finding list rather than by whatever the reviewer noticed — which is exactly the "employee not consultant" property the ADR admits references for. PAYS: the five findings are all **strategic and social**, so this review says nothing about correctness, performance, security or data (route those to DDIA, Hard Parts §J, Evolutionary's detectors). Treating this list as a complete architecture review would be a serious under-read.
- **still-true-in-2026:** yes
- **source:** Ch 13 · Strategic Analysis; Explore the Current Design; Evaluate the tactical design; Evaluate the strategic design · raw lines 3188–3223

---

# E. Brownfield sequencing

**3 rules.** The order in which boundaries are introduced into a system that already exists. This is the
section that turns the map of rule 31 into work.

### 32. logical-boundaries-before-physical
- **when:** modernizing an existing system after the review of rule 31.
- **rule:** align **logical** boundaries first — namespaces, modules, packages — and only then consider physical ones. *"A prerequisite for making this decision is to have boundaries dividing the system's subdomains. The boundaries don't have to be physical, making each subdomain a full-fledged bounded context. Instead, start by ensuring that at least the logical boundaries (namespace, modules, and packages, depending on the technology stack) are aligned with the subdomains' boundaries."* The move is cheap and safe: *"Adjusting the system's modules is a relatively safe form of refactoring. You are not modifying the business logic, just repositioning the types in a more well-organized structure."* And it must be **complete across platforms**: *"keep track of the subdomains' business logic implemented in different codebases; stored procedures in a database, serverless functions, and so on. Make sure to introduce the new boundaries in those platforms as well. For instance, if some of the logic is handled in the database's stored procedures, either rename the procedures to reflect the module they belong to or introduce a dedicated database schema and relocate the stored procedures."*
- **decides:** modernization sequence · context boundary
- **precondition:** the subdomains are identified and typed (section A). This is a re-organization *toward* the subdomain map, so the map must exist.
- **stop:** *"ensure that references by full type names, such as the dynamic loading of libraries, reflection, and so on, are not breaking."* Reflection and dynamic loading make a "safe" move unsafe, and the book flags it explicitly.
- **trade-off named:** BUYS the cheapest possible correction of a wrong boundary, and it is the operational form of rule 14's asymmetry — *"Refactoring logical boundaries is considerably less expensive than refactoring physical boundaries."* PAYS: a logical boundary is **not enforced** — nothing stops the next commit from reaching across a namespace, so the boundary decays silently unless something checks it. The book supplies no enforcement mechanism at all. That is Evolutionary's field: `archunit-governable-relationships`, `layer-access-rules-as-code`, `directionality-of-imports`. **A logical boundary without a fitness function is a comment.**
- **still-true-in-2026:** yes
- **source:** Ch 13 · Modernization Strategy · raw lines 3224–3229

### 33. physical-extraction-triggers
- **when:** deciding whether a logical boundary should become a physical one (its own service, project, deployable).
- **rule:** extract on **two named triggers, and no others**. *"Are multiple teams working on the same codebase? If so, decouple the development lifecycles by defining bounded contexts for each team. Are conflicting models being used by the different components? If so, relocate the conflicting models into separate bounded contexts."* Otherwise, *"look for where the most value can be gained by turning the logical boundaries into physical boundaries"* — and note the book's own warning against doing it eagerly: *"it can be risky to prematurely decompose the system into the smallest bounded contexts possible."* Chapter 3 adds the further legitimate reasons, all specific: *"constituting new software engineering teams or addressing some of the system's nonfunctional requirements; for example, when you need to separate the development lifecycles of some of the components originally residing in a single bounded context. Another common reason for extracting one functionality is the ability to scale it independently."*
- **decides:** context boundary · modernization sequence
- **precondition:** rule 32 is done for the component in question. Extracting before the logical boundary is clean extracts the mess.
- **stop:** if neither trigger fires and no named non-functional requirement applies, **do not extract** — and if the extraction would breach rule 16's bracket or split a subdomain (rule 13), stop regardless of trigger. For anything finer than the trigger list, the granularity question is ceded to Hard Parts (rules 10, 11, 24, 26, 30).
- **trade-off named:** BUYS independent lifecycles, independent scaling and enforced model separation. PAYS an integration pattern (all of section C), a deployment unit, and the loss of refactoring cheapness — you have converted a rename into a migration. The book's estimate of the reverse cost: *"refactoring bounded context boundaries is an expensive undertaking, and in many cases, the ineffective boundaries remain unattended and end up accumulating technical debt."*
- **still-true-in-2026:** yes
- **source:** Ch 13 · Strategic Modernization · Ch 3 · Scope of a Bounded Context · Ch 10 · Bounded Contexts · raw lines 3230–3235, 648, 2728–2731

### 34. strangler-or-in-place-refactor
- **when:** a component has been chosen for modernization and you must pick the migration shape.
- **rule:** two options, and the choice is stated as a fork: *"the modernization strategy: gradually replacing whole components of the system (the strangler pattern), or gradually refactoring the existing solution."*
  - **Strangler:** *"create a new bounded context—the strangler—use it to implement new requirements, and gradually migrate the legacy context's functionality into it. At the same time, except for hotfixes and other emergencies, the evolution and development of the legacy bounded context stops."* Paired with a façade: *"a thin abstraction layer that acts as the public interface and is in charge of forwarding the requests to processing either by the legacy or the modernized bounded context. When migration completes… the façade is removed as it is no longer necessary."* One rule is deliberately relaxed, **with an expiry**: *"Contrary to the principle of each bounded context having its own database that cannot be shared with other contexts, the rule can be relaxed when implementing the strangler pattern… The condition for bending the one-database-per-bounded-context rule is that eventually, and better sooner than later, the legacy context will be retired, and the database will be used exclusively by the new implementation."*
  - **In-place refactor:** incremental, and never in one leap: *"small incremental steps are safer than a big rewrite. Therefore, don't refactor a transaction script or active record straight to an event-sourced domain model. Instead, take the intermediate step of designing state-based aggregates."*
  Either way, protect the edges: *"when necessary as you're refactoring legacy systems, protect the new codebase from old models using an anticorruption layer, and protect the consumers from changes in the legacy codebase by implementing an open-host service and exposing a published language"* (rules 22 and 23).
- **decides:** modernization sequence
- **precondition:** *"A prerequisite to the successful modernization of a design is the domain knowledge and effective model of the business domain."* Without it you are re-implementing behaviour you do not understand.
- **stop:** **not a big rewrite, in either branch.** *"The 'big rewrite' endeavors, in which the engineers are trying to rewrite the system from scratch, this time designing and implementing the whole system correctly, are rarely successful. Even more rarely does management support such architectural makeovers."* The stance is *"think big but start small"*, and Eric Evans is quoted for the reason: *"not all of a large system will be well designed. That's a fact we have to accept, and therefore we must strategically decide where to invest."* Also stop if the shared-database relaxation has no retirement date — a permanent shared database is `no-shared-database-integration` violated, not a strangler.
- **trade-off named:** Strangler BUYS a clean new context and a reversible cutover per slice; PAYS a façade to build and delete, a frozen legacy codebase (hotfixes only), and a **temporarily violated invariant** — the shared database, which the book flags as one of the ways the pattern *"contradict[s] some of the core principles of domain-driven design during the migration process"*. In-place refactoring BUYS no new deployment surface and no dual-run; PAYS a long period where the code is neither the old design nor the new one, and it PAYS the ordering constraint: *"Going from state-based to event-sourced aggregates will be orders of magnitude safer than discovering wrong transactional boundaries in an event-sourced aggregate."*
- **still-true-in-2026:** yes — note the sibling overlap: `ford-parsons-evolutionary-architectures` carries `strangler-fig-with-a-fitness-function`, which adds the **enforcement** this rule lacks (a check that the legacy context is actually shrinking). Use both; Khononov supplies the DDD-specific relaxation and its expiry condition, Evolutionary supplies the gate.
- **source:** Ch 13 · Modernization Strategy; Strangler pattern; Refactoring Tactical Design Decisions; Exercises · raw lines 3224–3270, 3318–3327

---

## Rule count and reconciliation

**34 rules**, counted by the mandatory `when:` field.

| Section | Field | Rules | Numbers |
|---|---|--:|---|
| A | Subdomain classification (contract fork **a**) | 10 | 1–10 |
| B | Context boundary vs subdomain boundary | 7 | 11–17 |
| C | Integration-pattern selection (contract fork **b**) | 11 | 18–28 |
| D | Context map as emitted artifact | 3 | 29–31 |
| E | Brownfield sequencing | 3 | 32–34 |
| | **Total** | **34** | |

`decides:` distribution (rules may carry more than one, so this sums above 34):

| decides | rules |
|---|--:|
| subdomain type | 9 |
| integration pattern | 12 |
| context boundary | 9 |
| sourcing | 4 |
| modernization sequence | 5 |
| context map | 3 |

`still-true-in-2026`: **30 `yes`**, **4 `check`**, **0 `superseded`**. The four `check` rules, exhaustively:
**1** and **3** — the buy-vs-build economics of the generic branch have moved (Table 1-1's *axes* are
unaffected; only the cost side of the generic branch is); **26** and **29** — the named tooling is a 2021
list and its currency, not the rule, needs re-verifying.

**Judgment calls flagged:** 3 rules — `16` (Ch 14), `27` and `28` (Ch 15). All three are argued in
`EXTRACTION-NOTES.md` §3.

**Chapters that fed rules:** 1, 2 (one consequence only), 3, 4, 9 (Model Translation only), 10, 11, 13, 14
(one rule), 15 (two rules), 16 (one sentence into rule 23), Appendix A (corroboration for rules 4, 7, 10,
13, 14, 17), Closing Words (Table E-1 confirming rule 1).

**Chapters that fed nothing:** 5, 6, 7, 8, 12 — see SCARTATI.

---

## SCARTATI

Material deliberately **not** turned into decision rules, and why. The scope contract for this acquisition
is narrow by design (see the `when_not` hard-out table), so this section is larger relative to the book
than in any sibling extract. **That is the acquisition working, not failing.**

### 1. Tactical DDD — the building blocks. Four chapters, zero rules.
**Chapters 5, 6 and 7 in full**: transaction script, active record, domain model, event-sourced domain
model; value objects, entities, aggregates, aggregate roots, domain events as building blocks, domain
services; consistency enforcement, transaction boundaries, entity hierarchies, referencing other
aggregates; event sourcing mechanics, projections, snapshots, event store schemas, migration events;
`Ticket`, `Person`, `Color`, `PhoneNumber`, `Height` and every other code listing. **Chapter 8 in full**:
layered architecture, ports & adapters, CQRS as implementation scaffolding.

Excluded on three independent grounds, any one of which is sufficient. **(a)** The governing verdict
excludes it by name: *"The tactical half of DDD — aggregates, entities, value objects, repositories,
domain events… If Khononov's tactical chapters get extracted at all, they go to SCARTATI."* **(b)** The
founder's own limit — *"può diventare modellazione autoreferenziale"* — lands hardest exactly here; this is
the half that generates modelling for its own sake. **(c)** Admission-bar: these are mechanical patterns
that Opus 5 implements competently and identically without a reference, so there is no form to stabilise.

**What was checked before discarding, and what the check found.** Every tactical chapter was scanned for a
genuine *architectural* fork per the brief's exception clause. The candidate was Ch 7's state-based vs
event-sourced modelling decision. It was **not** promoted, for a stated reason: the decision does not live
in Ch 7. It lives in **Ch 10's heuristic** (*"Does the subdomain track money or other monetary transactions
or have to provide a consistent audit log, or is deep analysis of its behavior required by the business? If
so, use the event-sourced domain model"*), and Ch 10's chain — business-logic pattern → architectural
pattern → testing strategy — is a **tactical** decision tree keyed on the subdomain type. Admitting it
would re-import the whole tactical half through its selection rule. What is kept instead is the **one
strategic direction of that arrow**: rule 7, which runs the tree *backwards* to verify a subdomain type.
The tree itself is reproduced in `chapters/ch10-design-heuristics.md` for reference and is deliberately not
a rule here.

### 2. Ubiquitous language as a practice — ceded to an installed skill, not discarded.
Chapter 2 entire: knowledge discovery, the Telephone-game argument against translation layers, language of
the business, ambiguous and synonymous terms, model-as-map, effective modelling, continuous effort,
wiki glossaries, Gherkin tests, NDepend, the non-English-language advice; plus Ch 13's *Undercover
domain-driven design* section (appeal to logic not authority, watercooler conversations, patience with an
entrenched vocabulary) and Appendix A's *"ubiquitous language is the core subdomain of domain-driven
design"* discussion.

This is the book's own core, and it is **excluded because the vault already owns a working implementation
of it** — `~/.claude/skills/domain-modeling/`. The governing verdict makes this correction explicitly:
*"a book bought to fill a hole that a working skill already fills is exactly the failure mode the
recall-first rule exists to prevent."* **Exactly one consequence is retained**: language consistency as
the *ceiling* on context width (rule 12), because that is a boundary fact and the skill does not carry it.
Kept in `chapters/ch02-ubiquitous-language.md` at study depth.

### 3. Event storming — Chapter 12 entire, zero rules.
The ten steps (unstructured exploration → timelines → pain points → pivotal events → commands → policies →
read models → external systems → aggregates → bounded contexts), the variants, the facilitation tips, the
sticky-note colour conventions, the remote-workshop advice, the modelling space, the snacks.

Excluded as a **workshop procedure, not a fork resolver**: there is no condition under which it returns a
different answer, and no exit criterion — which puts it on the wrong side of the founder's stopping rule.
It is also a group activity, and the operator is one person. Where a rule needs the knowledge event
storming produces, the rule **halts and says so** (rule 31's stop, rule 34's precondition) rather than
importing the workshop. Note honestly what this loses: event storming is the book's designated remedy for
**recovering lost domain knowledge**, and nothing in this extract or the eleven siblings replaces it.

### 4. Communication mechanics — Chapter 9 minus Model Translation.
Outbox pattern, polling publisher vs transaction-log tailing, saga, process manager, integrating
aggregates, the `CampaignPublishingSaga` and `BookingProcessManager` listings. These implement a chosen
integration; they do not select one. The **Model Translation** half of Ch 9 *is* extracted (rule 26)
because it resolves a real fork inside a chosen pattern.

### 5. Data mesh — Chapter 16 almost entire.
Analytical vs transactional models, fact and dimension tables, star and snowflake schemas, data warehouse
and data lake architectures and their challenges, the four data-mesh principles, output ports, polyglot
data endpoints, the data-infrastructure platform team, the federated governance body.

Out of the acquisition's scope (analytical data architecture), and the library is already over-covered on
the data line by DDIA plus Hard Parts §D. **One sentence carried forward** into rule 23, because it
genuinely extends contract fork (b): *"exposing a bounded context's data in a model that is different from
its operational model is the open-host pattern. In this case, the analytical model is an additional
published language."* The chapter's closing observation that the six integration patterns apply to
analytical models as well is recorded here rather than duplicated as a rule.

### 6. Microservices — Chapter 14 minus the bracket.
The OASIS service definition, the front-door metaphor, micro-public-interface reasoning, the naive
one-method-per-service decomposition, local vs global complexity (Myers), deep vs shallow modules
(Ousterhout), the granularity-vs-cost-of-change curve. **One rule extracted** (16, the validity bracket).
The depth heuristic is ceded to the installed `codebase-design` skill; the granularity mechanics are ceded
to Hard Parts. The pizza/monitor-width joke answers in the exercises are noted as evidence that the
chapter's own target is the size fallacy, which is what rule 16 encodes.

### 7. Worked examples and narrative kept as examples, not promoted.
Gigmaster and BusVNext (Ch 1's two domain-analysis exercises), WolfDesk (the running exercise company
described in the Preface), the telemarketing lead example, the tomato-as-fruit/vegetable semantic-domain
story with the 1883 tax and the 1893 Supreme Court decision, Newton vs Einstein, the Siemens KG86NAI31L
refrigerator and its cardboard model, the LiDAR reply on Twitter, the emergency-alert (WEA/EU-Alert)
360-character analogy, the marriage event triplet. All are in the chapter files. Where one of them *is* the
statement of a rule, the rule carries the quote and the attribution — Uber and Google Search ranking for
rule 1, the jeweller and the fraud analysts for rule 4, BuyIT/DeliverIT and Amazon/AWS for rule 10.

**Appendix A is handled differently and deliberately.** Marketnovus is a first-person post-mortem of five
bounded contexts, and it is the richest evidence in the book — but it is a **single company's history**, not
a stated principle. Nothing here is promoted to a rule on the strength of the appendix alone. It is used
in exactly two ways: as **corroboration** for rules the author states as principles elsewhere (rules 4, 10,
13, 14, 17), and as the source of **one technique the author explicitly frames as a technique** — *"Here is
a trick I came up with at Marketnovus"* — which is rule 7, and which is independently stated as a heuristic
in Ch 10. Every appendix-derived claim in this file is marked with its raw line so the audit can check it.

### 8. Publishing apparatus and Early-Release artefacts.
Foreword (Julie Lerman), preface, acknowledgments, `#AdoptDontShop`, the O'Reilly boilerplate and contact
pages, exercise answer keys (Appendix B), the Further Reading list, the closing words, the index. Also the
Early-Release defects themselves: the duplicated Ch 2 fragment at the head of the file, the per-chapter
*"A Note for Early Release Readers"* blocks, the *"the GitHub repo will be made active later on"*
placeholders, Ch 11's misdirected cross-reference (*"In Chapter 2, you've learned the three types of
business subdomains"* — that is Ch 1), the truncated Randy Shoup citation (`Randy Shoup>`), and *"Mirtin
Fowler"* for Martin Fowler. **Noted, not propagated.** One item from the apparatus *is* used: the Further
Reading list is the author's own routing table, and it points at Team Topologies (Kaiser) and architecture
modernization (Tune) for the fields this extract cedes — independent confirmation that the cession is the
author's own view of his book's edge.

### 9. What is genuinely absent from the book — not discarded, simply not there.
Recorded so a future reader does not search for it.

- **No method for locating a boundary.** This is the important one, and it is the whole basis of the
  `when_not` hard-out. The book supplies a ceiling, a floor, a direction and a prohibition. It has **no
  fracture-plane catalogue, no cognitive-load model, no function-to-table mapping, no quantum analysis, no
  litmus test.** Every one of those belongs to a sibling.
- **No thresholds and no numbers, anywhere.** Not one quantity in the entire book: no size limit, no team
  size, no call-frequency threshold for rule 17, no coupling metric, no cost figure. Table 1-1's cells are
  `Yes/No`, `High/Low`. Every rule here that would benefit from a number needs one derived elsewhere —
  Evolutionary's `derive-thresholds-from-production-not-estimates` is the closest thing the library has.
- **No enforcement mechanism.** Boundaries are drawn and never checked. No fitness functions, no
  ArchUnit-style tests, no CI gates — the one exception is the shared kernel's mandatory integration tests
  (rule 20). A logical boundary from rule 32 will decay silently, and this book contains nothing that would
  notice.
- **No cost model.** Coordination cost, duplication cost and integration cost are the deciding variables in
  rules 3, 20 and 24, and **none of them is ever quantified or given a method of estimation.** The decisive
  input to three rules is left as a judgement call. This is a real defect, not an omission of detail.
- **No resilience, security, performance or data-mechanism content.** Timeouts, retries, circuit breakers,
  authorization, encryption, storage engines, replication, indexing: absent. Ch 15's *"Assume the worst"*
  list is the closest, and it is four bullets pointing at the outbox and saga patterns.
- **No treatment of the one-person case.** Every social rule assumes at least two teams. The degeneration
  is worked out in `when_not` → Solo-operator collapse because the book does not do it.
