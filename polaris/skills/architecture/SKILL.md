---
name: architecture
description: ◇ Polaris — Decide one architectural commitment and record it, usually when the move is already picked and offered for a sanity check. Fires when a change moves a boundary, an interface, a data contract or a dependency, when a schema changes under separately deployed readers, when a query is fast until it is not or a hot path repays the same cost every turn, when the written architecture is stale, or when code must be judged before refactor. Gates on reversibility first. Requires python3.
version: 1.6.1
user-invocable: true
auto: true
job: emit one decision record whose options are MECE, whose every option names what it COSTS, whose pick is the least worst, and which carries its enforcement hook and its closure check — or, before a target has been chosen, one audit report whose every finding names the simplification it enables — or, before a module exists at all, N genuinely different interface designs compared and one recommended — or halt naming the measurement that is missing and who owns getting it
when_not: mapping or reading a codebase without changing it (navigation, outside this skill); choosing what the company should build (strategy); the domain's own vocabulary, subdomain classification and integration patterns between contexts (that is the language-and-boundaries door, and it is not this one); vendor-specific tuning where a maintained vendor skill already carries the rules
lifecycle: "a `doctor` or `audit` run writes nothing — it reports, and every realignment is a verb the repo owner invokes · `decide` writes one record where `outputs.decision` points, in the home operating model §6 picks: an ADR in `docs/adr/NNNN-kebab-title.md`, always there and never a DEC file, when the decision is architecturally significant and passes all three ADR tests; a DEC file (`kind: process`) with `probe` and `probe_kills` plus one ledger line when a non-architecture choice must be enacted and a command can check it; else a ledger entry in decisions.md · records are written `proposed`, the founder sets `accepted`, only `plan close` writes `executed`, on the decision gate's word · `doc` writes the area README, or ARCHITECTURE.md with no area · `init` writes ADR 0001 into a repo with no ADR set · `land` binds an accepted record to call sites and its closure check · `design` emits a comparison, never a record · every halt is written into the record it interrupted · unmeasurable claims carry `ASSUMED`"
invokes: [domain, critic]
invoked-by: [human, database-schema, grill, apex-curate]
io: "receives: a repository to measure, a decision, accepted Decision, feature, framework, repo to fold in, schema change, hot path, system to judge, architecture document, or module that does not exist yet -> produces: a doctor report of one row per check (verdict, evidence, realignment) that repairs nothing; the reversibility verdict and fixed-field record; a landing receipt binding Decision to call sites, prerequisites and closure check; a current area README or ARCHITECTURE.md; an ADR-folder triage table; an audit report; N compared interface designs; or a halt naming what is missing."
status: active
---
# architecture

## What it does

Decides one architectural commitment and writes the document that carries it, after measuring the repository,
repairing nothing: the least-worst pick with its cost, enforcement and closure check, or a halt naming what is missing.

## When

- A change moves a boundary, an interface, a data contract, a dependency, a schema under other readers, a hot path.
- Stale written architecture, an ADR folder grown into a diary, code to judge before a refactor.
- Phase 3 (Define): the plan's contracts need a commitment, or `grill` found a moved boundary.

## Steps

1. **Pick the verb**, `/architecture <verb>`. No verb → `python3 scripts/arch_doctor.py --root . --quick`,
   then the numbered menu ([flow.md](references/flow.md), [menu.md](references/menu.md)).

   | Verb | Measures first | Emits |
   |---|---|---|
   | `init` · `doctor` | `scripts/check_context_backbone.py --init` · `scripts/arch_doctor.py` | receipt, plus ADR 0001 when no ADR set exists · one row per check, nothing repaired ([doctor.md](references/doctor.md)) |
   | `doctor <adr-dir>` | `scripts/adr_triage.py <adr-dir>` | one row per ADR, flags `appended` · `long`, a call: keep · amend · supersede · compact with <which> · demote to ledger · move to the area README; nothing moved |
   | `audit` | `scripts/detect.py <root> --json` | findings priced, each naming a simplification ([audit-arm.md](references/audit-arm.md)) |
   | `doc` | `scripts/check_context_backbone.py --check .` | the area README `docs/<areas|modules>/<area>/README.md`, or root `ARCHITECTURE.md` with no area ([doc-arm.md](references/doc-arm.md)) |
   | `decide` | Step 0, then the census | the record ([arms.md](references/arms.md)) |
   | `design` | nothing: no callers yet | 3+ divergent designs, one recommended, no record ([design-verb.md](references/design-verb.md)) |
   | `land` | call sites, prerequisites, the closure check | the landing receipt |

2. **Step 0, reversibility, before any advice.** `OWNED` only when the caller set is closed, every caller is in a repo
   you can push and landing needs no other party; else `PUBLISHED`; contested → halt ([process.md](references/process.md)).
3. **Census, then verify**: one script pass, the graph closes survivors, the rest ships `ASSUMED`; contested name → `domain`.
4. **Challenge and admit** ([record.md](references/record.md)): `critic` attacks the pick; sort decision · spec · detail; admit on six requirements.
5. **Pick the document** ([writing.md](references/writing.md): templates, budgets, examples).
   - **ADR**, always `docs/adr/NNNN-kebab-title.md`, never a DEC file: a decision affecting structure, non-functional characteristics,
     dependencies, interfaces or construction techniques that passes the three ADR tests (hard to reverse, surprising
     without context, a real trade-off). No ADR set yet → 0001 "Record architecture decisions" first ([adr-0001.md](references/adr-0001.md)).
     `# N. <short title>` · Date · Status (Supersedes / Superseded by, both ways) · Context (forces, measured) · Decision
     ("We will…") · Consequences (all) · optional Rejected, Measurement, Not decided, How it would be proven wrong; 1–2
     pages. Drift → amend in place, never the decision; reversal → supersede; overlap or dead → compact with a provenance note.
   - **Ledger line** in `decisions.md` (chose · over · because · evidence · supersedes · impact) for a threshold,
     method, prompt, heuristic or number, even when code carries it; a DEC `kind: process` only if still to build.
   - **Area README** `docs/<areas|modules>/<area>/README.md`, today's state only: what it owns · one diagram of the
     flow · per step in, logic, out, files, where it breaks, what is off in production · ADRs and ledger lines linked.
     `ARCHITECTURE.md` maps components, boundaries, cross-area flows. Never an appended update: state here, ADR compacted.
6. **Status.** Write `proposed`; the founder sets `accepted`; only `plan close` writes `executed`, once the probe passes.

## Output

Nine fixed fields (`reversibilità` · `opzioni` · `costo per opzione` · `scelta` · `enforcement` · `verifica di chiusura` ·
`modalità` · `ASSUMED` · `prossimo`, the next verb's exact command) and the document step 5 picked. Or a report, a halt.

## Where this goes

This skill produces: **adr, decision, architecture (ARCHITECTURE.md and the area README), audit, diagram** — at the paths `config.yml` `outputs` names.

## Not for

- Reading or mapping code with no change in view (navigation); deciding what to build (strategy).
- A domain's vocabulary, subdomain types or context map (`domain`).
- Vendor-specific tuning a vendor skill carries; a symptom whose root is not architectural (`bugfix`).
