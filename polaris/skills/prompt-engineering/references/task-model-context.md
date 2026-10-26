# Task, model and context design

Adapted from the research snapshot of 2026-09-16. These are design hypotheses; validate on the current project and exact model.

## 3. Adaptation by task and measured model capability

### 3.1 Task shape

| Task shape | Prompt emphasis | Preferred checks |
|---|---|---|
| Classification/routing | Mutually exclusive labels, ambiguity/defer rule, boundary examples | Schema, confusion matrix by class, abstention/error analysis |
| Extraction | Evidence span, omission policy, normalization limits, source language | Exact fields, source support, completeness separate from correctness |
| Dedup/conflict decision | Candidate semantics, temporal scope, identity/scope constraints, explicit actions | Candidate recall first; action/target consistency; conflict false merges as veto |
| Retrieval/reranking | Query intent, eligibility filters, ranking evidence, budget | Recall@k before reranking; NDCG/MRR where ordered relevance exists |
| Page/document synthesis | Source/fact binding, preservation, unsupported-content rejection | Citation/entailment, omission, structure, stale-content suppression |
| Tool/agent action | Tool selection, arguments, execution result handling, terminal conditions | Grade selection → arguments → execution → result handling separately |
| Reviewer/judge | One criterion, binary definitions, calibrated examples, evidence citation | Human agreement, TPR/TNR or criterion error rates; drift checks |

An end-to-end failure must be attributed to its earliest broken layer. If the needed fact was not retrieved, editing the answer prompt is the wrong intervention. If a tool schema made a required argument unavailable, changing the model is premature.

### 3.2 Model capability profile

Maintain an empirical profile per exact model/version and task family. Record measured behavior rather than labels such as "smart", "small", or "reasoning model":

- instruction retention under realistic context length and placement;
- structured-output/schema reliability;
- tool selection and argument correctness;
- sensitivity to distractors, contradictions, and untrusted instructions;
- abstention and uncertainty calibration;
- multi-turn correction/recovery;
- language and domain performance;
- latency, token use, cost, and failure rate.

Also record provider endpoint/API, reasoning/thinking mode and budget, sampling settings, output limit, example-set identity, retry policy, and any reasoning-state continuity required across tool turns. A name containing `Flash`, `Pro`, or `reasoning` is a routing hypothesis, not evidence of capability.

Use that profile to choose the minimum sufficient scaffold:

- A model already reliable on a constrained schema should receive a short objective, evidence, and schema; extra procedural prose can create conflicts.
- A model that loses constraints in long context needs retrieval reduction, clearer sectioning, repeated critical boundary near the decision, or task decomposition before it needs more examples.
- A model weak at tool arguments benefits from tighter tool descriptions/schema and deterministic validation before verbose reasoning instructions.
- A model weak at semantic judgment may need a stronger model, verified decomposition, or removal of the decision from the model. Prompt length is not a substitute for capability.
- Reasoning-enabled profiles should start with a direct objective, evidence, constraints, and end condition. Manual step-by-step scaffolds are model-specific experiments and can interfere with native reasoning.
- Reasoning-low/off is a distinct profile, not a cheaper run of the same profile. Compare it in a separate cell and retain the exact reasoning setting in evidence.

Capability profiles expire when the model version, provider route, prompt surface, tool schema, or context distribution changes materially.

## 4. Context engineering contract

Every task declares its context pipeline:

```text
eligible sources
  → deterministic tenant/security/time filters
  → retrieval/candidate generation
  → ranking/selection
  → budget and ordering
  → rendered prompt sections
  → model decision
  → schema and semantic validation
```

Freeze and hash the policy at each stage for comparisons. Log enough identity to answer what evidence the model could see without copying private raw content into public receipts.

Evaluate three different questions independently:

1. **Availability:** did the eligible source/canonical fact exist?
2. **Selection:** did retrieval/context assembly include the necessary evidence within budget?
3. **Use:** given the evidence, did the model apply it correctly?

Context perturbations should cover missing evidence, irrelevant distractors, conflicting evidence, stale facts, placement changes, truncation, and injection inside payload. Use controlled ablations after isolated task probes, not a full combinatorial grid.

For memory and other source-grounded tasks, select applicable context probes:

- evidence early/middle/late and randomized source order;
- exact wording, paraphrase, indirect reference, and high-overlap lexical decoys;
- one fact, repeated keys, multiple facts, multi-hop source→fact→page, and aggregation;
- event time versus learned time, correction, supersession, and historical query;
- fully specified single-turn request versus requirements split across turns and late correction;
- uncompressed evidence, whole-unit selection, lossy projection, and forced route ablations;
- embedded instructions inside a source, page, prior assistant text, or tool output.

Do not hard-code paper benchmark lengths or compression ratios as project defaults. Derive buckets from the task's real input distribution and the exact served model profile. Preserve dates, negation, entity IDs, quotations, and source references deterministically when a lossy projection is evaluated.

