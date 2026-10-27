---
name: plan-area
description: "◇ Polaris — Write ONE plan file per piece of medium or large work (area first, outcome, DoD, contracts, every claim assumed or proven), pour its phases into a Beads epic gated by feature_gate.py, record course changes, and close it after merge. Use when an idea is scoped and needs a plan, the plan must become phases, evidence contradicts it, or ship merged it. Requires bd (Beads), git, gh."
version: 0.5.0
user-invocable: true
status: active
lifecycle: "docs/<areas|modules>/<area>/plans/open/<date>-<name>.md + a poured Beads epic → plan close: canonical doc absorbs, file to done/, epic burned"
invokes: []
invoked-by: [issue-contract, grill, ship, implement-plan, human]
io: "scoped idea + code + open issues → one plan file (exec summary, diagram, status) and a Beads epic whose steps close only through feature_gate.py"
---

# plan

## What it does

One plan file per piece of work (spec and plan in one, operating model §5), poured into a Beads
epic whose steps close only through `feature_gate.py`, closed after merge. A plan records the
**decisions** a capable builder cannot make alone; everything else is the builder's job.

## When

Medium or large work is scoped (tiny work is a bead); the owner approved the file (pour);
evidence contradicts it (course change); `ship` merged it or it is abandoned (close).

## Steps

The goal: a plan the owner recognises as his (executive summary and phase diagram on top) that
a builder could execute without a question that changes what gets built. Done when
`check_plan_files.py --gate` passes, builder check and `critic` leave nothing blocking, and the
owner approved the file. Examples: `references/plan-file.md`; Beads: `references/beads.md`.

- **Before writing**: no bd → stop (`brew install beads`). Area from `outputs.plan` + area map;
  one open plan per area (else a bead `kind:idea`). Read the code, search duplicate issues, cite both.
- **The owner's words are the spec.** Carry them verbatim or with a pointer to where he said
  them; whatever you add is marked `proposal (agent):`. A proposal that changes what gets built
  is a question for him, not a line in the plan.
- **Spec by example**: every contract and DoD behaviour carries a real input → expected output
  (or a scenario with values) that can become its acceptance test, not an abstract sentence.
- **Decisions, not a transcript.** A code step: signature, file, the spec's values. A test step:
  the test name and its assertions. A body only where signature and tests leave an algorithm
  open; `check_plan_files.py` flags a plan that is mostly code.
- **Small phases, riskiest first**: the earliest phase proves or kills the riskiest assumption;
  each closes on its own tests; a step is one action with a checkable result.
- **Review Focus**: pre-mortem it ("this shipped and failed — why?"), then pin up to five inputs
  the spec implies but no test sends (empty, duplicate, malformed, boundary) with a test in the
  owning phase. Large work: name in the risks what reacts after release, and with what delay.
- **Builder check, then critic.** A fresh-context agent reads the plan as its builder
  (`references/builder-check.md`): answered → put the answer in the plan; minor → decide, mark it
  yours; the owner's → one round of questions. Then `critic` attacks it once.
- **Approval is of the file.** "Scope ok" on the idea is not "accepted": show him the path, he
  sets `accepted`. Then `feature_gate.py pour --record <plan> --repo .` (status → `in-progress`).
- **Course change**: append to §9 (date · what proved wrong · evidence · what changes) before the
  code changes. **Close** (from `ship`): the area README absorbs the plan, then
  `plan_close.py --record <plan> --repo . --merged --pr <N>` (or `--abandoned "<why>"`).
- Ask yourself: what would the builder get wrong here? Which line is mine, not his?

## Output

Plan path and status; after pour the epic id; after close the `done/` path and DECs promoted.
**Next:** written → builder check, `critic`, then the owner with options (accept · change ·
pause); poured → `implement-plan`; closed → STOP.

## Where this goes

This skill produces: **plan, idea, tasks** — the plan file at `outputs.plan`, ideas and phases in Beads.

## Not for

- Tiny work or a bug with a reproduction: a bead → `tdd-dev`, or `bugfix`.
- Executing phases: `implement-plan`. Judging a diff: `review`.
- Deciding one architecture commitment: `architecture`. Clarifying a vague idea: `grill`.
