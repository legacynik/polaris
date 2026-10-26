# Model profiles: write the prompt for the model that runs it

A prompt is tuned to a model family and version. Read the card for the model that serves the
prompt, then the vendor page it cites: these pages change, and a technique that names a model was
measured on that model only ("treat it as measured on that model and re-check it against your own
evals", Anthropic). Re-check every card against your own eval when the model, the provider or
the effort changes. Cards read 2026-10-05; `[obs]` marks behaviour observed in production use,
not vendor guidance.

## What every vendor agrees on

- **Describe the outcome, not the procedure.** "Describe the destination rather than prescribing
  every step" (OpenAI, GPT-5.6 guide); "Give Claude rules → let Claude use judgement" (Anthropic,
  context engineering for Claude 5).
- **No contradictions.** "Conflicting rules can create more instability than missing detail"
  (OpenAI). An exception written into a prompt ("null only when…") gets used at the same rate
  where it does not apply [obs]: define the exception where the rule is, or drop it.
- **Give the reason instead of absolute always/never rules** on judgment calls (OpenAI "Stop doing this";
  Anthropic: the model generalizes from the explanation).
- **Delimit instructions, context and input** with XML tags or Markdown (Anthropic, OpenAI,
  Google).
- **Control reasoning with the parameter, not with prose.** "Asking it in the system prompt to
  think less doesn't reliably reduce its thinking" (Anthropic); `reasoning_effort` and
  `verbosity` (OpenAI); `thinking_level` (Google); `reasoning.effort` on OpenRouter.
- **Long data first, the question last** (Anthropic: up to 30% better; Google: context first,
  question at the very end). Keep a one-line role or goal at the top.
- **Few tools, each described by what it does, when to use it, what it returns, how it fails**
  (OpenAI); let enums and parameters carry the usage (Anthropic).
- **Valid JSON is not a correct answer.** Validate values in code (Google); a response that hit
  `max_tokens` is failed even when its JSON parses (Anthropic).

## Cards

**Anthropic Claude 5.x** — docs: platform.claude.com prompting best practices and the per-model
pages; claude.dev "The new rules of context engineering for Claude 5-generation models".
- Fewer rules, each with its why; interfaces (schemas, enums) over prose; progressive disclosure;
  no examples duplicated between system prompt and tool descriptions.
- Thinking is adaptive; effort defaults high and maps to different amounts per model: sweep it.
- JSON on a reasoning task without thinking goes wrong: use adaptive thinking (or a higher effort)
  and parse the last JSON value. Do not ask for the reasoning inside the response. Prefilling the
  last assistant turn is rejected on recent models: use structured outputs or tool enums.
- At low effort it may stop to ask; at the highest efforts it may start extra review rounds a
  short instruction can switch off. Effort does not change visible length: ask for concision.

**OpenAI GPT-5.x** — docs: developers.openai.com prompt guidance for GPT-5.6; GPT-5 prompting guide.
- Role, goal and outcome first; a hierarchy of user outcome → success criteria → safety → tool
  rules → output format.
- Effort and verbosity are parameters: test the chosen effort and one level lower on
  representative tasks. Old "be brief" lines over-correct on newer versions.
- Contradictions hurt more than on other families. Sampling parameters may be dropped for
  reasoning models by the client library: check what reaches the wire.

**Google Gemini 3.x** — docs: ai.google.dev prompting strategies, Gemini 3, structured output.
- Temperature: "We strongly recommend keeping the temperature parameter at its default value of
  1.0… setting it below 1.0 may lead to unexpected behavior, such as looping or degraded
  performance." A lower temperature is a choice to measure, not a default.
- "We recommend to always include few-shot examples" (stronger than Anthropic or OpenAI).
- `thinking_level` (default high); never together with `thinking_budget`.
- Structured output supports a JSON Schema subset; very large or nested schemas may be rejected;
  syntax is guaranteed, meaning is not.

**Zhipu GLM-5.x** — docs: docs.z.ai thinking mode and GLM-5 pages; no official prompting guide.
- Thinking is forced and cannot be disabled; leaving the effort unset means the maximum. Pass a
  low effort explicitly and a `max_tokens` ceiling [obs: with no effort sent, a 2,048-token budget
  went entirely to reasoning; one run reached 131,072 tokens].
- Switching reasoning fully off broke tool use [obs]. Return the historical reasoning content
  between interleaved tool calls. No schema guarantee for JSON: validate and retry in code.

**DeepSeek V4.x** — docs: api-docs.deepseek.com quickstart and JSON mode.
- JSON mode (`json_object`, no schema): the prompt must contain the word "json" and an example of
  the format, with enough `max_tokens`; empty content can come back.
- Only disabling reasoning stops it; low and minimal efforts reasoned like the default [obs].
- Through a router, check which providers and quantizations actually serve it [obs: an intended
  first-party pin was never applied].

**OpenRouter (transport)** — docs: openrouter.ai structured outputs, reasoning tokens, provider
selection.
- Reasoning tokens count against `max_tokens`: an exhausted budget returns empty content with
  `finish_reason: length`, billed.
- `json_schema` is honoured only by some providers of the same model: require the parameter.
- Quantized providers (fp4/int4) may degrade some prompts: pin quantizations for prompts you
  measured.

## Where vendors disagree

| Topic | Disagreement | Default here |
|---|---|---|
| Temperature | Gemini, GLM and DeepSeek recommend 1.0; many pipelines run at 0 for repeatability | Keep the vendor default unless your eval shows the lower value is better |
| Examples | Gemini: always; Claude 5 and GPT-5.6: interfaces and outcomes first | Examples for Gemini; few, varied and never duplicated for the others |
| JSON | Schema-enforced (Anthropic, OpenAI, Google) vs `json_object` only (DeepSeek) or no guarantee (GLM) | Schema where the provider enforces it; validation and retry in code elsewhere |
