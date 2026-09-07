---
name: skill-meta
description: ◇ Use when writing a new SKILL.md, when editing the description, frontmatter or body of one that already exists, when building or running an eval for a skill — prompt set, trigger rate, behaviour rubric — or before proposing any skill for install or promotion.
version: 0.8.1
user-invocable: true
auto: true
lifecycle: "gate-report(T1,stdout,read at once) -> collision-report(T2a,stdout,read by the next run) -> eval/prompts.json + eval/checks.json(stored corpus, per skill, committed, edited only when the job changes) -> references/ratchet-state.json(T2b, pinned to the description, rewritten only by trigger_ratchet.py, never by hand) -> EVAL-REPORT.md(T3, baseline + strongest donor + candidate graded and challenged by one fresh-context critic before promotion)"
invokes: [critic]
invoked-by: [human]
io: "receives: a slug + root for a new skill or an existing skill directory, plus a FAST_SESSION or FULL_REFACTOR admission receipt from the Polaris playbook. produces: a valid-by-construction scaffold, the change class with the tiers it owes, T1/T2a/T2b verdicts with measured cost, and for new skills or behaviour changes a donor-parity T3 block carrying a fresh-context critic receipt. Never a .skill zip — that lives outside the four harnesses."
status: active
---

# skill-meta

## Overview

The one door for the whole life of a `SKILL.md`: writing one, editing one, evaluating one,
promoting one. Self-contained for **authoring** by decision — it invokes no other
skill-writing skill, so everything needed to write a skill is here or in this bundle's
`references/`. What it does **not** own is the running of the rank-1 measurement: no script
here drives it, so whoever orchestrates has to run it for real (see the tier table).

It does not write the domain knowledge; that stays with the author, human or agent. It
**validates, measures and challenges**: structure, trigger collision, routing rate, whether
the skill beats its own baseline and strongest applicable donor, and whether its corpus omitted
the attack that matters.

It consumes the admission receipt prepared by the Polaris playbook in `SPEC-MADRE.md`.
`FAST_SESSION` reuses fresh session evidence; `FULL_REFACTOR` carries the exhaustive census.
This door never repeats a complete mining pass that the receipt already proves.
For a read-only request, return the workflow and gates only; do not run repository commands.

Creation happens once; editing happens forever. So the tier that matters most is the one on
the edit, and the gate names it from the diff rather than asking the author what they think
they changed.

Two references, loaded at the phase that uses them, never both at once:

- **`references/design-bar.md`** — how to write the thing: invocation, information
  hierarchy, leading words, the frontmatter contract, file layout, script-versus-prose, the
  failure modes, the shipping checklist.
- **`references/eval-protocol.md`** — how to measure it: building the prompt set, the
  routing rate, judges and their correction, the modification gate, the four check
  categories.

Who owns which job in the wider ecosystem, and what this door superseded:
`references/census-2026-08-17.md`.

## When NOT to use it

- **A `.md` that is not an invocable skill** (plan, spec, ADR, report) — they have their own
  gates (`review`). This door applies to a `SKILL.md` inside `<root>/<slug>/`.
- **Finding or installing a skill someone else wrote** — `find-skills` queries the registry.
  This door builds and measures; it does not shop.
- **Compiling a book or a long document into a skill** — `book-to-skill` owns that
  extraction. The result comes back here for the tiers.
- **Freezing a successful browser scrape into a skill** — `skillify`, inside the gstack
  bundle, owns that end to end. Different input, different job.
- **Editing `_standard/validate_suite.py` or `SKILL-STANDARD.md`** — shared infrastructure,
  read in parallel by every job. A change there is a dedicated review, never a side effect.
- **Writing the domain knowledge of the skill under test** — this door measures the factory;
  it does not supply the competence of the job the skill covers.

## What a change owes

Run this first on any edit. It reads the previous version from git (or `--baseline` off git),
classifies what moved, and refuses what it cannot verify.

```bash
python3 scripts/change_gate.py --skill <dir> [--base REF | --baseline FILE]
```

| What moved | Class | Owes | Why |
|---|---|---|---|
| `description` · `name` · `auto` · `user-invocable` | TRIGGER | T1 T2a T2b | the trigger moved: the old rate describes a skill that no longer exists |
| the `◇`/`✦` mark and nothing else | MARK | T1 + receipt | the trigger text is identical, so the measurement stands; what it owes is the receipt row |
| `io` · `lifecycle` · `invokes` · `invoked-by` | BEHAVIOUR | T1 T3 | the declared contract moved: what the next step receives changed |
| a body line carrying a command, a path, a table row or a hard rule | BEHAVIOUR | T1 T3 | mechanism is what the agent acts on |
| runtime bundle files under `scripts/` · `references/` · `assets/` · `templates/` | BEHAVIOUR | T1 T3 | the skill changed even when `SKILL.md` did not; generated `ratchet-state.json` is excluded |
| body prose only | PROSE | T1, exit 3 | probably harmless, not provably so — declare it |
| whitespace or reordering | COSMETIC | T1 | nothing to measure |
| nothing on record | NEW | T1 T2a T2b T3 | no baseline is not evidence of a small change |

`version:` is excluded from the signal on purpose: every change bumps it, so it discriminates
nothing.

**The rate is pinned to the description it measured.** `trigger_ratchet.py --skill <dir>`
stores the sha256 of the description beside the rate, and `change_gate.py` refuses a pin that
no longer matches the file. That is what stops a green from travelling across a trigger edit
— a hash, not an mtime, so there is no clock to be wrong about. The mark is excluded from the
hash, so promoting a skill does not void its measurement.

**Red, never a wall.** The gate exits 1 so a runner sees it; what it blocks is promotion and
install, not the save. Fail-closed only inside the suite's own CI and the AFK pipeline, where
no human reads the red.

## The description budget (founder 2026-09-06)

A description is a router key, not a manual. The harness truncates long descriptions when the
catalogue is large (measured 2026-09-06: 74 skills, 27,325 characters of descriptions, the model
sees less of each and chooses worse), so length is a routing defect, not a style choice.

- **Target ≤ 300 characters, hard ceiling 500** (marker included). `architecture` at 1,761 was
  5.7× the catalogue median: that is the shape to never write again.
- One sentence for the job, one for the trigger phrases, one for the loudest "not for". Nothing else.
- **No quoted examples** inside the description: they broke YAML on eight skills (#302) and they
  are what pushes the length. Examples live in the body under "When to use".
- The two official guides disagree — Anthropic says "a little pushy", Codex says "avoid exhaustive
  capability lists". The budget above follows Codex; the pushiness goes in the first sentence.
- T1 (`validate_suite.py`) enforces the ceiling; a description over 500 characters fails the gate.
  Shortening an existing description is a TRIGGER change and owes T2b like any other.

## The four tiers

| Tier | What it measures | Command | When | Blocks |
|---|---|---|---|---|
| T1 | frontmatter contract, "when NOT to use", `bypass-test.md`, `--selfcheck` on every script, line ceiling, promotion mark | `scripts/new_skill.py --check <root>` (shells `_standard/validate_suite.py`, never duplicates it) | every save | yes, exit 1 |
| T2a | description against the catalogue, TF-IDF | `scripts/collision_check.py` | trigger changed | yes on BLOCK ≥75%, warns at ≥50% |
| T2b | rank-1 rate on TEST plus model, valid/excluded runs, input/output tokens and `wall_ms` | `scripts/split_traintest.py` → a rank-1 run per case (3×, majority) or `scripts/rank1_cheap.py` for the calibrated one-call proxy → `scripts/trigger_ratchet.py` pins rate + cost receipt | trigger changed | yes below floor or without receipt |
| T3 | baseline vs strongest donor vs candidate quality and cost, plus omitted attacks found by one fresh-context `critic` | `scripts/eval_verdict.py` validates three measured envelopes and the critic receipt | new skill or behaviour changed | blocks install on donor regression, no strict quality win, breached cost limit, critic BLOCK or missing receipt |

Two descriptions that do not discriminate steal each other's trigger, and the theft is
invisible at runtime — that is "review → 15 candidates" in the register. The floor rises and
never falls, and stops at 95%: a floor at 100% turns one flaky sample into a permanent red.

**T2b is measured, not supplied — and only one thing counts as the measurement.**
`trigger_ratchet.py` pins the rate and its cost receipt but does not run the harness. The numbers
must come from running each TEST-split
case in the **real installed catalogue** and recording which skill the model reaches for
**first**: rank-1 is `first tool == Skill && skill == <slug>`, three runs per case, majority
vote, and any run without a real model response or with the wrong working directory is
**excluded as unmeasured** rather than counted as a miss. Report the negatives separately —
how many wrongly fired — because a description that fires on everything scores well on
positives alone.

**What is NOT T2b.** `skill-creator`'s `run_loop.py` measures a different quantity: it builds
a synthetic single-skill project and asks whether that skill triggers **in isolation**. That
removes the competition T2a and T2b exist to detect, so its number can never be fed to the
ratchet — doing so combines two incompatible modes into one comparison, the failure the
chaos-test register already records. It remains genuinely useful **before** the expensive
tier: it iterates description wording against negative controls cheaply, which is where
wording iteration belongs. Use it as a pre-filter, and measure rank-1 separately.

## Flow

**Editing an existing skill** — the common case:

1. **Admission — name the failure and where it lives.** Quote the invocation that produced
   it, then say which half it came from: the **skill** (wrong routing, a rule rationalised
   away, an output with the wrong shape) or the **operator** (fired at the right trigger at
   the wrong moment, misread the request, skipped a step the skill already carried). Only
   the first half is an edit. If it was the operator's judgement, say so and stop — there is
   nothing here to diff. Creation has this gate (Phase 0 below); editing did not, and on
   2026-08-19 that absence turned one misread word into a description rewrite, twenty
   fixtures and three gate runs, none of which the failure needed.
2. `change_gate.py --skill <dir>` → the class and the tiers owed. It refuses at once if the
   corpus those tiers need is missing, thin, all-positive, or full of placeholders.
3. Make the edit. `design-bar.md` is the bar the text is graded against.
4. Run T1/T2 tiers the class owed, in order, and read the exit codes. If T3 is owed, declare the
   candidate cost limits, then run baseline, strongest-donor and candidate arms on the same cases
   in one batch; do not issue the verdict yet.
5. Dispatch exactly one `critic` with no inherited session context
   (`fork_turns="none"`, or the harness's fresh-context equivalent). Give it the target diff,
   the complete skill bundle, the eval corpus and all three transcripts — never the authoring
   conversation. It grades the declared checks, then attacks what those checks may have
   omitted: sibling destructive branches, claim/code mismatches, bypasses and false-green
   selfchecks. It must grade every ID in the target `eval/checks.json`, inventory the concrete
   candidates for each of the four attacks, then probe every inventoried target exactly once.
   Seal the exact reviewed diff and raw
   critic transcript with SHA-256; `eval_verdict.py` recomputes both before accepting the
   receipt. Missing coverage, generic evidence, a stale seal, extra lane, inherited context or
   `BLOCK` fails.
6. Only then propose promotion.

**Writing a new skill** — evaluation-driven, never documentation-first:

1. **Phase 0, admission receipt.** Read the selected playbook lane. A fresh `FAST_SESSION`
   receipt is enough: use its failure, source, current-catalog check, rival and budget, then
   resolve only missing fields. A `FULL_REFACTOR` receipt must prove the ordered census in
   `SPEC-MADRE.md`. No receipt or a stale source ref means return to the playbook; do not guess.
   Always name the selected lane in the returned plan or execution receipt. Do not infer the change class
   from admission evidence: only `change_gate.py` output may name it; until then,
   describe every owed tier conditionally, without calling one likely or expected.
   The full census stands or falls on four rules, each from a miss on 2026-08-19:
   - **The search space is every `SKILL.md` on disk**, plugin trees and third-party installs
     included — 2,826 files, not the ~680 of the three directories that come to mind. The
     strongest donor of the set lived in the half that was skipped.
   - **Read the survivors in full.** A candidate is never judged by its description; scoring
     a donor without opening it is the same false-positive machine as counting by name.
   - **Verify identity, not the name.** The key is a content field — the `description`, a
     hash — never the directory's name. Two third-party skills were reported as ours.
   - **The expected outcome is a distillation, not an addition.** Three admissible exits:
     EXTEND what exists · ABSORB-AND-DELETE the donors · CREATE, which is last and must be
     argued. A census that adds a door without removing one usually skipped a step.
2. **Establish the baseline before writing a line.** Run the naked agent on the real task and
   write down exactly how it fails — the wrong step, the skipped check, the rationalisation
   it offers, verbatim. A skill written against imagined failures documents imagination. If
   the baseline does not fail, stop: there is nothing to build.
3. **Scaffold.** `scripts/new_skill.py <slug> --root <skills-suite> [--donor <slug> ...]` —
   valid by construction: every mandatory key present, `bypass-test.md` stubbed, T1 green on
   the raw scaffold before a word of content exists.
4. **Write the mechanism before the prose.** What must not vary belongs in a script with an
   exit code, not in a sentence asking the agent to remember. Every script needs
   `--selfcheck` that exercises the ignorance branch — absent input, empty input, missing
   command — or T1 blocks. `design-bar.md` carries the script-versus-prose rule.
5. **Write the text against the documented failures**, minimally: address what the baseline
   actually got wrong, nothing more. Match the form to the failure — a rule that gets
   rationalised away needs a prohibition plus the rationalisation table; an output with the
   wrong shape needs a positive contract, not a longer prohibition.
6. **Build the eval artifacts**: `eval/prompts.json` (10-20 cases by dimension and tuple,
   three positive kinds, at least three negative controls) and `eval/checks.json` (must-pass
   only, one outcome check minimum). `eval-protocol.md` has the method and the schemas.
7. **Run the tiers cheapest-first**: T1 → T2a → T2b, then all three T3 arms. Re-run the same bypass
   from `bypass-test.md` that succeeded in step 2 and prove it now fails.
8. **Fresh critic and T3 verdict.** The same one-agent gate as the editing flow: no session
   context, complete bundle and diff, every declared check plus the four structured attacks.
   Only after its receipt exists may `eval_verdict.py` issue the T3 verdict.
9. **Promotion.** Criterion, flip procedure and receipt rule live in
   `_standard/SKILL-STANDARD.md` — the single source. It is not restated here, because two
   copies of a promotion rule is how one of them goes stale.

## The shared verdict format

Same grep-verifiable block as `review` — never a second format: a
`## REVIEW REPORT` block, a `VERDICT: PASS|CONCERNS|FAIL` line, and the exact closing
sentinel `NO UNRESOLVED DECISIONS`. Whoever can read one can read both.

## Portability — four harnesses, no hooks

Every script is pure Python 3 stdlib: no PyYAML, no pip, identical on Claude Code, Codex,
Hermes and Pi. **No hook required** — the record mechanism is the explicit invocation in the
Flow above, not a Claude-only `PreToolUse`. A hook on `Write`/`Edit` of `*/SKILL.md` stays an
optional enhancement, never the guaranteed path.

**A declared boundary, not a hidden one:** this door operates on a source checkout of
`skills-suite`, where `_standard/` lives — not on a bundle installed in isolation. If
`_standard/` cannot be found, `new_skill.py --check` fails loudly with exit 2 instead of
passing in silence. That is the difference between "not verifiable here" and "verified, ok".

## Known gaps, not hidden

- **A local receipt cannot prove agent provenance.** The runtime must actually dispatch the one
  fresh `critic`; SHA seals prevent stale evidence, and inventory↔probe equality prevents an
  accidentally partial review, but a malicious orchestrator can forge both JSON and transcript.
  Solving that needs runtime-signed agent telemetry, not more self-attested fields here.
- **Maintenance is ours.** This door absorbed the method of three vendor skills instead of
  calling them, so their upstream improvements no longer arrive on their own. Accepted cost,
  founder 2026-08-17; the compensation is the pinned snapshot in `_archived/` that makes
  drift visible when someone looks.
- `_standard/validate_suite.py` (T1) requires only `name/description/version/user-invocable/
  lifecycle/io`, while `SKILL-STANDARD.md` declares `auto` and `status` as part of the same
  contract. A real hole in the shared standard, left alone because `_standard/` is under
  concurrent edit; `new_skill.py` always generates both fields anyway.
- **Nothing here runs the rank-1 measurement.** `trigger_ratchet.py` requires rate, model, token,
  latency and run counts but cannot tell measured values from invented ones, and no script in this
  bundle drives the per-case runs — whoever orchestrates must actually run them. A vendor pre-filter
  exists (`skill-creator/scripts/run_loop.py`) but measures triggering in isolation, which is a
  different quantity and must never reach the ratchet.
- The `--measured-on` tripwire reads the *file name* for `test`/`train`. A renamed file slips
  past it. The description pin closes the more dangerous half — a stale rate — not this half.
- ~~`check_chain()` treats external actors as slugs to resolve~~ — **closed 2026-09-01**
  (polaris-os#215). `_standard/validate_suite.py` now declares them: `EXTERNAL` (a regex for
  `human`/`cron`/`hook` triggers, `invoked-by` only) and `PLUGIN_SKILLS` (exact names of the
  session skills that live in the polaris-team-os plugin: `start`, `update`, `end`,
  `plan-week`; both directions). The old resolution also sniffed `~/.claude/skills`, so the
  verdict depended on what was installed — green locally, red in CI; that sniff is gone. The 6
  chain errors the real catalogue produced without it are 0. Extend `PLUGIN_SKILLS` when a new
  plugin skill really appears in a chain; do **not** put chain errors in
  `nonconforming.allow`, which is skill debt, not gate vocabulary.
- `change_gate.py` calls a body edit behaviour-affecting whenever a changed line carries a
  command, a path or a hard rule, and treats runtime bundle files as behaviour. It
  over-demands on a line that merely *mentions* one, and it is deliberately blind to a prose edit
  that changes meaning without those markers.
  Fail-closed in the direction that costs money, not the one that ships an unmeasured change.
- The receipt check greps the changelog for the slug. It proves a row exists, not that the
  numbers in it are true. Those are the founder's to write.

## Quick reference

```bash
python3 scripts/change_gate.py --skill <dir> [--base REF|--baseline FILE]   # what it owes
python3 scripts/new_skill.py <slug> --root <skills-suite> --donor <slug>...
python3 scripts/new_skill.py --check <root>
python3 scripts/collision_check.py --skill <dir> --catalog-dir <root> [--donor <slug>...]
python3 scripts/split_traintest.py eval/prompts.json --out-dir eval/split/  # holdout .4, seed 42
python3 scripts/trigger_ratchet.py --slug <slug> --rate <r> --state <f> \
        --measured-on eval/split/test.json --skill <dir> --model <model> \
        --input-tokens <n> --output-tokens <n> --wall-ms <n> \
        --valid-runs <n> --excluded-runs <n>                               # pins rate + cost
python3 scripts/eval_verdict.py --baseline b.json --donor d.json --donor-label <name> \
        --new n.json --critic critic.json \
        --checks eval/checks.json --diff reviewed.patch --critic-transcript critic.txt \
        --skill <slug> --append EVAL-REPORT.md
python3 scripts/<any>.py --selfcheck        # every branch, including the adversarial one
```

Bypass-test: `references/bypass-test.md`.
