# Write: questions for a System One decision model (TypeSafe Jev)

A System One model does not generate text. It reads a **state** and answers typed **questions**
(Choice, Noul, Score) with probabilities. The prompt surface is the state layout, the question
text and the answer definitions; code owns the workflow, the thresholds and every exact rule.
Use it for fast, repeated, narrow judgments (routing, classification, per-condition checks,
evaluator questions); use a generative model when the answer needs reasoning, prose or arithmetic.
Sources: live docs, https://docs.typesafe.ai/llms.txt (read the pages for the primitive you use;
they change), the `typesafe-ai` skill; for evaluator design around these questions, the
`eval` skill (`references/graders.md`).

## Anatomy

1. **The judgment, sized right.** One judgment a knowledgeable person makes in a second given the
   right context ("Does this message convey urgency?"), not an analysis ("analyze this message
   and determine…"). Several independent factors become several questions, combined in code.
   (docs: primitives)
2. **The primitive, by what the answer means.** Choice for one of a known unordered set; Noul for
   whether one condition holds (probability of yes, one Noul per label when several may apply);
   Score for a position along a described dimension. When two fit, pick the one whose answer
   code can act on directly. (docs: primitives)
3. **The state, lean and named.** Text only: a string, a JSON object or an array of text values.
   Named JSON fields when context has parts; reference them with backticked paths
   (`ticket.messages[0].text`) in the question. Only what this question needs: material the
   question does not use lowers accuracy. Put the observed outcome in the state (the stored row,
   the printed text), not a model's claim about it. (docs: state; Langfuse Jev-as-a-judge)
4. **Instructions and criteria.** The question goes in `instructions`, the possible answers in
   `criteria` (Choice options with descriptions, Score levels, a `true` and a `false`
   description for a Noul). Both are sent to the model;
   question and option ids are not, so each text carries its full meaning. Short strings for
   short questions; an object with named fields when background, examples or values from code
   belong next to the question instead of spliced into it. (docs: choice; how-to-build, "Use
   structure in the questions")
5. **A way out.** The model always picks an answer and does not abstain. Add a no-match option
   ("none of the above", "the state does not say") whenever nothing may fit, or ask a separate
   presence Noul when presence is useful on its own. For selecting a value among candidates,
   check that the right value is among them: the model cannot choose an omitted one.
   (docs: choice; typesafe-ai skill)
6. **Score levels that stand alone.** Each level is evaluated separately; the model does not see
   its number or its neighbours, so "worse than the previous level" and numbers in the text mean
   nothing. Describe a concrete situation per level; use only as many levels as you can describe
   distinctly (2 to 10). (docs: score)

## Rules

- **Exact rules stay in code.** Arithmetic, dates, unit conversion, literal string matching and
  known lookups are checked deterministically; ask the model only for the semantic part.
  (typesafe-ai skill; Langfuse blog 2026-09-18 on literal, arithmetic and date weaknesses)
- **Batch questions over the same state** in one request: they run in parallel and do not see each
  other's answers. Make a second request only when an answer is needed to build the next state.
  Speculative questions state their premise; code uses only the applicable answers. (docs:
  primitives, fan-out)
- **Write the questions in English** even when the state is in another language: other languages
  are accepted with lower accuracy (docs: state, models#language-support). Measure the difference
  on your data before relying on either.
- **Thresholds live in code and follow the cost of being wrong**: 0.5 when both errors cost the
  same, higher when a false yes is expensive, lower when a miss is. A Noul near 0.5 means similar
  probability of yes and no, not medium intensity. Choice/Score `confidence` measures how
  concentrated the distribution is, not whether the answer is right. (docs: noul, confidence)
- **Combine in code, never in one question.** "Any serious violation" is several conditions with a
  veto; weighted sums only for compensating preferences. (docs: composite-scoring)
- **Typed output guarantees the interface, not truth.** Validate on labeled cases from your own
  domain before code acts on an answer; stability checks include the same request twice and the
  candidate order shuffled. (typesafe-ai skill; `eval`, judge calibration)
- **When several per-label Nouls fire together, or on clean cases,** do not tune one threshold
  per label. Ask one Choice for the dominant label with a no-match option, or pair each label
  with a Noul asking whether it applies at all; and put the facts code can count (repeats, same
  error again, calls between two failures) in the state instead of more raw text.
  ([jev-belay](https://github.com/valentynkit/jev-belay), "How it decides";
  [pi-warden](https://github.com/DevMortimer/pi-warden), `eval/reports/2026-09-26-judge-bench`)
- **Start calibration from existing tools and measurements, not from scratch.**
  [jev-calibrate](https://github.com/smkrv/jev-calibrate): per-question verdict (act, act above a
  confidence, rank only, unusable), tune/holdout split with a ledger.
  [jevcal](https://github.com/abhixhek/jevcal): wording lint, threshold picked on one half and
  verified on the other, lock file with a CI drift check.
  [jev-calibration-audit](https://github.com/jujumilk3/jev-calibration-audit) `FINDINGS.md`:
  §1 a missing no-match option, §3 rewording moves probabilities, §5 added questions in one
  request. Limits of each are in [research.md](research.md).
- **When a question is an evaluator,** derive it from labeled failures, not from the wording of
  the prompt it checks; never copy evaluator questions into that prompt. Shared wording makes the
  two fail together. (`eval`, error analysis and judges)
- **Data leaves your system.** State and questions go to the provider (and its upstream gateway);
  decide per data class what may be sent. (Langfuse Jev-as-a-judge)

## Checklist (binary)

- [ ] Each question is one second-sized judgment; independent factors are separate questions
- [ ] Primitive chosen by the meaning of the answer
- [ ] State holds only the fields these questions use, named, with backticked paths in questions
- [ ] Question and answer texts carry their full meaning without ids
- [ ] A no-match option or a presence Noul exists wherever nothing may fit
- [ ] Score levels describe concrete standalone situations, no numbers or relative wording
- [ ] Arithmetic, dates, units and literal matches are checked in code, not asked
- [ ] Questions over the same state are batched in one request
- [ ] Questions in English, or the language choice measured
- [ ] Thresholds are in code and tied to the cost of each error; picked again after any rewording or model change
- [ ] Validated on labeled domain cases, including a repeated request and a shuffled candidate order
- [ ] What the state may contain was decided for the data class it carries
