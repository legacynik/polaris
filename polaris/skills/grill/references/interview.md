# The interview — look, play back, ask, lay out

How steps 2–8 of `grill` run. The body of the skill says what; this file says how, with an example
per behaviour. The founder is not a developer: plain words, his vocabulary, no process jargon, and
never quote this skill to him.

## Scope

Name one primary repository and one change; list other repositories as dependencies with their own
contracts. Resolve the repository root and its Polaris contract (`_polaris/` or `config.yml`). If
the contract is absent, continue from repository evidence and say once that durable Polaris
context is unavailable; never bootstrap it from here.

## Look before you ask

Read what the founder pointed at and the code it connects to until you can explain how the relevant
parts work today and what the change would touch. Never ask what the project already answers.
Read only what can change the interview:

1. The governing `AGENTS.md`, `CLAUDE.md` or equivalent.
2. Current state (`state/current.md` or the repository's equivalent) for open threads and blockers.
3. Accepted decisions with their supersession links, and the lessons in `records/`.
4. Any issue, request, design note or spec the founder named.
5. The implementation surface: manifests, lockfiles, entry points, tests, routes, services, jobs,
   auth boundaries, current code.
6. The data surface when relevant: schema, migrations, ORM models, generated types, constraints,
   indexes, tenancy, and the code that reads or writes them. Load `database-schema` for this; it
   never runs DDL, DML, migrations or type generation during a grill.
7. Earlier ideas: open beads `kind:idea` for the area, `plans/archive/` and `plans/done/` for the
   same subject — and why they stopped.
8. The agent memory, through `ai-memory-retrieval` when installed: earlier sessions on the idea.
   Skip it when absent and say so once. Memory is a lead; verify it on code.

Follow the repository's code-discovery rules: its code graph when present, text search for
strings, configuration and gaps in the graph.

### Keep evidence honest

A small working ledger with three labels: **Evidence** (observed now in code, tests, git, the
tracker, the database or official docs) · **Inference** (reasoned, still to confirm) · **Unknown**
(a material branch neither the repository nor the founder has resolved). Decisions, lessons, plans
and notes are leads; current-state claims are verified on code, git, the tracker or the runtime.
When decisions conflict, name the newest active one, what it supersedes, and whether the code
follows it. Never put secrets, credentials, customer or personal data in a question or the plan.

### Prior art

How other repositories and products solved the same problem, from primary sources: their code,
docs, release notes, issues. Name each source with what it does better than what we have. For an
external SDK, framework or API, read the installed version from the lockfile and query its official
docs for that version; record version and conclusion as Evidence. Never send proprietary code,
secrets or customer data to an external tool.

### Tear down the premise — before the first message and whenever an answer moves it

1. Already satisfied? Does its stated cause hold? When a safe read-only command can show the
   behaviour, run it; record `file:line`, command and output in the ledger.
2. Compare the request with code, accepted decisions, docs and earlier statements. Record each
   contradiction with both sides; never settle it by picking a document. Against an accepted
   decision → the question offers the real choice: respect it, or reopen it through `architecture`.
3. One word with several meanings → list them with evidence and route the naming to `domain`.
4. A moved boundary, interface, schema or data contract, or dependency → `architecture` owns it.

## The first message

**He already said what he wants** (a spec, a detailed request): about 200 words. Play the request
back in your own words — what, for whom, why, as far as he said. Add what you found that bears on
it: how it works today, what the change touches, and plainly anything he may not have considered (a
constraint, a conflict, a cheaper path). One line inviting corrections. Then one question: the
thing still open whose answer would most change what gets built.

> Example. Request: "Excel export of quotes with our price breakdown, so the accountants at our two
> biggest clients stop retyping them." Message: "So: the accountants at your two biggest clients
> get each quote as a spreadsheet they can import instead of retyping it. Today quotes leave only as
> PDF (`quotes/export.py`), and the breakdown sits next to our margin fields — which an accepted
> decision says customers never see. Correct me if I got it wrong. Should their sheet carry the
> per-line breakdown without margins, or only the totals their bookkeeping imports?"

**He has not:** one open question in his terms about the biggest unsettled thing, saying what the
answer would change.

> Example. "Un cruscotto per i clienti che stanno per abbandonarci." → "If it is for you to call
> them before they leave, I would rank a short list of names each Monday; if it is to understand why
> they leave, it is a different tool. What do you want to do the moment you see a name there?"

## Questions — Socratic, one per turn

- One sentence, no list of example answers hanging off it. Open questions first: his own words
  carry intent that options cannot. A short menu only when he is stuck.
- Build each question on his last answer or on something found, so it walks him through a
  consequence or a case he may have missed. Say what the answer would change when it is not plain.
- A proposal he can correct, with your reason, often beats a question; "yes" accepts it as the
  default. When he says "you decide" or "what do you think?", propose something concrete.
- Turn vague words ("fast", "safe", "done") into an observable threshold.

> Example. After "installers dictate measurements offline": "If a dictated 2.40 is heard as 24.0,
> the quote is wrong by a factor of ten — should a value outside the usual range stop the quote
> until someone confirms it?"

**Ground to cover** is territory, never a script read aloud.

- What kind of thing this is and what makes it special
- Why now and what success looks like to him
- Goals, non-goals, anti-goals (what would make it a failure even if it works)
- Prior art he has seen, loved or hated
- Current state and what he already tried
- The details he cares about
- **appetite**
- **no-gos**
- **rabbit holes**

**Appetite** is how much time the work is worth to him, not an estimate: "Is this worth two days,
two weeks or a quarter to you?" It caps the scope; when the scope outgrows it, cut scope, not
appetite. Never invent it and write it as his. **No-gos** are what it must not do; **rabbit holes**
are the parts likely to eat the appetite, each with how it is avoided or time-boxed.

**How it gets made.** Find out early which technical choices he wants to own and which he hands
over. Someone handing over gets sensible defaults said in plain words; existing work keeps what it
already uses. A handed-over choice is written `agent's call: <choice> — because <reason>`, never as
something he agreed to.

## Play back in chunks

As soon as one part is clear (what it is for, or how one piece behaves), describe it back in about
200–300 words, then ask about the next part. Only what he said goes in as his, in his words and
numbers — never strengthened, softened or rounded. Anything you filled in is marked as your
proposal with its reason. End each chunk by asking what is wrong or missing.

> Example. "You said: installers lose about two hours a day re-entering measurements; they should
> dictate on the phone, offline on site, Italian only, Android only. My proposal: keep each audio
> clip until the quote is sent, so a doubtful value can be replayed — because offline dictation
> will mishear. My call: on-device recognition, since offline rules out a cloud engine. What is
> wrong or missing?"

## Lay out the approaches — a message of its own, before the plan file

**Three thinking tools, one line each** (the full catalogue is in `problem-solver`):

- **What would have to be true** for this to work? Each answer is an assumption to test.
- **Pre-mortem**: "a month from now this failed — why?" The answers are anti-goals, no-gos and
  rabbit holes.
- **Diverge before converging**: list candidates quickly, including at least one opposite or
  inverted one (do nothing, do it by hand, move it elsewhere), then keep the two or three real ones.

Once what he wants is clear, think of several ways to build it and drop the weak ones (those that
work against why he wants it, or that existing work rules out). Present two or three at coarse
grain — a short paragraph each: what it means in this project, what it trades off. Recommend one
with the reason; he picks. One sensible way only → say so and why the others do not fit. These are
not designed architectures.

- **They differ on a boundary, a data contract, a dependency or the shape of a pipeline** → do not
  settle it here: hand off to `/architecture design` (divergent designs, no record), then
  `/architecture decide`, before the plan.
- **Every approach is weak, earlier attempts keep failing, or he asks for new options or to flip
  the plan** → hand off to `problem-solver`. It finds the crux, offers three opposite ways of
  looking at it for him to pick, and the cheapest experiment that confirms the answer. Then resume
  the grill with what it learned. Never force a pick among weak options.

## Press release + FAQ — an option for Large work

When the why is still soft, offer to write it backwards: a five-line press release as if shipped
(who, what changes for them, why it matters, one quote from a customer) and the three hardest
questions with their answers. If the release cannot be written convincingly, the idea is not ready.

## Assumptions and convergence

Every assumption in section 3 says how it will be tested: a command, a spike for `prototype`, a
measurement. Stop asking when material branches are resolved, acceptance is observable, appetite,
no-gos and exclusions are explicit and every assumption has a test. Low-value questions are not
asked.

## Gotchas

- The feature already exists → show the live result before asking what still needs changing.
- Code, docs and earlier statements disagree → name both sides; recency alone is not reconciliation.
- A default he never heard is one he could not reject: say every fill out loud.
- "Sounds good" covers what he saw, not a plan file you have not written.
- Convergence is not permission to build: the exit is his yes on scope, then `plan-area`.
