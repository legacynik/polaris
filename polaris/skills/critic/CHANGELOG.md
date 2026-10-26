# Changelog — critic

## 0.3.3 — 2026-10-26

- `invoked-by` names `apex-curate`, which runs critic on its AGENTS.md proposals.

## 0.3.2 — 2026-10-25

- Public-package clean (C5): recorded runs and patches carry `<vault>/` and `~/` instead of the machine path. Evidence content unchanged.

## 0.3.1 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 0.3.0.

## 0.3.0 — 2026-10-24

- What it attacks and when, with costs by work size (operating model §10): a plan once before `accepted`, each decision record, a claim before anyone relies on it, a diff that needs more than `review`. Never on tiny work.
- Blocking versus taste: `critical`/`important` findings go back to the author and keep a plan or DEC from being accepted; `minor` findings are taste, the only part that reaches the human. No schema change; `critic_gate.py` and the eval fixtures are untouched.
- 60-line form; the pass, halt rules and report schema moved unchanged to `references/flow.md`. `invoked-by` drops `review`, which no longer calls critic.
- Description changed, so `references/ratchet-state.json`'s trigger rate is stale until the next measured run.
- Evals: 4 new trigger cases (plan, decision record, tiny work, review audit), one behavioural check.
- Plan: operating model §3, §10, §11 (DEC-polaris-operating-model-001), Wave B unit B4b.

## 0.2.5 — 2026-10-24

- Dropped `wayfinder` from `invoked-by`: that skill moved to `skills-suite/_archived/` (unused since 2026-08-09, cut approved 2026-10-24).
