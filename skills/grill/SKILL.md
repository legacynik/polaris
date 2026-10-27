---
name: grill
description: ◇ Polaris — Discover, phase 1. Grill an idea against the repo's docs, earlier ideas, how other repos solved it and what is in or out of scope; list every assumption with how to test it; propose the size; open the plan file at status discovery. Use for "grill this idea", "clarify this feature", "challenge this spec" or an ambiguous request before planning. Requires git; bd to park an idea or file Tiny work.
version: 2.1.0
user-invocable: true
auto: true
status: active
lifecycle: one plan file in the area's plans/open/ at status discovery, sections 1–3 → `plan-area` takes it to proposed; Tiny and Bug sizes write no file
invokes: [prototype, plan-area, domain, architecture, database-schema, problem-solver]
invoked-by: [human]
io: "an idea, request or spec draft → a size (Large · Medium · Tiny · Bug) and, for Large and Medium, the plan file with Area, Why and outcome, Discovery; or a halt naming the open question"
---

# grill

## What it does

Phase 1 (Discover). Finds out what the founder wants and why, so the choices he never mentions get
made his way: digs into what exists, plays his idea back, asks the one question that most changes
what gets built. Sizes it, opens the plan file at `status: discovery`. Implements nothing.

## When

An idea, request or spec draft: "grill this idea", "challenge this spec", a request too vague to plan.

## Steps

Shared understanding, not a form to tick. Moves, examples: [interview.md](references/interview.md).

1. **Area** from `config.yml` `outputs.plan` (unknown → ask once); one already open → bead `kind:idea`.
2. **Look before you ask.** Read what he pointed at and the code, data, decisions, earlier ideas and
   prior art it connects to, until you can say how it works today and what it touches. Already
   done? Cause real? Against a decision? One word, two things (`domain`)? Never ask what it answers.
3. **First message.** His request in your own words (what, for whom, why), what you found that
   bears on it (a constraint, a conflict, a cheaper path), a line inviting corrections, then ONE
   question: the open thing that most changes what gets built. Vague → one open question, saying
   what the answer changes. Skip what is already settled.
4. **Then one question per turn**, one sentence, no menu of answers, built on his last answer or a
   finding. A proposal he can correct, with your reason, often beats a question.
5. **Play back in chunks** as parts get clear: his words and numbers stay his, unchanged; anything
   you filled in is your proposal with a reason; a choice he hands over is "my call". End each chunk
   on "what is wrong or missing?".
6. **Before writing**, ask what he will not tell unprompted: the **appetite** (how much time it is
   worth — never invent it as his), **no-gos**, **rabbit holes**. Pre-mortem: "a month on, this
   failed — why?" Large and the why still soft → offer a press release + FAQ as if shipped.
7. **Approaches**, once the what is settled: diverge first (at least one inverted or opposite
   way), then a message of their own with 2–3 coarse ways, a paragraph and a trade-off each, one
   recommended, he picks. Differ on a boundary, data contract, dependency or pipeline shape →
   `/architecture design` then `decide`, no pick here. All weak, earlier attempts failed, or he
   asks to flip it → `problem-solver`, then resume.
8. **Size**, first match wins, he overrides in one word. **Large**: new external dependency, public
   interface or data contract, irreversible step, > 1 area → `/architecture decide`, `prototype`,
   `plan-area`. **Medium**: > 1 PR or a contract in one area → `plan-area`. **Tiny**: one PR, no
   contract → a bead → `tdd-dev`. **Bug**: reproduced defect → `bugfix`. Tiny, Bug: no plan file.
9. **Plan file** (Large, Medium) from [plan-file.md](references/plan-file.md). Assumptions = what
   would have to be true for this to work, each with its test, `assumed` or `proven: <pointer>`.
   His yes on scope and assumptions is the exit.

## Output

`<outputs.plan>/open/<date>-<name>.md` at `status: discovery`: an executive summary (`## Executive`)
and a scope diagram, then 1 Area · 2 Why and outcome (falsifiable) · 3 Discovery (prior art, what we
own, scope in/out, appetite, no-gos, rabbit holes, approaches, assumptions with tests). **Next:** a
decision surfaced → `/architecture decide`; else offer the size's next door from step 8.

## Where this goes

This skill produces: **plan, idea** — the plan file at `outputs.plan`; a parked idea as a bead.

## Not for

- Status, resume or implementing; a reproduced bug (`bugfix`); a plan past `discovery`
  (`plan-area`); opening issues (`issue-contract`), branches or pull requests.
