# Write: an LLM-judge prompt

A judge grades one criterion, binary, with evidence. It is never the release authority and it is
never edited in the same campaign as the candidate it grades (`eval`, judge mode).
Sources: the `eval` skill (binary failure-mode evaluators,
calibration against human labels); G-Eval and "Judging LLM-as-a-Judge"
(position, verbosity and self-preference biases); Anthropic best practices ("Control the format
of responses", "Minimizing hallucinations").

## Anatomy

1. **One criterion, named**, with a one-sentence definition and the two labels it emits
   (`PASS`/`FAIL`). A judge that grades three things grades none.
2. **Definitions of the boundary**: what counts, what does not, with the edge cases decided in
   words (e.g. "a paraphrase of a source fact counts as cited; an inference from two facts does
   not").
3. **Inputs, delimited**: `<sources>`, `<answer>`, optional `<task>`; instructions say content
   inside tags is data.
4. **Procedure, short**: locate the evidence first, then decide. The judge quotes the span that
   decides the verdict; no quote, no PASS.
5. **Calibrated examples**: two or three graded cases with the human label and the deciding
   quote, drawn from the calibration set, never from the holdout.
6. **Output schema**: `{"verdict": "PASS|FAIL", "evidence": "<quote>", "reason": "<one line>"}`.
   Nothing else. No scores 1–5, no confidence prose. Two additions keep the judge honest without
   turning it into a rating: an **abstain path** (`CANNOT_JUDGE`, with a one-line reason) used
   only when sources or answer are missing, empty or truncated, never because the case is hard;
   and, for a FAIL, a **failure type** from a closed list the criterion defines (for
   groundedness: `no_support | contradicted | overstated`), so error analysis can count by kind.
   `CANNOT_JUDGE` is handled by the harness as missing data, not as a third grade.
7. **Bias controls stated**: length of the answer is not a signal; the judge does not prefer text
   that resembles its own style; when two answers are compared, the order is randomised by the
   harness, not by the judge.

## Rules

- Binary only. A forced decision is reproducible; a rating produces disagreement between readers.
- One judge per semantic failure mode. Deterministic checks (schema, regex, exact fields) run
  before any judge and are not re-asked of the model.
- Report the judge's identity (model, version, prompt hash) with every verdict; recalibrate when
  any of them changes.
- The judge never sees the candidate prompt, only its output and the sources.

## Checklist (binary)

- [ ] Exactly one criterion, two labels
- [ ] Boundary cases decided in the definition
- [ ] Inputs delimited as data
- [ ] Verdict requires a quoted span
- [ ] Output schema closed, no numeric score
- [ ] Calibration examples present and marked as such
- [ ] Bias controls stated
- [ ] Abstain path for missing/empty/truncated inputs, and a closed failure-type list
