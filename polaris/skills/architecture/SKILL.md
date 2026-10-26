---
name: architecture
description: ◇ Polaris — Decide one architectural commitment and record it, usually when the move is already picked and offered for a sanity check. Fires when a change moves a boundary, an interface, a data contract or a dependency, when a schema changes under separately deployed readers, when a query is fast until it is not or a hot path repays the same cost every turn, when the written architecture is stale, or when code must be judged before refactor. Gates on reversibility first. Requires python3.
version: 1.5.2
user-invocable: true
auto: true
job: emit one decision record whose options are MECE, whose every option names what it COSTS, whose pick is the least worst, and which carries its enforcement hook and its closure check — or, before a target has been chosen, one audit report whose every finding names the simplification it enables — or, before a module exists at all, N genuinely different interface designs compared and one recommended — or halt naming the measurement that is missing and who owns getting it
when_not: mapping or reading a codebase without changing it (navigation, outside this skill); choosing what the company should build (strategy); the domain's own vocabulary, subdomain classification and integration patterns between contexts (that is the language-and-boundaries door, and it is not this one); vendor-specific tuning where a maintained vendor skill already carries the rules
lifecycle: "a `doctor` or `audit` run writes nothing — it reports, and every realignment is a verb the repo owner invokes · `decide` writes one record where `outputs.decision` points, in the home operating model §6 picks: a DEC file with `probe` and `probe_kills` plus one ledger line when the choice must be enacted or passes all three ADR tests (`kind: architecture` only then), else a ledger entry in decisions.md · records are written `proposed`, the founder sets `accepted`, only `plan close` writes `executed`, on the decision gate's word · `doc` writes ARCHITECTURE.md · `land` binds an accepted record to call sites and its closure check · `design` emits a comparison, never a record · every halt is written into the record it interrupted · unmeasurable claims carry `ASSUMED`"
invokes: [domain, critic]
invoked-by: [human, database-schema, grill]
io: "receives: a repository to measure, a decision, accepted Decision, feature, framework, repo to fold in, schema change, hot path, system to judge, architecture document, or module that does not exist yet -> produces: a doctor report of one row per check (verdict, evidence, realignment) that repairs nothing; the reversibility verdict and fixed-field record; a landing receipt binding Decision to call sites, prerequisites and closure check; a current ARCHITECTURE.md; an audit report; N compared interface designs; or a halt naming what is missing."
status: active
---

# architecture

## What it does

Decides one architectural commitment and records what it costs. Each verb measures what is true
in the repository before any option is written, and repairs nothing. A record names the least-worst
pick, its cost, enforcement and closure check; otherwise the run halts naming the missing measurement.

## When

- A change moves a boundary, an interface, a data contract or a dependency; a schema changes under
  separately deployed readers; a hot path repays the same cost every turn.
- Stale written architecture, code to judge before a refactor, or a module that needs a shape.
- Phase 3 (Define): the plan's contracts need a commitment, or `grill` found a moved boundary.

## Steps

1. **Pick the verb**, `/architecture <verb>`. No verb → `python3 scripts/arch_doctor.py --root . --quick`,
   then the numbered menu ([flow.md](references/flow.md), [menu.md](references/menu.md)).

   | Verb | Measures first | Emits |
   |---|---|---|
   | `init` · `doctor` | `scripts/check_context_backbone.py --init` · `scripts/arch_doctor.py` | receipt · one row per check, nothing repaired ([doctor.md](references/doctor.md)) |
   | `audit` | `scripts/detect.py <root> --json` | findings priced, each naming a simplification ([audit-arm.md](references/audit-arm.md)) |
   | `doc` | `scripts/check_context_backbone.py --check .` | `ARCHITECTURE.md` ([doc-arm.md](references/doc-arm.md)) |
   | `decide` | Step 0, then the census | the record ([arms.md](references/arms.md)) |
   | `design` | nothing: no callers yet | 3+ divergent designs, one recommended, no record ([design-verb.md](references/design-verb.md)) |
   | `land` | call sites, prerequisites, the closure check | the landing receipt |

2. **Step 0, reversibility, before any advice.** `OWNED` only when the caller set is closed, every
   caller sits in a repo you can push, and landing needs no other party; else `PUBLISHED`. Contested
   → halt with both readings and their costs. Detail: [process.md](references/process.md).
3. **Census, then verify**: one script pass, the graph closes the survivors, the rest ships
   `ASSUMED`. Name the graph reached, or write `modalità: ridotta — missing: graph-verify`.
4. **Names first**: a contested domain or component name → `domain` before it enters `governs`.
5. **Challenge and admit** ([record.md](references/record.md)): `critic` attacks the pick in a fresh
   context; sort the ask into decision · spec · detail; only a decision meeting six requirements is recorded.
6. **Pick the home** (operating model §6). A DEC file with `probe` and `probe_kills`, plus one
   ledger line, when it must be enacted (code, config, infra, a process a command can check) or
   all three ADR tests pass — hard to reverse, surprising without context, a real trade-off; only
   then `kind: architecture`, else `kind: process`. Anything else → one entry in `decisions.md`.
7. **Status.** Write `proposed`; the founder sets `accepted`; `executed` only `plan close` writes,
   once `check_decision_execution.py` reports the probe passing. Accepted is the target; code is reality.

## Output

A record with the nine fixed fields — `reversibilità` · `opzioni` · `costo per opzione` · `scelta`
· `enforcement` · `verifica di chiusura` · `modalità` · `ASSUMED` · `prossimo` (the next verb with
its exact command) — in the home step 6 picked. Or: a doctor or audit report, `ARCHITECTURE.md`, a
design comparison, a landing receipt, or a halt.

## Where this goes

This skill produces: **decision, architecture, audit, diagram** — at the paths `config.yml` `outputs` names.

## Not for

- Reading or mapping code with no change in view (navigation); deciding what to build (strategy).
- A domain's vocabulary, subdomain types or context map (`domain`).
- Vendor-specific tuning a vendor skill carries; a symptom whose root is not architectural (`bugfix`).
