---
name: grill
description: ◇ Polaris — Discover, phase 1. Grill an idea against the repo's docs, earlier ideas, how other repos solved it and what is in or out of scope; list every assumption with how to test it; propose the size; open the plan file at status discovery. Use for "grill this idea", "clarify this feature", "challenge this spec" or an ambiguous request before planning. Requires git; bd to park an idea or file Tiny work.
version: 2.0.5
user-invocable: true
auto: true
status: active
lifecycle: one plan file in the area's plans/open/ at status discovery, sections 1–3 → `plan-area` takes it to proposed; Tiny and Bug sizes write no file
invokes: [prototype, plan-area, domain, architecture, database-schema]
invoked-by: [human]
io: "an idea, request or spec draft → a size (Large · Medium · Tiny · Bug) and, for Large and Medium, the plan file with Area, Why and outcome, Discovery; or a halt naming the open question"
---

# grill

## What it does

Phase 1 of the operating model (Discover). Grills an idea against what already exists — the repo's docs
and decisions, earlier ideas, how other repos solved it — until scope in/out and every assumption, with
how to test it, are on paper. Proposes the size, opens the plan file at `status: discovery` with
sections 1–3, hands it to `plan-area`. Never implements; opens no issue, branch or pull request.

## When

- An idea, request or spec draft for a new feature or change: "grill this idea", "clarify this
  feature", "challenge this spec", or a request too vague to plan.

## Steps

1. **Area.** From `config.yml` `outputs.plan` and the area map; unknown → ask once. Its `plans/open/`
   already holds a plan → stop: the idea waits as a bead `kind:idea`, or the founder pauses that plan.
2. **Evidence before questions.** Governing AGENTS.md/CLAUDE.md, current state, accepted decisions,
   lessons, then the code and data surface. Ask the agent memory (`ai-memory-retrieval`) for earlier
   sessions on the idea; skip if absent; memory is a lead, never proof. A database in play →
   `database-schema`. How: [interview.md](references/interview.md).
3. **Prior art.** How other repos and products solved it, from primary sources; what we already own
   that covers part of it. A dependency question → its official docs for the installed version.
4. **Tear down the premise.** Already done? Cause real? Against an accepted decision? Run safe
   read-only commands instead of reading source. Overloaded term → `domain`; a moved boundary,
   interface, schema or dependency, or any choice that binds the future → `/architecture` now (`design` if open, else `decide`), before the plan.
5. **Grill, one question per turn**: a real choice, your recommendation as the default, the evidence
   or unknown it settles. Turn vague words ("fast", "safe", "done") into an observable threshold.
6. **Assumptions.** Each one with how to test it (a command, a spike, a measurement), tagged
   `assumed` or `proven: <pointer>`.
7. **Size** — the first row that matches wins; the founder overrides in one word:

   | Size | First match wins | Next |
   |---|---|---|
   | Large | new external dependency, public interface or data contract; an irreversible step (migration, deletion, pricing); or > 1 area | `/architecture decide`, `prototype`, then `plan-area` |
   | Medium | > 1 PR, or touches a contract inside one area | `plan-area`; `prototype` first only if an assumption stays `assumed` |
   | Tiny | one PR, no new interface or contract, no decision | a bead with acceptance → `tdd-dev` → `ship`; no plan file |
   | Bug | a defect with a reproduction | `bugfix` → `ship`; no plan file |

8. **Write the plan file** (Large, Medium) from [plan-file.md](references/plan-file.md), then ask the
   founder to agree scope and assumptions. Their yes is the exit of this phase.

## Output

`<area plans folder from outputs.plan>/open/<date>-<name>.md` at `status: discovery`: an
executive summary on top (`## Executive`, a few lines for a person) and a scope diagram, then 1 Area · 2 Why and outcome (a falsifiable success criterion) ·
3 Discovery (prior art with sources, what we own, scope in/out, assumptions with their tests).
Sections 4–9 stay for `prototype` and `plan-area`. **Next:** a decision surfaced → `/architecture decide` first; then ask the founder, with options, size and scope: Large → `prototype` then `plan-area` · Medium → `plan-area` · Tiny → a bead and `tdd-dev` · Bug → `bugfix`.

## Where this goes

This skill produces: **plan, idea** — the plan file at `outputs.plan`; a parked idea as a bead.

## Not for

- Status, session resume, or implementing anything.
- A bug with a reproduction (`bugfix`); a plan already past `discovery` (`plan-area`).
- Opening issues (`issue-contract`), branches or pull requests.
