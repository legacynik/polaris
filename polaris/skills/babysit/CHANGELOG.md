# Changelog — babysit

## 1.3.2 — 2026-10-25

- Public-package clean (C5): the PR 1942 fixtures carry a neutral owner (`acme-owner`, `acme/acme-api`) and drop GitHub's per-user API URLs; the test's viewer follows. Same states, same 29 tests.

## 1.3.1 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 1.3.0.

## 1.3.0 — 2026-10-24

- Rewritten to the 60-line form; the contract options, the loop in full, reply rules and gotchas
  moved to `references/loop.md`. Scripts unchanged.
- Harness-neutral: the WAITING rerun uses "a recurring runner your harness provides, or cron".
- New `eval/` (prompts, checks, train/test split). Description names its deps (gh, python 3).
- Version bump: minor, from 1.2.0. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md`.

## 1.2.0 — 2026-10-24

- Renamed from `pol-babysit` to `babysit` (plain names, "Polaris" in the description); directory, `name:`, chain fields, body references, scripts and tests follow.
- Version bump: minor (rename), from 1.1.0. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
