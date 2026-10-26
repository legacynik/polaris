---
title: systems — eval
description: What changes when the target is an agent, a multi-turn conversation, a retrieval pipeline or a tool-using system — where to look for the first failure and which metric to use.
status: active
---

# Agents, conversations, retrieval, tools

The method is the same; what changes is where the first failure hides.

## Multi-turn conversations

- **Session first.** One PASS/FAIL per conversation: was the user's goal met? Drill into turns only
  in sessions that failed; scoring every turn by default is expensive and noisy.
- **Is it really multi-turn?** Condense the failing turn into one prompt with all the context it
  needed. It still fails → a single-turn problem (grounding, retrieval, instruction). It passes →
  truncate the conversation just before the failing turn and sample it many times: the rate at
  which the constraint survives is the multi-turn number.
- **Coherence checks** only when memory is the suspect: does a later turn contradict an earlier
  fact or commitment?
- **Perturbations** on passing conversations: change the goal halfway, add ambiguity to a clear
  message, contradict the agent; one change at a time. Models often commit early and do not revise.

## Retrieval

- Evaluate retrieval separately from generation. Swap in unrelated context: an unchanged answer
  means the model ignores retrieval, and the fix is the prompt, not the retriever.
- Metrics by stage: first-stage retrieval → **Recall@k**; reranking → **NDCG@k** (read beside
  recall); one key fact needed → **MRR**; multi-hop → Recall@k or NDCG@k.
- Synthetic questions copy the source's wording and flatter keyword search. Make hard ones: pick a
  chunk with a clear fact, find similar chunks without it, ask for a question only the first one
  answers using the others' vocabulary. Always add 20–30 real logged queries.
- Before blaming the embedding model, grid-search chunk size × overlap and re-measure; bigger
  chunks are not automatically better.

## Tool calls — four stages, four fixes

| Stage | Fails as | Fix |
|---|---|---|
| selection | wrong tool, a tool that does not exist, a needed call missing | tool names and descriptions |
| arguments | schema-invalid, or valid but semantically wrong; injection in a value | schema validation, argument examples, sanitising |
| execution | runtime error, a silent empty result | handle and log errors; treat empty as a signal |
| output handling | result misread, a critical detail dropped, not integrated in the answer | a judge on consistency between tool output and answer |

## Agents with many steps

- Attribute each failing trace to its earliest failed step. For hundreds of traces, define discrete
  states and count transitions (last good state → first failed state); the hottest transitions say
  where to read first. Column totals mislead: a state may fail only when entered from one
  predecessor.
- Every agent loop has a hard step cap and timeouts; a run that hit the cap is its own failure mode.
- A model's stated confidence correlates poorly with being right. Before routing on confidence (a
  cascade to a stronger model), measure that correlation on a held-out set.
