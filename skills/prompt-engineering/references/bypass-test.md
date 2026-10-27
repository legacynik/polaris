---
title: bypass-test — prompt-engineering
description: The ways this skill can be skipped or emptied, and the check that catches each. Proved by the trigger eval (eval/) run through skills-suite/_standard/eval_run.py and by the behavioural checks.
status: active
---

# Bypass cases

## B1 — "done" without a measure

A prompt is rewritten, reads better, and is called fixed. Nothing ran.
Caught by: Step 6 and check `c4` — the reply carries `eval`'s verdict on frozen identities or
says `NOT_RUN`. A stub or harness-pending run is not a verdict (`eval`, Output).

## B2 — the measurement is absorbed here

"Write a judge and tell me how often it is right" or "compare the two models" is handled as a
wording task, and the number is made up or skipped.
Caught by: the decoys `n09`–`n12` in `eval/prompts.json` (they must route to `eval`):

```bash
python3 skills-suite/_standard/eval_run.py --skill prompt-engineering --backend harness
# answer the requests, rerun with --answers FILE: n09–n12 must come back "no"
```

## B3 — candidate and judge edited together

The judge is loosened in the same campaign as the prompt it grades, so the score rises and
nothing improved. Caught by: Step 5 and `write-judge.md` — a judge changes only in its own
campaign and is recalibrated by `eval` before it grades anything.

## B4 — a skill body or instruction file through this door

A SKILL.md or AGENTS.md is written as if it were a prompt and skips the repository's standard.
Caught by: decoys `n01`, `n02` and check `c3`.
