# The flow — `/architecture` with no verb, from question to a true document

Load this when the skill is invoked with no verb, or when the person says they do not know what
the skill can do for them. It is a **menu, not a pipeline**: the person chooses, every time. The
skill's job is to show, in writing, everything it can do here, mark what the measure recommends,
and after each step offer the next options that make sense from where the person now is — so a
founder who is not an architect never has to know that the verbs exist.

## The first answer: the written menu

Run `arch_doctor.py --root . --quick` (read-only, seconds), read `DOMAIN.md` and the live
documents' freshness, then answer with this, always in full, in the person's language:

1. **What this repository is**, in one sentence, and **whether its map can be trusted today**.
2. **What the measure found** — the two or three things that matter, one line each.
3. **Everything the skill can do here**, as a numbered list, one plain line each, with ⭐ on the
   one or two the measure recommends and the reason in brackets:
   - *Explain how it is built* — read the code and write or re-true `ARCHITECTURE.md` (stage 7).
   - *Find what is wrong in one area* — dependencies in and out, cycles, modules that do too much (stages 1–2).
   - *Propose how to fix one problem* — three or more different refactors, compared, one recommended (stage 3).
   - *Record a choice* — so it is not re-debated and agents follow it (stage 4).
   - *Check that a past choice actually reached the code* (stage 6).
   - *Settle a name or a boundary of the domain* — handed to `domain` (see below).
   - *Full check-up* — every health check, with what to do about each (`doctor`).
4. **One question**: «What do you want to do?» — the person answers with a number or in their own words.

After every stage, end with the same shape, shorter: what was produced, then the numbered options
that make sense next (for example after an analysis: propose a fix · record what was found in the
map · analyse another area · stop), with ⭐ on the recommended one. Never end a stage without the
options written out.

## Rules of the conversation

- **Plain language in chat.** No verb names, Decision IDs or check names in the question itself;
  say what was found and what it would cost, the way you would to a smart person who does not
  write code. Technical names go in the artifacts, and in brackets when the person needs them.
- **One question at a time**, each with: what was found (one or two lines), the options (two to
  four), what each costs, and your recommendation first. A question whose answer would not change
  scope, a boundary, an irreversible commitment or acceptance is not asked: state the assumption
  and continue.
- **Nothing is written without a yes.** Measuring is free; every stage that writes (a Decision, an
  issue, the document) waits for an explicit yes to that stage.
- **Every stage can be the last.** The person may stop after any stage; the flow says in one line
  what was produced and where to resume.
- **Say when an earlier answer was wrong.** When a later stage falsifies something already told to
  the person, the next answer opens with the correction, explicitly («correzione: …»), never by
  silently changing the number.
- **Claims match coverage.** «Nothing from the last audit is fixed» is only written when every
  prior finding was re-checked; otherwise say how many were re-checked and which were not.
- **State lives in the work item, not the transcript** — the issue or plan that the flow opens or
  was given. A resumed run reads it and continues from the first open stage (`director.md`).

## Stages — what each option runs

The order below is the natural one when the person wants everything; any stage can be chosen
directly, and the prerequisites it needs are measured, not assumed.


| # | Stage | Runs | Tells the person | Asks |
|---|---|---|---|---|
| 0 | **Orient** | the written menu above | the menu above | «What do you want to do?» |
| 1 | **Pick the area** | list the `DOMAIN.md` domains; resolve the chosen one to paths: the union of `paths` of every component whose `domains` includes it | the areas, each in one line, with the one that stage 0 flagged first | «Which area?» — or the whole repository. A word that is not a `DOMAIN.md` domain (a folder name, a nickname) is mapped to the components whose `paths` it overlaps; the mapping is **stated in the answer** and the stage continues. **Halt** only if no component matches: `DOMAIN.md` does not describe it, and that is the first finding (offer `doc` / adoption), not a reason to guess the folders |
| 2 | **Analyse** | first the **prior art**: the latest audit report for these paths (the repository's `audit` output area) and the accepted Decisions governing them — if one exists, the run is a delta: each prior finding is re-checked and marked `STILL TRUE` · `FIXED` · `NOT RECHECKED`, never re-derived from scratch. Then `audit` on the **import root** — the directory absolute imports resolve from (`backend` when the code reads `from app.x import`), never the package itself: a subpackage root silently undercounts cycles. Keep the findings that touch the area's paths — and, above all, the dependencies that **cross** the area's boundary in either direction | what the area depends on, what depends on it, the cycles it sits in, the modules that are bags; each finding in one line with what fixing it would make simpler, ranked by blast radius | «Which of these hurts?» — pick one to three. Recommend the one with the largest blast radius that is cheap to reverse |
| 3 | **Propose** | `design` on each picked finding: three or more genuinely different shapes, compared on depth, locality and seam placement | the options as pictures in words — what moves where, what gets simpler, what it costs, how reversible it is; one recommended | «Which shape?» — or none. **Halt** if every option is a two-way door with no caller outside the module: that is a refactor to just do, not a decision; hand it to step 5 of the tracker (`issue-contract`) directly |
| 4 | **Decide** | `decide` — Step 0 reversibility first; a record only when the choice is a one-way door or sets direction for months | in one line what is being committed to, and what would reverse it | «Record it?» — yes writes the admitted record where the repository keeps its decisions; no leaves it as the recommendation in the work item |
| 5 | **Hand off the work** | `issue-contract` with the Decision (or the recommendation) as the mother document | the issue(s) that will carry the change, and who or what runs them | «Open them?» |
| 6 | **Land** | after the change merges: `land <DEC-id>` — call sites, prerequisites, closure check | whether the decision is actually in the code, or only approved | nothing, unless it is not landed: then «reopen the work?» |
| 7 | **Document** | after the yes: draft to the contract in `doc-arm.md` (the code map where a boundary moved, *Known limits* for what the analysis found and nobody fixed, *Design principles* if one was decided) → the **mandatory** fresh-context reader (below) → fix every false sentence it finds → write | what changed in the map, in two lines, and how many sentences the reader caught | «Write it?» — asked before drafting |

Understanding-only runs go 0 → 1 → 7. A clear, already-decided change starts at 4. These are
examples of what people pick, not routes the skill imposes.

## Parallel lanes and background work

The analysis and the proposal are not one pass by one mind. They run as read-only waves under
[`director.md`](director.md) — declared workers, one axis each, same snapshot, one row per worker
in the reduction, a missing result recorded as `non_observable`, never as clean:

| Stage | Parallel lanes (read-only, dispatched together) | Model |
|---|---|---|
| 2 Analyse | **dependencies** (`detect.py`: cycles, instability, what crosses the area's line) · **domain fit** (does the code divide where `DOMAIN.md` divides; bags that mix subdomains) · **change coupling** (from `git log`: files that always change together across the line) · **tests and gates** (what in the area no test or gate would catch) · **data ownership** (who writes each store the area touches) | lanes: cheap model — they return evidence (commands, counts, file lists), not verdicts. The reduction — ranking, `STILL TRUE`/`FIXED`, what to tell the person — runs on the strong model, then **one fresh-context critic** checks the reduction against the lanes' evidence before it reaches the person |
| 3 Propose | the ≥3 radically different designs of `design-verb.md`, then **one fresh-context critic** on the recommended one before it reaches the person | designs: default; critic: strong model, fresh context, never a fork |
| 7 Document | a fresh-context reader who knows nothing of the run checks the new map against the code: every name resolves, every invariant is true today, nothing an ordinary PR would falsify | strong model |

Long measures (the full audit on a large repository, the landing check) run in the background
while the conversation continues; the person is told when they are back, and the stage ends only
on the reduced result — a background event is not evidence until the worker has returned.

## Where `domain` enters

`domain` decides what is **true** — what a thing is called, where the domain divides, which
subdomain is core. This flow decides what a change **costs** and where the code's lines go. The
flow reads `DOMAIN.md`; `domain` owns it. So the flow hands over at three points, waits for the
one settled question, and resumes at the same stage with the updated `DOMAIN.md`:

| Stage | Hand to `domain` when | Resume with |
|---|---|---|
| 1 | the area resolves to no path, a component sits in two areas nobody meant to share, or the person names the area with a word the code uses for something else | the area's canonical name and its component → paths mapping in `DOMAIN.md` |
| 2 | a finding is a module that mixes two subdomains, or a dependency that crosses a line the domain does not draw — the question is *where does the domain divide*, not *what does moving it cost* | the line, and the subdomain type of each side (core work is kept in house and refactored first; generic work is a candidate to buy or leave) |
| 3 | two options differ only in which area owns a concept, or two areas must integrate | the owning area, or the integration pattern and what it costs |

The order is fixed: the domain line first, then the architecture cost. A refactor designed across
a line the domain has not settled moves code twice. A domain question inside one finding parks
**that finding** until `domain` answers; the other findings continue.

## What the flow never does

- Never runs a writing stage as a side effect of presenting it.
- Never skips stage 2 to reach a proposal: a refactor proposed without the measure is advice,
  and the skill's contract is that every verb measures before it advises.
- Never writes the document before the analysis when the person asked what is wrong: the
  document would then describe the map the person already doubts.
- Never guesses an area's folders. Area → paths comes from `DOMAIN.md`, or the flow stops.
