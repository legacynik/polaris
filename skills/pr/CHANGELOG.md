# Changelog — pr

## 1.4.2 — 2026-10-25

- Public-package clean (C5): fixtures carry a neutral owner and repo (`acme-owner`, `acme/acme-api`, `qa@example.com`) and `senza-skill.md` is renamed `no-skill.md`. Same verdicts, same tests.

## 1.4.1 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 1.4.0.

## 1.4.0 — 2026-10-24

- Rewritten to the 60-line form; the template and title rules moved to `references/template.md`,
  step details, proof, risk, voice and gotchas to `references/writing.md`. Checker unchanged.
- `tests/test_controlla_pr.py::test_c1` reads the template from `references/template.md` (RED
  recorded with `red_check.py` before the move).
- New `eval/` (prompts, checks, train/test split). Description names its deps (gh, python 3).
- Version bump: minor, from 1.3.0. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md`.

## 1.3.0 — 2026-10-24

- Renamed from `pol-pr` to `pr` (plain names, "Polaris" in the description); directory, `name:`, chain fields, body references, scripts and tests follow.
- Version bump: minor (rename), from 1.2.0. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
