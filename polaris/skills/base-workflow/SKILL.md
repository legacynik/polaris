---
name: base-workflow
description: ◇ The build method — apply it before and while writing any change that touches code, a feature, a bugfix, a refactor, "add X", "fix Y", a pasted stack trace. Fixes the order (understand, spec, test-first, verify, ship), routes each gated step to the skill that owns it, and takes every threshold from the repository's own rules.
version: 0.3.0
user-invocable: true
auto: true
lifecycle: the step-2 spec, when written, lives where the host repository keeps specs and closes with the work item that consumes it; the evidence of each gated step is produced and drained by the skill the step routes to (tdd-dev RED log, real-testing verdict, critic ledger, architecture Decision)
invokes: []
invoked-by: [human]
io: in - one code change (feature, defect, refactor) in a repository → out - the order of steps and the repository's declared thresholds; each gated step's evidence is emitted by the skill it names
status: draft
---

# Base Workflow

## Overview

The default way to build. Complexity is the enemy: aim for software simple enough that any
engineer, or agent, can hold the whole thing in one session. This skill fixes the **order** and
the **method**; the gates live in the skills it names (`tdd-dev`, `bugfix`, `architecture`,
`critic`, `real-testing`, `git-power`) and the **numbers** live in the repository you work in.

> **RFC 2119 grading** — **MUST** is a hard gate, **SHOULD** a strong default you leave only with
> a stated reason, **MAY** optional. Know which is which.

Depth scales with size — a one-line fix runs the arc in a minute — and the **order always holds**.

## Where this goes

This skill produces: **spec (only when the step-2 design is written down)**. It lands where the
host repository's output map (`outputs:` in its config) or its docs place specs; the task list
lives in its tracker. Every other artifact is emitted by the skill the step routes to.

## When to use

Before and while implementing, fixing, refactoring, extending or changing code, including when
the request is only "add X", "fix Y", "make it do W" or a pasted stack trace.

## When NOT to use

- **Branch, commit, PR, merge, deploy** → `git-power` and the repository's `CONTRIBUTING.md`.
- **A typo, a doc line, a config value with no behaviour** → make the edit directly.
- **A throwaway prototype a human authorised on the record** → the prototype's own rules.
- **Generated code** → apply the arc to the generator.
- **Deciding an architectural commitment** → `/architecture`; this skill says when to call it.

## The arc

1. **Understand.** You **MUST** read the existing code and map dependencies and blast radius
   before writing: use a code-graph tool when the harness has one (find symbol, find references),
   otherwise `git grep` plus reading the callers. A census uses a script; the graph or the reading
   verifies the survivors. You **MUST** look for prior art first (the repository's docs, `git log`,
   an existing helper) so it is extended, not rebuilt. You **MUST** read the repository's declared
   rules (*Thresholds*) and the accepted Decisions governing the components you touch.
2. **Design — the spec** (the output of step 1). It **MUST** carry the happy path **and** the
   error paths, an explicit **fallback** per failure mode, and **SHOULD** carry measurable
   acceptance criteria. Break it into small tasks. A change that moves a boundary, an interface,
   a data contract or a dependency direction goes through `/architecture` before building.
3. **Build** — test-first through `tdd-dev`, 360° tests, the simplicity ladder, the thresholds.
4. **Verify** — fresh eyes through `critic` (fresh context, or a different model) and a
   real-product verdict through `real-testing`, staging or equivalent, before calling it done.
5. **Ship** — branch, PR, real-test gate, merge and deploy follow the repository's
   `CONTRIBUTING.md` (root or `docs/`) for each kind of work; commits and PR boundaries go through
   `git-power`.

## Thresholds — the method is fixed, the numbers belong to the repository

You **MUST** apply the limits the repository **declares**, in this order of authority:

1. the repository's **`CONSTRAINTS.md`** (root or `docs/`): what "good enough to ship" means
   there, as numbers a command checks (floor, suppressions, test rules, size limits, exceptions);
2. accepted Decisions that govern the component (`decisions/`, or the repository's own register);
3. the repository's `AGENTS.md` / `CLAUDE.md` and `.claude/rules/`;
4. when the repository declares nothing: **≤ 20 lines per function, ≤ 3 parameters, ≤ 2 nesting
   levels, ≤ 200 lines and ≤ 10 functions per file**, coverage ≥ 80% (the functional core → 100%).

A declared measure replaces the default for that measure (cyclomatic complexity ≤ 10 instead of a
line count, say); the two never stack. The change that was failing a constraint keeps the
constraint intact; an exception is a row in the repository's Exceptions table with an owner and a
date. Before completing a file, measure it against the threshold that applies. Over the limit →
split now, or cite the declared exception.

## Simplicity — the ladder

Run it **after** you understand the problem. Stop at the first rung that holds:

1. Does this need to exist at all? A speculative need is skipped, in one line.
2. Is it already in this codebase? Reuse the helper, type or pattern that lives here.
3. Does the standard library do it?
4. Does a native platform feature cover it (DB constraint, CSS, a framework primitive)?
5. Does an already-installed dependency solve it? A new dependency earns more than a few lines.
6. Can it be one line?
7. Only then: the minimum code that works.

**A bug fix is a root-cause fix in the shared function.** List every caller of the function you
are about to change; one fix where all callers route through is both the smaller diff and the one
that leaves every sibling caller fixed too.

## Architecture while coding

Commitments are made in `/architecture` and recorded as its Decision records. While you build:

- **Dependencies point where the repository's `ARCHITECTURE.md` says.** Go through the
  abstraction the architecture declares (the port, when one exists, over a direct DB call).
- **Modules stay out of dependency cycles.** Ask `/architecture` for the cycle measure on the base
  and on your head: the metric is the **modules inside non-trivial strongly connected
  components**, never the number of cycles — merging two cycles into one lowers the count and
  worsens the code. Your change keeps that number equal or lower.
- **A change that moves a boundary** — an interface, a data contract, a dependency direction, a
  schema under separately deployed readers — goes through `/architecture decide` before the code
  lands. A change that contradicts an accepted Decision is a superseding Decision, written as one.
- **The record threshold is one question:** if someone reversed this in six months without knowing
  it existed, would it cause harm? Yes → a Decision through `/architecture`. No → an issue (the
  *how* of a direction already taken) or the session log.

## Test-first and 360°

- **TDD — MUST, through `tdd-dev`.** One behavioural test through the public seam, its RED
  recorded **before** any production change, GREEN on the unchanged test, then the
  repository-authoritative regression suite, lint and type-check. Every shipped line has a test
  that failed first. Commands per stack: `references/execution.md`.
- **360° — SHOULD.** Past the happy path: edge cases, **real** inputs, and exactly the failure
  classes the spec named. Reason about coverage more than once.

## Bug fixes and durability

A bug goes through `bugfix` (find without assuming → fix through `tdd-dev` → prove the consequence
→ rewrite the tests that lied). First name the test gap: when the tests pass and the bug exists,
say what they missed. Durability:

- When the same file, bug or area keeps coming back, you **MUST** root-fix the mechanism, and
  **SHOULD** add a fail-first check on the **failure class** (blind error, timeout, null, parse).
  KPI: did this area stop coming back?

## Phase calibration — before choosing patch vs rewrite

The minimal-diff default is calibrated for mature production systems; a product in design phase
needs the opposite default. The failure it prevents: a month of compensation PRs orbiting two
roots an audit had already named.

- **Design phase (pre-scale, few or no users): the root rewrite is the default** and a patch
  justifies itself with one of three reasons — safety of active users (an existing lock stays
  until its replacement lands), data integrity, or a dated external blocker. "Smaller diff" is
  the bias this rule corrects, so it is never the reason.
- **Rewrite onto the mature or native primitive** (framework, official stack) rather than a
  parallel homegrown build.
- **Mature/production phase:** minimal-diff again, and a rewrite goes through `/architecture`.
- An incident patch **MUST** name the root issue with an owner and a date.

## Quality and security gates — MUST

Pre-commit runs lint (auto-fix), type-check and tests · secrets stay out of code · `.env` is
git-ignored · client-exposed env vars (`VITE_*`, `NEXT_PUBLIC_*`) carry no secrets · input is
validated at boundaries (Zod / Pydantic) · queries are parameterized · every failure is surfaced.

Keep the code plain: explicit state, named constants, shallow nesting, short parameter lists,
names that explain (rename instead of a *what* comment), one responsibility per file, small PRs,
refactor and feature in separate commits.

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "It's a small change, I'll skip reading the callers." | The smallest change in the wrong place is a second bug. |
| "The default says 20 lines, the repo says complexity ≤ 10 — I'll satisfy both." | The repository's declaration replaces the default. |
| "I'll guard it in the caller the ticket names." | Every sibling caller stays broken. Fix the shared function. |
| "Cycle count went down, so the graph is better." | Merging cycles lowers the count. Measure modules inside SCCs. |
| "I'll write the test after, it's obvious." | A test that never failed proves nothing; `tdd-dev` refuses it. |
| "This interface change is internal." | Reversibility is the test. Run `/architecture`. |

## Red flags

- Production code edited before a RED is recorded.
- A new helper that already exists two directories away.
- A threshold quoted from memory instead of from the repository's rules.
- A boundary moved with no Decision behind it.
- "Done" with no `real-testing` verdict and no fresh-context review.

## Verification

- [ ] Prior art searched and the code read; callers of every changed function listed.
- [ ] The thresholds applied are the ones the repository declares, cited by file.
- [ ] RED recorded through `tdd-dev` before the change; GREEN and the regression suite pass.
- [ ] Modules inside SCCs on head ≤ base.
- [ ] Any moved boundary has an `/architecture` Decision.
- [ ] `critic` from fresh context and a `real-testing` verdict on the served commit.

## Deeper reference (load on demand)

- `references/execution.md` — RED/GREEN/VALIDATE commands per stack, atomic task and bug formats.
- `references/examples.md` — a feature end-to-end and a bug fixed with durability.
- `references/bypass-test.md` — the ways to skip this method, and what catches each.

## Editing this method

This skill is the build method — the single source. Change it here, grounded in a real example of
what went wrong or right, with a line in the suite `CHANGELOG.md`. Per-repository **numbers** go in
that repository's rules, which this method already reads.
