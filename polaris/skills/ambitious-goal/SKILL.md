---
name: ambitious-goal
description: ◇ Refine a feature or epic into a clear outcome and verifiable Definition of Done. Use when ambition, scope or acceptance evidence needs sharpening before work is recorded or executed.
version: 1.0.3
user-invocable: true
auto: true
job: define the intended result and proof of completion for an epic or feature issue
when_not: routine bugs, mechanical tickets, implementation or runtime goal management
lifecycle: outcome and DoD returned to the caller; issue-contract records them in the existing tracker when authorized
invokes: []
invoked-by: [issue-contract, human]
io: idea or feature request plus existing evidence -> outcome, scope, DoD and regression checks
status: active
---

# Ambitious Goal

Turn ambition into a result an agent can deliver and someone else can verify.
Here, **goal** means the desired outcome of an epic or issue; its **DoD** names
what must be true, with evidence, to call that outcome complete. No runtime goal.
Work in the user's language. A short request can produce a short answer.

## Recover and sharpen the objective

Read applicable instructions and the relevant existing issue, specification, code
or raw evidence. Reuse existing work and preserve ownership. Distinguish implemented,
demonstrated, integrated and released; donor code is an input, not a shipped feature.
Name who benefits, what changes for them and the decision or action this enables.
Go one level above the requested task when that clarifies its purpose.

If an answer would change outcome, scope or acceptance, ask **one question at a time**.
Retrieve answers already available in context before asking. When useful, offer two
or three materially different directions, explaining the tradeoff and recommending
one. Wait for the answer before committing to that unresolved direction; continue
independent retrieval meanwhile. Use the reply to refine the outcome and ask again
only if a material gap remains. Clear requests skip the interview. No question quota.
A broader ambition stays an option until chosen; do not silently add modules.

## Deepen before expanding

Once material intent gaps are resolved, apply the user-provided prompt:

> I want a deeper version of this task, not a bigger one. Before rewriting it: (1) say what a top professional in this field would do here that I’m not asking for; (2) name the rawest material they would start from instead of what has already been digested for me; (3) name the specific methods and tools they would use; (4) say what, other than you or me, would show the result is right. Then rewrite my prompt to ask for exactly that.

Answer concretely, then rewrite the objective. Name actual raw artifacts, methods
and available tools. Separate observations, inference and missing sources; explain
the smallest acquisition step for unavailable material. Retain original constraints.
Professional vocabulary, role-play or a second model agreeing is not independent proof.
Respect privacy, authorized data and environment boundaries.

Check four lenses without creating four workstreams:
- Speed: shorten time to the same verified result.
- Altitude: clarify the outcome behind the artifact requested.
- Depth: use raw evidence and appropriate methods to resolve the hard uncertainty.
- Range: borrow another discipline only if it changes a concrete decision.

An ambitious target is a hypothesis until feasibility is supported. Separate required
acceptance from optional stretch goals. Preserve user-given targets, flag contradictions,
and never invent baselines, dates, owners, budgets or accuracy thresholds. Without a
credible number, use an observable condition and say what still needs measuring.

## Define the outcome and DoD

Return the smallest useful contract, ready to fit an existing issue or epic:

```markdown
<Who benefits, what becomes possible, why it matters; relevant source/evidence links.>

## Scope
<Included capability, existing work to reuse and material exclusions.>

## DoD
- <Given representative input/context, the observable result required.>
- <How that result is independently verified, against which source or expectation.>

## Regression checks
- <Existing behavior to preserve and relevant error/edge cases to exercise.>

## Open dependencies
<Only material unknowns or prerequisites, with the next proof or decision needed.>
```

Adapt headings to the caller's language/template; omit empty sections. The fields
are thinking aids, not a mandatory long form. A small feature can be a few bullets.
Each DoD criterion pairs an observable result with evidence that could refute it.
Do not use completed tasks, documents written or code imported as substitutes for
user benefit. A representative positive journey must succeed; rejecting all inputs,
returning only unknowns or passing only negative cases cannot satisfy a product DoD.
Separate evidence already collected from tests still required. Name the environment
that counts as complete: candidate, integrated, released or accepted by actual users.
Do not invent customer acceptance or silently substitute one stage for another.

For an epic, state the integrated outcome across its children. If phases are needed,
give each one an observable result, bounded ownership, prerequisites, independent
verification and integration responsibility. Preserve existing assignments; proposed
roles are not launched agents. Check coupling, data writers, transactions and shared
interfaces before suggesting parallel lanes. Gate only the affected phase, not an
entire epic on unrelated research. Worktrees do not isolate shared databases/staging.

When a core hypothesis is unproved, name the smallest proof: hypothesis, representative
input, positive and negative expectations, safe boundary and stop condition. Its
result is VALIDATED, REJECTED or INCONCLUSIVE. An experiment can settle a question
without delivering the product; keep research completion separate from product DoD.
Describe the proof here; execution needs its own existing authorization. Follow local
evidence gates before a detailed implementation roadmap. Replan on contradictory
evidence rather than silently lowering acceptance or persisting without a bound.

## Handoff and boundaries

- `issue-contract` may call this skill for a feature or feature epic whose outcome,
  scope or DoD needs refinement, then use the result in its normal short ticket.
  Already clear feature contracts need no extra interview. Bugs and mechanical
  tickets keep the existing direct path.
- Return to the caller; this skill neither calls `issue-contract` back nor publishes
  tickets. It does not invoke any goal runtime, create/resume goal
  state, launch agents, implement features or deploy anything.
- Use the existing issue/spec as the destination when persistence is requested.
  The owning workflow handles tracker writes under existing authorization. Do not
  create a parallel goal file, local dossier or tracker. Repository output rules apply.
- Keep decisions already made; refine missing intent or proof, not the whole project.

## Where this goes

This skill produces: **none (standalone files)**. Return the outcome and DoD to the
caller; the owning workflow places them in the existing issue/spec under the host
repository's output rules. No additional goal document is created.

## When NOT to use

Routine bug reporting, mechanical edits, execution, status bookkeeping or runtime
goal management. If the user is comparing similar skills, explain their differences;
do not invoke them merely because they were mentioned as alternatives. A complete existing contract can pass through unchanged.

## Verification before returning

- [ ] Outcome, beneficiary and scope are clear; material answers were not guessed.
- [ ] DoD includes useful positive behavior and independently checkable evidence.
- [ ] Relevant regression checks, remaining unknowns and completion stage are explicit.
- [ ] No invented proof, runtime state, duplicate artifact or unauthorized execution.

See [mechanisms](references/sources.md) for the mechanisms and their limits, and
[bypass cases](references/bypass-test.md) for behavioral checks and evidence limits.
