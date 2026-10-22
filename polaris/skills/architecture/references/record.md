# The record — challenge the pick, sort the statements, admit, write

Load this once `decide` has a pick and something is about to be written down. Four steps, in
order: challenge the pick, sort what the ask contains, admit it against six requirements, then
write it where the repository keeps its decisions.

## 1. Challenge the pick

A pick offered for a sanity check is a claim, and the claim gets one fresh adversary before it
stands. Run it for any pick that crosses a module or service boundary, asserts a property no
compiler checks (ordering, idempotence, an invariant), or is `PUBLISHED`. Skip it for a pick that
is a mechanical rename or move.

1. **Write the claim** in two lines: what stands, and what breaks if it is wrong. A claim that
   does not fit two lines is still a vibe; sharpen it first.
2. **Extract the artifact and the contract**: the proposal in three to five sentences, the
   constraints it must satisfy (the reversibility verdict, the options and their costs). Leave
   out your reasoning and your claim — a reviewer handed a conclusion returns agreement.
3. **Hand them to a fresh-context reviewer** that has not seen this run — the `critic` door —
   with an adversarial brief: *find what is wrong with this artifact against this contract — unstated assumptions,
   unhandled edge cases, hidden coupling, ways the contract could be violated, conventions it
   breaks; report issues only, or state that thorough examination found none.*
4. **Reconcile every finding against the artifact text**, first matching class wins:
   **contract misread** (the contract was unclear — fix the contract, re-run) · **actionable**
   (change the pick, re-run) · **accepted trade-off** (real, cheaper to accept — it becomes a cost
   in `costo per opzione`) · **noise** (correct under context the reviewer lacked — note which
   context would have prevented it).
5. **Stop** when a cycle returns only trivial or already-considered findings, or after three
   cycles — then hand the open findings to the founder. Two cycles in a row with substantive
   findings and none classified actionable means the reviewer is being validated, not heard:
   stop and escalate.

Completion criterion: every finding carries one of the four classes, and every accepted
trade-off appears as a cost in the record.

## 2. Sort the statements

Sort every **statement** of the ask, not the ask as a whole; one request usually mixes kinds.
One question decides each: **what does it take to undo this?**

| kind | the test | where it goes |
|---|---|---|
| **decision** | undoing it needs more than a commit: it fixes the shape or meaning of stored data, something a customer signs, sees and relies on, something another system calls, money, a vendor or a legal commitment, or who the product serves. Judge by effect: a one-line flip that lets bad data be stored is a decision | a record, below |
| **spec** | it says how something works or must be built: behaviour, fields, flow, limits, wording, tests. Changing it is normal product work | the area's document (`outputs.spec` in the repository's output map, else the area README) |
| **detail** | a real choice, cheap to undo, with no stored or customer-visible consequence: a name, a placement, a threshold, a tool | the pull request description, or a comment beside the code |

When no statement is a decision, write no record: say so in one line and say where each
statement went. A dated line in the area document keeps a choice from being re-argued without
turning it into a constraint every later agent must obey.

## 3. Admit it — six requirements

A commitment becomes a record only when it meets all six. Check each against the draft and write
the result beside it; a draft that meets them is admitted, one that misses any is answered in the
reply and written nowhere as an authority.

1. **Costly to undo.** The reversibility verdict is `PUBLISHED`, naming which of `(a)`, `(b)`,
   `(c)` fails and why — or it is `OWNED` and the record retires an earlier record by name. An
   `OWNED` choice that retires nothing is undone in one commit: it is a detail, and it goes in the
   pull request or the area document.
2. **Two or more options priced apart.** Each option has a name and a cost that says something
   (`€200/month` is a cost, `TBD` is not); no two options share a name or a cost.
3. **Cites rules this skill defines.** Each rule is written `<file>:<rule-id>` — the rule file's
   name without `.md` ([routing.md](routing.md) lists them) and the heading slug or number
   (`governance:principles-without-enforcement`, `component-boundary:12`) — and each one is a rule
   heading of that file.
4. **Evidence.** What was tried or measured before deciding (`load test, 3 runs`).
5. **Enforcement.** The test, gate or named reviewer that notices a violation. A choice that
   nothing checks binds no one, so it belongs in the area document.
6. **Review trigger.** The outside condition that puts the decision back on the table. When it
   arrives the decision was not wrong: the condition it named arrived.

These six hold the form; whether a `PUBLISHED` verdict is true is the reader's judgement, which
step 1 challenges. Where the repository keeps records with structured frontmatter, the six travel
as the keys `reversibilita`, `options` (`[{"name": …, "cost": …}]`), `rules`, `evidence`,
`enforcement` and `review_trigger`.

## 4. Write it where the repository keeps its decisions

The output map (`outputs.decision`) names the place: an append-only decisions log, a folder of
typed records, or a folder of prose records. **The repository's own convention wins**: write in
the shape its existing records use, name the location in `modalità`, and leave existing records in
the shape they have. One commitment is one record, in one place; `kind: architecture` marks the
architectural ones inside that place.

Where the repository has no shape yet, use these parts, in this order, on about one screen
(60 lines):

1. **Decision** — one or two sentences, only the statements that passed the sort.
2. **Undo cost** — what reversing it takes, naming the stored data, contract or commitment.
3. **Options** — at least two that were really weighed, each with what it costs. "What we did
   before" is an option only with its cost written.
4. **Evidence** — what was tried or measured before deciding.
5. **Reopen when** — the review trigger.
6. **Check** — the enforcement: the command or test that fails when the decision is violated, or
   the named reviewer.
7. **Rules** — the `<file>:<rule-id>` list.
8. Metadata: `status`, `kind: decision`, and the paths it governs — only paths that exist and
   that it really governs.

The how — flow, fields, limits, tests — goes to the area's spec, and the record links it.

**Lifecycle.** A record with Options or Evidence still unfilled is `status: proposed`, and the
missing part says what is missing; ask for it in one line, as a trade-off ("we want X, but we
lose Y: which matters more?"). It becomes `accepted` only when every part is filled. A decision
is never edited into another decision: write a new record whose Options include the old choice
with what it cost, mark the old one `superseded`, link the two, and leave the old text otherwise
untouched.

## Red flags

- An `accepted` record with one option, or with "to be filled" anywhere.
- Numbers of seconds, pixels, items or button labels inside a Decision section — that is spec.
- A record longer than one screen.
- A decision with neither a reopen condition nor a check.
- A pick that reached the record without its challenge, when step 1 applied.
