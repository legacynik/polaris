# The plan file

One file per piece of work at `docs/<areas|modules>/<area>/plans/open/<YYYY-MM-DD>-<name>.md`
(operating model §5). Spec and plan in one document: the stable contract lives here, the moving
state (phases, tasks, findings) lives in Beads. `feature_gate.py` parses the frontmatter, the
`## 6. DoD` bullets, the `### Phase N: title` headings under `## 7. Approach` and the
`Beads epic:` line under `## 8. Links` — keep those shapes.

The skeleton is one file for the whole life of the plan: `../../grill/references/plan-file.md`.
`grill` writes sections 1–3 from it at `status: discovery`; this skill fills the rest — the
`tests:` frontmatter key, the `## 6.` DoD bullets, the `### Phase N:` headings with their `- task`
bullets under `## 7. Approach`, and the Links lines (`pour` writes `- Beads epic: <id>`). A plan
that starts here without a grill run copies the same skeleton.

## Rules

- **Tags.** Every claim in sections 3–7 is `assumed` or `proven: <test | receipt | verdict | PR | path>`.
  `check_plan_files.py` refuses a `proven:` path that does not exist.
- **Outcome and DoD** (ex ambitious-goal). Name who benefits and what becomes possible; go one level
  above the request when that clarifies it. Ask one question at a time, only when the answer changes
  outcome, scope or acceptance. Separate required acceptance from stretch; never invent baselines,
  dates or thresholds — without a credible number, an observable condition plus what to measure.
  A DoD of "code written" or "document produced" is not a DoD. Name the environment that counts as
  done (candidate, integrated, released).
- **Read before writing** (gstack /spec). The Discovery section cites the code read and the issue
  search; a plan that cites neither is written from memory.
- **Phases.** Each phase has an observable result and can close on its own checks (model §10). A
  phase that only exists to "set up" is folded into the next.
- **Status moves.** `paused` → the file moves to `archive/paused/` and a bead `kind:idea` keeps the way
  back; `abandoned` → `plan_close.py --abandoned` (archive/ + digest); `done` → only `plan_close.py`.
- **Decisions to enact** get a DEC file through `architecture`, named in Links; `plan close`
  promotes them.

## Writing it — one example per behaviour

These are tools, not a checklist: use the one the plan in front of you needs.

**The owner's words, not a paraphrase.** The founder said: "se una riga ha il prezzo vuoto la
saltiamo". The plan carries `> "se una riga ha il prezzo vuoto la saltiamo" (founder, chat 2026-10-27)`
or `rows with an empty price are skipped (founder: issue #41, comment 2)`. What you add:
`- proposal (agent): log the skipped rows' SKUs in the import summary`. A proposal that changes
scope, cost or a user-visible behaviour is asked, not written in.

**Spec by example.** Not "VAT is applied correctly", but: *net 100.00 → 122.00; net 10.005 →
12.21 (half-up); net 0 → 0.* Not "skipped rows are reported", but: *a 3-row file with an empty
price on row 2 → 2 prices updated, summary "1 skipped: row 2 (SKU A-17)".* Each example is the
acceptance test written in advance: a reader can turn it into an assertion without asking.

**Riskiest first (knock-out).** Name the assumption that, if false, makes the rest worthless
("the supplier's CSV is stable enough to parse"), and make phase 1 prove or kill it on real data.
Building the UI before that is answered spends phases on a plan that may die.

**Pre-mortem.** Imagine it shipped and failed. Write the three likeliest reasons; each one is a
Review Focus line, a DoD line or a risk — not a worry left in your head.

**Loops and delays (Large work only).** After release, what reacts and when? "Suppliers see their
prices change overnight → support tickets the next morning"; "the nightly job's runtime grows
with the catalogue → in a few months it overlaps the 6:00 backup". Name it in the risks with the
delay, so the DoD watches the right moment.

**A code step is a decision.** Not the body:

    def total_with_vat(net): … 9 lines …

but: *`total_with_vat(net: Decimal) -> Decimal` in `pricing/vat.py`; rate 0.22, half-up to 2
decimals (spec §5).* A body appears only for an algorithm the signature and the tests leave open,
or exact copy the spec fixes.

**A test step names the test and its assertions.** Not "write tests for the above", but:
*`test_total_with_vat_rounds_half_up`: `total_with_vat(Decimal("10.005")) == Decimal("12.21")`;
`total_with_vat(Decimal("0")) == Decimal("0")`.*

**Proportion.** Compare the plan with the spec it implements. Several times longer, or mostly
code blocks, is a transcript: replace bodies with signatures, test names and assertions, then
check each step still lets the builder write exactly one reasonable thing. The opposite failure
is a line that decides nothing ("handle edge cases", "TBD", a type no phase defines).
`check_plan_files.py` reports `transcript` when code lines outnumber prose lines.

**Small phases, small steps.** A phase closes on its own tests; a step is one action with a
checkable result ("write `test_x`, see it fail on the missing function" — not "implement import").
The reader writes idiomatic code once given the interface and the test; don't teach them how.

**Review Focus** (a `## Review Focus` section between §6 and §7). The spec says what the software
must do, not everything it will meet; its silence on an input is not permission to crash on it.
Spec: "users upload a CSV `sku,price`". Phases test two valid rows. Review Focus:

    - empty file / header only → "0 rows imported", nothing changed — phase 1: test_import_empty_file
    - price not a number ("12,50") → row rejected with its line number — phase 1: test_rejects_bad_price
    - same SKU twice → last row wins, summary says so — phase 1: test_duplicate_sku_last_wins

Each line's test is added to the phase that owns the code. At most five, most likely first.

**Approval.** "Scope ok" approves the idea. The owner approves the written file: send the path
and the three things to check (DoD §6, Review Focus, the proposals); only then `accepted`.
