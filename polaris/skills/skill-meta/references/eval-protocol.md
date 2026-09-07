# Eval protocol — measure it, do not declare it

Everything needed to evaluate a skill, with no other source. The prose bar is
`design-bar.md`; this is the behaviour bar.

## Contents

- [The two stored artifacts](#the-two-stored-artifacts)
- [Building the prompt set — dimension, tuple, query](#building-the-prompt-set--dimension-tuple-query)
- [How many cases is enough](#how-many-cases-is-enough)
- [T2b — rank-1 on the TEST split](#t2b--rank-1-on-the-test-split)
- [The modification gate](#the-modification-gate)
- [T3 — the behaviour rubric](#t3--the-behaviour-rubric)
- [Running T3 — three arms and one fresh critic](#running-t3--three-arms-and-one-fresh-critic)
- [Pressure cases, for skills that impose a discipline](#pressure-cases-for-skills-that-impose-a-discipline)
- [Model-graded checks — the judge discipline](#model-graded-checks--the-judge-discipline)
- [Correcting a judge's number](#correcting-a-judges-number)
- [Leakage — the silent invalidator](#leakage--the-silent-invalidator)
- [Judge drift and model pinning](#judge-drift-and-model-pinning)
- [This is CI, not a quality measure](#this-is-ci-not-a-quality-measure)
- [Advanced signals](#advanced-signals)
- [Declared cost](#declared-cost)

## The two stored artifacts

Every skill in the suite owns two eval artifacts, stored beside it and committed:

```
<slug>/eval/prompts.json    the routing corpus  — does the right skill fire?  (T2a/T2b)
<slug>/eval/checks.json     the behaviour rubric — did the run come out right? (T3)
```

They are stored, not improvised per session. That is what makes the modification gate
possible: a later edit is measured against **the same corpus**, so two rates are comparable.
An eval set rebuilt for each run measures a moving target.

## Building the prompt set — dimension, tuple, query

Do **not** ask for "15 test queries for this skill". That yields four paraphrases of one
capability — "check my skill", "validate my skill", "review my skill", "look at my skill" —
and a rate of 100% on a corpus that tests one thing. Three ordered steps instead:

1. **Name the dimensions**: the axes along which a real request varies. Three sufficiently
   different axes are enough to start; add more when you learn where it actually fails.
   Choosing dimensions *is* choosing where you expect to fail. For a skill gate the axes are
   typically: which branch of the job (write / edit / evaluate / promote), who is asking (the
   founder mid-session, a panel executing a plan, a teammate who has never seen the suite),
   and how the request arrives (names the skill / names the job / buries it in context).
2. **Write the tuples by hand** — one value per dimension, e.g. `(edit, panel, buries it)`.
   Hand-write them: doing so is how you discover which combinations you had not thought
   about. This is the step that cannot be delegated.
3. **Turn each tuple into a prompt in a separate pass**, one at a time. The tuple constrains
   the prompt so it cannot collapse into paraphrase. Throw away and regenerate any prompt
   that reads awkwardly or drifts off its tuple — quality control here pays compound
   interest, because every later number is computed on this corpus.

Schema:

```json
{"skill": "<slug>",
 "cases": [
   {"id": "p01", "should_trigger": true,  "kind": "explicit",
    "prompt": "run skill-meta on bugfix"},
   {"id": "p02", "should_trigger": true,  "kind": "implicit",
    "prompt": "I rewrote the description of the bugfix skill, is it safe to install?"},
   {"id": "p03", "should_trigger": true,  "kind": "contextual",
    "prompt": "the review door keeps losing the trigger to plan-review, fix its wording"},
   {"id": "n01", "should_trigger": false, "kind": "negative",
    "prompt": "review this pull request before I merge it"}
 ]}
```

- **Three positive kinds, all mandatory** — one untested invocation style is one routing
  failure you never see. `explicit` names the skill; `implicit` names the job in the user's
  own words; `contextual` buries the trigger in a realistic message with other content, file
  paths, typos and the founder's actual phrasing.
- **At least three negative controls** (`should_trigger: false`). Negatives catch trigger
  theft, the failure a positives-only set is structurally blind to: a description that fires
  on everything scores 100% on positives. At least two must be **near-misses** — the adjacent
  job a sibling door owns (`review`, `plan-review`, `bugfix`) — because that is where theft
  actually happens. `T2a` only measures text similarity; this measures behaviour.
- Never a placeholder prompt, never a duplicate: both inflate the rate without adding
  evidence, and `change_gate.py` fails on either.

## How many cases is enough

10 to 20 for a door with one job. Fewer and the rate is noise; more and nobody re-runs it.

**The band scales with the arms, because both of its halves do.** A door that routes N distinct
triggers needs `2N` cases before either split means anything, and stops being cheap to re-run
around `3N`, so `change_gate.py` reads `dimensions.arm` from the corpus and refuses a set
outside `max(10, 2N) – max(20, 3N)`. Declare no arms and you get the original 10-20.

The number that forced this is worth keeping: `architettura` measured 50% rank-1 on 16 cases
over nine arms, and the two failing arms had exactly one case each, both of which the shuffle
put in test. At that density the rate moves on which arm the seed happened to hold, not on the
description — so the first honest response to a red is to check the density before touching a
word of the wording.

The principled version of the same number, for a skill whose failures you are still
discovering: keep adding cases until you have **at least 20 problematic runs recorded and new
failure modes have stopped appearing**. That is the stop rule — saturation, not a quota. And
when you have real failures to mine, do not invent the categories first:

1. Read the failed runs end to end, from the user's point of view, and write a short freeform
   note on the **first** thing that went wrong. No causes, no fixes, no grouping yet. This
   step is yours, not a model's — it needs your taste about what counts as failure.
2. Only then cluster the notes into named failure modes. Split two that look alike when they
   have different causes and need different fixes; merge two you cannot tell apart reliably.
3. Each named mode earns a case in the corpus, and at most one judge (below).

Generic categories borrowed from papers — "hallucination", "instruction following" — sound
reasonable and miss everything specific to this skill.

## T2b — rank-1 on the TEST split

**Before rewriting anything because of a red: diagnose where the misses ROUTE.** If they go to
another door that claims that territory in its own description, the corpus is wrong, not the
skill. Reclassifying a case demands the routing proof attached to the case itself; and the
proof that the reclassification is honest rather than convenient is that **the negatives stay
clean** — moving a case out of the positives raises the score mechanically.
*(2026-08-19, twice in one day: one red was a rounded floor plus a case that belongs to
`claude-api`; the other was two architecture cases filed in `domain`'s corpus. Neither was the
skill, and a rewrite was about to start on both.)*

**Declare the expectation before the run**, and record the outcome as verified rather than
assumed. **Read every flagged match** — template echoes and quoted counter-examples masquerade
as hits, and automated counts overstate failure and success alike.

**Never report a raw rate, and never store a floor rounded up.** With a small test split the
confidence interval is wide enough that the ratchet ends up comparing noise, and a floor
rounded up locks the gate at perfection. *(2026-08-19: floor `0.89` was the previous
measurement, 8/9 = 0.8889, rounded. On nine positives only 100% could pass — the ratchet had
closed on itself.)* **Every pinned rate carries the model that measured it**; numbers taken
with different models on different days must not be compared in silence.

```bash
python3 scripts/split_traintest.py eval/prompts.json --out-dir eval/split/   # holdout .4, seed 42
```

Then, for **every** query in `eval/split/test.json`, three real runs — one sample of an LLM is
noise, and single samples lie. The orchestrating agent drives its own harness
non-interactively (`claude -p "<query>"` on Claude Code, the equivalent on Codex/Hermes/Pi)
and observes whether the skill tool is **actually invoked**, not whether the answer looks
relevant. Capping the run at its first turn is enough: routing is decided there, and the cap
is what makes the measurement affordable.

```
rank-1 rate = positive queries where the skill fires first / total positive queries
```

measured on `test.json` only, then handed to the ratchet **pinned to the description it was
measured on**:

```bash
python3 scripts/trigger_ratchet.py --slug <slug> --rate <rank1> \
  --state references/ratchet-state.json --measured-on eval/split/test.json --skill . \
  --model <model> --input-tokens <n> --output-tokens <n> --wall-ms <n> \
  --valid-runs <n> --excluded-runs <n>
```

`train.json` exists only to iterate on the wording — try variants, see where they fail. Never
to produce the number that sets the floor. Two physically distinct files, rather than one
shuffled set, are the mechanism that keeps that honest; `--measured-on` is the tripwire on
top of it.

The floor rises, never falls. A regression fails the gate; it does not lower the bar.

**A floor measured by another model is not a bar this run can clear — it is a different
bar.** `trigger_ratchet.py` re-baselines instead of failing when the receipt on record
names a different model than the one measuring now (or names none at all), writes the old
floor and model into `superseded_floor` / `superseded_model`, and says `RE-BASELINE` out
loud. The next run on the same model is judged normally, so a genuine regression is red
again immediately. Without this the arrival of the cheap proxy turned `architecture` and
`review` permanently red at a rate their **unchanged** descriptions already produced —
a stale bar reading as a regression is the fastest way to a gate somebody switches off.

## Calibrating the cheap proxy

Three full harness runs per case is what stopped anyone re-running T2b, so eleven
descriptions sat over the budget with the debt declared rather than paid.
`scripts/rank1_cheap.py` is the affordable stand-in: the whole catalogue goes into one
prompt, a cheap model names the skill it would reach for first, one call per query. A
proxy is worth exactly its calibration, so it carries one — measured 2026-09-06 on
`architecture`, whose test split holds 8 positives:

| Arm | Definition | rank-1 |
|---|---|---|
| proxy, `claude-haiku-4-5-20251001` | the model ranks the 82-skill catalogue in one call | 7/8 = 0.875 |
| real harness, `claude-sonnet-5`, 3 runs per case | first `Skill` invoked in the run | 7/8 = 0.875 |
| real harness, `claude-haiku-4-5-20251001`, 3 runs per case | first `Skill` invoked in the run | 0/8 = 0.000 |

Per-case agreement between the proxy and the Sonnet arm is 8/8, including the same
single miss (`p19` routes to `doc-truth` in both). The declared band was ±1 case; the
delta is 0. **Two conditions make that number honest, and neither is optional.**

**Count the first SKILL invoked, not the first tool of the run.** The literal reading of
rank-1 — `first tool == Skill` — measures 0/8 here on every arm, because the founder's
global `CLAUDE.md` mandates a polmem `Bash` call before anything else. Under that rule no
run can ever have a skill as its first tool, so the literal metric reports zero for a
description that routes perfectly and would rank a rewrite that made things worse exactly
the same. Read the first `Skill` block in the run instead, with a cap on tool calls so a
run that never routes still terminates.

**Run the real arm on a model that invokes skills at all.** Haiku 4.5 ranks descriptions
as well as Sonnet does when asked to rank them — that is the proxy — and reaches for the
`Skill` tool once in 24 runs when left to decide for itself. Those are two different
quantities, and using Haiku on both sides of the calibration would have produced a 0/8
versus 7/8 disagreement that says nothing about any description. Re-run this calibration
after any model change, on both sides.

It also stops rising at `FLOOR_CAP = 0.95`. A floor at 100% turns one flaky sample into a
permanent red, and a permanently red gate is a gate that gets switched off — and it claims a
precision the corpus cannot back: with four positives in the test split the smallest
observable change is 25%. The cap is honesty about resolution, not leniency; the recorded
`last_rate` still keeps the real number. The same state row stores the model, input/output tokens,
`wall_ms` and valid/excluded run counts; a pin without that cost receipt is incomplete.

## The modification gate

Creation happens once, editing happens forever, so the gate that matters is the one on the
edit. `change_gate.py` classifies the change and names the tiers it owes — deterministically,
from the diff, never by asking anyone what they think they changed.

| What moved in the diff | Class | Owes |
|---|---|---|
| `description`, `name`, `auto`, `user-invocable` | TRIGGER | T1 T2a T2b |
| the `◇`/`✦` mark alone | MARK | T1 + a receipt row naming the slug |
| `io`, `lifecycle`, `invokes`, `invoked-by` | BEHAVIOUR | T1 T3 |
| a body line carrying a command, a path, a table row or a hard rule | BEHAVIOUR | T1 T3 |
| runtime bundle files under `scripts/`, `references/`, `assets`, `templates` | BEHAVIOUR | T1 T3 |
| body prose only | PROSE | T1 (exit 3) |
| whitespace or reordering | COSMETIC | T1 |
| no previous version on record | NEW | T1 T2a T2b T3 |

`version:` is deliberately excluded: every change bumps it, so it discriminates nothing.

**The receipt is pinned to the description.** When T2b records a rate it stores the sha256 of
the description it measured. `change_gate.py` compares that pin to the file on disk, so a
green cannot travel across a trigger edit — the bypass that used to work (B5). A hash, not an
mtime: no clock to fool, no touch to game. The promotion mark is excluded from the hash, so
promoting a skill does not void its measurement.

**Enforcement is always red plus a comment, never blocking**, outside the suite's own CI and
the AFK pipeline where nobody reads a red. `change_gate.py` exits 1 so a runner can see it;
what it protects is promotion and install, not the save.

## T3 — the behaviour rubric

`eval/checks.json` — every entry is must-pass, which is why the list stays short (max 8,
enforced):

```json
[
 {"id": "c1", "category": "outcome",    "assertion": "the EVAL-REPORT block exists with a VERDICT line",
  "cmd": "grep -q '^VERDICT: ' EVAL-REPORT.md"},
 {"id": "c2", "category": "process",    "assertion": "T1 ran before the description was rewritten",
  "cmd": null},
 {"id": "c3", "category": "style",      "assertion": "the report ends on the exact sentinel"},
 {"id": "c4", "category": "efficiency", "assertion": "no more than 12 tool calls, no repeated identical command"}
]
```

Four categories, and the list stays small on purpose:

- **outcome** — the task actually got done. At least one is mandatory: process without outcome
  grades ceremony.
- **process** — the right steps, in the right order, with the right tools. Where a discipline
  skill lives or dies, and only checkable from the trace.
- **style** — the output contract held: the declared block, the fixed fields, the sentinel.
- **efficiency** — no thrashing: a tool-call ceiling, a token budget, no loop repeating the
  same command. Add one only where thrash is a real risk for that skill.

**Every check is binary — pass or fail, never a 1-5 score.** A forced binary decision is
reproducible; a rating without a detailed rubric produces disagreement between two readers and
between two runs of the same judge, and the disagreement is invisible in the average. If a
finer scale is genuinely unavoidable, every point on it needs its own worked example.

**Deterministic graders first.** A check with a `cmd` is decided by running the command; only
what no command can decide goes to a judge. `change_gate.py` reports CONCERNS when no check
carries a `cmd`, because a rubric riding entirely on a model is a rubric whose failures are
unreproducible. Order: parse the trace for command presence and order, check the files that
should exist, and only then ask about quality.

## Running T3 — three arms and one fresh critic

1. **Same turn, never in sequence.** The orchestrator dispatches three arms in one
   response: *baseline* (without the skill, or with the previous version when optimising an
   existing one), *donor* (the strongest applicable donor opened during admission), and *new*
   (with the skill under test), on the same behavioural tasks. These
   are tasks to execute, not the routing queries of T2b. Sequential runs introduce temporal
   drift — context, model and system instructions can move between them — so it is no longer
   the same experiment.

   **The baseline must run where the skill is NOT reachable.** Otherwise it is not a
   baseline: the skill sits in the PATH, the agent finds it unprompted and uses it. Isolate
   the search path, and read the baseline's own output for any mention of the skill before
   trusting the comparison. *(2026-08-19: the "blind" arm opened the skill on its own
   initiative and said so in its answer. Unread, the verdict would have inverted to "the
   naked model matches it, so F3, it buys nothing".)*

   **How the verdict returns is part of the verdict.** The judge's contract **and** the
   channel it reports through are written in a file the subagent reads (`agents/`), never
   left in the dispatcher's head. *(2026-08-19: four subagents dispatched, none delivered —
   plain text does not reach the orchestrator. Whoever retries gets a different result, or
   none.)*

   **Report cost beside quality.** Cost is a separate gate, never folded into the quality rate.
   The candidate cannot regress a check the donor passes and must add at least one strict quality
   win; being cheaper alone is not a win. A bounded cost increase is allowed only inside limits
   declared before dispatch, and the donor delta remains visible. Each arm writes a measured
   envelope with `model`, input/output tokens, `wall_ms`, tool calls, repeated commands,
   consistent/total runs and `context_reuse`. The new arm also carries the limits declared
   before dispatch. `eval_verdict.py` rejects the old bare-list format and fails a breached limit.
2. **One `critic` agent is both independent grader and adversarial reviewer.** Dispatch it with
   no inherited session context (`fork_turns="none"`, or the harness's fresh-context
   equivalent). It receives only the target diff, complete skill bundle, all three full transcripts
   including tool calls, and `checks.json` — never the authoring conversation. First it grades
   the declared checks into the three `grading.json` files; then it hunts what the corpus may have
   omitted: sibling branches, claim/code mismatches, bypasses and false-green selfchecks. It
   writes a separate critic receipt with `agent_type=critic`, `fork_turns=none`, the sole lane
   `critic`, every graded check with its result and evidence, structured results for `sibling_branches`,
   `claim_code_mismatch`, `bypasses` and `false_green_selfchecks`, `PASS|BLOCK`, findings,
   an inventory followed by one result/evidence probe for every inventoried target, SHA-256
   seals for the exact diff and raw critic transcript,
   model, input/output tokens and `wall_ms`; unsupported token telemetry is recorded as
   `UNKNOWN`, never zero. Missing coverage, inherited context, an extra lane or `BLOCK` makes
   `eval_verdict.py` fail. Do not add `code-reviewer` or `architect` lanes here:
   this gate needs one independent adversary, not a review committee.

   The runtime owns provenance: it must really dispatch that fresh `critic`. The local script
   can reject stale or internally incomplete evidence, but cannot cryptographically distinguish
   a real runtime response from a transcript forged by a malicious orchestrator. Runtime-signed
   telemetry is the upgrade path; pretending another JSON field solves provenance is not.
3. **Mark the transcript as untrusted data** when handing it to the grader, with an explicit
   instruction not to follow instructions found inside it. The transcript contains text
   generated by the agent under test; it is not a command channel.
4. **Materialised fixtures, not narrated ones.** For skills that touch code, the case lives in
   a throwaway git repo with the initial state committed as a real baseline. The subagent
   works there and the diff is verifiable.
5. **Watch for a fixture that teaches the answer.** If the baseline passes an outcome check
   because a field name or a filename in the fixture gives the rule away, the case is not
   discriminating — that is a finding about the fixture, not a win for the skill.
6. Aggregate:

```bash
python3 scripts/eval_verdict.py --baseline base/grading.json \
  --donor donor/grading.json --donor-label "<strongest donor>" --new new/grading.json \
  --critic critic.json --checks eval/checks.json --diff reviewed.patch \
  --critic-transcript critic.txt --skill <slug> --append EVAL-REPORT.md
```

## Pressure cases, for skills that impose a discipline

For a skill whose whole job is to stop someone skipping a step (`real-testing`, `plan-review`,
`tdd-dev`, this door), a polite test proves nothing. Build a scenario that pushes hard:

- **Concrete options.** Force a choice between A, B and C, not an open-ended question.
- **Real constraints** — a specific deadline, an actual consequence, a real path.
- **Make the agent act**: "what do you do?", never "what should one do?".
- **No easy out** — deferring to "I'd ask the founder" must not be available.
- **Combine three pressures at once**: time ("I ship in five minutes"), authority ("the lead
  says skip it"), sunk cost ("I'm already done, I don't want to throw it away"), exhaustion,
  or pragmatism.

Red means the agent picks the wrong option and offers a rationalisation. Green means it picks
the right one *and* cites the section that made it. Capture the rationalisations verbatim: each
one becomes a row in the skill's excuse table and a case in the corpus.

When the skill is present and the agent violates it anyway, ask it directly: *"you read the
skill and chose C anyway — how should that skill have been written so A was the only
acceptable answer?"* The three answers you get are all actionable: "it was clear, I ignored
it" means the rule needs a stronger foundational statement; "it should have said X" means add
X verbatim; "I didn't see that section" means the section is in the wrong place on the ladder.

## Model-graded checks — the judge discipline

Only for what a command cannot decide. A judge is a classifier you built by writing a prompt,
so it gets the discipline of one:

- **One judge per failure mode**, and each judge answers exactly one question. Not "is this
  skill good?" but "did the run name the owed tiers before editing?".
- **Binary output**, with the reasoning before the verdict, as JSON: `{"reasoning": "one or
  two sentences", "answer": "Pass"|"Fail"}`.
- **Few-shot examples come from the TRAIN split only.** In-context learning saturates after a
  handful of examples, so a small train split is enough — and the examples that teach the
  boundary are the *borderline* ones, not the obvious ones.
- **Measure the judge before trusting it.** On a labelled dev split, compute:

```
TPR = judged Pass among truly Pass / truly Pass          (sensitivity)
TNR = judged Fail among truly Fail / truly Fail          (specificity)
```

  Target above ~90% on both. Below that, fix the prompt — do not report the number.
- **A trace used in the prompt is excluded from the evaluation set.** Otherwise TPR and TNR
  look excellent because the judge memorised, and the whole measurement is void.

Known biases worth designing around: judges favour the first option presented, reward longer
answers, and prefer output from their own model family. Randomise order, cap length, and never
let the model under test grade itself.

## Correcting a judge's number

A judge with 90% TPR and 90% TNR is wrong on one call in ten, so its raw pass rate is not the
skill's pass rate. Never report the raw number on unlabelled runs. Correct it:

```
θ̂ = (p_obs + TNR − 1) / (TPR + TNR − 1)
```

- `p_obs` — the observed pass rate: runs judged Pass / runs judged.
- `TPR`, `TNR` — measured on the held-out labelled split, not the one used to write the prompt.
- `θ̂` — the corrected estimate. Clip it to `[0, 1]` for floating-point noise.

**The formula is invalid when `TPR + TNR ≈ 1`** — the denominator goes to zero because a judge
at chance carries no information, and no arithmetic recovers a signal that is not there. Fix
the judge instead.

When the number is load-bearing, put an interval on it: resample the labelled split with
replacement, recompute TPR and TNR on each resample, recompute θ̂, and take the 2.5th and
97.5th percentiles. A low TPR shows up here as a very wide interval, which is the honest
reading — improving TPR narrows it faster than anything else.

For a skill gate this machinery is usually overkill: prefer a `cmd`. It earns its cost only
when a number gets quoted to someone making a decision.

## Leakage — the silent invalidator

The most common way a corpus is quietly voided: a case from it ends up inside a prompt, a
few-shot example, or the skill body itself. That case no longer tests anything — the answer is
in the question — and the rate goes up while the skill gets no better.

Keep the corpus in `eval/`, separate from every prompt and from `SKILL.md`, and check it
mechanically on every change: if a prompt string from `eval/prompts.json` appears verbatim in
the skill body or in a judge prompt, that is leakage, not coverage. A suspiciously perfect
judge is the symptom to distrust first.

## Judge drift and model pinning

Two independent things move under you: the provider updates the model behind an unversioned
name, and your own sense of "correct" shifts as you see more real runs. Both change the score
without anyone changing the skill, which makes the regression almost undiagnosable.

- **Pin exact model versions** in the harness — the dated identifier, never the floating alias.
- **Revalidate a judge every few weeks**: label a handful of fresh runs, recompute TPR and TNR,
  check the interval is still tight. If either has dropped, fix the judge before reading its
  output again.
- **Revalidate after any model change**, including one you did not ask for.

## This is CI, not a quality measure

The stored corpus is a smoke test. If it fails, something is definitely wrong. If it passes,
nothing known has broken — and that is all it says. It does not measure whether the skill is
good, and it cannot: it only holds failures someone already thought of.

The failures nobody thought of come from **reviewing real invocations**. The lifecycle already
declares the drain: the weekly `sleep-optimize` pass samples actual uses of the skill —
including a genuinely random slice, not only the ones that looked wrong, because the random
slice is the only unbiased view — and every new failure mode it finds becomes a corpus case
with `fails_before` set to the current version. The corpus grows from real failures, never
from imagination.

## Advanced signals

Add one only when it maps to a failure this skill can actually have; a signal nobody acts on
is sediment in the rubric.

| Signal | Read from | Add it when |
|---|---|---|
| command / loop count | the trace | the skill can thrash, retry, or re-read the same file |
| token budget | run metadata | the skill loads references and could load them all |
| permission regression | the trace | the skill can widen what it touches (writes, network, installs) |

## Declared cost

T2b: 3 runs × the test split (typically 4-8 queries at 40% holdout on a 10-20 case set) —
cheap, minutes. T3: 3 behavioural arms plus a grader per case — expensive in tokens and
minutes, which is why the change classes reserve it for new skills and behaviour changes. Not
running it on a cosmetic refactor is not laziness; it is the materiality rule applied to the
cost of the gate itself, not only to its findings.
