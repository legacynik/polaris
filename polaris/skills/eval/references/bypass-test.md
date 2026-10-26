---
title: bypass-test — eval
description: The ways a measurement gets faked or skipped, and the runner behaviour or check that refuses each. The executed proof is skills-suite/_standard/tests/test_eval_run.py.
status: active
---

# Bypass cases

## B1 — paid run with nobody looking at the price

A full run on a metered judge starts straight away and spends what nobody priced.
Refused: without a pilot receipt for the exact backend, model and items, the runner exits 2.

```bash
OPENROUTER_API_KEY=x python3 skills-suite/_standard/eval_run.py --backend openrouter \
  --model deepseek/deepseek-v4-pro --out /tmp/e; echo "exit=$?"
# expected: no priced pilot for this exact run ... · exit=2
```

Test: `test_full_paid_run_refused_without_a_pilot`, `test_pilot_for_another_model_does_not_unlock`.

## B2 — a GPT judge through OpenRouter

The house rule: GPT models run only on the ChatGPT subscription, never on OpenRouter. A GPT id, a bare id, or a router
that may pick one is refused before any call.

```bash
OPENROUTER_API_KEY=x python3 skills-suite/_standard/eval_run.py --backend openrouter \
  --model openrouter/auto --pilot 3; echo "exit=$?"
# expected: REFUSED --model 'openrouter/auto' on OpenRouter: ... · exit=2
```

Test: `test_openrouter_refuses_gpt_family_and_routers`.

## B3 — a stub run reported as a result

`--dry-run` judges nothing. Its verdict is STUB and its rates are blank, so a dry run can never
be pasted as accuracy. Test: `test_dry_run_reports_every_skill_without_network`.

## B4 — an unparseable judge reply counted as a pass

Refused: the item is an error, the skill's verdict is ERROR, exit 1.
Test: `test_openrouter_unparseable_reply_is_an_error_not_a_pass`.

## B5 — the key leaks into output

Test: `test_key_never_reaches_stdout_stderr_or_files` — the key is only in the request header.

## B6 — "better" without a baseline

A candidate is called an improvement on its own numbers. Refused by the method: the loop and
release modes need `--compare` against the baseline report, and REGRESSED exits 1.
Test: `test_compare_flags_a_regression_against_the_published_report`.
