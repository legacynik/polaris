---
name: base-workflow
description: ◇ Polaris — The router. On any request that touches code or the tracker (an idea, "add X", "fix Y", a traceback, "open the PR", "track this"), name the case, invoke the skill that owns it, and at the end of each skill propose the next one or stop and ask with the options. Use at the start of work and after every skill ends.
version: 0.7.2
user-invocable: true
auto: true
lifecycle: writes nothing of its own — the size and path are stated in the conversation; the design lives where the size's path puts it; each gated step's evidence is produced and drained by the skill the step routes to (tdd-dev RED log, review findings, real-testing verdict, critic ledger, architecture Decision)
invokes: []
invoked-by: [human]
io: in - a request that touches code or the tracker → out - the case, the skill invoked for it, and after each skill the next one or a STOP with the options; the evidence is emitted by the skill it names
status: active
---

# base-workflow

## What it does

The router of the suite. It names the case, invokes the skill that owns it — never doing that
work by hand — and when a skill ends it proposes the next one, or stops and asks with the options.
The person never has to remember the chain. The method each step applies (understand, design,
test first, verify) lives in those skills and in `references/method.md`.

## When

- A request touches code, a plan or the tracker — an idea, "add X", "fix Y", a traceback.
- A skill just ended (its **Next:** is a hand-off), or you resume: read the plan file's `status:`.

## Steps

1. **Name the case and invoke its skill:**

   | Case | Skill | Why |
   |---|---|---|
   | idea, vague feature | `grill` | scope and size before anything is built |
   | bug, traceback, error report (DB, issue, bead, chat) | `bugfix` | cause and consequence proved, TDD inside |
   | scoped Medium or Large work | `plan-area` | one plan file: DoD, contracts, phases |
   | accepted plan, epic poured | `implement-plan` | phase by phase, RED first, gated |
   | one small clear change | a bead → `tdd-dev` | a plan would be ceremony |
   | any decision: a high-level architectural choice, or a rule that binds the future | `/architecture decide` (`design` first when options are open; `doc` for ARCHITECTURE.md) | it picks the home: ADR/DEC with probe, or a `decisions.md` entry |
   | work finished, "open the PR" | `ship` | one coordinator owns the order |
   | track it, for later | `issue-contract` | GitHub or a bead, with the reason |
   | words a model reads | `prompt-engineering` → `eval` | better only when measured |

2. **When a skill ends, propose its next step:**

   | After | Next |
   |---|---|
   | `grill` | a decision surfaced → `/architecture decide` first; then **STOP** — size and scope: Large → `prototype` → `plan-area` · Medium → `plan-area` · Tiny → `tdd-dev` · Bug → `bugfix` |
   | `prototype` | `plan-area` reads the verdict; a verdict that kills the scope → back to `grill` |
   | `plan-area` | `critic` → **STOP** accept · change · pause → pour → `implement-plan` |
   | `implement-plan`, `tdd-dev`, `bugfix` | `ship` |
   | `ship` | `pr` → `babysit` → **STOP** the owner's yes → merge → `plan-area` close |
   | `issue-contract` | **STOP** — start now (`bugfix` · `plan-area` · `tdd-dev`) or later |

3. **At a STOP, ask** with exactly those options (the harness's question tool when it has one).
4. **Decisions only through `/architecture decide`**, from any skill and any phase: never write an
   ADR, a DEC file, `decisions.md` or `ARCHITECTURE.md` by hand (a hook refuses it). Architecture first, then the plan.
5. **Never skip a skill's gate to save a step.** Thresholds come from the repository's own rules.

## Output

The case named and its skill invoked; after each skill, its next step or a STOP with options.
Diagram and rarer cases: `references/chains.md`; `eval/chain_probe.py` measures it on real cases.

## Where this goes

This skill produces: **none** — each step's evidence is written by the skill it routes to.

## Not for

- Doing a case's work by hand when its skill exists.
- A typo, a doc line, a config value with no behaviour: edit it directly.
- Branch, commit and PR mechanics: `git-power`, `ship`.
