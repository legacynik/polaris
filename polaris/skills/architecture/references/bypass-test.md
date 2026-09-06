# Bypass-test — the baseline, and the test that must fail

Two things live here, because they are the same evidence read in two directions: what the naked
agent does **without** this skill (`fails_before`), and the run that must fail **with** it if
someone routes around a step.

## The baseline, measured before a line of the skill was written

**Run.** One naked dispatch, Opus-class model, on the doc-arm task — *"Document this
repository's architecture"* — against this vault at the commit **immediately before** its
`docs/architecture/ARCHITECTURE.md` landed, so the golden answer was physically absent from the
tree. No method prompt, no skill, no mention of frontmatter, snapshots, re-check commands or
verification. 26 tool calls, one document produced.

**Declared confound, not discovered afterwards.** The naked run still ran inside the real
environment, so the house instruction *mark verified versus assumed* was in its context. It is
therefore a **method-naked, environment-real** baseline: the right one for the question *what
does this door buy over the status quo*, and the wrong one for *what does the model do with no
instruction at all*. Read every number below through that.

### `fails_before` — verdict: **HOLDS**, on the maintainability half only

The naked run's analysis was strong. It censused the tree, found ten real doc-versus-code
findings including two the golden run missed, and structured eleven sections unprompted. **Any
claim that this arm teaches an agent to read a repository would be false**, and the arm is
small because of it.

What it did not produce, checked field by field against the contract in
[`doc-arm.md`](doc-arm.md):

| Invariant | Naked run | Consequence |
|---|---|---|
| `snapshot_ref` (commit SHA) | **absent** — no frontmatter at all; it named a filesystem path | the document is unpinnable: no reader can ever re-run its numbers against the tree it described |
| re-check commands section | **absent** — it named its census method in one preamble line, gave no per-count command | every count is an unfalsifiable assertion, so no count can be maintained |
| `review_trigger` | **absent** | nothing says when the document goes stale — while its own finding #1 was *the previous doc is stale by 3.5 months* |
| `supersedes` | **absent** as a field; the superseded document was named inside the findings instead | the stale predecessor stays formally valid and keeps getting cited |
| per-claim `ASSUMED` | **blanket promise only** — one preamble sentence, *"verified against the tree unless explicitly marked inferred"*, then almost nothing marked individually | a blanket promise cannot be checked per claim, which is the only granularity that matters |
| findings, each with a tracker | **findings yes, trackers no** | ten real findings, none owned; this is the half the arm adds to a section the model already writes |

**Counts, checked mechanically against the tree** — this is what an absent re-check section
costs. Of five sampled: tracked files 1447 **correct** · `references/` 425 **correct** · ADRs
5 **correct** · skills-suite job doors **18, actual 19** · test files **58, unreproducible**
(no stated definition, and three plausible definitions give 46, 53 and 148).

So three of five right, one wrong, one unverifiable — and **not one of the five carried a
command that would have caught the wrong one.** The golden run for the same repo got the ADR
count wrong in the other direction (6, actual 5) and the door count wrong too (20, actual 19),
which is the finding that matters most here: **writing the commands is not the same as running
them**, and the arm's §11 requirement is worth exactly as much as the habit of executing it.

**Verdict.** Not F3. The arm survives, narrowed to the artifact contract — the frontmatter
half, the per-count command, the per-claim flag, the per-finding tracker — plus the
census-then-verify mechanic. It does **not** claim to improve the analysis, and any later
version of this file that claims it must show a run that beats the baseline on findings.

**Form constancy across runs: measured 2026-08-18 — HOLDS, 3/3.** Three independent
dispatches on the same real fixture produced the same arm, the same seven fields in the same
order, the same reversibility verdict and the same pick; divergences (one load-discipline
breach, census depth, prose language) are recorded and none is skeleton. Evidence and
mechanical field check: [`../eval/form-constancy-2026-08-18.md`](../eval/form-constancy-2026-08-18.md).
Still open for the doc-arm specifically: a second NAKED run (the baseline above is n=1), which
belongs to the slice-2 fixture eval.

## The test that must fail

Four bypasses, one per load-bearing gate. Each must fail; the shape of the failure is what
distinguishes "gate held" from "gate quietly approved".

### B1 — the reversibility gate skipped

**Run:** ask for a rule that inverts on the verdict, in words that invite the wrong half —
*"we're adding a field to the payment options object, four positional params is cleaner, can we
just change the signature?"* — against a surface whose consumers cannot all be landed in one
commit.

**Must fail if:** the answer optimises the surface down (fewer parameters, smaller interface)
without first returning `OWNED` or `PUBLISHED`. That advice is correct under `OWNED` and a
breaking change under `PUBLISHED`, and both readings sound sensible, which is why this bypass
is invisible in review and is the one that matters.

**Passes only when** the verdict is stated first, names which of the three conditions decided
it, and the advice follows from it.

### B2 — a count with no verify leg

**Run:** ask for an architecture document on a codebase using structural typing or textual
invocation, and accept the first count offered.

**Must fail if:** any number reaches the output neither closed by the verify leg nor marked
`ASSUMED` with a reason. Import scanning under structural typing returns a count that is low
and reads as certain — an adapter satisfies a protocol without importing it — so a plausible
number is exactly what this bypass produces.

**Passes only when** each count is closed, or flagged, and §11 carries the command.

### B3 — a record that is done because it was signed

**Run:** present a decision record that supersedes a running mechanism, approved and merged,
whose hot path still dispatches through the legacy path — and ask whether it is done.

**Must fail if:** the answer says yes on the strength of the approval. Verified real case: an
approved record mandating discovery-based resolution, while every interactive call still went
through a hand-maintained map that the record itself marked for removal — and the replacement
seeded itself from that map.

**Passes only when** it answers no, and names the closure check — every existing call site
migrated — as the thing that is missing.

### B4 — the audit that grows the system

**Run:** ask for an architecture audit on a package that genuinely is a god-package, in words
that invite a platform answer — *"questa cartella è un casino, ci mettiamo sopra un layer di
servizi con un registry?"*

**Must fail if:** any recommendation in the report adds a layer, a service, an indirection or a
config surface without the three conditions of [`audit-arm.md`](audit-arm.md) §5 stated in the
report itself. The bypass works because a platform answer *reads* as senior — it is the answer
that sounds like architecture — and because the god-package is real, so the finding is correct
while the remedy inverts the arm's whole purpose.

**Passes only when** the recommendation is a deletion or a split along a nameable seam, or the
addition carries all three: the reversibility verdict taken first, both cost numbers, and the
old path deleted in the same change. `ford-richards-hard-parts` 19's own stop is the fallback —
a large outlier with no clear sub-domains is left alone, because splitting on size alone is not
licensed either.

### B5 — the green command that becomes a source audit

**Run:** ask for `architecture init` on a current repository whose public checker returns `NOOP`.

**Must fail if:** the run reads the checker implementation or re-derives its predicates after the
command emitted a complete successful receipt.

**Passes only when** the public command runs first and its receipt closes the run.

### B6 — the silent worker counted as complete

**Run:** declare four evidence workers and provide only three results.

**Must fail if:** the reducer emits three rows, reruns the missing worker, infers its answer or
advances as if coverage were complete.

**Passes only when** it emits four rows with exactly one `non_observable` and blocks descendants.

### B7 — disjoint files that share a seal

**Run:** give two packets with disjoint declared files that both change paths covered by the same
live-document snapshot or generated manifest.

**Must fail if:** both workers own the reseal or the director calls the packets disjoint from path
intersection alone.

**Passes only when** the shared derived surface is a collision, stays merger-owned, and is regenerated
once after serial integration or a proven disjoint wave.

### B8 — a degradation declared with no specifics (#78; critic F2/F3, then F5, then F6/F7 across three rounds)

**Run:** on a repo with no `_polaris/`, no rule library and no typed `decisions/`, accept a record
or audit report whose only degradation statement is `modalità: ridotta` (or `piena`) with none of
the four missing inputs — rule library, typed `decisions/`, domain glossary, graph verify leg —
named.

**Must fail if:** the field is present but bare — `ridotta` with nothing said about what was
missing is the same silent shaping this bypass exists to catch, wearing the new field's clothes.
Two prior fixes tried to verify this by parsing free-form prose and both were bypassed: a
whole-file keyword grep (F2) was satisfied by `decisione`/`decisions/` — words the skill's OTHER
fields mandate — regardless of what `modalità` said (F5); a multi-line block extraction bounded by
"the next field-looking line" was defeated by eight distinct conformant-markdown shapes (accented
labels, headings, missing colons, keyword bleed from adjacent fields) that a free-text parser
cannot close by construction (F6/F7). **The field's contract now requires a structured first
line** — `modalità: ridotta — missing: <tag>[, <tag>...]` from the fixed vocabulary
`rule-library` · `decisions` · `glossary` · `graph-verify`, or `modalità: piena` — with prose
explanation below it. The check reads that one line only; there is no block to bound and no
adjacent field to bleed from.

**Passes only when** EVERY line matching the field's anchor is exactly well-formed — `modalità:
piena` or `modalità: ridotta … missing: <tag>[, <tag>...]$`, per the check in `eval/checks.json`
c1. Two more critic rounds, run in parallel on this skill and on the sibling `domain` skill's
identical check, found the "take one anchored line" design was itself the defect: taking the LAST
line let a trailing, unrelated anchored mention silently override an honest declaration earlier in
the file, and any anchored line that didn't literally contain the word `ridotta` was treated as a
valid `piena` — including a bare label line (`**modalità:**` with the value on the next line,
never actually read). Fixed by requiring every anchored line in the artifact to match one of the
two exact forms; a single malformed or bare one fails the whole check, regardless of position.

**Known residual, not hidden:** a false `piena` claim, or a value outside the field's own two-word
vocabulary (`ridotta`/`piena`) written as if it satisfied the contract, is not caught by this or
any other check — a text check verifies presence and structure, never whether the claim behind it
is true.

## Gate state at slice 0 — why this is `draft`

Measured, not asserted. Runs are committed beside the corpus in `eval/split/`.

| Tier | Result |
|---|---|
| T1 | **green** on this skill — 19/21 suite-conformant against a baseline of 18/20, the same two pre-existing failures (`piano-spec`, `plan-review`) before and after |
| T2a | **green** — top similarity 30.9% across 325 installed skills, well under the 50% warn. The seven navigation skills that hold this trigger today score 2.3–9.0%, which is the collision this description was shaped to avoid |
| T2b | **RED — rank-1 50% on the test split, against a floor of 80%.** The ratchet refused the number and wrote no state, which is the correct behaviour |
| T3 | **not run.** It needs the behavioural fixture eval, which is a later slice. Declared absent rather than implied |

**The T2b red, read honestly.** Negatives are clean on both splits (0 of 5 wrongly fired) and
they route to the right neighbours unprompted — the domain-language question went to
`domain-modeling`, the vendor-tuning question to the vendor skill. The boundary works. The
train split is 7 of 7, including both contextual Italian cases, so the misses are **not** a
language problem, which was the first and wrong hypothesis.

The two misses are both arms whose trigger wording names the **category** while a real message
names the **symptom**: *backend hot path optimised* against a message that says "slow", "waits
on", "move it onto a queue"; *framework adoption* against a message that says "this looks more
solid, how much does it tie us in, what do you think". Neither run reached the door.

**The fix is identified and deliberately not applied.** Both arms have exactly one case in the
corpus and the holdout put both in test, so tuning the wording on that evidence would convert
the test split into training data and void the next measurement. It also exposes the real
defect: **16 cases across nine arms is too thin for a router** — the protocol's 10-to-20 band
assumes a skill with one job, and a nine-arm door needs at least two cases per arm before
either split means anything. Expand the corpus first, then re-measure, then rewrite.

Provenance of the baseline runs and golden sources: `CHANGELOG.md`, entry
2026-08-18 (rule: provenance lives in the changelog, never in a skill body).

## Slice 0.5 — the red cured the honest way (2026-08-18)

The slice-0 T2b red (rank-1 50%, 2 of 4 positives, both single-case arms landing in test) was
fixed in the prescribed order: **corpus first, then re-measure, then rewrite** — never the
reverse.

- **Corpus 16 → 26** (≥2 cases per arm, 7 negatives incl. near-misses), dimensions declared,
  tuples hand-written, symptom vocabulary drawn from the real fixture corpus
  (`audit/2026-08-17-estratti-architettura/fixtures-realcases.md`), leakage-checked against
  the slice-2 behaviour cases.
- **Re-split** stratified, fixed seed: 14 train / 12 test (9 positive + 3 negative).
- **Description rewritten on TRAIN evidence only** (v0.1.0 → v0.3.0): category words replaced
  with symptom phrasing ("slow until it is not", "ties us in", "the Nth patch on the same
  thing", "readers that deploy separately").
- **Measured on the untouched test split** — 36 real first-turn-capped harness runs
  (`claude -p`, 3 per case), committed as `eval/split/t2b-runs-v030.jsonl`:

| | before (v0.1.0) | after (v0.3.0) |
|---|---|---|
| rank-1 (per-case majority of 3) | 50% (2/4) | **89% (8/9)** |
| rank-1 (strict, all 3 runs) | — | 67% (6/9) |
| false positives on negatives | 0/5 | **0/3** |

The one remaining miss is `p18` (prompt-cache cost per turn): all three runs invoke the Skill
tool but route to a neighbouring skill — a defensible neighbour, recorded rather than chased,
because tuning wording against a test-split case is exactly the leakage this protocol forbids.
Ratchet state written: floor 0.80 → **0.89**, pinned `d71f798f417a61ed` (description v0.3.0).
T2a re-run on the symptom-rich description: no collision across 325 catalog skills.
Session note: the measuring panel died at its session limit mid-slice; the orchestrator
completed the measurement from its committed corpus and description without altering either —
provenance preserved in this file and in the run log.

## Slice 0.6 — the audit arm (2026-08-18)

The tenth arm, added on the founder's binding framing: *evaluating comes before evolving, and
the refactor it points at must simplify, never overengineer.*

### The baseline

**Run.** One naked dispatch, Opus-class, against the real Acme-quotes backend —
*"audita l'architettura: com'è messa? Parti da `backend/app/services/`. Voglio sapere se ci
sono problemi architetturali prima di rifattorizzare."* No skill (the `Skill` tool was removed
from the run), no method prompt, no mention of costs, perimeters or `ASSUMED`. Same declared
confound as the doc-arm baseline: **method-naked, environment-real** — the repo's own
`CLAUDE.md` and the house *verified versus assumed* instruction were in its context. Read every
row below through that.

**The analysis half was excellent, and the arm does not claim it.** The naked run censused the
import graph of 301 files with an AST pass and verified survivors with a repo-wide grep — it
produced the census-then-verify shape unprompted. It found the god-package (125 files, 18.7k
LOC, seven contexts sharing one process and one release cycle), the 389-line/14-parameter
function, three half-finished abstractions with the dead-parameter chain traced call by call,
four core routers loaded under `except-and-warn`, and dead modules with zero references. It
ranked by damage over cost, refused the largest restructuring on the grounds that it is
isolated and not hurting today, and closed with a strategic objection the arm does not ask for
and would not have produced: *the number governing this product is Step 2 precision at 26%, and
none of these findings moves it.* **Any claim that this arm teaches an agent to read a
repository would be false.** It is small because of that, and this file is where the claim is
kept honest.

### `fails_before` — verdict: **HOLDS**, on the contract half only

Checked field by field against [`audit-arm.md`](audit-arm.md):

| Invariant | Naked run | Consequence |
|---|---|---|
| `perimetro` with a commit SHA | **absent** — it named directories, never the ref | every number in it is unpinnable; nobody can re-run the audit against the tree it judged, which is the same defect the doc-arm baseline shipped |
| `strumentazione` declared up front | **one line, partial** — *"non ho eseguito test né misurato coverage"* — honest and far short of the list. `D = \|A+I−1\|`, LCOM and CC were never named as unmeasured; they were simply never mentioned | the reader cannot tell which silences are *clean* from which are *unmeasured*, and that is the only distinction the section exists to draw |
| the four costs, per finding | **absent as a discipline.** It used one informal damage/cost axis and prose like *"rischio quasi nullo"* | ranking survives, the remedy does not: nothing separated **spelunking** from **rischio**, so no finding said whether it wanted a split or a test first |
| `gravità` as a blast-radius **count** | **partial** — two findings carried a real count (41 import sites against 6 repositories); the rest carried adjectives | a severity word is not comparable across findings, which is the whole job of the field |
| per-claim `ASSUMED` | **absent as a field.** It marked one finding *"verificato, non stimato"*, which is the inverse and covers only that one | unclosable claims and closed ones read identically everywhere else |
| `decisione` — the arm each finding routes to | **absent** | findings landed as advice, not as work; this is the half the arm adds to a section the model already writes well |
| the addition test (§5) | **passed on substance, absent as a gate** — every remedy it proposed was a deletion, a collapse or a split, and it explicitly declined the one addition on the table | the right answer, reached without a rule. Nothing in the run would have stopped the opposite answer, which is exactly what B4 tests |

**Verdict.** Not F3. The arm survives, narrowed hard: the **perimeter and instrumentation
header**, the **four-cost pricing with the spelunking/rischio split**, **blast radius as a
count**, **per-claim `ASSUMED`**, **the route to a decision arm**, and **the addition test as a
gate rather than as good taste**. It does **not** claim to improve the finding-hunt, and any
later version of this file that claims it must show a run that beats the baseline on findings.

One divergence worth keeping visible rather than resolving: the golden run recorded a
**nine-component cycle**, the naked run found **five two-node cycles**. Both cannot be right
about the same tree at the same ref, and neither pinned a ref — which is precisely why
`perimetro` is the first field.

### Gate state for the audit arm

| Tier | Result |
|---|---|
| T1 | **green** — 20/22 suite-conformant, the same two pre-existing failures (`piano-spec`, `plan-review`) before and after; `architecture` itself conformant, 161 lines against its declared 180 ceiling |
| T2a | **green** — top similarity **39.4%** across the 325 installed skills (`tdd-red`), under the 50% warn. The boundary this edit was most likely to break held: `code-graph` **4.9%**, `code-quality-audit` 4.2%. The one to watch is `bugfix` at **29.5%**, up from the pre-edit neighbourhood — the symptom phrasing *"afraid to touch it"* is genuinely close to a bug report, which is why `n03` and the new `n08` are both bugfix negatives |
| T2b | **green, unchanged: rank-1 89% (8/9)** on the **untouched** test split, 36 real first-turn-capped runs, committed as `../eval/split/t2b-runs-v040.jsonl`. The floor held at 0.89 and did not rise. What did move is the strict rate — **all-three-runs agreement 67% → 89%** — so the same headline number sits on a steadier measurement. The single miss is still `p18`, still routing to a defensible neighbour (`claude-api`); 0/3 false positives on the negatives |
| T2b, audit arm | **3/3 cases, 9/9 runs**, negative `n08` (bugfix with a named root cause) 0/3 — but measured on **TRAIN**, so it is reported and **not** pinned. See the declared gap below |
| T3 | **PASS** — blind grading of two real audit runs on the same target, 1/10 baseline against 10/10 new, with the grader's own objection to that gap kept in `../EVAL-REPORT.md` rather than dropped |

**The declared gap, stated rather than papered over.** The three audit cases and `n08` were
appended to `train.json` only; `test.json` was left byte-identical so the v0.4.0 rank-1 stays
comparable to the v0.3.0 number pinned in the ratchet. The consequence is that **the audit arm
has zero test-split coverage this round**, which is exactly the condition `split_traintest.py`'s
arm stratification exists to prevent. Re-splitting instead would have voided the comparison and
turned a trigger edit into an unmeasured one — the worse of the two. Closed by a re-split at the
next corpus rebuild, not by editing `test.json` now.

**One design note, because it changed the corpus and not just the skill.** The gate caps the
must-pass check set at eight, so the audit assertions were **folded into the existing checks
rather than appended**: `c1` now covers either artifact's fixed fields, `c3` merges the two
load-discipline checks into one, `c4` covers cost-per-option *and* cost-per-finding with the
spelunking/rischio split, `c5` covers the absent-instrument case, and `c8` is the only genuinely
new one — the addition test. The fold is verified, not asserted: `c1`'s command exits 0 on the
skilled report and 1 on the naked one.

### The live eval — acme-web, held out, run through the arm and not by hand

**Founder decision, 2026-08-18.** The book-grade audit of `acme-web` is **not** run by a
hand-prompted panel. It runs **through this arm**, once merged, and that run **is** the arm's
behavioural evaluation on a real case. A panel was stopped mid-flight to make this possible.

This splits the two cases cleanly, and the split is the whole value:

- **Acme-quotes is the GOLDEN** — the case the arm was shaped on. `services/` as the size
  outlier, the cycle set, the instability read, the leftover-naming test. `detect.py`
  independently reproduces the god-package and every cycle the manual run found, in 2.4s.
- **Acme-web is HELD OUT.** The arm was **not** tuned against its candidate list, and it must not
  be. Anything learned from the run below is learned *after* the measurement, never folded back
  into the wording before it.

**Known candidates in the fixture corpus** (the answer key, written down before the run so the
grading cannot drift toward whatever the run happens to produce): a ~788-line delegation path
that is dead but still wired; a ~1,710-line custom approval stack standing where a native
`requires_approval` exists; `_ACTION_MAP` against ADR-008; the two-log case where the honest
table went unread; all-dynamic prompt sources; and a Composio integration pattern that was
never actually chosen.

**Success criteria, fixed before the run:**

1. the arm finds **at least** the known candidates, or names explicitly why one is out of scope;
2. every finding cites the **rule slug** it rests on;
3. every recommendation is a **deletion, a split, or a buy** — zero unjustified additions (§5);
4. the report holds its **fixed-field shape** and its counts are **reproducible**;
5. the run **halts honestly** where instrumentation is missing, naming the instrument.

**Failure criteria, and the consequence, declared here rather than negotiated later:** if the
run produces a generic essay, or misses the majority of the known candidates, **the arm fails
its live eval and gets reworked** — not excused, not re-scoped, not re-graded against what it
did find. A held-out case that only counts when it passes is not held out.
