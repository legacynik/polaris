# Governance rules

These rules decide how architectural intent is enforced and kept true over time: what counts as a
fitness function and where it runs, how coupling, contracts and quanta are judged, how schemas,
deployments and migrations change safely, and which organisational shapes the architecture needs.
Each rule reads condition → decision → why → check. A step loads only the rule ids it names, never
the whole file.

## Where these rules stop

| Question | Who decides it instead |
|---|---|
| Which of two designs to pick, how to weigh the trade-off | the decomposition rules (decomposition rule 27 `tradeoff-statement-to-the-business`); these rules supply the forces, not the verdict |
| Service granularity in full (what pulls a service apart against what holds it together) | the decomposition rules; these rules give only the floor (`transactional-boundaries-set-the-granularity-floor`) and the direction (`start-with-a-few-large-services`) |
| Cross-service transactions, sagas, eventual-consistency patterns | the decomposition rules |
| Data ownership, access against update, choosing a database type | the decomposition rules and the data-systems rules; these rules keep only the refactoring half (expand/contract, migrations, moving logic out of the database) |
| Where a team boundary goes, whether a team is overloaded, team types | the ownership rules |
| Naming a bounded context, settling an overloaded term | the `domain` door |
| What a role looks like, how to assess the person in it, hiring, pay, performance, termination | people and roles — outside this skill |
| Who may decide what, how decision rights move, escalation and veto | people and roles — outside this skill |
| Operating rhythm, one-to-one accountability | people and roles — outside this skill |
| Strategy, the real problem, what to build, which business number a person or team owns | strategy — outside this skill |
| Writing a proposal that survives review | strategy — outside this skill |
| Verifying business behaviour (a change of address, a price rule) | nobody: write the code and its ordinary tests (`no-domain-fitness-functions`) |

When a step needs both coupling judgement and enforcement: load the decomposition rules for the
coupling decision and these rules for the governance mechanism. Where both fire, these rules yield on
the decision and keep the enforcement. The definition of an architecture quantum and the
static/dynamic coupling split live here; the contract strictness spectrum also lives here.

## Conditions that change a rule's footing

- **Automation split.** Of the 152 rules, 49 are fully automatable, 34 partly (a machine detects, a
  person adjudicates) and 69 need judgement. Automatable rules become guardrails; partial ones become
  detectors with an escalation path; judgement rules become a checklist a person works through. Do not
  dress a judgement rule up as a pipeline check. The automation, scale and instrument conditions vary
  independently; never infer one from another.
- **Rules that presume several teams or an organisation (19):**
  `automation-creates-the-headcount-you-thought-you-lacked`, `cognitive-load-caps-capability`,
  `cross-functional-by-default`, `data-product-quantum`, `detector-reuse-bottleneck`,
  `detector-vendor-king`, `ea-governs-capabilities-not-technology`,
  `effective-reuse-requires-abstraction-plus-low-volatility`, `enterprise-slot-in-every-pipeline`,
  `fidelity-cutover-gate`, `garbage-collect-unrouted-services`, `inverse-conway-maneuver`,
  `just-enough-governance-three-stacks`, `organize-around-business-capabilities`,
  `platform-hides-implementation-details`, `product-over-project`, `quantum-count-cost-sweet-spot`,
  `sidecar-for-orthogonal-coupling`, `team-size-by-connection-count`. They stay
  true below that scale but may be unavailable. The enterprise slot survives almost intact: at one
  operator with several products it becomes one shared pipeline template every product inherits, with a
  stage amended once that takes effect everywhere. Build that.
- **Rules that presume a second party (24):**
  `baseline-data-quality-before-evolving`, `canary-with-a-fitness-function-attached`,
  `carve-bounded-context-with-fitness-functions`, `communication-governance-by-log-harvest`,
  `consumer-driven-contracts`, `culture-audit-questions`,
  `detector-reporting-on-the-system-of-record`, `developer-must-understand-the-why`,
  `dimensions-before-fitness-functions`, `fitness-functions-as-checklist-not-stick`,
  `hypothesis-driven-development`, `licence-change-detection`, `make-decisions-reversible`,
  `mandate-parsable-logs-first`, `manual-fitness-functions-are-legitimate`,
  `manual-stage-in-the-pipeline`, `ownership-changes-behaviour`,
  `polyglot-persistence-on-decomposition`, `prefer-duplication-to-coupling`,
  `publish-results-visibly`, `report-fitness-function-outcomes`, `single-writer-cached-readers`,
  `synthetic-transactions`, `ui-coupling-collapses-the-quantum`. An agent can stand in when all the second party does is execute a check
  (`communication-governance-by-log-harvest`, `consumer-driven-contracts`, `publish-results-visibly`,
  `report-fitness-function-outcomes`). Where the job is to hold a different
  incentive (the review and audit stages of `manual-stage-in-the-pipeline`, `ownership-changes-behaviour`),
  an agent configured by the same operator is not independent and supplies the look of a second party
  without its protection. Self-certification is not verification; say so where it applies.
- **What survives at one operator:** one named owner per fitness function, even when it is always the
  same person; the rationale recorded when the check is written (`document-the-why`), which is the only
  second party available when the writer, the maintainer and the person hitting a red build are one
  person on three different days; and an explicit note wherever independent verification is missing.
- **Rules that need an instrument that may not exist.** A rule not listed here costs no new plumbing.
  - A deployment pipeline with separable stages: `cascading-fitness-function`,
    `enterprise-slot-in-every-pipeline`, `fan-out-to-verify-both-states`,
    `manual-stage-in-the-pipeline`, `pipeline-not-ci-server`. Most rules here depend on it.
  - Production monitoring with an alerting hook: `cadence-by-criticality` (continual form),
    `canary-with-a-fitness-function-attached`, `measure-the-instrument-before-trusting-it`,
    `derive-thresholds-from-production-not-estimates`, `monitoring-driven-development`, `synthetic-transactions`.
  - A shared, machine-readable log format in all services: `communication-governance-by-log-harvest`,
    `mandate-parsable-logs-first`. The format is the instrument and is enforced on the shared
    container image.
  - A metrics tool for the language: `afferent-efferent-coupling`, `cc-threshold`,
    `distance-from-main-sequence`, `lcom-before-splitting-a-shared-class`. Ready-made on Java and .NET
    (ArchUnit, NetArchTest, JDepend, NDepend, ckjm); elsewhere it means the language linter plus rules you
    write.
  - A migration tool wired into the pipeline: `schemas-tested-versioned-incremental`,
    `migrations-are-immutable`, `expand-contract`.
  - Running two implementations side by side: `fidelity-fitness-function`,
    `strangler-fig-with-a-fitness-function`.
  - A dependency inventory with versions: `pull-model-for-dependencies`, `licence-change-detection`,
    `security-dependency-scan-in-the-pipeline`, `temporal-fitness-function`.
  - When the instrument is missing, build it first or choose another rule. A weakened rule reading a
    missing instrument produces a green pipeline that lies.

## How a fitness function is built and kept honest

1. **Choose what to protect.** List the dimensions (technical, data, security, operational, plus the
   qualities success depends on). → `dimensions-before-fitness-functions`
2. **Break each down until it is measurable.** What resists gets a manual stage or is recorded as
   ungoverned. → `decompose-until-measurable`
3. **Admit it only if it is a fitness function.** It yields an objective outcome and runs on every
   change. → `continuous-verification-or-its-not-one`, `objective-outcome-or-its-not-one`
4. **Pick where and how often it runs.** Immediate-consequence violations run continually against the
   live system; structural ones may run triggered, after the fact; time-driven risks get a time
   component. → `cadence-by-criticality`, `temporal-fitness-function`
5. **Make it a gate.** It lives as a pipeline stage and a failing stage stops the pipeline, so blocking
   comes from where the check lives. A check that can only warn is a check outside the pipeline; ask why
   it is not a stage. Being manual is no reason to be a warning: a manual stage still gates what follows.
   → `manual-stage-in-the-pipeline`, `pipeline-not-ci-server`, `principles-without-enforcement`
6. **If the code already fails it, schedule it.** Warn now and escalate to an error on a named date; a
   warning is a dated transition, never a resting state. → `cascading-fitness-function`
7. **Keep it next to the code.** It lives in the repository, changes with the requirement and stays
   green. → `keep-them-green`, `fitness-functions-evolve-with-requirements`
8. **When it goes red.** The person who hits it reads the recorded purpose, repairs the fault and
   resumes. These rules provide no triage ladder, waiver or override, so the rationale must be findable
   from the failure. → `document-the-why`, `developer-must-understand-the-why`
9. **Measure the governance.** Report pass/fail rates on a cadence and post results where people see
   them. → `report-fitness-function-outcomes`, `publish-results-visibly`

### When the fitness function itself is wrong

These rules model a check that is absent, run only now and then, or too burdensome. They carry no
general method for a check that passes while the quality it guards degrades, and no rule for retiring a
check that has stopped meaning anything. What they offer, and how far each falls short:

- `measure-the-instrument-before-trusting-it`: aim a check at the instrument itself. It generalises a
  single worked case; treat it as our extrapolation.
- `derive-thresholds-from-production-not-estimates`: replace guessed thresholds with production
  figures. It is reactive: it catches a wrong threshold only after production has contradicted it.
- `cc-cannot-separate-essential-from-accidental`: know a metric's blind spot before gating on it. It
  covers one metric.
- `govern-the-synthetic-flag-itself`: guards one instrument, and only the flag's presence.
- `holistic-selectively-and-let-difficulty-inform-value` with `fitness-functions-as-checklist-not-stick`:
  fewer, higher-value checks reduce exposure without validating any of them.

The operational consequence: while a check only warns, its errors are cheap; once it is promoted to a
gate, an unvalidated check becomes expensive, because it blocks work on a wrong verdict or passes work on
a false one. Before promoting a check to a gate, run `measure-the-instrument-before-trusting-it` on it
and record what result would show it is lying. Treat the remaining risk as a known cost of this method.

# The rules

## Fitness functions and the governance surface — 47 rules

### objective-outcome-or-its-not-one
- **condition:** An existing monitor, metric, dashboard or check is being called a fitness function.
- **decision:** Count it as one only when it yields an objective outcome: pass/fail, a breached threshold, or membership in a set. A monitor turns into a fitness function once an alarm fires on deviation from a stated acceptable range.
- **why:** It separates governance from observation. The cost is that someone must commit to an acceptable value, a judgement no tool supplies.
- **check:** The acceptable range is written down. If the only outcome is a person reading a chart and forming an impression, halt: record it as a monitor, or the quality as ungoverned, until a threshold exists.

### continuous-verification-or-its-not-one
- **condition:** A linter, metrics suite, scanner or audit is run now and then, or on request.
- **decision:** The fitness function is the wiring into verification on every change, not the tool. Wire it in before counting it.
- **why:** An occasional run catches drift only by luck. Wiring costs pipeline time and upkeep on every change.
- **check:** Something fires on every change: a pipeline, a hook, or a scheduled job with an owner. If no such execution surface exists, halt and build it first; every other rule here depends on it.

### principles-without-enforcement
- **condition:** An architectural principle lives in a wiki, a standards page, an agent instruction file or a decision record and is expected to be followed.
- **decision:** Treat it as aspiration until a check fails when it is violated. A principle that cannot become an automated check becomes a manual pipeline stage owned by a named reviewer (`manual-stage-in-the-pipeline`) or is deleted.
- **why:** Principles nothing enforces go unread and unfollowed. Enforcing them costs stating each one precisely enough that a violation is recognisable without debate.
- **check:** A violation can be recognised without a judgement call. Precise principles (layer access, import direction) automate; vague ones are rewritten or dropped, never left standing as pretend governance.

### cadence-by-criticality
- **condition:** Choosing between a triggered fitness function (fired by an event such as a commit, a stage or a periodic harvest) or a continual one (running constantly against the live system, usually through monitors).
- **decision:** Let the criticality of what is governed decide, not convenience. Violations with an immediate consequence, such as security, get continual, proactive checks; purely structural rules may use triggered, after-the-fact checks such as a log harvest.
- **why:** Continual catches the violation at once and pays runtime overhead. Triggered costs nothing at runtime and lets the violation stand for the whole interval.
- **check:** For the continual form, the runtime emits the signal (monitors, a queue, a consistent log format) and the overhead is acceptable. If the consequence lands before the next triggered run, halt: choosing triggered because it is cheaper means accepting the incident.

### cascading-fitness-function
- **condition:** You want to impose a threshold the existing code already fails, so switching the gate on now would break every build.
- **decision:** Keep the target threshold. Make the check warn past it now and escalate to an error on a scheduled date, narrowing the values step by step; leave the check in place afterwards so the code cannot slide back.
- **why:** Existing debt is paid down in controlled steps while new degradation is blocked. The cost is a period in which the channel only warns, which decays into noise if the date slips.
- **check:** A target value and an escalation date both exist; a warning without a date is the failure this rule prevents. If nobody can name the date the warning becomes an error, halt. Threshold and schedule are both mechanical.

### decompose-until-measurable
- **condition:** A stakeholder names a quality to protect: secure, scalable, maintainable, reliable.
- **decision:** Break it into parts until each part has an objective measure; the fitness functions fall out of the breakdown. What still resists after honest effort is recorded explicitly as ungoverned.
- **why:** Only what is measured can be governed, and a named gap beats a plausible wrong number. The cost is architect time and judgement that no machine replaces.
- **check:** Each leaf has a measure that tracks the quality itself. Never attach a proxy that does not track it; a proxy gate is the green pipeline that lies.

### dimensions-before-fitness-functions
- **condition:** A new system is starting, or governance is about to be added to a system already running.
- **decision:** First list the dimensions to protect. The default set is technical (frameworks, dependencies, languages), data (schemas, layouts, optimisation), security (policies, guidelines, tools) and operational (how the system maps to infrastructure), plus whichever qualities success depends on. Then write fitness functions per dimension; one dimension usually needs several.
- **why:** Without the list, checks protect whatever was easy to measure. The cost is involving business, operations and security for each dimension.
- **check:** Every dimension has an owner who can say what correct looks like; halt on any that has none, because a check written without understanding the dimension is worse than none. At one operator the involve-the-others step loses its cross-check; record that.

### atomic-vs-holistic
- **condition:** Deciding the scope of a new fitness function.
- **decision:** An atomic check runs in a single context on one aspect (a unit test on module coupling, a cycle check). A holistic check runs in a shared context on a combination, to catch two qualities that pass alone and clash together: caching makes the scalability check pass and serves data stale enough to fail the security check.
- **why:** Holistic checks find interaction failures atomic ones cannot see. They cost an integration environment realistic enough for the interaction to occur.
- **check:** For holistic checks, that environment exists. The failure to watch for is never building any holistic check at all.

### holistic-selectively-and-let-difficulty-inform-value
- **condition:** Choosing which combinations of qualities to test holistically.
- **decision:** Select a few combinations instead of all of them, and read how hard each one is to build as information about how entangled the architecture is and how much that quality is worth.
- **why:** Testing every combination is too expensive. Selecting leaves some interactions untested, which is the accepted cost.
- **check:** The atomic checks for each constituent quality already exist and pass. A holistic test that cannot be built is a testability finding (`architect-for-testability`) to record, never something to skip quietly.

### static-vs-dynamic-result
- **condition:** The acceptable value for a check depends on runtime conditions.
- **decision:** Static checks have a fixed result: binary, a fixed range, set inclusion. Dynamic checks move with context, e.g. response time may degrade as concurrent users rise, but not past a limit. Dynamic still means objective: the input is live, the verdict is definite.
- **why:** Dynamic checks fit real load without false alarms. They cost reading the context input reliably at evaluation time.
- **check:** The context input (user count, load, time of day) is readable when the check runs. If the dynamic input is someone's sense of what is reasonable today, halt: it is a subjective gate in disguise.

### manual-fitness-functions-are-legitimate
- **condition:** A quality resists automation: legal or regulatory demands, exploratory testing, an audit, or practices not yet mature enough to automate.
- **decision:** Define the fitness function anyway and verify it through a process a person runs. It is a first-class check whose invocation happens to be manual.
- **why:** Unautomatable properties stay inside governance instead of outside it. The cost is a person's time on every run and the wait for their availability.
- **check:** A named person or role performs it and the outcome is objective; with nobody named it is a hope. The verifier must be someone other than the person whose work it checks.

### manual-stage-in-the-pipeline
- **condition:** A manual fitness function exists and needs a home.
- **decision:** Place it inside the deployment pipeline as a named manual stage that the specialist starts on demand, and gate the later stages on it. This unifies how verification is seen; makes the manual step's cost visible and comparable (a monthly audit behind a weekly security review shows the audit is the release bottleneck, which turns paying for more frequent audits into a business question); and lets automated stages replace manual ones later without disruption.
- **why:** Exposing the bottleneck is the payoff. The cost is a pipeline that supports on-demand manual stages and waits on people.
- **check:** The pipeline supports manual stages and on-demand triggers. A manual step outside the pipeline goes unmeasured; move it in before optimising anything else. Review and audit stages exist so delivery does not certify its own work, so an agent set up by the same operator does not satisfy them.

### intentional-and-emergent-fitness-functions
- **condition:** The running system shows behaviour nobody anticipated at design time.
- **decision:** Beside the intentional checks written at inception, add emergent checks aggressively whenever misbehaviour a check could catch shows up. Expect the initial set to be incomplete.
- **why:** Unknown unknowns guarantee gaps, and each emergent check closes one. The cost is someone watching continuously, since nothing triggers this automatically.
- **check:** Someone owns watching for misbehaviour. The failure here is inaction.

### retrofit-at-the-stress-point
- **condition:** A nonfunctional requirement breaks in production or in test.
- **decision:** Treat the break as the specification for a new fitness function and add it so the break cannot recur, the same way a bug fix earns a regression test.
- **why:** Checks born from real breaks guard real risks. The cost: a check written from a guessed cause guards the wrong thing permanently.
- **check:** The break was observed and its root cause understood. If the cause is unclear, halt on the check and finish the diagnosis; a check pinned to a symptom is a permanent false gate. Running it automates; writing it is judgement.

### no-domain-fitness-functions
- **condition:** Deciding whether a verification belongs among the fitness functions or in the ordinary test suite.
- **decision:** Fitness functions govern architecture, not business behaviour. Test: if the check can be stated without naming your business (elasticity reads the same for a game, a catalogue or a video site), it is a fitness function; verifying a change of address needs domain knowledge and belongs to ordinary tests.
- **why:** The split avoids duplicated and misdirected effort. The cost is a judgement call per check.
- **check:** Applying the test is judgement, even when the resulting check is automated. If the two sets have already merged, separate them only for that practical reason, not for purity.

### not-every-test-is-a-fitness-function
- **condition:** Auditing an existing test suite to find governance that is already there.
- **decision:** A test counts as a fitness function when it verifies an architectural concern. Expect to find unnamed ones in metrics suites (SonarQube), linters (ESLint, pyLint, cppLint) and source analysers (PMD).
- **why:** Existing governance is found cheaply. The cost is classifying each test.
- **check:** Each test counted guards a structural property, not a business behaviour.

### outcome-over-implementation
- **condition:** Reviewing or copying a fitness function.
- **decision:** Judge what it measures and why, never the mechanism. Checks are often written in another stack than the product, with operations tooling, or as 10–20 lines of glue.
- **why:** Attention stays on the protected quality. The cost is tolerating mixed implementations.
- **check:** If the discussion has drifted to the framework, restart from the outcome.

### build-glue-not-a-framework
- **condition:** No ready-made tool governs the architecture in front of you, which is the normal case because every architecture is its own mix of choices and technologies.
- **decision:** Write the check yourself as roughly 10–20 lines of script that combine the output of tools you already have; skip building a framework. The first question is whether the information you need exists anywhere.
- **why:** Glue delivers governance now at small cost. The cost is owning one more script.
- **check:** The information exists in some readable form: logs, an API, a database, tool output. If it exists nowhere, halt and schedule producing it as a separate, larger task.

### check-for-a-tool-first
- **condition:** You are about to build a custom fitness function.
- **decision:** Search for an existing tool first; the more common the ecosystem, the likelier one exists. Known examples: ArchUnit (Java), NetArchTest (.NET), Pa11y (accessibility), Black Duck (licences), Dependabot and snyk (dependencies and supply chain), Spectral with OpenAPI.Tools (API specs), Pact (consumer-driven contracts), jQAssistant with Neo4j (structural queries), Scientist (fidelity), Swabbie (orphaned cloud resources), and the language linter for everything else.
- **why:** You avoid building what exists. The cost is search time and adopting a tool you do not control.
- **check:** The search result is recorded before custom code is written. Re-verify the tool list against current tooling before acting.

### linter-when-no-archunit-exists
- **condition:** The platform has no architecture-testing framework, i.e. anything outside Java and .NET.
- **decision:** Use the language linter as the check surface: write custom rules for structure, allowed call patterns and other governance. Examples: ESLint (JavaScript), Cpplint (C++), Staticcheck (Go), sql-lint (SQL).
- **why:** Most structural checks become possible in nearly any codebase. The cost is less convenience than a dedicated framework, and rules you maintain yourself.
- **check:** The linter supports custom rules or plugins.

### mandate-parsable-logs-first
- **condition:** You want to govern behaviour across services built on different stacks, which no one compile-time tool can inspect together.
- **decision:** Make the first fitness function a mandate for one consistent, parsable log format in every service, enforced on the shared container image; only after that add checks that harvest those logs. Fields: correlation ID, service name, method name, username, IP address, elapsed time, and the UTC time the message arrived.
- **why:** The log format becomes the instrument for every cross-stack check. The cost is getting every service to agree and enforcing it at one chokepoint.
- **check:** A shared image or equivalent chokepoint exists. If services cannot agree on a format, fall back to runtime monitors (the continual form of `cadence-by-criticality`) and accept their overhead.

### communication-governance-by-log-harvest
- **condition:** One service (an orchestrator) is the sole owner of workflow state, and domain services must never call each other directly.
- **decision:** On a fixed cadence, read the previous interval's logs and fail whenever a call's destination is anything but the orchestrator; a loop of about nine lines suffices. This is the reactive half of `cadence-by-criticality`.
- **why:** Structural rules are enforced at zero runtime cost. The cost is that a violation stands for up to one interval.
- **check:** `mandate-parsable-logs-first` is in place. Where a forbidden call could produce a security or data-integrity incident before the next harvest, switch to runtime monitors. An agent can run this check.

### synthetic-transactions
- **condition:** You need to measure a complex cross-service interaction in production, and triggered tests reveal little about real behaviour.
- **decision:** Mark a request as synthetic, let it travel the normal path tracked by its correlation ID, and have the final step read the mark and skip the real commit.
- **why:** You observe genuine production behaviour end to end. The cost: one step that ignores the mark turns a probe into a real order, charge or delivery.
- **check:** Every step propagates the mark and the final commit reads it. If any step can commit an irreversible side effect (a charge, an email, a shipment) before that final check, halt.

### govern-the-synthetic-flag-itself
- **condition:** Synthetic transactions are in use.
- **decision:** Add a fitness function asserting that every check identified as synthetic (by annotation or naming convention) actually sets the flag.
- **why:** The instrument gets its own guard. The cost of relying on it: it covers only this one mechanism and only whether the flag is present.
- **check:** Synthetic checks can be identified by a machine.

### monitoring-driven-development
- **condition:** A quality can only be judged against real traffic.
- **decision:** Use production monitors as continual fitness functions for both technical and business health, alongside tests.
- **why:** Real behaviour is measured. The cost is production monitoring and checks that are more dynamic and noisier than triggered tests.
- **check:** Alerts are bound to objective thresholds; otherwise this falls back into failing `objective-outcome-or-its-not-one`.

### temporal-fitness-function
- **condition:** Risk grows with elapsed time rather than with change: a security-sensitive dependency going stale, a back-ported feature that will collide with the real release, a framework falling over a major version behind.
- **decision:** Give the check a time component. Three uses: a periodic reminder to check a security-sensitive dependency for updates; a break-on-upgrade test wrapping a back-port, forcing re-evaluation when the real upgrade lands; escalating reminders to take a framework upgrade, driven by a tool such as Dependabot or snyk once house criteria (e.g. the first patch release) are met.
- **why:** It is the only mechanism here keyed on time instead of a change event, which is the shape a drift detector needs. The cost is reminders that turn into noise if nobody acts on them.
- **check:** A version or release feed exists to key against.

### fitness-function-driven-architecture
- **condition:** The whole system's success depends on one stringent quality, and it is unclear whether any design can meet it.
- **decision:** Write the fitness function before the design, experiment against it, and keep it running while the rest is built. Worked case: a trading platform needing millions of transactions per second tried threads and several actor models, measured everything, found context switching dwarfed the business logic, and reached over six million transactions per second on a single thread with ring buffers, changing direction several times as approaches failed the check.
- **why:** Design budget goes only to approaches that meet the target. The cost is spending that budget chasing the number.
- **check:** The target is known and defensible. If it came from a stakeholder's wish instead of a requirement, halt and establish the requirement first.

### mechanical-sympathy
- **condition:** A performance check is failing and the cause is not visible at the layer you work in.
- **decision:** Instrument and understand the layers beneath your abstraction, down to the network, and measure every part instead of tuning the obvious layer. Keep working knowledge of at least one layer below your usual one.
- **why:** The surprising cause gets found (in the trading case, context switching outweighed business logic). The cost is instrumenting and learning layers you normally ignore.
- **check:** You can instrument below your normal working layer. This is judgement, not a gate.

### fidelity-fitness-function
- **condition:** Replacing an old system or code path whose behaviour is poorly documented and must be preserved.
- **decision:** Run old and new side by side and use the old one as the oracle, in the shape of the Scientist framework: the existing behaviour is the control (`use`), the new one the candidate (`try`). The harness decides whether to run the candidate at all on a configured share of traffic, randomises the order of the two, times both, compares and logs the results, logs and swallows any candidate exception so users never see it, and always returns the control's value.
- **why:** In the worst case users get exactly what they had before while the new path is proven. The cost is running two implementations, and swallowed errors can hide damage.
- **check:** Both can run on the same input without conflicting side effects. If the candidate writes anything and cannot be made side-effect-free, halt: live traffic would corrupt data and the swallowing would hide it.

### fidelity-cutover-gate
- **condition:** Deciding when the side-by-side comparison has run long enough to delete the old path.
- **decision:** Apply the shape sample, run, demand a clean tail, then delete. One high-traffic code host's figures at about 60 deploys a day: candidate on 1% of invocations for 4 days, no slow cases and no mismatches during the final 24 hours, then the old path removed.
- **why:** Deletion rests on evidence. The cost: those figures presume enough traffic to surface every edge case quickly, so copying them at low volume buys false confidence.
- **check:** The sampled traffic demonstrably exercised the branches you care about; assert branch coverage, not elapsed time. Otherwise raise the sample rate or lengthen the window. Never copy 1% / 4 days / 24 hours below that traffic.

### measure-the-instrument-before-trusting-it
- **condition:** A monitoring or governance tool raises alerts someone has to triage, and nobody knows whether the alerts are real.
- **decision:** Point a fitness function at the instrument rather than at the system, with its decision threshold fixed in advance, e.g. replace the tool if more than 10% of messages escape it. Procedure: estimate message volume and frequency in a controlled environment; build a mock service at that volume; let the mock query the monitor's own store for the messages it processed; derive the loss rate and the volume at which the tool crashes; decide. In the worked case a UDP-based monitor lost 40% of messages at high volume and was replaced.
- **why:** A lying instrument stops consuming people's time and passing as evidence. The cost is a controlled environment and a mock at representative load. This rule extrapolates one worked case; treat it as our rule, not settled doctrine.
- **check:** A pre-production environment can carry representative volume and the instrument's store is readable. Until the error rate is measured, stop treating the tool's output as evidence. The measurement automates; replace-or-keep stays a person's call.

### derive-thresholds-from-production-not-estimates
- **condition:** A check's threshold was set from an estimate because the system was new.
- **decision:** Once the system is live, swap the estimate for a measured production figure, and expect it to be off by an order of magnitude. Procedure: count real incoming calls to find the peak and the auto-scaling factor availability needs; query the APM tool for calls per second; re-run load and concurrency tests at the real figure; watch memory and CPU and set the stress point; leave the check in the pipeline. Worked case: an estimate of 120 requests/second, load tests passing at 300/s, a service that kept crashing, and a real average of 1,200/s.
- **why:** Thresholds match reality. The cost is that the rule is reactive: it corrects a wrong threshold only after production has contradicted it.
- **check:** The service is live and an APM or query tool reports real call rates. If a service crashes while its load tests pass, suspect the estimate and measure it before raising the auto-scaling factor blind.

### security-dependency-scan-in-the-pipeline
- **condition:** A manual software-supply-chain review imposed after a breach is slowing delivery below what the market requires.
- **decision:** Replace it with a pipeline stage that scans the dependency list against a block list updated in real time and alerts on any affected component. Automation takes the regression work; people stay in the loop for what only they can judge.
- **why:** Security gets the fastest feedback possible without throttling delivery. The cost is depending on the quality of the feed.
- **check:** A maintained block-list feed exists (snyk, Dependabot). Re-verify against current tooling before acting.

### licence-change-detection
- **condition:** The code depends on open-source components whose licence terms could change in a routine version bump, and such a change would create legal exposure.
- **decision:** Automate detection and keep the judgement human, in four steps: store where each dependency's licence file sits in its package; store its contents or a hash alongside the version; when a new version appears, fetch and compare its licence file; if it differs, fail the build and notify the lawyer. Do not try to interpret the difference automatically.
- **why:** Surprises are caught with no ongoing effort. The cost is a blocked build and a legal review on each licence change. This is the canonical machine-detects, person-approves shape.
- **check:** Each licence file sits at a stable, discoverable path. A dependency whose licence cannot be found is reported as unaudited, never passed silently. A second party owns the legal call.

### availability-fitness-function-before-a-rewrite
- **condition:** Choosing between integrating with a legacy system and rewriting it, with no objective view of whether it can carry the load.
- **decision:** Before committing resources, put the legacy service under stress and compare its errors with its total responses. In the worked case it showed headroom for the new integration and the rewrite budget was freed.
- **why:** A gut call becomes a measurement. The cost is a safe environment in which to stress the legacy system.
- **check:** The system can be stressed safely and a monitoring tool reports the error ratio.

### canary-with-a-fitness-function-attached
- **condition:** A change with unpredictable real-world impact is about to ship, such as a temporary scaling fix, a feature heavy on bandwidth or a new algorithm.
- **decision:** Attach a fitness function to a feature flag and expose the change to an expanding share of users, widening only while monitoring stays good. Run continuously, the check also tells you how long a stopgap will hold.
- **why:** Exposure grows with evidence, and the gate doubles as a countdown on the scaffolding. The cost is flag routing by user criteria and monitoring at cohort granularity.
- **check:** Flag infrastructure routes by user criteria and monitoring resolves the flagged cohort.

### system-wide-fitness-function
- **condition:** Two fitness functions pull against each other, e.g. performance against the cost of encryption for security.
- **decision:** Treat the system-wide fitness function as the collection of individual checks, used to prioritise future decisions and never evaluated as one value. The checks expose the forces with objective measures; resolving the trade-off stays with you.
- **why:** Conflicts are reasoned over with data. The cost is that no check resolves the trade-off for you.
- **check:** The individual checks exist and are objective. Do not compute a composite (`no-composite-score`). Judgement throughout.

### no-composite-score
- **condition:** Someone wants the architecture's health as a single number.
- **decision:** Refuse the composite. Report the individual outcomes and the conflicts between them; genuinely conflicting qualities have no single optimum, so choices are forced.
- **why:** Precise conversations about the architecture replace a misleading average. The cost is a less tidy report.
- **check:** When asked for a health score, hand over the separate outcomes and the named conflicts. A weighted composite of team metrics has failed in practice for the same reason.

### guided-or-its-reactionary
- **condition:** A team ships rapid incremental changes and calls the result evolutionary.
- **decision:** Evolution needs all three parts: guided by fitness functions, incremental, and across several dimensions. Incremental change without guidance is drift with good tooling.
- **why:** A named target keeps changes converging. The cost is the up-front work of defining the guidance.
- **check:** You can name what the changes are guided toward. If not, halt and run `dimensions-before-fitness-functions` before shipping more.

### fitness-functions-evolve-with-requirements
- **condition:** An architectural requirement changes.
- **decision:** Change the matching checks in the same move. They live in the repository next to the code they govern, which is their whole versioning; no separate mechanism is needed.
- **why:** Checks and requirements stay aligned. The residual cost: co-location makes drift likely to be noticed but never detects it.
- **check:** The checks are under version control with the code. A check living elsewhere (a dashboard config, an external scanner's saved query) drifts silently; move it in. Spotting a stale check is mechanical; stating the new requirement is not.

### keep-them-green
- **condition:** A fitness function is failing and the fix is not immediate.
- **decision:** Architects and developers keep the checks passing at all times; a check red for long has stopped measuring anything. The two exits: fix the code, or convert the check into a `cascading-fitness-function` with a dated escalation.
- **why:** A passing suite remains an objective measure of the architecture's fitness. The cost is interrupting other work to restore green.
- **check:** If people route around a red check, take one of the two exits; leaving it red is neither. Detecting a long-red gate automates; choosing the exit is a person's call.

### developer-must-understand-the-why
- **condition:** A fitness function fails in someone else's build.
- **decision:** The person who hits it must understand its purpose, not just its assertion, so they can repair the fault and continue the build.
- **why:** Governance stays a useful constraint instead of a felt burden. The cost is collaboration and a recorded rationale.
- **check:** The rationale is findable from the failure (`document-the-why`). If the only route to green is weakening or disabling the check because nobody knows why it exists, halt: that is governance turning into theatre. At one operator this reduces to recovering your own reasoning, which only a written record makes possible.

### document-the-why
- **condition:** Writing a check that someone, including you later, will run into.
- **decision:** Record the intent next to the enforcement. Options: (1) the check itself as documentation, always honest because anyone can execute it, but hard for non-technical readers; (2) a decision record with a section stating how the decision is governed, the default; (3) a BDD framework such as Cucumber, mapping plain language to verification code, at the cost of a tool built for requirements being bent to describe checks; (4) a Jupyter document combining the rule text with on-demand execution, e.g. jQAssistant with Neo4j to query structure.
- **why:** Whoever hits a red build can repair rather than disable. The cost is keeping the record current. Executing the check stays the priority; documentation never replaces the gate.
- **check:** Every check links to its rationale. At one operator, the decision record is the only second party available.

### publish-results-visibly
- **condition:** Fitness functions exist and are running.
- **decision:** Post their results in a visible, shared place so developers keep them in mind during everyday coding.
- **why:** The checks stay present in people's minds. The cost is a channel someone must keep readable.
- **check:** Results are published automatically on each run. An agent can do this.

### report-fitness-function-outcomes
- **condition:** Governance has run for some time and its effectiveness is unknown.
- **decision:** Generate a periodic report (weekly in the worked case) of the checks' pass/fail rates to judge health, cadence and related factors.
- **why:** The governance itself becomes measurable. The cost is storing outcomes durably.
- **check:** Outcomes are recorded somewhere queryable, not only as pass/fail in a transient log. An agent can run this.

### fitness-functions-as-checklist-not-stick
- **condition:** The check set is growing and developers experience it as an obstacle.
- **decision:** Treat the checks as a checklist that keeps skilled people from skipping steps in repetitive, complex work, as pilots and surgeons use one. Avoid building ever more complex, interlocking checks that add burden without matching value; keep the high-value ones.
- **why:** Developers keep trusting the gates. The cost is giving up checks that protect too little.
- **check:** For each check, compare its upkeep with the value it protects and remove it when upkeep wins. Fewer checks reduce exposure to wrong ones but validate none of them.

### cc-cannot-separate-essential-from-accidental
- **condition:** Cyclomatic complexity, or any metric, gates the build and fires on code you believe is correct.
- **decision:** Learn the metric's blind spot before gating on it: it cannot tell essential complexity (an algorithmically hard problem yields complex functions) from accidental complexity (poor code or poor partitioning). When it fires on essential complexity, scope an exemption or change the measure.
- **why:** The signal stays intact everywhere else. The cost is a human judgement on each firing.
- **check:** Someone can tell the two apart by reading the code; where nobody can, do not use the metric as a gate here. Never raise the threshold globally to silence essential cases.

## Coupling, quanta, and contracts — 20 rules

### connascence-strength-ladder
- **condition:** Coupling between two components needs reducing, and reduce coupling is too vague to act on.
- **decision:** Name the connascence (two components are connascent when changing one forces a change in the other to keep the system correct) and refactor toward a weaker form. Static, weakest to strongest: Name; Type; Meaning or Convention (magic values instead of constants); Position (argument order where the types fit and the meaning does not); Algorithm (both sides must compute, say, the same hash). Dynamic, stronger still: Execution (call order matters); Timing (races); Values (several values must change together, as in a transaction across separate databases); Identity (both must reference the same entity, such as one shared distributed queue).
- **why:** A concrete ladder turns a vague goal into a refactoring target. The cost: dynamic forms are hard to see because runtime analysis tooling is weak compared with call-graph analysis.
- **check:** You can read both sides of the coupling. Static forms are detectable by source analysis; dynamic forms mostly need a person.

### prefer-static-to-dynamic-connascence
- **condition:** You can choose how two components will depend on each other.
- **decision:** Choose static connascence, which source analysis reveals and refactoring tools improve, over dynamic. Example: replacing a magic value (Meaning) with a named constant (Name).
- **why:** Coupling stays visible and fixable with tools. The cost is sometimes more explicit structure.
- **check:** The chosen dependency is visible in source.

### rule-of-locality
- **condition:** Judging whether a given coupling is acceptable.
- **decision:** Read strength and distance together: convert strong forms into weaker ones, and the farther apart two elements are, the weaker their connascence must be. Two classes in one component sharing a Meaning-level dependency is a small smell; the same dependency between two components is serious.
- **why:** Tight coupling is allowed where it is cheap. The cost is knowing where module boundaries sit.
- **check:** Module boundaries are known, since distance is measured against them. Partly automatable.

### page-jones-three-guidelines
- **condition:** Restructuring a system for modularity.
- **decision:** In order: (1) reduce overall connascence by splitting the system into encapsulated elements; (2) reduce whatever connascence still crosses those boundaries; (3) maximise connascence inside each boundary. Tight coupling within a boundary is correct; scattering related things to look decoupled is the error.
- **why:** Change stays local. The cost is accepting dense coupling inside each unit.
- **check:** Encapsulation boundaries exist or can be drawn. Judgement.

### degree-of-connascence
- **condition:** Deciding whether a known coupling problem is urgent.
- **decision:** Weigh its degree: how many classes or modules it touches. Strong dynamic connascence across a few modules is tolerable, but expect codebase growth to enlarge it.
- **why:** Effort goes to couplings with wide reach. The cost: a small problem left alone grows with the code.
- **check:** Count affected modules now and revisit as the codebase grows.

### restrict-implementation-coupling-to-the-tightest-scope
- **condition:** Deciding what to expose across a boundary.
- **decision:** Keep implementation details inside the boundary; only the contract crosses it. The extreme case is a database schema used as an integration point, where one application's schema change can break others without warning.
- **why:** It avoids brittleness, where a small local change breaks distant parts. The cost is maintaining a contract layer.
- **check:** Communication across the boundary goes through a contract. If a schema, internal class or private structure is already an integration point, break that coupling first. Per-boundary checks automate (ArchUnit package rules, `carve-bounded-context-with-fitness-functions`); deciding what counts as a detail is judgement.

### architecture-quantum
- **condition:** You need the real unit of independent change in a system, as opposed to what the diagram claims.
- **decision:** A quantum is something you can deploy on its own that also has strong functional cohesion, strong static coupling and synchronous dynamic coupling; it must meet all three. Static coupling is everything needed to bootstrap it: OS, frameworks, transitive dependencies, data stores, message brokers, container orchestration. Dynamic coupling is how quanta call each other at runtime.
- **why:** It exposes hidden lockstep. The cost is an inventory of operational dependencies, not only code ones.
- **check:** You can list the operational dependencies. Independent deployability alone would make a monolith a quantum; cohesion keeps the scope useful.

### the-database-is-inside-the-quantum
- **condition:** Counting quanta in a supposedly distributed architecture.
- **decision:** A shared database collapses the count to one unless the database deploys in lockstep with the application. Services that only call database-touching services join that quantum too. Any holistic coupling point the system needs in order to work (an orchestrator, a mediator in event-driven systems) also forms one quantum around it.
- **why:** It stops designs built on independence that does not exist. The cost is admitting the claimed benefits are absent.
- **check:** If services presented as microservices share a database with its own deployment cadence, say it is one quantum before designing on top of the assumption. An inventory can reveal the shared store; judging lockstep is a person's call.

### ui-coupling-collapses-the-quantum
- **condition:** A services backend sits behind a single user interface.
- **decision:** A tightly coupled UI makes the whole system one quantum, because most UIs stop working when parts of the backend are down, and per-service operational qualities (performance, scale, elasticity, reliability) become hard to vary. Escapes: asynchronous communication between front and back, or micro-frontends where each service emits its own UI elements onto an event-mediated canvas, making each service plus its UI piece a quantum.
- **why:** Per-service qualities become possible again. The cost is UI architecture complexity.
- **check:** If per-service qualities were the reason for distribution and the UI is synchronous and monolithic, halt: you pay the cost of distribution without its benefit.

### static-quantum-diagram-for-legacy
- **condition:** An inherited architecture is poorly understood and the impact of a change is unknown.
- **decision:** Draw the static quantum diagram: how the parts are actually wired, operational dependencies included, to find which systems a change touches and where decoupling is possible.
- **why:** Change impact becomes visible. The cost is building the diagram from operational topology.
- **check:** You can see the operational topology, not only the source. Partly automatable.

### three-forces-of-dynamic-coupling
- **condition:** Deciding how two services communicate within a workflow.
- **decision:** Choose three forces together, since each pulls on the others: communication (synchronous, where the caller blocks, or asynchronous, with a reply queue when a value is needed), consistency (atomic or eventual) and coordination (orchestration or choreography). Transactions are easiest with synchronous orchestration; the highest scale comes from asynchronous, eventually consistent choreography. Build a matrix and test what changing any one force does to the other two.
- **why:** Hidden interactions surface before commitment. The cost: these rules supply the axes and not the verdict.
- **check:** To pick the cell, go to the decomposition rules (decomposition rule 27 `tradeoff-statement-to-the-business`).

### contract-strictness-by-change-frequency
- **condition:** Choosing a contract format between parts of an architecture, where a contract is any format carrying information or dependencies, including transitive dependencies, internal and external integration points, and caches.
- **decision:** Place it on the spectrum from strict to loose: remote method calls and gRPC defaults (names, parameters, types and order fixed); JSON with an attached schema (typed properties, required fields); REST and GraphQL modelling resources (new fields do not break existing readers); bare name/value pairs in JSON or YAML. Choose by how often the contract changes against how many parts depend on it; frequent change combined with many dependents is where strictness hurts most. Use strict only where it pays, never by default.
- **why:** Loose contracts absorb change. They cost contract certainty, verification and extra application logic.
- **check:** Change frequency is known or honestly estimated. Going loose requires fitness functions that replace the lost guarantees; if you will not build them, stay strict.

### need-to-know-contracts
- **condition:** A contract is being defined and there is a pull to add fields a consumer may want later.
- **decision:** Carry only what is consumed. Passing everything is stamp coupling: if a wishlist needs only a name from a profile but the contract carries the whole profile, a change to a field the wishlist ignores still breaks it and forces coordination.
- **why:** Unused data stops causing breaking changes. The cost is negotiating additions when a consumer later needs more.
- **check:** Diff contract fields against actual use; the diff automates, deciding intent does not.

### postels-law-for-contracts
- **condition:** Designing either side of an integration point.
- **decision:** Send conservatively: no more than needed, since every extra field invites dependents and tightens a contract that could stay loose. Accept liberally: tolerate more than you use and validate only what you consume (needing a phone number means validating only the phone number). Version when you break a contract, automated through consumer-driven contracts.
- **why:** Contracts stay loose and change stays local. The cost is design discipline on both sides that no tool enforces for the first two clauses.
- **check:** The versioning clause automates (`consumer-driven-contracts`); the send and accept clauses are design-review items.

### prefer-duplication-to-coupling
- **condition:** Two services both need one concept, e.g. an item shared by checkout and shipping.
- **decision:** In a strongly decoupled style such as microservices, duplicate: each service keeps its own representation and passes what is needed across the boundary in a loose form. In a service-based style, coupling is more likely the right answer.
- **why:** Teams change independently instead of propagating every change to all sharers. The cost is duplicated code and the risk of semantic drift.
- **check:** The style is one where decoupling dominates. If the concept must stay identical everywhere (a tax calculation, a security algorithm — connascence of Algorithm), coupling is the lesser harm. A default, not an absolute.

### reuse-usability-inverse
- **condition:** Building something meant to be reused.
- **decision:** Expect usability to fall as reusability rises: every option and hook added for another caller makes the basic use harder. Treat reuse as deliberate, difficult work, closer to an organ transplant than to snapping bricks together.
- **why:** It prevents over-general code. The cost is building specific things more often.
- **check:** If an abstraction is gathering configuration knobs for unknown future callers, stop and build the specific thing.

### effective-reuse-requires-abstraction-plus-low-volatility
- **condition:** Deciding whether a candidate is safe to share across an organisation.
- **decision:** Share only what is both genuinely abstract and rarely changing; shared code that changes often spreads pain, while stable abstractions repay the sharing.
- **why:** Shared assets pay off instead of rippling changes outward. The cost is declining to share things that look reusable.
- **check:** Low churn is shown from version-control history; without that evidence, treat the candidate as high-churn and keep it unshared. Abstractness is judgement (`distance-from-main-sequence`).

### sidecar-for-orthogonal-coupling
- **condition:** Concerns that should be uniform — monitoring, logging, authentication, access control, circuit breakers — cut across a decomposition organised around domains.
- **decision:** Recognise the coupling as orthogonal (two distinct purposes that must still intersect) and isolate the operational concerns in a sidecar, shared across teams or owned by an infrastructure group. When every service carries one, the sidecars link into a service mesh that enables unified dashboards and control. The shape is ports-and-adapters with one change: data schemas and transactionality stay inside the service instead of being one more adapter; structurally it is a decorator.
- **why:** Operations become uniform without coupling domains. The cost: without a mesh, unifying on one monitoring tool means one sidecar per platform, so cost grows with the number of platforms.
- **check:** A fitness function verifies the sidecar is present on every service; without it the mesh has holes and the uniformity is imaginary.

### data-product-quantum
- **condition:** Analytics and reporting cut across an architecture split by domain: the sidecar's orthogonal shape, with more complexity.
- **decision:** Place a data product quantum next to each service: code and data that the service's own domain team owns, acting as the analytics interface. It is a cooperative quantum: operationally separate, talking to its service asynchronously with eventual consistency, tightly contract-coupled to that service and loosely to analytics. Three types: source-aligned (serves one service's analytical data), aggregate (combines several inputs, sync or async), fit-for-purpose (built for one need: reporting, BI, ML). A domain may hold several when they need different qualities.
- **why:** Analytics stops reaching into operational schemas. The cost is domain teams owning an analytical interface as well as an operational one.
- **check:** The domain team can own both interfaces. The non-architectural parts of data mesh (domain ownership of data, data as a product, a self-serve platform) are outside these rules.

### afferent-efferent-coupling
- **condition:** You need a number for how entangled a codebase is.
- **decision:** Measure afferent coupling (incoming connections) and efferent coupling (outgoing connections) per artifact, with tools such as JDepend, IntelliJ's dependency structure matrix, SonarQube, JArchitect or NDepend.
- **why:** Ungoverned connections grow into a dense web nobody can understand; the measure makes it visible. The cost is a metrics tool per platform.
- **check:** A metrics tool exists for the platform.

## Code-level governance — 7 rules

### distance-from-main-sequence
- **condition:** You need one structural-health number for a component, especially before restructuring or migrating it.
- **decision:** Compute abstractness `A = Σma / (Σmc + Σma)`, instability `I = Ce / (Ce + Ca)` and normalised distance `D = |A + I − 1|`. Near the ideal line is balanced; top right is the zone of uselessness (too abstract to use); bottom left is the zone of pain (too much implementation, too little abstraction, brittle). Mock code drifts toward uselessness by nature. Repair: find the large methods driving the score, extract parts to raise abstractness, then remove the duplication the extraction exposes, which improves instability. Leave it running as a check so the code does not decay that far again.
- **why:** It gives a mechanical repair path and a regression gate. The cost is an object-oriented codebase and a metrics tool.
- **check:** A tool computes the metrics (NDepend, JDepend, SonarQube, JArchitect). Never migrate a component sitting in the zone of pain; fix it in place first, since moving an unstable base is harder than moving a solid one.

### read-instability-and-abstractness-together
- **condition:** Interpreting an instability score on its own.
- **decision:** Always pair `I` with abstractness: `I` near 1 is unstable, but `I` near 0 means stable when the component is mostly abstract and rigid when it is mostly concrete.
- **why:** It avoids mistaking rigidity for stability. High stability costs reuse, since self-contained components tend to duplicate.
- **check:** Both metrics are available.

### cc-threshold
- **condition:** Setting a cyclomatic complexity gate. CC is `E − N + 2` for one function (edges minus nodes plus two) and `E − N + 2P` in general, with `P` connected components.
- **decision:** Industry treats under 10 as acceptable outside complex domains; prefer under 5, which indicates cohesive, well-factored code. Past 50, no coverage can rescue the code (the Crap4j combination of CC and coverage). Test-first development tends to yield smaller, simpler methods: a lever, not a gate.
- **why:** A clear numeric gate. The cost is false firings on essentially complex code.
- **check:** A metrics tool exists for the language and you know how much of the domain's complexity is essential (`cc-cannot-separate-essential-from-accidental`). If the codebase fails the threshold everywhere, keep the threshold and use `cascading-fitness-function`.

### archunit-governable-relationships
- **condition:** A structural design decision should be enforced rather than documented, on the JVM (ArchUnit) or .NET (NetArchTest).
- **decision:** Assert five relationship classes: (1) cycles, e.g. `slices().matching(...).should().beFreeOfCycles()`, because IDE auto-import quietly creates component cycles that developers dismiss by reflex; (2) package dependencies, as a deny rule `noClasses().that().resideInAPackage(...).should().dependOnClassesThat()...` or an allow-list `onlyHaveDependentClassesThat().resideInAnyPackage(...)`; (3) class dependencies by name pattern; (4) inheritance, a coupling form that matters architecturally only across component or deployment boundaries; (5) annotations, verifying intent tags are applied, e.g. only transactional classes may depend on an entity manager.
- **why:** Design intent becomes a failing test. The cost is being tied to JVM or .NET tooling.
- **check:** The platform is JVM or .NET; elsewhere use `linter-when-no-archunit-exists`.

### layer-access-rules-as-code
- **condition:** A layered architecture relies on developers not bypassing its layers.
- **decision:** Encode the layers and their allowed access as an executable check, e.g. `layeredArchitecture()` defining controller, service and persistence layers, with controllers accessed by no layer, services only by controllers, persistence only by services. It blocks shortcuts such as reaching persistence straight from presentation for speed, which raises coupling and defeats the reason the layers exist.
- **why:** Layer isolation actually holds. The cost is maintaining the layer map as packages move.
- **check:** Layers map recognisably onto packages or namespaces. Without this check you have no grounds to trust that the layers are respected.

### directionality-of-imports
- **condition:** A rule about which module may depend on which lives in a coding guideline.
- **decision:** Assert the import direction in a unit test so a violation fails before commit, e.g. a JDepend `DependencyConstraint` inside a JUnit test.
- **why:** The rule becomes an executable artifact and developers spend attention on the domain, not on policing and scolding. The cost is a programmable analysis API.
- **check:** A coupling-analysis tool with a programmable API exists for the platform.

### lcom-before-splitting-a-shared-class
- **condition:** Decomposing a monolith and hitting a shared ancillary class, e.g. an address class shared only because one deployable made it convenient.
- **decision:** Measure LCOM (lack of cohesion in methods; `ckjm` in Java), which counts missed chances to share fields between methods. High LCOM: it was never really one class; split it and give each service its part. Low LCOM: it is cohesive, so either extract it into a shared package both depend on (coupling, discouraged in microservices) or replicate it into both; in a distributed setting, messaging or a service call can do the same job.
- **why:** The split follows real cohesion. The cost: a cohesive class forces a share-or-copy choice.
- **check:** A cohesion-metrics tool exists for the platform. If LCOM is low and neither sharing nor replication is acceptable, the boundary is in the wrong place; move it instead of forcing the split.

## Data and schema — 14 rules

### schemas-tested-versioned-incremental
- **condition:** A relational or other database sits inside a system you intend to evolve.
- **decision:** Treat schema changes like source changes: tested (add checks that ORM mappings stay in step with schemas), versioned together with the code that uses them, and applied incrementally by automated migration tools, never by hand.
- **why:** Schema and code are interdependent and evolve together; separating them only adds friction. The cost is migration tooling wired into the pipeline.
- **check:** A migration tool runs in the pipeline. If any environment takes hand-applied changes, fix that first; the other data rules depend on it.

### migrations-are-immutable
- **condition:** A migration that has already run turns out to be a mistake.
- **decision:** Never edit or delete it; write a new migration that reverses it, the way a ledger corrects an entry with a counter-entry.
- **why:** Code written after the original keeps working when you rebuild to an intermediate point, and environments that already applied it stay consistent. The cost is a longer migration history.
- **check:** The migration tool enforces immutability of applied migrations.

### skip-undo-migrations
- **condition:** Deciding whether to write an undo block for every migration.
- **decision:** Skip them. Rebuild forward to any point instead (to restore version 95, run 1 through 95); avoid maintaining and testing correctness in two directions; accept that some changes cannot be undone anyway, such as a dropped table, and that parking it under a renamed table soon holds irrelevant data.
- **why:** It halves the testing burden. The cost is depending on full rebuilds.
- **check:** A rebuild from migration 1 completes in reasonable time. At large data volumes this fails and the calculation changes.

### expand-contract
- **condition:** A schema or interface must change incompatibly while other systems still rely on the current shape.
- **decision:** Insert a transition phase: start, expand (old and new coexist and are kept in sync), contract (remove the old). The transition may last from days to months, giving other systems time to catch up; it is a case of the general parallel-change pattern.
- **why:** Consumers migrate at their own pace. The cost is running and synchronising two shapes, in a database usually with a trigger.
- **check:** Both representations can be kept in sync. Contract only on evidence that every consumer has moved (a check as in `migrate-method-from-database`, or a person), never on a calendar.

### expand-contract-three-cases
- **condition:** Applying expand/contract to a specific column change, e.g. splitting a full-name column into first and last name.
- **decision:** Two independent facts pick the procedure: is there legacy data, and are there integration points. (1) Neither: add the new columns, drop the old. (2) Legacy data only: add columns, fill them via extraction functions, drop the old. (3) Both, the hardest and most common case: add columns, migrate the data, install a two-way trigger (writes to the old column derive the new ones; writes to the new columns are concatenated into the old), and drop the old column only once every consumer uses the new shape. Fallbacks for contraction: mark the column unused when dropping is too slow at volume; add a generated column when read-only access to the old shape is still needed; either way the old column stops being a write path.
- **why:** Each case gets just the machinery it needs. Case 3 costs trigger logic and a long sync window.
- **check:** The database supports triggers for case 3, and unused-column marking or generated columns for the fallbacks.

### no-shared-database-integration
- **condition:** Several applications need the same data and pointing them all at one database looks obvious.
- **decision:** Keep each application's data its own and integrate through contracts, never through a shared database.
- **why:** A shared schema fossilises across every project that uses it, and any change by one can break the others; it happens mostly out of habit because everyone already uses the same database. The cost is building the integration a shared table seemed to give for free.
- **check:** A check can detect a second application connecting to the schema. If a shared database already exists, the exit is `expand-contract`, not a rewrite.

### transactional-boundaries-set-the-granularity-floor
- **condition:** Decomposing a system and choosing service size.
- **decision:** Let the transactions the business needs, not the class graph, set the smallest service you can build. Transactions bind quanta together like a strong force and are invisible to coupling tools.
- **why:** It keeps the structure from fighting the problem it serves. The cost: heavily transactional systems fit poorly with very small services.
- **check:** The real transactional boundaries are mapped, usually by asking the business rather than reading code. If the target granularity breaks a transaction the business needs, the target is wrong. Cross-service transactions and sagas belong to the decomposition rules.

### limit-transactional-contexts
- **condition:** Designing any system, monolithic or distributed.
- **decision:** Keep transactional contexts as few and as small as possible. Recognise why they spread: analysts like stop-the-world operations regardless of technical cost; transaction boundaries reveal how business concepts are really coupled, which is useful information; and a separate data team may own them, making splits expensive to coordinate.
- **why:** Components can change without dragging others along. The cost is giving up some atomic guarantees.
- **check:** Each transactional context has its business reason recorded.

### referential-integrity-becomes-a-fitness-function
- **condition:** Splitting a database so entities once joined by foreign keys live in separate stores.
- **decision:** Replace the lost database guarantee with a fitness function. Identifiers become GUIDs or random sequences, and a check ensures that when the owner deletes an entity the deletion propagates to every service still referencing it, typically by the owner publishing to a durable queue that the others consume.
- **why:** The guarantee moves from schema level to architecture level instead of vanishing, which is also the argument for a sceptical data team. The cost is building and running the propagation.
- **check:** A durable messaging mechanism exists and each entity has one owner. If you cannot name the owner, do not split yet: propagation has no source.

### single-writer-cached-readers
- **condition:** Several services read the same reference, configuration, audit or customer data; a shared table and a call per read are both ruled out.
- **decision:** Separate who writes from who reads. Of three options — shared tables (couples services to one database), a service per shared concern (heavy inter-service traffic that hurts performance), or a single writer with cached readers — choose the third: the owning service alone writes; readers cache on startup with a suitable refresh interval; updates go as requests to the owner, which then publishes the change.
- **why:** No shared schema and no chatty reads. The cost is staleness up to the refresh interval.
- **check:** Every reader accepts that staleness. A reader that needs strong consistency uses the dedicated-service option instead.

### migrate-method-from-database
- **condition:** Business logic lives in stored procedures or triggers, and the data split leaves the procedure without everything it needs.
- **decision:** Apply expand/contract to behaviour, a strangler fig for the database. Expand: add the replacement method in the owning service and point callers at it, first as a pass-through to the procedure, then reimplemented in well-tested code; both paths work meanwhile. Contract: when a fitness function confirms every dependency now calls the service, drop the procedure.
- **why:** Behaviour moves into code that is testable and refactorable, unlike stored procedures. The cost is data volume and transport once logic leaves the database.
- **check:** Callers can be enumerated so the check can assert none remain. The alternative is equally valid: widen the service boundary so the procedure stays with its data; decide case by case.

### baseline-data-quality-before-evolving
- **condition:** Starting an architectural evolution on data that has survived several generations of software and their quirks.
- **decision:** Clean the data first instead of building permanent mechanisms around its defects. Keep the data with real value in the evolving path and move older data out to a reference store.
- **why:** Legacy data has value but taxes every change. The cost is a business decision about what to discard.
- **check:** Someone with power to decide what data matters is involved; this is a business conversation, not a technical one. Confirm you can evolve both the schema and the data quality before evolving the architecture.

### refusing-to-refactor-couples-you-to-the-past
- **condition:** The data team's habit is to add a join table instead of changing a schema.
- **decision:** Name the habit as accumulating coupling: each join table hides the real abstraction (one entity represented by several things) and stacks every past schema version on top of the others. Refactor the schema and retire old data.
- **why:** The model keeps matching reality; refusing ties the architecture to a past it can no longer refactor. The cost is the risk of breaking existing consumers, handled through `expand-contract`.
- **check:** Count the join tables added in place of schema changes; each is a refactoring candidate.

### polyglot-persistence-on-decomposition
- **condition:** A monolith is being split, and its one relational database currently serves catalogue, analytics and operational data together.
- **decision:** Use the decomposition to choose persistence per problem instead of copying the relational default: some data suits key/value stores, and some questions a graph database answers in seconds take a relational one hours or days.
- **why:** Each workload gets a store that fits. The cost: moving from one database to several, even of one type, brings its own operational issues.
- **check:** The team can operate more than one database technology. When the data team resists, lay out each option's trade-offs instead of asserting the architectural requirement.

## Deployment and incremental change — 11 rules

### pipeline-not-ci-server
- **condition:** A team has a CI server with a long task list and considers it sufficient.
- **decision:** Build a deployment pipeline with separable stages. It models any number of post-commit tasks at different levels, verifies production readiness instead of only integration, and runs on every change of any kind. That is where fitness functions live.
- **why:** Separate stages give the task isolation and feedback a CI server lacks, and a failing stage blocks. The cost is building and running the pipeline.
- **check:** The pipeline exists before you write fitness functions; it is the precondition for most of these rules.

### build-the-environment-in-the-pipeline
- **condition:** The pipeline runs against a hand-maintained environment.
- **decision:** Have the pipeline build its own deployment environment, a container or a declaratively generated host, rebuilt from nothing.
- **why:** Development and operations gain high confidence that what was tested is what runs. The cost is expressing the environment as code.
- **check:** The environment is expressible as code.

### fan-out-to-verify-both-states
- **condition:** Continuous deployment, where a green pipeline run lands in production.
- **decision:** Verify two things for every change: current production is unharmed, and the change succeeds in the future-state environment. Run the jobs in parallel (fan out), then join into one thread for deployment once all pass (fan in), repeating wherever a change must be evaluated in several contexts.
- **why:** Both states are proven before release. The cost is parallel pipeline capacity.
- **check:** The pipeline supports parallel jobs.

### feature-toggle-to-decouple-deploy-from-release
- **condition:** You want continuous deployment and the business wants staged, visible releases.
- **decision:** Deploy behind a feature toggle and release separately. At its simplest a toggle checks an environment variable or a config setting; more capable ones pick up new configuration and flip while running. Toggles that route by criteria (IP, access list) also enable QA in production: a feature visible only to testers, exercised in the real environment.
- **why:** Deployment and release cadences come apart. The cost is toggle debt that must be removed (`remove-toggles-aggressively-never-reuse`).
- **check:** A toggle mechanism with routing criteria exists.

### remove-toggles-aggressively-never-reuse
- **condition:** A feature toggle has served its purpose.
- **decision:** Remove it promptly and never repurpose an old flag. Cautionary case: dormant code sat behind a toggle nobody removed; the flag was reused for new code deployed to seven of eight servers; switching it on made seven servers sell while the eighth, still running the old code under the same flag, bought. The loss passed $400 million in 45 minutes, more than the firm was worth.
- **why:** A whole class of catastrophic misfires disappears. The cost is cleanup work after each release.
- **check:** Stale-toggle detection automates; deletion is a person's call. If a toggle's original purpose cannot be established, delete it and create a new one.

### consumer-driven-contracts
- **condition:** A provider serves several consumers and must be able to change without breaking them.
- **decision:** Invert who writes the test: each consumer writes tests capturing what it needs and hands them to the provider, which runs them beside its own suite and keeps them passing; the provider may then evolve in any way that keeps them green. Tool: Pact. These are atomic integration fitness functions.
- **why:** Providers evolve freely within known limits. The cost is consumers writing and maintaining their suites.
- **check:** Consumers exist and maintain their tests, and builds are trustworthy (`engineering-maturity-precondition`). When the consuming side is an agent, or a sibling product run by the same operator, the mechanism carries over unchanged; only the negotiation between separate teams does not.

### engineering-maturity-precondition
- **condition:** Adopting consumer-driven contracts, or any check whose value depends on the build being trustworthy.
- **decision:** Restore build discipline first: a build left broken for days voids the guarantees that integration checks give.
- **why:** Checks deliver what they promise only on a working build, and policing practice through checks saves much manual pain. The cost is fixing build hygiene before adding governance.
- **check:** If builds routinely stay broken, add no new checks; they would just be one more broken thing. This is the most commonly skipped precondition in this file.

### cycle-time-as-a-fitness-function
- **condition:** You want one process metric that predicts how fast the architecture can change.
- **decision:** Track cycle time — from a developer starting a unit of work to it running in production — and gate on it. Prefer it to lead time, which includes subjective work such as estimation and prioritisation. Speed of change is proportional to cycle time (`v ∝ c`), so the system cannot evolve faster than it. Worked gate: a three-hour cycle time creeps up as stages accrete; an alarm past four hours forces an explicit choice between restructuring the pipeline and accepting four hours.
- **why:** A silent slowdown becomes a decision instead of an implicit drift. The cost: it forces a decision rather than blocking a change, so someone must make it.
- **check:** The pipeline records start and finish so cycle time is actually measured.

### make-decisions-reversible
- **condition:** Shipping a change whose failure modes you cannot fully foresee.
- **decision:** Build the undo first, using one of three mechanisms: blue/green deployment (two identical environments, revert to the other if the new one misbehaves); feature toggles for canary release to a subset, switched off on unexpected behaviour; or service routing by request context to particular instances.
- **why:** A failure costs a switch, not an outage. The cost is duplicate environments or routing infrastructure.
- **check:** The revert path has been exercised before the change it protects ships.

### garbage-collect-unrouted-services
- **condition:** Teams adopt new service versions at their own pace, and old versions linger with no formal release cycle.
- **decision:** Monitor routes, not just services, and remove any service that received no traffic within a defined interval, as Swabbie does.
- **why:** Dead services stop costing money and adding risk. The cost is the danger of removing a legitimately rare-traffic service.
- **check:** Route-level monitoring exists and the interval is long enough to spare genuinely low-traffic services.

### version-services-internally
- **condition:** An endpoint's behaviour changes in a breaking way and callers must migrate at their own pace.
- **decision:** Of version numbering (a new endpoint name per version, old callers hit the old one) and internal resolution (one permanent name whose logic detects the caller's context and returns the right version), choose internal resolution. Support only two versions at a time, and only temporarily.
- **why:** Callers are not coupled to version numbers. The cost: each extra version adds testing and engineering burden.
- **check:** The service can determine the caller's context. A check can assert at most two live versions. If two are not enough, the change is too big for versioning; renegotiate the contract.

## Migration and evolvability — 18 rules

### last-responsible-moment
- **condition:** A decision could be made now or deferred.
- **decision:** Defer as long as possible and no longer, to maximise the information available for the trade-off. Ask three questions: must this be decided now; can it be deferred safely without slowing any work; what can be put in place now that suffices and is easy to change later. Decide the objective drivers early and order the decisions by them; drivers are not deferrable, implementations are.
- **why:** Deciding at the right point buys the most information. The cost of missing it either way: early decisions overengineer, chasing generality that complicates specific implementations without paying back; late ones miss architectural goals.
- **check:** Deferral is not free: when deferring blocks other work, the moment has arrived. Judgement throughout.

### jit-anticorruption-layer
- **condition:** You must depend on an incidental-plumbing component such as a message queue, a search engine or a cache.
- **decision:** Put it behind an interface you own, extracted just in time rather than up front. Worked case: a web application needing async batch upload took a very simple database-backed queue behind an API instead of the fanciest queue for imagined future needs; a second async need later reused it; after two years the load outgrew it, and since the real async needs were by then clear, switching queues took one developer pair under a week without disturbing anyone. Keep layers to what is needed; preemptive abstraction everywhere hurts understanding.
- **why:** You avoid buying debt through premature complexity and keep swaps cheap. The cost is an interface you maintain.
- **check:** The semantics you need are stable even if the API is not; design the interface around the semantics. Weigh the dependency's benefits against its cost in updates and dependency management. Here an anticorruption layer is a wrapper around a third-party dependency, not a translation between two domain models.

### remove-needless-variability
- **condition:** Parts of the stack can change without your involvement: the OS, the toolchain, developer machines.
- **decision:** Turn them into constants. Use immutable infrastructure, changed only through source and rebuilt on every pipeline run, and give every developer the same machine image, which also lets you add a tool to everyone's setup at once.
- **why:** Environment changes nobody anticipated stop breaking the system, and immutability makes evolution safer, not harder. The cost is declarative definitions for every environment.
- **check:** The environment is expressible declaratively.

### prefer-evolvable-over-predictable
- **condition:** Deciding how much to invest in up-front planning.
- **decision:** Invest in the ability to change rather than in plan accuracy. Unknown unknowns defeat big up-front design, and every architecture ends up iterative; an iterative process just starts sooner.
- **why:** Easy change absorbs surprises no plan foresaw, so nobody needs a crystal ball. The cost is giving up the comfort of a complete plan.
- **check:** The design names its change points. Judgement.

### pull-model-for-dependencies
- **condition:** The build depends on third-party components whose upstream you do not control.
- **decision:** Keep an internal repository as the component store and treat upstream changes as pull requests into it: admit beneficial changes, reject destabilising ones such as a core dependency vanishing. Give that repository its own pipeline that takes the update, builds the affected applications, runs smoke tests on them, and admits the change only if they pass. The lesson from an 11-line package whose removal broke builds worldwide: external dependencies carry costs as well as benefits, and outside forces must never affect build stability.
- **why:** Builds stay stable. The cost is running the store and its pipeline, and it mitigates transitive-dependency risk without solving it.
- **check:** An internal artifact repository exists.

### frameworks-push-libraries-pull
- **condition:** Deciding how urgently to take a dependency upgrade.
- **decision:** Classify by who calls whom: your code calls the libraries it uses, while a framework calls your code and therefore couples to all of it. Update fundamental frameworks (coupling above a set threshold) aggressively, as soon as the release is stable and time can be allocated; update libraries when needed. Never let a fundamental framework fall more than two major versions behind. At design time, choose libraries over frameworks where possible, since they couple less and swap out more easily.
- **why:** Early framework upgrades cost a fraction of late ones. The cost is recurring upgrade time.
- **check:** You can classify the dependency by coupling measurement or by inspection. The classification is measurable; allocating time is not.

### sacrificial-architecture
- **condition:** Entering an uncertain market or proving a concept, unsure which architecture eventual scale will need.
- **decision:** Build one deliberately to throw away; once it exists, the unknowns are known. Successful platforms have gone through several stack rewrites (one marketplace ran on three languages in seven years), and shipping a simple stack first can be what wins the market.
- **why:** Speed to market and learning. The cost is the replacement later.
- **check:** There is an explicit commitment of time and resources to replace it after the market is validated; lacking that commitment, it is simply a poor design with a good excuse. Watch for second-system syndrome, where a small successful system bloats under inflated expectations because nobody wants to discard working code; when restructuring, remove historical compromises first.

### start-with-a-few-large-services
- **condition:** Decomposing a monolith toward services.
- **decision:** Start with a few coarse services, settle where they integrate, and repeat across several restructuring rounds.
- **why:** Coarse services avoid transaction and orchestration problems by keeping more business context inside each one; too-fine components bring orchestration, communication overhead and interdependence. The cost: larger services grow operational difficulty.
- **check:** You understand how the current code is joined. The reason for migrating is better than following a trend; otherwise halt.

### choose-the-partition-axis-deliberately
- **condition:** Identifying new service boundaries during a decomposition.
- **decision:** Pick one of three axes for what you optimise: business functionality groups (mirror the existing capability hierarchy, since team structure shapes the system anyway); transactional boundaries (often the hardest coupling to break; see `transactional-boundaries-set-the-granularity-floor`); deployment goals (release cadence or operational qualities, e.g. marketing wanting far more frequent updates than inventory, each service's health tracked by fitness functions).
- **why:** The seam serves a stated aim. The cost: each axis sacrifices the other two.
- **check:** The chosen axis and its reason are written down. Judgement.

### split-the-ui-early
- **condition:** Partway through a monolith-to-services migration.
- **decision:** Split the interface off from the business layers early, putting a mapping proxy between UI components and the backend services they call.
- **why:** UIs tend to recombine into a monolith because users need one unified interface, and the proxy insulates UI changes from architecture changes. The cost is one more layer.
- **check:** The proxy is the only path from UI components to backend services.

### service-discovery-early
- **condition:** The migration will produce services that must find and call each other.
- **decision:** Build discovery before you need it, usually as a simple proxy that components call and that maps each call to an implementation, so parts can migrate as soon as they are ready.
- **why:** Gradual migration becomes possible. The cost: every added level of indirection makes the services harder to navigate.
- **check:** Count the indirection layers and keep only those that serve the migration.

### naive-partitioning-becomes-a-latency-problem
- **condition:** About to split modules apart into services.
- **decision:** Treat every in-process call you cut as a new integration connection with latency, availability and error-handling costs. Choose seams after examining transaction boundaries and structural coupling, and add fitness functions and consumer-driven contracts at each new integration point.
- **why:** It avoids serious performance regressions. The cost is checks at every new seam.
- **check:** Each new integration point has a check that its contract stays stable.

### refactoring-vs-restructuring
- **condition:** Describing a large architectural change.
- **decision:** Call it restructuring unless external behaviour stays identical. Architecture changes almost always alter both structure and behaviour, and switching patterns switches which qualities are prioritised; leaving an event-driven style chosen for scalability will likely lower scalability.
- **why:** The right word carries the right risk. The cost is a harder approval conversation.
- **check:** If a change sold as a refactoring shifts the prioritised qualities, say the risk is mislabelled before it is approved.

### strangler-fig-with-a-fitness-function
- **condition:** Replacing a legacy system one behaviour at a time while the legacy store remains the source of truth.
- **decision:** Build the new service and run it in production writing to both stores while the legacy one stays the source of truth, paired with `fidelity-fitness-function` to prove the new path matches the old.
- **why:** Replacement proceeds with proof, and it tends to surface undocumented data sources in the legacy system. The cost is double writes.
- **check:** Both stores accept the write without conflict.

### cots-hold-integration-points-to-your-maturity
- **condition:** Commercial off-the-shelf or packaged software is part of the ecosystem.
- **decision:** Hold its integration points to your own engineering maturity; where that is impossible, accept that some parts will evolve less easily. Manage three deficits: incremental change (automation and testing lag, so put logical barriers at the integration points and treat the package as a black box under test); appropriate coupling (an opaque API offering almost enough flexibility, the last-10% problem); fitness functions (too few internals exposed for unit or component tests, leaving coarse behavioural integration tests that need complex environments). The worst case is the vendor database as integration point, where you must take control of it back to evolve at all.
- **why:** The package's limits stay contained. The cost is heavy integration testing.
- **check:** When stuck with necessary package software, build the strongest fitness-function set you can and run it at every opportunity.

### where-to-start
- **condition:** Evolvability is to be added to a running architecture and a first target is needed.
- **decision:** Choose low-hanging fruit (an already-decoupled part off the critical path) to minimise risk for a sceptical organisation, at some cost in value; or highest value first when already committed, when testing how well the techniques fit your ecosystem, or when you want actionable data early. Either way, measure before and after: a demonstration settles more than discussion does.
- **why:** The first target matches what must be proven. The cost: each choice gives up the other's benefit.
- **check:** Testing (`coarse-functional-tests-before-restructuring`) and infrastructure may have to come first: outsourced operations, a hard wall between development and operations, or infrastructure debt. When deployment is hard, every feedback loop stalls.

### coarse-functional-tests-before-restructuring
- **condition:** Restructuring is planned on code with little or no test coverage.
- **decision:** Skip the tests-only project, which management distrusts when features stall. Combine modularity work with coarse functional tests added around a behaviour before restructuring it, proving overall behaviour is unchanged; retrofit unit tests later.
- **why:** Restructuring gets a safety net at once. The cost: coarse tests locate failures imprecisely.
- **check:** The behaviour is observable from outside the code being moved.

### four-reasons-not-to-build-an-evolutionary-architecture
- **condition:** Deciding whether evolvability is worth its cost for a given system; it is not worth it for every project.
- **decision:** Decline for any of four reasons: (1) it is a big ball of mud, where making it evolvable likely costs more than a rewrite (first find whatever modularity exists and restructure around it, then judge the effort); (2) other qualities dominate, since no architecture serves conflicting core goals and one tuned to a single characteristic rightly resists evolution; (3) it is deliberately sacrificial; (4) the business does not expect to exist in a year.
- **why:** Effort is saved where evolvability would not pay. The cost is living with a system that resists change.
- **check:** Treat feasibility as a quality in its own right and ask whether the project should be undertaken at all.

## Framing rules — 8 rules

These settle what kind of system you are building and how much architecture it needs, before the
other groups apply.

### three-step-mechanics
- **condition:** Putting evolutionary architecture into practice on any project, new or existing.
- **decision:** Work through three steps in sequence: (1) name the dimensions that evolution will touch — technical every time, usually data, security, scalability and other relevant qualities — involving business, operations and security; (2) define fitness functions per dimension, usually several each, note in a lightweight place which dimensions need ongoing attention, and decide what may misbehave as each evolves; (3) automate them in deployment pipelines along with provisioning and testing, and keep cycle time short, since new generations of the architecture arrive at the pace cycle time allows. Steps 1 and 2 recur throughout the project, not only at the start.
- **why:** It gives a repeatable path. The cost: steps 1 and 2 stay judgement work.
- **check:** A deployment pipeline exists for step 3.

### evolvability-is-a-meta-characteristic
- **condition:** Someone asks where evolvability sits among the other architectural qualities.
- **decision:** Treat it as a wrapper that protects the others as the system changes (a system designed for scalability must not lose it as it evolves), not as one more quality on the list.
- **why:** Attention moves to protecting the qualities already chosen. The cost: it is empty until those qualities exist.
- **check:** The other qualities are named and measurable.

### architect-and-develop-for-evolvability
- **condition:** Making evolvability a first-class design concern.
- **decision:** Three duties: think in objective measures when analysing qualities; design appropriate coupling and avoid brittleness; treat data and external integration points as first-class (integrate database changes continuously like code, and weigh data dependencies equally with code dependencies). Choose process and tooling for least friction and fastest feedback.
- **why:** Evolvability is designed in rather than hoped for. The cost is attention to data and integration from day one.
- **check:** Data dependencies appear in the same dependency views as code dependencies.

### architect-for-testability
- **condition:** An architecture is hard to test and the difficulty is blamed on the domain.
- **decision:** Treat testability as a design outcome and design for it, mainly through single responsibility: mixing business logic with messaging infrastructure, as in an enterprise service bus, makes neither testable in isolation.
- **why:** Hard-to-test systems tend to be hard to maintain and extend. The cost is separating concerns early.
- **check:** Every fitness function needs a seam to attach to, so an untestable component is ungovernable; record each component without one.

### scale-dictates-the-level-of-architecture
- **condition:** Asked how much design a project needs.
- **decision:** Size the design to the scale: a doghouse needs materials and a start, a fifty-storey building needs design; a site over a simple database needs little, a highly scalable and available site needs careful trade-offs. Ask how little unneeded design you can carry while keeping the ability to iterate; the aim is no useless architecture, not no architecture.
- **why:** It avoids both bureaucracy and under-design. The cost is judging scale honestly.
- **check:** Each design step has a reason tied to the scale.

### no-emergent-architecture
- **condition:** Someone proposes to start coding and let the architecture emerge.
- **decision:** Allow emergence only for simple problems; elsewhere put minimal scaffolding in place first, because architecture is what the other parts attach to and something must exist to begin. There is no perfect architecture, but some styles fit a problem with less resistance and fewer workarounds.
- **why:** It balances the structure long-term goals need against needless formality. The cost is some up-front design.
- **check:** The scaffolding is minimal and each piece serves a long-term goal.

### evolutionary-not-adaptable
- **condition:** Under pressure, choosing between making something work and making it right.
- **decision:** Prefer evolution (changing the architecture in place, protected by fitness functions) to adaptation (keeping the old behaviour and layering new behaviour beside it). Each adaptation cycle adds parallel behaviour and complexity, which is technical debt by construction.
- **why:** It avoids a growing legacy of outdated solutions hidden inside the system. The cost is real change instead of a quick workaround.
- **check:** Adaptation is sometimes right: toggles running competing hypotheses are deliberate, useful debt, provided they are removed once the decision resolves.

### greenfield-is-cheaper-than-retrofit
- **condition:** Deciding when to install evolvability.
- **decision:** Install it at inception: the pipeline exists from day one, checks are easier to plan before code exists and scaffolding for complex ones is already there, and there are no bad couplings to untangle. Retrofit cost depends on three factors: component coupling, engineering maturity, and how easily developers can write checks. Easy change rarely appears later on its own.
- **why:** Turning a big ball of mud into services takes immense effort. The cost of doing it at inception is design work before the product is proven.
- **check:** For an existing system, add flexibility points to the current architecture instead of rebuilding it whole.

## Detectors — 11 rules

Each names a situation that looks right at first and proves a mistake later (an antipattern), or one
that shows itself quickly as a bad path (a pitfall), and gives the exit.

### detector-last-10-percent-trap
- **condition:** Evaluating a low-code or no-code platform, a 4GL, an orchestrator, or any tool promising to remove development complexity.
- **decision:** Evaluate the hardest requirement first, not the easiest. Such tools typically make the first 80% quick, the next 10% possible but very hard, and the last 10% impossible. Find the limits early so alternatives exist for what the tool cannot do.
- **why:** You avoid hitting the wall at 90%. The cost is a less impressive early demo.
- **check:** You know the hardest requirement before the trial. These tools are routinely oversold as a cure-all to stakeholders eager for speed; weigh that when they push.

### detector-vendor-king
- **condition:** An architecture is being built around a vendor product such as an ERP, with gaps to be filled by plug-ins.
- **decision:** Treat every product as one more integration point, even one with broad responsibilities, and insulate it with anticorruption layers, so behaviour that is not useful can be replaced through other integration points.
- **why:** The vendor stops dictating persistence, infrastructure and workflow. The cost is integration work up front; bending your processes to the tool is acceptable only where they are not a competitive advantage.
- **check:** Watch for the terminal state where both sides, having invested heavily, quietly declare success with much of the promised functionality missing.

### detector-reuse-bottleneck
- **condition:** A shared internal component has a dedicated team, and other teams must request features through it.
- **decision:** When the coupling point blocks evolution, break it by forking or duplication: any team may fork the component and own its changes, or opt out entirely. Reuse of a technical component fails once its team cannot keep pace with the change around it.
- **why:** Teams stop queueing behind a silo that ties up strong developers on a backlog. The cost is duplicated maintenance.
- **check:** The forking team accepts ownership of its fork. Keep building reusable assets, but re-evaluate them continually to confirm they still deliver value.

### re-evaluate-past-correct-decisions
- **condition:** An old decision, correct at the time, now yields poor results.
- **decision:** Treat it as the ecosystem having moved (e.g. users shifting from installed clients to the browser), not as an original error, and continually re-evaluate whether each prioritised quality still adds value.
- **why:** Old decisions get revisited before they become antipatterns. The cost is recurring review time.
- **check:** A record exists of why the decision was made and under which conditions; without the conditions, the re-evaluation has nothing to compare against. Pair with `temporal-fitness-function` for a time-based trigger.

### detector-leaky-abstraction
- **condition:** A fault surfaces as an incomprehensible error far from where it began.
- **decision:** Assume every nontrivial abstraction leaks, and that a low-level break can travel up the stack and surface as a cryptic UI error. Identify the fragile joints in the stack and state the invariants each key integration point must keep, as fitness functions in the pipeline, so leaks are caught where they start.
- **why:** Low-level breaks stop cascading unseen. The cost is knowing the stack deeply.
- **check:** You can name the fragile joints. Keep working knowledge of at least one layer below your usual one, which grows harder as the stack specialises.

### detector-resume-driven-development
- **condition:** An architecture choice is justified by the technology instead of the problem.
- **decision:** Understand the problem domain first, then choose the architecture; reject frameworks and tools added for the sake of having used them.
- **why:** The architecture serves the problem. The cost is passing on appealing technology.
- **check:** Each chosen technology names the problem it solves.

### detector-metawork
- **condition:** A team builds infrastructure that already exists as open source, or an architect leans toward building over using.
- **decision:** Use what exists, and switch to an available equivalent once one appears, even if building your own was right when nothing existed. Treat the pull toward building frameworks, which is more fun than using them, as a bias. Worked case: a homegrown application server and web framework kept the best developers on plumbing maintenance for a decade.
- **why:** Effort goes to the product, not the plumbing. The cost is accepting minor differences in approach.
- **check:** Price every trade-off before a build that cannot be undone.

### just-enough-governance-three-stacks
- **condition:** An organisation standardises on one technology stack for consistency and interchangeable staff.
- **decision:** Standardise on three stacks — simple, intermediate, complex — and let each service's requirements pick one. A single standard forces every project to carry the complexity of the most demanding case, multiplying effort for no benefit. Worked instance: small = Ruby on Rails with MySQL; medium = Go with Cassandra, MongoDB or MySQL depending on data needs; large = Java with Oracle.
- **why:** Small projects stop paying for industrial-strength tools. The cost is supporting three stacks.
- **check:** Services are decoupled enough for a per-service choice; in a monolith governance choices hit everyone and this rule does not apply. The single-stack model arose when infrastructure was expensive commercial software; that premise has expired.

### detector-reporting-on-the-system-of-record
- **condition:** Reports are being built straight onto the operational schema because the data is right there.
- **decision:** Decouple them: populate each domain's system-of-record database through an event stream or message queue inside its quantum, with eventual consistency instead of transactions, and have separate reporting services consume the same stream into a denormalised reporting database.
- **why:** Schema changes stop breaking reports, and different uses get different abstractions free of coordination. The cost is eventual consistency and an event stream. For the current form, see `data-product-quantum`.
- **check:** An event stream or durable queue exists. A check can detect reporting connections to the operational schema.

### detector-excessively-long-planning-horizon
- **condition:** Heavy effort has gone into validating assumptions before any code exists.
- **decision:** Recognise that planning effort buys attachment, not accuracy: sunk cost turns into defending the plan against evidence. Break large programmes into small early deliverables that test both the architecture and the infrastructure, and avoid technologies requiring big up-front investment (large licences, support contracts) before user feedback confirms the fit.
- **why:** Decisions are made with more information and are easier to drop. The cost is less certainty up front.
- **check:** For each plan, name the evidence that would make you discard it; if nobody can, the attachment is already there.

### product-customization-multiplies-fitness-functions
- **condition:** Sales wants per-customer variants of the product.
- **decision:** Price customisation in tests and fitness functions, not only in features. Three techniques on a cost spectrum: a separate build for each customer (a branch and tag per client); feature toggles left on permanently (variants per client, or a free tier); product-driven customisation exposed in the UI, which makes every option a permanent feature. Toggles and customisation multiply the paths through the product and the checks needed to protect them.
- **why:** The real cost becomes visible. Customisation does impede evolvability.
- **check:** Price it rather than refuse it: the estimate includes the added test scenarios and checks per permutation.

## Team, organisation, and enterprise governance — 16 rules

Team boundaries, team types and cognitive load belong to the ownership rules. This group keeps the
mapping from architecture to teams and the fitness functions that operate across an enterprise.

### inverse-conway-maneuver
- **condition:** The team structure and the target architecture disagree.
- **decision:** Shape the teams like the target architecture, because systems tend to copy the communication structure of the organisation that builds them. Retaining teams per technical layer — frontend, backend, database — during a move to a distributed architecture multiplies cross-layer coordination for every domain change. Narrowing a person's scope narrows the designs they can pursue, and it is hard to change what someone else owns.
- **why:** The target architecture becomes easier to reach. The cost is reorganisation.
- **check:** You can actually restructure the teams. When forces outside architecture fix the team structure, shape the architecture to fit those teams rather than fight a losing battle.

### cross-functional-by-default
- **condition:** Forming a team around a domain.
- **decision:** Put every role needed to design, build and deploy the service on the team: architecture (design out bad coupling; a well-modularised monolith can do this too); business analysts (co-located for fast feedback in complex domains); data (DBAs, analysts and scientists facing new granularity, transaction and system-of-record questions); developers (broader, full-stack); designers (with their team, plus time with other teams' designers for a consistent UI); operations (automated provisioning and deployment); product managers (freed from coordinating many technical teams); testing (cross-domain integration, environments, contracts).
- **why:** Nobody waits on another silo for a database change or a machine. The cost is roles that are often scarce.
- **check:** The roles exist; when a skill is scarce, rotate one shared specialist across teams.

### organize-around-business-capabilities
- **condition:** Choosing the axis along which to divide teams.
- **decision:** Divide teams by business capability, not job function, so the team boundary matches the usual unit of change (a customer entity, not a technical layer).
- **why:** Domain changes stay inside one team. The cost is losing the shared-resource efficiency that once drove functional teams, a constraint open source has largely removed.
- **check:** Layering may remain inside a domain for separation of concerns; the layers sit inside the domain, not above it.

### cognitive-load-caps-capability
- **condition:** A team aligned to a business capability that turns out to be large.
- **decision:** Cap capability alignment by cognitive load: one payment scheme may suit a team, while five or six concurrent schemes likely exceed it before technical complexity is even counted. Exit: split into several stream-aligned teams, or add a complicated-subsystem team for one scheme while a stream-aligned team owns the end-to-end journey.
- **why:** Teams stay able to deliver. The cost is more teams and more interfaces between them.
- **check:** Assessing cognitive load and choosing team types belong to the ownership rules; go there for anything beyond this split.

### team-size-by-connection-count
- **condition:** Deciding how large a team may be.
- **decision:** Count communication links, `n(n − 1) / 2`: 14 people make 91 links, 50 make 1,225. Keep teams small and cross-functional, with the people who build a thing also running it, and keep connections between teams few; where integration points do exist between teams, guard them with fitness functions.
- **why:** Communication cost falls, and silos stop inflating the number of collaborators. The cost is more teams to coordinate at their edges.
- **check:** The arithmetic automates; the restructuring does not.

### product-over-project
- **condition:** Work runs as time-boxed projects that finish and pass their code to a separate maintenance group.
- **decision:** Organise as products: they live indefinitely so the team stays with its product, each has an owner who advocates for it and manages requirements, and the team is cross-functional.
- **why:** It fixes three problems: maintenance after the team has moved on, developers caring less about quality when cut off from how their code runs, and decisions skewed by a project's end date. The cost is a standing team per product.
- **check:** Each product has a named owner and a standing team.

### ownership-changes-behaviour
- **condition:** Quality is imposed on the team from outside instead of being something the team owns.
- **decision:** Shrink the distance between whoever writes the code and whoever is woken when it fails, by having one team carry both.
- **why:** Cross-silo blame ends and ownership grows. The cost is on-call duty for the people who build.
- **check:** The team actually carries the operational consequence. The mechanism is one person answering to a colleague; an agent does not reproduce it.

### automation-creates-the-headcount-you-thought-you-lacked
- **condition:** A shared operations function is a bottleneck and hiring looks like the answer.
- **decision:** First inventory the manual work for accidental complexity (misconfigured machines, a mix of hardware brands, other fixable faults) and automate it. In the worked case this freed enough people to embed an operations engineer in every project permanently, with no new hires and no major change in roles.
- **why:** Capacity appears without hiring. The cost is the automation effort.
- **check:** The manual work can be inventoried. Partly automatable.

### enterprise-slot-in-every-pipeline
- **condition:** A zero-day vulnerability is announced in a framework or dependency, and you must know within hours which systems are affected and stop them shipping.
- **decision:** Reserve a slot in every project's pipeline where a central function can deploy fitness functions. Day to day it holds routine checks (no passwords stored in databases); on a zero-day it inserts a test for the affected framework and version that fails the build and notifies the central function. A known breach shows the cost of lacking it: patch released on day 0, warning on day 1, a scan on day 8 that found most but not all affected systems, the missed ones patched on day 144 after the breach was spotted, disclosure on day 184. Extend the slot to supply-chain metadata: alert on any change to code, database schema, deployment configuration or the checks themselves.
- **why:** One insertion reaches every system at once. The whole cost is uniform pipelines, paid in advance.
- **check:** Every project runs a pipeline with enough shared structure for one inserted stage to work everywhere; if not, you find out during the incident. At one operator with several products, this is one shared pipeline template every product inherits, with a stage amended once.

### ea-governs-capabilities-not-technology
- **condition:** An enterprise architecture function chooses technology for delivery teams.
- **decision:** Have it define platform-level fitness functions that encode long-term strategic goals, and let domain architects choose technology inside those guardrails. Enterprise architects sit far from implementation, fall behind on current technology, and tend to impose a pet fear from one past incident on every design.
- **why:** Strategy is enforced while decisions sit with the people closest to the code, which also grows the next generation of architects. The cost is enterprise architects writing checks instead of picking tools.
- **check:** The qualities involved have been decomposed until measurable (`decompose-until-measurable`). Partly automatable.

### platform-hides-implementation-details
- **condition:** Applications throughout the organisation call services in many parts of the enterprise directly.
- **decision:** Interpose platforms that expose a consistent, slow-changing API through contracts and hide how the organisation solves each problem.
- **why:** Implementation coupling stops leaking into applications, so the whole becomes less brittle. The cost is a platform contract someone must own.
- **check:** Someone owns the platform contract and can keep it slow-changing.

### carve-bounded-context-with-fitness-functions
- **condition:** A layered (technically partitioned) architecture contains a bounded context, and layering's cross-cutting reuse conflicts with the context's ban on it.
- **decision:** Keep the layers and forbid coupling across the context with fitness functions placed where it matters. Splitting the domain's parts by technical feature does no harm; other applications coupling to those details is what must be blocked, by the locality rule of connascence.
- **why:** Separation of concerns stays without damaging cross-context reuse. The cost is writing context-specific checks, which depend on the assets you want to protect.
- **check:** The bounded context is identified and its edge expressible in package or namespace terms. Naming the context is the `domain` door's question.

### quantum-count-cost-sweet-spot
- **condition:** Choosing service granularity with cost in view.
- **decision:** Expect cost per quantum to fall as quanta multiply (clearer separation of concerns, and operational chores that must be automated once there are many) and then rise when coordination dominates at extreme granularity (a service per form field). The sweet spot is specific to each company: one in a fast market may want small quanta, another may rightly keep a monolith for simplicity. Declare the quantum size explicitly; it sets the lower bound on incremental change, and smaller quanta tend to shorten cycle time.
- **why:** Granularity becomes a priced choice. The cost is estimating coordination overhead honestly.
- **check:** The quantum size is written down; an undeclared size is a decision made by accident.

### hypothesis-driven-development
- **condition:** A feature is about to be built because an analyst thinks it is a good idea.
- **decision:** Restate it as a hypothesis with a number and an experiment (bigger sale images will raise those items' sales by 5%), run A/B tests, and tally the results. Each hypothesis names what to test, which experiments settle it, and what validation means for later work. Features that each made sense alone can together degrade the experience; in one case three UI versions were built and users chose. Run experiments long enough for significance, and prefer measured outcomes to pop-up surveys.
- **why:** Features earn their place by evidence. The cost is the machinery behind it: evolutionary architecture, modern DevOps, changed requirements practice, and running several versions at once (e.g. routing across live instances).
- **check:** Two versions can run side by side; if not, that is an architecture problem to fix first.

### culture-audit-questions
- **condition:** You need to know whether a team can sustain evolutionary architecture, beyond having the tooling.
- **decision:** Ask six questions: whether everyone knows what fitness functions are and weighs new tools by their effect on writing new ones; whether teams measure how well systems meet them; whether engineers understand cohesion, coupling and connascence; whether teams discuss which domain and technical concepts belong together; whether teams choose by ease of change rather than by what they want to learn; and how teams handle business change, struggling with small changes or spending too long on them. If answers are poor, change the process, since people behave as they are measured: require a short experiment measuring the coupling any new dependency adds before adoption, and ask in code review how many places would change if a new external integration point changed.
- **why:** It exposes gaps that tooling hides. The cost is process changes and review time.
- **check:** Guard against overengineering: do it once, tolerate the duplicate the second time, refactor on the third.

### make-room-for-experiments
- **condition:** A team is fully committed to a delivery plan and never experiments.
- **decision:** Pick from six mechanisms: bring in outside ideas (conferences, external advisers); explicit continuous improvement led by those closest to the problem; spike and stabilise (a throwaway solution to learn a hard problem fast); innovation time (a share of working hours, hackathons, 24-hour ship days); set-based development (prototype several approaches in parallel within a few days); connecting engineers with users (A/B tests, watching users perform tasks). Judge success by how many experiments fit into a day.
- **why:** Learning speed rises. The costs: a spike trades quality for speed, and parallel options cost extra work up front while revealing real constraints of tooling and approach.
- **check:** A spike never ships to production; shipping one turns a learning device into debt.
