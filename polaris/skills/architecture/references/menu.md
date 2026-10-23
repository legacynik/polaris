# The menu — measurement to verb

Read this for the invocation with **no verb**. The user is asking "what should I do here?", and
the answer has to come from this repository rather than from a static list.

Run `python3 scripts/arch_doctor.py --root . --quick` once — read-only, three checks, a five
second budget for the whole measure, no writes — then lead with **three to five verbs, each with
one line of reason lifted from that output**, followed by the full Commands table. **Never
auto-run a verb.** The recommendation is a suggestion the founder confirms, and a menu that
executed one of its own suggestions has already made the decision it was asked to present.

## Every verdict has a row

`UNKNOWN` is the common case, not the exception: on a repository that never adopted the backbone
every row reads `UNKNOWN`. A menu that only answers `RED`
is empty exactly when the user most needs it, so every check the doctor can emit has a row for
both verdicts below. Where the honest answer is that no verb follows, the row says so and why —
**"no verb"** is an answer; silence is not.

| Measure | Lead with | The reason line |
|---|---|---|
| `backbone` RED | `doc`, or `land <DEC-id>` on a `DECISION_CALL_SITE_MISSING` cause | the document cites a path that is gone — re-true it. A call-site cause means an accepted Decision's call sites moved under it |
| `backbone` UNKNOWN | `audit <import-root>` if the harness is absent; **adoption** (`check_context_backbone.py --init .`) if the cause is `LIVE_DOC_MISSING` or `FRONTMATTER_MISSING`; **no verb** if the checker itself failed — fix the checker first | nothing is declared here yet, so there is nothing to re-true; `doc` would write a document into a repository with no backbone to hold it |
| `decisions` RED | `land <DEC-id>` | a Decision is accepted and its old call path still runs — approval is not landing |
| `decisions` UNKNOWN | **adoption** (`check_context_backbone.py --init .`) when there is no `decisions/` register; **no verb** when the checker is absent or failed | a repository with no register has nothing to judge, and a predicate that did not run is not a predicate that passed |
| `scope-drift` RED | `decide` | changed files no active intent claims: either the plan's scope is wrong or the change is |
| `scope-drift` UNKNOWN | **no verb yet**: record the active intents in `state/intents.json` | with no intent source every changed file reads as unowned, so the row would be RED by construction and would measure nothing |
| `symbol-drift` RED | `bugfix` on the symbol named | its checksum moved from what was recorded against the spec |
| `symbol-drift` UNKNOWN | **no verb**: it asks about named files | run it yourself on the files you touched — it is not a repository-wide question and the doctor will not pretend otherwise |
| `decision-drift` RED | `land <DEC-id>` | the code a Decision referenced moved; revisit the record before the call sites drift further |
| `decision-drift` UNKNOWN | **no verb yet**: nothing was ever recorded | an empty ledger measures nothing; record the Decision's refs, then this row starts answering |
| `dependency-drift` RED | `decide` | a module's import set moved; new coupling is a commitment, not a detail |
| `dependency-drift` UNKNOWN | **no verb yet**: nothing was ever recorded | same — record the dependency set first |
| `test-drift` RED | `bugfix` / `tdd-dev` | a symbol changed while its test stayed frozen — the suite may prove the old behaviour |
| `test-drift` UNKNOWN | **no verb yet**: nothing was ever recorded | same — record the symbol/test pairs first |
| `install-hygiene` RED | **no verb here**: it is an install repair, not an architectural one | a dangling link or a lockfile ghost is fixed in the install roots; naming it as architecture work sends the founder to the wrong file |
| `install-hygiene` UNKNOWN | **no verb**: the lockfile or the roots are missing | the harness is not installed for this user; nothing about this repository follows from it |

Three extra evidences, whatever the check: `timeout`, `over quick budget` and `ledger unreadable`
all mean the measure did not finish, never that it passed. Offer the full run (`/architecture doctor`) rather than a
verb, and say which check ran out of time.

## Choosing among them

Lead with the **blocking** rows — the table marks them, and only a RED on `backbone` or
`decisions` is ever marked so.
The drift checks are context, and a context row presented as urgent is noise. Two blocking rows
RED at once: `backbone` first, because `decisions` reads the map it governs.

When every row is `UNKNOWN` and the ask is architectural anyway, say so in one line and route to
`audit` or `design` — both work on the code itself and need no backbone. Do not offer `doctor` a
second time to a repository that has already answered `UNKNOWN` on every row.

A named verb always wins over anything inferred here.
