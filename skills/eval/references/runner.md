---
title: runner — eval
description: The lab's eval_run.py for skills — commands, exit codes, judge backends, the GPT-family rule — and what it does not record yet.
status: active
---

# The runner

## Commands, for skills

```bash
python3 skills-suite/_standard/eval_run.py --dry-run                      # $0, whole lab, format check
python3 skills-suite/_standard/eval_run.py --skill X --backend harness    # $0, you judge
export OPENROUTER_API_KEY=…                                               # or TYPESAFE_API_KEY
python3 skills-suite/_standard/eval_run.py --skill X --backend openrouter --model vendor/model --pilot 3
python3 skills-suite/_standard/eval_run.py --skill X --backend openrouter --model vendor/model --bar 0.9
```

```bash
python3 skills-suite/_standard/eval_run.py --lift --skill X --backend claude-code --model sonnet   # with vs without the skill
```

Exit 0 ok · 1 format defect, judge error, below bar, regression or stop rule · 2 usage or
refusal (GPT judge on OpenRouter, missing key, no pilot) · 3 harness answers pending.

## Judge backends

| backend | what it is | cost | when |
|---|---|---|---|
| `stub` (`--dry-run`) | answers "no" without judging; rates are blank | $0 | prove the wiring, count the items |
| `harness` | writes `requests.jsonl`; the current agent answers yes/no; `--answers` scores | $0 | small sets, first passes, no key |
| `claude-code` + `--model sonnet` | one headless `claude -p` per item: no tools, no MCP, no settings or hooks, in an empty dir; JSON reply `{reasoning, answer}` | $0 marginal (the Claude subscription); tokens reported, `--max-usd` cannot cap it | the promotion gate (`promote.py`): unattended, no key — chosen by the founder on 2026-10-26 over a paid OpenRouter judge and over promoting without evals |
| `openrouter` + `--model vendor/model` | chat model, JSON reply `{reasoning, answer}`, temperature 0; cost read from the response | metered | larger sets; any family except GPT |
| `typesafe-jev` + `--model jev-…` | System One `noul` question: typed yes/no with its probability | metered (tokens) | fast binary judgments where the probability is useful |

The GPT family never goes through OpenRouter (it runs only on the ChatGPT subscription): the
runner refuses `openai/…`, any id containing `gpt`, bare ids (OpenRouter prefixes them with
`openai/`), and routers (`openrouter/*`, `*/auto`, `…router`, `switchyard`, `fusion`, `pareto`)
that may land on one — a judge must be a pinned model anyway. Keys come only from
`OPENROUTER_API_KEY` / `TYPESAFE_API_KEY`; the runner never prints or writes them, and names the
variable when it is missing.

A trigger case is judged with the whole lab catalog as decoys: "would the agent pick this skill,
among all of them, for this message?" — not the description in isolation, which flatters it.

`--repeat 3` (odd only) judges each item three times and scores the majority; `items.json` keeps
every answer. Under `--compare`, REGRESSED means more cases went from right on every baseline call
to wrong on every call now than the reverse: one call against one refuses a flicker at random.
`promote.py` runs both arms with `--repeat 3`, only for a new skill or a changed description (`--evals` judges every one).

## Not built yet

`--lift` gives the arms SKILL.md only, with no tools: they describe the work instead of doing it,
and a check that depends on a reference file the body only points to can fail in both arms.

`eval_run.py` writes `report.json` and `items.json` under `--out` (default `.eval-runs`, local).
It does not yet write the record of [records.md](records.md) (`run.json`, `cases.jsonl`, the
index line) nor send runs to the trace platform. Until it does, copy its report into the record by
hand and say so in the run's README.
