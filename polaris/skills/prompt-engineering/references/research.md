# Research snapshot — 2026-09-16

Extracted from a previously reviewed product-repo blueprint. This migration did not re-fetch sources or validate behavior in other projects. Provider guidance can change.

## 11. Research basis

The standard uses the repository's existing evaluation research plus the following evidence ledger. Living vendor guidance was retrieved on 2026-09-16. Vendor guidance establishes API semantics and useful starting hypotheses; it is not cross-provider proof.

### Model and prompt profiles

| Source | Date / type | Supports | Limit applied here |
|---|---|---|---|
| OpenAI [Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering) and [Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices) | living official docs, retrieved 2026-09-16 | Pin snapshots; distinguish instruction authority; use direct prompts for documented reasoning families; test prompt/model changes | OpenAI-specific and mutable; no transfer claim to Claude, Gemini, or GLM |
| Anthropic [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) | living official docs, retrieved 2026-09-16 | Clear instructions, structured sections, examples, and model/mode-specific revalidation | Example counts, XML, and thinking guidance are Claude-specific hypotheses |
| Google [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking) and [Gemini 3 guide](https://ai.google.dev/gemini-api/docs/gemini-3) | living official docs, retrieved 2026-09-16 | Thinking settings/state are part of model identity; Gemini 3 guidance favors direct prompts and API controls | Applies only when the resolved endpoint/version matches; summaries are not faithful reasoning proof |
| Zhuo et al., [ProSA](https://aclanthology.org/2024.findings-emnlp.108/) | EMNLP Findings 2024, peer reviewed | Prompt sensitivity varies by model/task; few-shot reduced sensitivity in tested settings | Tested models/datasets do not define current project-specific thresholds |
| Seleznyov et al., [When Punctuation Matters](https://aclanthology.org/2025.findings-emnlp.1109/) | EMNLP Findings 2025, peer reviewed | Small formatting/phrasing perturbations can change performance | Seeds robustness tests; does not prescribe one hardening recipe |

### Context, memory, and agent evaluation

| Source | Date / type | Supports | Limit applied here |
|---|---|---|---|
| Liu et al., [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/) | TACL 2024, peer reviewed | Evaluate evidence position and input length; capacity is not uniform utilization | Models are older; no universal U-curve claim for 2026 endpoints |
| Hsieh et al., [RULER](https://arxiv.org/abs/2404.06654) | 2024 preprint + official benchmark | Measure multiple retrieval, chain, aggregation, duplication, and hallucination failures | Mostly synthetic; its effective-context threshold is not a project-specific limit |
| Modarressi et al., [NoLiMa](https://proceedings.mlr.press/v267/modarressi25a.html) | ICML 2025, peer reviewed | Test semantic/indirect lookup and high-overlap decoys, not only lexical matches | Small constructed set and some parametric-knowledge dependence |
| Levy et al., [Context Length Alone Hurts LLM Performance](https://aclanthology.org/2025.findings-emnlp.1264/) | EMNLP Findings 2025, peer reviewed | Total irrelevant input can hurt even with correct retrieval; separate retrieval from reading | Synthetic expansion; two-stage mitigation was narrow and adds a failure boundary |
| Wu et al., [LongMemEval](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html) | ICLR 2025, peer reviewed | Separate extraction, multi-session reasoning, temporal reasoning, updates, and abstention | Constructed histories; not evidence for database recovery/write integrity |
| Laban et al., [LLMs Get Lost In Multi-Turn Conversation](https://arxiv.org/abs/2505.06120) | ICLR 2026 paper | Test sharded requirements, late corrections, early assumptions, and compiled current intent | Simulated conversations; does not generalize to every organic dialogue |
| Wallace et al., [The Instruction Hierarchy](https://arxiv.org/abs/2404.13208) | 2024 first-party research paper | Separate privileged instructions from untrusted retrieved/user/tool content | Gains came from training; delimiters alone are not authorization |
| Liu et al., [G-Eval](https://arxiv.org/abs/2303.16634) and Zheng et al., [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) | 2023 preprints/research | Explicit criteria can improve judging; position, verbosity, and self-preference require controls | A judge remains fallible and cannot be the sole release authority |
| Liu et al., [AgentBench](https://arxiv.org/abs/2308.03688) and Yao et al., [tau-bench](https://arxiv.org/abs/2406.12045) | ICLR 2024 / 2024 research | Include multi-turn state, tool stages, policy compliance, environment outcomes, and repeated reliability | Public environments differ from project-specific; local contracts and side effects still govern |

### Optimization and self-improvement

| Source | Date / type | Supports | Limit applied here |
|---|---|---|---|
| Khattab et al., [DSPy](https://proceedings.iclr.cc/paper_files/paper/2024/hash/f1cf02ce09757f57c3b93c0db83181e0-Abstract-Conference.html) | ICLR 2024, peer reviewed | Separate typed task signatures/program structure from prompt/examples as tunable parameters | Gains depend on metric/data; no new framework dependency implied |
| Opsahl-Ong et al., [MIPROv2](https://aclanthology.org/2024.emnlp-main.525/) | EMNLP 2024, peer reviewed | Optimize instruction/examples by component; use bounded search and full selection after mini-batch filtering | Search is costly/noisy and downstream scores can misassign credit |
| Agrawal et al., [GEPA](https://openreview.net/forum?id=RQm2KQTM5r) | ICLR 2026, peer reviewed | Trace and textual rubric feedback; retain a Pareto frontier rather than one average | Bad feedback enables evaluator exploitation; adaptive search consumes development data |
| Yuksekgonul et al., [TextGrad](https://www.nature.com/articles/s41586-025-08661-4) | Nature 2025, peer reviewed | Propagate textual feedback to the first responsible component and propose local changes | No convergence guarantee; critics can misdiagnose and bloat prompts |
| Yang et al., [Large Language Models as Optimizers](https://proceedings.iclr.cc/paper_files/paper/2024/hash/3339f19c5fcee3ad74502947a32be9e6-Abstract-Conference.html) | ICLR 2024, peer reviewed | Candidate search can use prior candidates/results | It maximizes the supplied metric; development gain is not promotion evidence |
| Li and Li, [Revisiting Automated Prompting](https://aclanthology.org/2023.acl-short.155/) | ACL 2023, peer reviewed | Keep a simple manual/served baseline; automatic methods did not consistently win | Older methods/models; methodological control, not a 2026 optimizer ranking |
| Schneider et al., [Overtuning in Hyperparameter Optimization](https://proceedings.mlr.press/v293/schneider25a.html) | AutoML/PMLR 2025, peer reviewed | Adaptive repeated search can overfit noisy validation; pre-register budget and use sealed holdout once | Indirect evidence from HPO, not a prompt-specific algorithm study |

### Decision models (System One)

| Source | Date / type | Supports | Limit applied here |
|---|---|---|---|
| TypeSafe docs: [state](https://docs.typesafe.ai/concepts/state.md), [primitives](https://docs.typesafe.ai/primitives.md), [Choice](https://docs.typesafe.ai/primitives/choice.md), [Noul](https://docs.typesafe.ai/primitives/noul.md), [Score](https://docs.typesafe.ai/primitives/score.md), [confidence](https://docs.typesafe.ai/confidence.md) | vendor docs, read 2026-10-05 | Question sizing, primitive choice, lean named state, no-match options, standalone Score levels, thresholds by cost, English as primary language | Vendor documentation; accuracy claims are the vendor's |
| Langfuse, [Jev as a judge](https://langfuse.com/docs/evaluation/evaluation-methods/jev-as-a-judge) and [blog 2026-09-18](https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals) | vendor docs/blog, 2026-09 | No rationale, no abstention, lean state (~32k tokens), weak on literal, arithmetic and date questions, data sent to the provider | Only published accuracy is 91.5% agreement with another LLM on 6,003 checks, not with humans |

| [jev-calibrate](https://github.com/smkrv/jev-calibrate) | open-source tool, README read 2026-10-08 | Per-question verdicts (gate, ranker, unusable), tune/holdout by stable hash, holdout ledger, edit criteria only, repeated-run spread | Bundled example is 66 messages labelled by the question author |
| [jevcal](https://github.com/abhixhek/jevcal) | open-source tool, README read 2026-10-08 | Wording lint, threshold picked on one half and verified on the other, lock file with CI drift check, confident-and-wrong review | Publishes no model numbers by design; its demo is a simulator |
| [jev-calibration-audit](https://github.com/jujumilk3/jev-calibration-audit) `FINDINGS.md` | independent audit, 2026-09-18, read 2026-10-08 | Measured: no-match option removed (accuracy 0.950 to 0.000 on unanswerable items), Noul vs two-option Choice differ by 0.125 on average, 15 added questions shift confidence by 0.008 | One model version on one day; multiple-choice benchmark data, not agent traces |
| [jev-belay](https://github.com/valentynkit/jev-belay) | open-source hook, README read 2026-10-08 | Facts gated in code before the call; an applicability question beside a claim question (AUROC 0.777 to 0.976); threshold swept against a wrong-action budget | 100 cases, 12 positives, labels from a model, one person's corpus |
| [pi-warden](https://github.com/DevMortimer/pi-warden) judge bench | project report, 2026-09-26, read 2026-10-08 | Computed evidence beat more raw text for loop judgments (0.725 to 0.992) | 80 cases; authors call the gain an upper bound |
| [awesome-jev-projects](https://github.com/logicrw/awesome-jev-projects) | community index, scanned 2026-10-08 | Where to look for further open-source uses | 854 entries, about 15 on evaluation; most descriptions are boilerplate, read the source |

The applied evals practice (error analysis first, then measurement, then improvement) supplies the workflow used here: diagnose comprehension, specification, and generalization separately; prefer binary failure-mode evaluators; and separate retrieval from generation.

Research findings guide hypotheses. A technique becomes a project-specific standard only after task- and model-specific evidence under the contracts above.
