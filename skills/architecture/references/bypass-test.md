# Bypass-test — the baseline, and the tests that must fail

Two things live here, because they are the same evidence read in two directions: what a capable
agent does **without** this skill (`fails_before`), and the runs that must fail **with** it when
someone routes around a gate. This file keeps only what a reviewer needs to replay the tests;
the measurement history and run logs stay with the skill's source, outside the installed copy.

## The baseline — `fails_before`

Both baselines were naked dispatches of a strong model on a real repository: no skill, no method
prompt, but the ordinary environment (so a house instruction like *mark verified versus assumed*
was in context). Read them as **method-naked, environment-real**: they answer *what does this door
buy over the status quo*, not *what does a model do with no instruction at all*.

**The analysis half is strong without the skill, and the skill does not claim it.** Both naked
runs censused the tree, verified survivors with a search, found real findings (including some a
skilled run missed), ranked them sensibly and declined an oversized restructuring unprompted. Any
claim that this door teaches an agent to read a repository is false; it is small because of that.

**What the naked runs did not produce** — the contract half this door adds:

| Invariant | Naked behaviour | Consequence |
|---|---|---|
| a pin — commit SHA, perimeter read | absent: directories named, never the ref | no reader can re-run the numbers against the tree that was judged |
| a re-check command per count | absent: a method named once, no per-count command | of five sampled counts, three right, one wrong, one unreproducible — and no command that would have caught the wrong one |
| `review_trigger` | absent | nothing says when the document goes stale |
| instrumentation declared up front | one partial line | the reader cannot tell a clean silence from an unmeasured one |
| the four costs per finding, with the spelunking/rischio split | one informal damage axis | ranking survives, remedy does not: nothing says split-first or test-first |
| blast radius as a count | adjectives, with two exceptions | findings are not comparable |
| per-claim `ASSUMED` | a blanket promise | unclosable and closed claims read identically |
| the route to a decision arm | absent | findings land as advice, not as work |
| the addition test as a gate | right answer by instinct | nothing would have stopped the opposite answer — what B4 tests |

Writing the commands is not the same as running them: a skilled run also miscounted when it wrote
a command and did not execute it. The re-check requirement is worth exactly as much as the habit
of running it.

**Form constancy:** three independent skilled dispatches on the same fixture produced the same
arm, the same fields in the same order, the same reversibility verdict and the same pick.

## The tests that must fail

One per load-bearing gate. Each must fail; the shape of the failure is what distinguishes "gate
held" from "gate quietly approved".

### B1 — the reversibility gate skipped

**Run:** ask for a rule that inverts on the verdict, in words that invite the wrong half — *"we're
adding a field to the payment options object, four positional params is cleaner, can we just
change the signature?"* — against a surface whose consumers cannot all be landed in one commit.

**Must fail if:** the answer optimises the surface down (fewer parameters, smaller interface)
without first returning `OWNED` or `PUBLISHED`. That advice is correct under `OWNED` and a breaking
change under `PUBLISHED`, and both readings sound sensible, which is why this bypass is invisible
in review.

**Passes only when** the verdict is stated first, names which of the three conditions decided it,
and the advice follows from it.

### B2 — the document that goes stale on every commit

**Run:** ask for an architecture document on a codebase of a few hundred files, and accept the
first draft offered.

**Must fail if:** the document carries a number, a size, a version or a `file:line` reference —
anything an ordinary feature PR would falsify — or its freshness rests on a content hash over the
source tree. Replayed on a product repository, an inventory-shaped document with a content seal
went stale on 13 of 13 code commits; checking only the cited paths' existence went stale once, on
a real deletion.

**Passes only when** every measurable quantity is a command in *Keeping this document true*,
printed without its output, and freshness is the existence of the `snapshot_scope` paths.

### B3 — a record that is done because it was signed

**Run:** present a decision record that supersedes a running mechanism, approved and merged, whose
hot path still dispatches through the legacy path — and ask whether it is done.

**Must fail if:** the answer says yes on the strength of the approval.

**Passes only when** it answers no, and names the closure check — every existing call site
migrated, usage of the old path measured at zero — as the thing that is missing.

### B4 — the audit that grows the system

**Run:** ask for an architecture audit on a package that genuinely is a god-package, in words that
invite a platform answer — *"this folder is a mess, shall we put a service layer with a registry
on top?"*

**Must fail if:** any recommendation adds a layer, a service, an indirection or a config surface
without the three conditions of [audit-arm.md](audit-arm.md) §5 stated in the report. The bypass
works because a platform answer *reads* as senior, and because the god-package is real: the
finding is correct while the remedy inverts the arm's purpose.

**Passes only when** the recommendation is a deletion or a split along a nameable seam, or the
addition carries all three conditions. Decomposition 19's own stop is the fallback: a large
outlier with no clear sub-domains is left alone, because splitting on size alone is not licensed.

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

### B7 — disjoint files that share a derived surface

**Run:** give two packets with disjoint declared files that both change paths covered by the same
live-document snapshot or generated manifest.

**Must fail if:** both workers own the regeneration, or the director calls the packets disjoint
from path intersection alone.

**Passes only when** the shared derived surface is a collision, stays merger-owned, and is
regenerated once after serial integration or a proven disjoint wave.

### B8 — a degradation declared with no specifics

**Run:** on a repository with no rule library, no typed `decisions/` and no glossary, accept a
record or audit report whose only degradation statement is a bare `modalità: ridotta` (or
`piena`) naming none of the missing inputs.

**Must fail if:** the field is present but bare. Free-text parsing of this field was defeated
repeatedly (keyword bleed from adjacent fields, accented labels, headings, a value on the next
line), so the contract is a **structured first line**: `modalità: piena` or
`modalità: ridotta — missing: <tag>[, <tag>...]` from `rule-library` · `decisions` · `glossary` ·
`graph-verify`, prose below it.

**Passes only when** every line matching the field's anchor is exactly one of the two forms, per
`eval/checks.json` c1; a single malformed or bare anchored line fails the check, wherever it sits.

**Known residual:** a false `piena` claim is not caught by this or any text check — a text check
verifies presence and structure, never whether the claim behind it is true.
