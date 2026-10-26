# Changelog — prompt-engineering

## 1.0.1 — 2026-10-26

- `references/write-system-one.md` points at `eval`'s `references/graders.md` (was `judges.md`,
  merged into it).

## 1.0.0 — 2026-10-24

- Imported into the lab from `~/.agents/skills/prompt-engineering` (unversioned there) and made
  ours: the 60-line form, description `◇ Polaris — …`, no model and no harness tool named in the
  body. The old body's surfaces, task contract and construction rules moved to
  `references/method.md`; its measurement rules, modes `prepare/run/analyze/propose` and the
  bounded loop moved to the new `eval` skill, which calls this one for each candidate.
- Scope: the words only. Measuring, judge calibration and model comparisons are `eval`'s; the
  trigger cases that asked for them are now decoys (`n09`–`n12`).
- Dropped `references/ratchet-state.json` (a trigger-rate floor from a runner the lab no longer
  has); the trigger rate is now measured by `skills-suite/_standard/eval_run.py`.
- Sources cited by concept; the private book references were replaced by the `eval` skill.
