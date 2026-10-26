# Process — the full procedure behind SKILL.md

`SKILL.md` carries the steps; this file carries the detail each step loads: the verbs, Step 0,
census-then-verify, the domain handoff, the nine fixed fields, the rationalizations, the red flags
and the verification commands. Paths to scripts are relative to the skill directory.

## Overview

Measure, then advise. Every verb below runs a script that reports what is actually true in this
repository **before** a single option is written, and the record it emits names what the choice
**costs**. Nothing here repairs what it finds: a doctor that rewrites a document as a side effect
is how a false document becomes a signed one.

Emit **one** commitment, with its cost. Not a survey of the options, not a map of the code — this
door opens only when something is being committed to.

The rules live in this skill's own rule files: `references/decision-rules/` (decomposition,
governance, data-systems, ownership, domain-strategy, component-boundary); [routing.md](routing.md) maps each subject to its file and
says which one adjudicates at a fork. Every row below names the exact rule ids it loads. **Load
only what the row names**: a step that loads more is a step whose answer stopped being
reproducible. A run that cannot load its rules still emits **every fixed field** and declares the
loss in `modalità`.

## Commands

`/architecture <verb> [argument]`. A named verb wins over inference; the description routes the
asks that arrive without one. Seven verbs, four phases — and every one measures before it advises.

| Command | Phase | Measures FIRST | Emits AFTER | Reference |
|---|---|---|---|---|
| `init [root]` | Check | `check_context_backbone.py --init <root>` — audit, scope and freshness must be `READY` | the adoption receipt and the manifest write; the verb the menu names on `FRONTMATTER_MISSING` / `LIVE_DOC_MISSING` | [doctor.md](doctor.md) |
| `doctor [root]` | Check | `scripts/arch_doctor.py --root <root>` — backbone (cited paths exist), Decision health, scope/decision/dependency/test drift, install hygiene | one row per check: `check · verdict · evidence · realignment`. Repairs **nothing** | [doctor.md](doctor.md) |
| `audit <import-root>` | Map | `scripts/detect.py <import-root> --json`, then census-and-verify | the audit report — every finding priced in the four costs, ranked by blast radius, each naming the **simplification** it enables | [audit-arm.md](audit-arm.md) |
| `doc` | Map | `check_context_backbone.py --check .` — which cited paths the live documents name that are gone | repository-root `ARCHITECTURE.md` to its contract, plus the derived map where the repository declares a generator | [doc-arm.md](doc-arm.md) |
| `decide <question>` | Decide | Step 0 reversibility, then the census the question needs | the challenged pick and the record, all nine fixed fields | [arms.md](arms.md), then [record.md](record.md) |
| `design <module>` | Decide | nothing — there is no caller set yet, so Step 0 has nothing to judge, and saying so is the measurement | 3+ genuinely divergent designs compared on depth, locality and seam placement, one recommended — **never** a decision record | [design-verb.md](design-verb.md) |
| `land <DEC-id>` | Land | every `call_sites[]` entry resolved against `DOMAIN.md`, every prerequisite checked on its live authority, then the declared `closure_check` executed | the landing receipt: Decision ID, call sites, prerequisite verdicts, closure command, exit code, source hashes, `modalità` | [arms.md](arms.md#the-land-verb--make-an-accepted-decision-real) |

**The invocation with no verb answers with the written menu.** Run
`python3 scripts/arch_doctor.py --root . --quick` — read-only, under five seconds — then write, in
the person's language: what the repository is and whether its map can be trusted, the two or three
things the measure found, and **the numbered list of everything the skill can do here**, with ⭐ on
what the measure recommends. Then one question. Every stage ends the same way: what it produced,
then the next options written out. A writing stage waits for an explicit yes, and a finding is
presented, never repaired, while the menu is shown. The stages are
[flow.md](flow.md); the measure-to-verb reasons are [menu.md](menu.md).

## Process

### Step 0 — reversibility, before any advice

**Can every caller still change in one commit?** Answer before reading a single rule: the answer
inverts what comes after, because the same question about the same interface has two correct and
opposite answers depending on it.

`OWNED` requires **all three**; any one failing makes it `PUBLISHED`:

| # | Condition | How it is checked |
|---|---|---|
| a | the caller set is **closed** — enumerable today, no consumer you cannot name | census script over the tree, then the graph on the survivors |
| b | every caller sits in a repo you can push | list the repos the callers live in |
| c | landing them together needs no other party's release, deploy window or approval | name the parties; zero others = pass |

It is **not** "internal versus external" and **not** a count. A module inside one repo with forty
consumers fails (c). A published library with one known consumer fails (a) — the consumers you
cannot name are the whole problem.

| | `OWNED` | `PUBLISHED` |
|---|---|---|
| Optimise for | **depth** — behaviour per unit of interface | **commitment** — what you can no longer take back |
| A smaller surface | wins: fewer methods, fewer parameters | loses: an options object that can grow beats positional parameters |
| Build the seam | at **two** adapters — one adapter is a hypothetical seam | at **zero** adapters — adding it later is a breaking change |
| Wrong because | it **costs** — coupling, a seam nobody earned | it **cannot be taken back** — every observable behaviour is already a contract |

`OWNED` loads [interface-and-seam.md](interface-and-seam.md); `PUBLISHED` loads
[contract-and-commitment.md](contract-and-commitment.md). **Halt** if the answer is
genuinely contested: that contest is the decision, and it is the repo owner's. Record both readings
and what each costs, and stop.

### Census, then verify — how any count in the output is produced

1. **One script pass** finds the candidates — one traversal, never N graph calls for a counting
   question.
2. **The graph closes the question** on the survivors that carry the decision. Where invocation is
   textual rather than symbolic, the verify leg is a name-search across the config surfaces.
3. **Whatever the verify leg cannot close is marked `ASSUMED`**, with the reason.
4. **Name the graph you actually reached, or declare that you reached none.** A census closed by
   text search alone reads exactly like one closed by a symbol graph. A run with no graph is still
   valid — every unclosed survivor ships `ASSUMED` — but it is `ridotta`, and `modalità` names the
   missing leg. Structural typing, dynamic dispatch and textual invocation all defeat import
   scanning: a count produced by scanning imports in such a codebase comes out low and reads as
   certain.

### Domain handoff — names before commitments

Before a Decision introduces or reuses a contested domain, component or context name, invoke
`domain`. It returns the canonical term or halts with the unresolved ambiguity; only then may this
door place that stable ID in `governs`. `architecture` owns what the commitment costs and where it
lands; `domain` owns whether the name is true.

### What every verb emits

Nine fixed fields. A record missing one is incomplete output, not a draft. The names are
deliberately Italian — typed Decisions keep their narrative fields in Italian and
`eval/checks.json` greps these exact strings, so renaming one is a contract change, not a
translation.

| Field | Means |
|---|---|
| `reversibilità` | `OWNED` or `PUBLISHED`, with which of the three conditions decided it |
| `opzioni` | MECE — mutually exclusive, collectively exhaustive. Two options that overlap are one option written twice |
| `costo per opzione` | what each one **costs**, not what it buys. An option with no cost stated is a defective option |
| `scelta` | the least worst combination of trade-offs. Never "the best design" — there isn't one |
| `enforcement` | what mechanically notices a violation, and where — a red check with a comment, warning rather than blocking unless it is one of the repository's own merge gates |
| `verifica di chiusura` | the predicate, declared **before** the work, mechanically checkable, executed by something that is not the repo owner |
| `modalità` | `piena`, or `ridotta` naming every missing input. **First line is machine-checkable**: `modalità: piena` or `modalità: ridotta — missing: <tag>[, <tag>...]`, tags from `rule-library` · `decisions` · `glossary` · `graph-verify`; prose follows below it |
| `ASSUMED` | every claim the verify leg could not close, each with its reason. A record with no `ASSUMED` line says the verify leg closed everything, which is itself a claim |
| `prossimo` | the next verb **with its exact command**: `prossimo: /architecture land DEC-foo-001` · `prossimo: nessuno — il ciclo si chiude qui`. A record whose reader has to re-derive what happens next is where a signed decision stalls |

Before anything is written, [record.md](record.md) runs four steps: challenge the
pick with a fresh-context reviewer, sort the ask's statements into decision · spec · detail, admit
the decision against six written requirements, then write it where the repository keeps its
decisions, in that repository's own shape. **A commitment becomes an authority only when it is
admitted**; one that misses a requirement is still answered, it just binds no later work.

## Rationalizations

| What it sounds like | What is actually true |
|---|---|
| "The doctor found a gone path, I'll just drop it from the citation." | A path is gone either because it moved or because the document is now **false**. Fix the citation only when the content is still true; otherwise `doc` or `land`. |
| "No checker is installed here, so there's nothing wrong." | Absence of a measurement is `UNKNOWN`, never GREEN. A green zero on an uninstalled harness is the fabricated number this door exists to refuse. |
| "The ledger is empty, so there's no drift." | An empty recording measures nothing. The row is `UNKNOWN` and the realignment is to record it. |
| "It was signed, so it's done." | A record that supersedes a running mechanism is done when every call site has moved, and the `verifica di chiusura` is what proves it. An approved record whose hot path still runs the old way is the most expensive failure here. |
| "I'll recommend the best design." | There isn't one. `scelta` is the least worst combination of trade-offs. |
| "Better to record it, just in case." | A record is an authority every later packet must load and obey. One written for a choice that is undone in one commit is a constraint with no matching cost. No admission, no record. |
| "I can answer this without the reversibility verdict." | The same question about the same interface has two correct and opposite answers depending on it. Step 0 is not a formality. |

## Red flags

- A bare number in the output that no verify leg closed and no `ASSUMED` covers.
- A recommendation that **adds** a layer, a service, an indirection or a config surface,
  presented as an audit finding. Audit findings delete or split; an addition is a hypothesis.
- Advice given before Step 0, or a `decide` run whose census never ran.
- A citation edited to silence the gate for something that was never read.
- A menu that executed one of its own suggestions.
- A record without `prossimo`: that is where the work stops.

## Verification

| command | when | blocks? |
|---|---|---|
| `python3 scripts/arch_doctor.py --root . --quick` | the naked invocation, and before any verb that writes | no — exit 0 always, it reports |
| `python3 scripts/arch_doctor.py --root . [--json]` | the full `doctor` run | yes — exit 2 when a blocking check is RED |
| `python3 scripts/detect.py <import-root> --json` | the audit arm's mechanical leg, always first | no — produces candidates, never recommendations |
| `python3 scripts/check_absorption.py` | after editing a reference: the 26 load-bearing items each still have their anchor | yes — exit 1 names the missing item |
| `python3 -I "$BACKBONE" --init <repo>` | adopting the backbone in a repository that has none — the doctor routes here, never to `doc` | yes — audit, scope and freshness must be `READY` before the manifest write |
| `python3 -I "$BACKBONE" --check .` | `doc` and `land`; validates the three live documents plus the scoped Decision landing contract | yes — stale, unknown or conflicting sources block |
| `python3 -I "$BACKBONE" --emit-context <repo> --work-item <id>` | emitting the ContextPack for a work item | yes — undeclared work items return `WORK_ITEM_UNVERIFIED` |

`arch_doctor.py`, `detect.py`, `check_absorption.py` and the backbone checker
`check_context_backbone.py` ship in this skill's `scripts/`. Resolve the checker with
`BACKBONE=$(python3 scripts/arch_doctor.py --which check_context_backbone.py --root .)`, which
prints this skill's own copy. A nonzero exit means the skill's `scripts/` is incomplete: the rows
it would measure are `UNKNOWN`, and `doc` checks every `snapshot_scope` path by hand and records
that in `modalità`. `--emit-context` also needs the Polaris ContextPack resolver (`contextpack.py`),
which only a full Polaris installation carries; without it the checker exits 2 with
`CONTEXTPACK_UNAVAILABLE`. For `init`, `check` and `emit-context`, the **first** access to the checker is the
exact command above: reading, grepping or hashing it first invalidates the run. `land` is the
exception — resolving and hashing the Decision, `DOMAIN.md`, the declared call sites and the
prerequisites before running the closure command is exactly what that verb is for. A zero exit
with every promised receipt field closes the run; a second audit to re-prove it adds nothing.
`BLOCK` and `REPLAN` are not `PASS`. Load [director.md](director.md) only for
multiple evidence lanes, multiple landing packets, a missing result, background work or resume.
The tests this skill must fail without its gates: [bypass-test.md](bypass-test.md).

## Where this goes

A skill decides **how** to produce a document, never **where** it lives. Read the host
repository's output map before writing any record, report or diagram — a document that lands
where the repository does not look was never written:

```bash
sed -n '/^outputs:/,/^[^ ]/p' _polaris/config.yml 2>/dev/null || sed -n '/^outputs:/,/^[^ ]/p' config.yml
```

This skill produces: **decision, diagram** (the derived map beside `ARCHITECTURE.md`). If the
repository declares no map, say once where you wrote and why.
