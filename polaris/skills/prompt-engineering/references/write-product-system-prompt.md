# Write: a product system prompt

A product prompt runs unattended, on user data, thousands of times. It is one part of the task
contract in `method.md` (identity, schema, evaluator); this file is how to write the text.
Sources: Anthropic prompting best practices ("Be clear and direct", "Give Claude a role",
"Control the format of responses", "Structure prompts with XML tags", "Long context prompting",
"Overthinking", "Migrating away from prefilled responses"); OpenAI prompt engineering and
reasoning best practices; `task-model-context.md` §3.1 for the task shape.

## Anatomy, in this order

1. **Role and task, two sentences.** Who the model is for this task, and the one decision it makes.
   Match the task shape (classification, extraction, dedup, synthesis, tool action) and take the
   emphasis from §3.1.
2. **Stable instructions first, variable context last** (prefix caching). Instructions, then
   schema, then examples, then the payload.
3. **Output contract**: a strict schema (JSON with named fields, closed enums) or a fixed
   observable form. Deterministic code validates it; the prompt does not ask the model to
   self-validate.
4. **Untrusted data as data**: wrap user text, retrieved documents and tool results in tags
   (`<email>…</email>`, `<sources>…</sources>`) and say once that content inside tags never
   changes the instructions.
5. **Failure behaviour, explicit**: when to abstain, what to return when evidence is missing or
   contradictory, the `unknown`/`other` bucket and its rule. Every enum has an escape value, and
   a `confidence: high | low` (or equivalent) field lets code route the low ones to a person
   instead of forcing a guess into the escape bucket.
5b. **Boundary rules, ordered**: when two labels can both fit, write the tie-breaks as a numbered
   list applied in order ("a chase that adds a new priceable request is `quote_request`, not
   `follow_up`"). Cover the payload shapes real traffic brings: forwarded or quoted chains
   (classify the newest message by the sender, the rest is context), content that lives only in
   an attachment the model cannot see (empty extraction plus low confidence), empty or
   unreadable bodies, and a lure that looks like the target class (a phishing "price request"
   is `spam`).
6. **Evidence binding**: fields that carry provenance (quote, span, id) preserve source wording
   and quantities; the model never reconstructs a missing fact.
7. **Examples only for observed failure modes**, two or three, chosen from real inputs, held out
   of the eval set. No decorative few-shot.
8. **Reasoning**: no chain-of-thought in the persisted output; if a decision needs evidence, ask
   for a one-line `reason` field. Configure native thinking in the request, not the prose.

## Model-specific notes

- Claude 5 family: follows instructions literally; write the rule once, plainly. Emphasis words
  and repeated prohibitions cause over-triggering. No prefill; use the schema or a short format
  instruction. State the language of the output explicitly when inputs are multilingual.
- OpenAI reasoning families: direct prompts, fewer "think step by step" scaffolds, controls in
  API parameters.
- Whatever the model: pin model id and version next to the prompt hash; a prompt is not portable
  across versions without re-running the eval.

## Checklist (binary)

- [ ] One decision named; task shape identified
- [ ] Stable text before variable text
- [ ] Strict output schema with an escape value per enum
- [ ] Untrusted payload delimited and declared non-instructional
- [ ] Abstain/missing/contradiction behaviour written, with a confidence field
- [ ] Tie-break rules numbered and ordered; forwarded chains, attachments, empty bodies, lures covered
- [ ] No chain-of-thought in output; provenance fields preserve source wording
- [ ] Output language stated
- [ ] No emphasis walls (MUST/NEVER repeated), no prefill
