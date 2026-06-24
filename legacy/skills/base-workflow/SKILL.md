---
name: base-workflow
description: >
  The base development method — apply it BEFORE and WHILE building anything that
  touches code: a feature, a bugfix, a refactor, any change. It is not optional and
  not a formality: any coding task goes through it. Trigger it whenever you're about
  to implement, fix, refactor, extend, or change code — even when the user just says
  "add X", "fix Y", "change Z", "make it do W", or pastes a stack trace. It enforces:
  understand the code first (code-graph + dependencies), a spec with error paths and
  fallbacks following clean architecture, strict TDD (test fails first), 360° tests,
  the simplicity limits, fresh-eyes review, a real test, and that fixes hold (root
  cause, not patch). This is the BUILD method; the team-workflow (branch / PR / merge
  rules) is a separate concern. Use this first, by default.
---

# Base Workflow

The default way to build. Complexity is the enemy — aim for software simple enough
that any engineer (or AI) can hold the whole thing in one session.

> **Steps are graded with RFC 2119 keywords** — **MUST** (hard gate, no exceptions),
> **SHOULD** (strong default, deviate only with a reason), **MAY** (optional). The
> grade is the point: know what's a gate versus a judgment call.

Any change that touches code **MUST** go through this. **Depth scales with size** (a
one-line fix is light), but the **order MUST hold**.

## The arc

1. **Understand** — you **MUST** read the existing code with code-graph (cgc /
   codebase-memory) and map dependencies + blast radius before writing new code; you
   **SHOULD** brainstorm options and weigh them.
2. **Design — the spec** (the *output* of step 1, not the start). It **MUST** have:
   the happy path **and** the error paths; an explicit **fallback** per failure mode;
   it **MUST** fit clean architecture; it **SHOULD** carry measurable acceptance
   criteria. Then you **MUST** plan it into subtasks.
3. **Build** — strict TDD + 360° tests + the simplicity limits (below).
4. **Verify** — you **SHOULD** get **fresh eyes** (clean-context sub-agent, or a
   different model: Codex / Gemini); you **MUST** run a **real test** (staging, not
   just unit) before calling it done.
5. **Ship** — branch / PR / real-test gate / merge / deploy → the **team-workflow**
   standard. Separate concern.

## TDD — MUST

You **MUST** write the test first (**RED** — watch it fail; that proves it validates
the requirement) → **GREEN** (minimum code to pass) → **VALIDATE** (lint +
type-check + full suite, coverage ≥ 80%). **No code ships without a test that failed
first.**

## Bug fixes — MUST, plus durability

1. You **MUST** diagnose the test gap — if tests pass but the bug exists, the tests
   are incomplete. Name what they missed.
2. **RED** — a failing test that reproduces the exact bug.
3. **GREEN** — the fix.
4. **VALIDATE** — the **full** suite (catch regressions) + lint + type-check.

When the same file / bug / area keeps coming back, you **MUST** root-fix the
mechanism, not patch the instance, and **SHOULD** add a fail-first eval on the
**failure class** (blind-error / timeout / null / parse) so it can't recur. KPI:
*did this file stop coming back for bugs?*

## 360° tests — SHOULD

You **SHOULD** push past the happy path: edge cases, **real** inputs (not invented
ones that happen to pass), and exactly the failure classes the spec named. Reason
about coverage more than once.

## Simplicity limits — MUST (every file)

- **≤ 20 lines / function** · **≤ 3 params** · **≤ 2 nesting levels** · one
  responsibility · descriptive names over comments.
- **≤ 200 lines / file** · **≤ 10 functions / file** · one primary purpose.
- Before completing a file you **MUST** count lines / functions / params. Over the
  limit → **split now**; you **MUST NOT** defer it.

## Clean architecture — MUST

Domain **MUST** have **zero imports** from infra/adapters · ports & adapters · one
use case = one class · you **MUST NOT** bypass an abstraction (don't hit the DB when
a port exists) · new capability = new port + adapter.

## Anti-patterns — MUST NOT

global state · magic numbers/strings · deep nesting · long parameter lists ·
comments explaining *what* (rename instead) · dead code · copy-paste duplication ·
god files · circular dependencies · premature optimization · large PRs · mixing
refactor with feature in one commit · silent failures.

## Quality & security gates — MUST

- Coverage **MUST** be ≥ 80% (the functional core → 100%); CI blocks below.
- Pre-commit **MUST** run: lint (auto-fix) + type-check + tests.
- No secrets in code · `.env` git-ignored · no secrets in `VITE_*`/`NEXT_PUBLIC_*` ·
  validate input at boundaries (Zod/Pydantic) · parameterized queries only.

---

> Apply this by default, before any "add X / fix Y / change Z". **Build = this.**
> Tiny change → run it light and fast, but in this order. Shipping the result
> (branch, PR, real-test gate, merge, deploy) → the **team-workflow** standard.

## Deeper reference (load when needed)

- **`references/execution.md`** — exact RED/GREEN/VALIDATE commands per stack, the
  atomic-todo format, and the bug-report format with the TDD execution log.
- **`references/examples.md`** — worked examples: a feature built end-to-end, and a
  bug fixed with the diagnose→RED→GREEN→durability discipline.

## Editing this method

This skill **is** the working method — the single source. To change how you build
(add a rule, tighten a limit, encode a lesson), edit this skill, grounding the
change in a **real example** of what went wrong or right. Don't fork the method into
prompts or docs; change it here, and every repo picks it up.
