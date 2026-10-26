# Decision records

Most choices are not decisions. The code shows how something was built, and the plan shows why;
neither needs a record. A record exists only for a choice that someone would otherwise re-argue or
undo without knowing what it cost.

## Decision, spec or detail

Sort each statement by one question: **what does it take to undo this?**

| Kind | The test | Where it goes |
|---|---|---|
| **Decision** | undoing it takes more than a commit: it fixes the shape of stored data, something a customer relies on, something another system calls, money, a vendor or a legal commitment; or it supersedes an earlier decision; or it fixes direction for months | a record, below |
| **Spec** | it says how something works or must be built: behaviour, fields, flow, limits, wording, tests | the plan file or the area's main document |
| **Detail** | a real choice, cheap to undo, with no stored or customer-visible consequence: a name, a placement, a threshold, a tool | the PR description, a CHANGELOG line, or a comment beside the code |

When nothing is a decision, nothing is recorded. That is the common case.

## The two homes

| Home | Write one when | Shape |
|---|---|---|
| **Ledger entry** in `decisions.md` | the choice could be questioned later and enacting it needs nothing a command could check | one entry, newest on top: chose · over · because · evidence · supersedes · impact |
| **Decision file** `decisions/DEC-<workspace>-<key>-NNN.md` | the choice must be **enacted** (code, config, infrastructure, a process a command can check), or it passes all three ADR tests | JSON frontmatter with `probe` and `probe_kills`, plus one ledger line pointing to it |

An **ADR** is not a third home. It is a decision file with `kind: architecture`, written only when
all three tests pass: the choice is hard to reverse, it would surprise a reader without the
context, and it came from a real trade-off. Any other decision file is `kind: process`.

A **lesson** (a fact learned from a failure) is never a decision. It goes to `records/` through
`scripts/lesson_record.py`.

## What a decision file must carry

`/architecture decide` writes it; it admits a draft only when all six hold:

1. **Costly to undo**, or it retires an earlier record by name.
2. **Two or more options**, each with a cost that says something (`€200/month`, not `TBD`).
3. **Rules cited** from the architecture rule library.
4. **Evidence**: what was tried or measured before deciding.
5. **Enforcement**: the test, gate or named reviewer that notices a violation.
6. **Review trigger**: the outside condition that puts it back on the table.

`probe` is the exact command that proves the decision is in effect; `probe_kills` names one of its
own call sites. A probe that still passes with that call site removed proves nothing, and the gate
rejects it.

## Its states

| status | Meaning | Who writes it |
|---|---|---|
| `proposed` | written; the owner has not agreed | `/architecture decide` |
| `accepted` | in force as direction; **not yet a fact** | the owner |
| `executed` | a fact: the probe passes, and fails with `probe_kills` removed | only `plan close`, after `check_decision_execution.py` reports it |
| `superseded` | replaced by a newer record, linked both ways; the old text is never edited | the new record |
| `deprecated` | dropped with no replacement, with a one-line reason | the owner |

`check_decision_execution.py` runs the probe of every accepted or executed record. `NOT_DONE`
means decided and not done; `status` and `week` print that list, oldest first. For an agent, an
`accepted` record describes the target and the code describes reality.

## Enforcement

Records come from `/architecture decide`, before the plan that depends on them; `base-workflow`
routes every decision there. `check_decision_execution.py` is the gate on what a record claims.
A local Claude Code hook (`porta-decision-guard.py`, not shipped in this package yet) also refuses
any hand-written change to `decisions/`, `decisions.md`, `docs/adr/` or `ARCHITECTURE.md` unless
the `architecture` skill ran in the session.
