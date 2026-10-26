---
name: prototype
description: ◇ Polaris — Prototype, phase 2. Answer one named design question with throwaway code on a spike branch — does this state model or logic hold, what should this UI look like — and write only the verdict into the plan file. Use when a plan assumption is still assumed and code can settle it, or before building anything new. Requires git.
version: 1.0.2
user-invocable: true
auto: true
status: active
lifecycle: a spike branch that never merges + one verdict block in plan file section 4 → read by `plan-area` when it writes contracts and approach; a spike that answers nothing is deleted and leaves nothing
invokes: []
invoked-by: [human, grill]
io: "one named question and the assumption it tests → a pushed spike branch plus one verdict block (question, answer, evidence, what it changes) under section 4 Prototype verdicts; or the spike deleted"
---

# prototype

## What it does

Answers **one** named question with throwaway code before production code exists: a logic demo
a non-developer can click through, or several radically different UI variants on one route. The
code lives on a spike branch and never merges; only the verdict enters main, as a block in the
plan file's section 4. The verdict may change scope, contracts or the plan.

## When

- Phase 2: `grill` left an assumption `assumed` that code can settle (always for Large work).
- "Does this state model feel right?", "what should this page look like?", before building anything new.

## Steps

1. **Name the question** in one sentence, answerable by the spike, and the plan assumption it tests
   (`A2` in section 3). Two questions → two spikes. No question → no spike: back to `grill`.
2. **Branch** `spike/<plan-name>-<slug>` from main. Nothing on it will merge.
3. **Pick the shape**: logic or state → [logic.md](references/logic.md), one HTML file driven by
   buttons; look and layout → [ui.md](references/ui.md), variants behind `?variant=`. Ambiguous
   and nobody to ask → follow the surrounding code and state the assumption at the top.
4. **Build it throwaway**: named as a prototype, one command or a double-click to run, state in
   memory (a scratch store only when persistence is the question), no tests or polish, the full
   state shown after every action or variant switch.
5. **Run it with the founder**, or hand it over. The answer is what they say when something
   "shouldn't be possible" or when they pick parts of two variants.
6. **Push the branch and write the verdict** into section 4 through the repo's normal path for
   the plan file, never from the spike branch (format below). Tag the tested
   assumption `proven: <verdict>`, or rewrite it when the answer contradicts it. Scope, contracts
   or plan changed → say which section.
7. **Answered nothing?** Delete the branch, write nothing; the assumption stays `assumed`.

## Output

A verdict block in plan file section 4:

```markdown
### V1 — <the question>
- answer: <one line>
- evidence: spike/<plan-name>-<slug> @ <sha> — <what was run and what was seen>
- tests: A2 → proven: V1 (or rewritten)
- changes: <scope / contracts / approach, or "nothing">
```
**Next:** `plan-area` reads the verdict into §3–5; a verdict that kills the scope goes back to `grill` — ask the founder which.

## Where this goes

This skill produces: **plan (the verdict block in section 4)**; the spike code stays on its branch.

## Not for

- Building the real thing: that is the build phase, test-first (`tdd-dev`).
- A reproducible bug (`bugfix`) or a choice with no code question (`architecture`).
- An idea with no named question yet (`grill`).
