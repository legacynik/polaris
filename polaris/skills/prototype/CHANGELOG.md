# Changelog — prototype

## 1.0.2 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 1.0.1.

## 1.0.1 — 2026-10-25

- The verdict is read by `plan-area` (renamed from `plan`). No behaviour change.
- Version bump: patch, from 1.0.0.

## 1.0.0 — 2026-10-24

- Imported into polaris-os `skills-suite/` from `mattpocock/skills` (`skills/engineering/prototype`,
  MIT; see CREDITS.md), where it lived only in `~/.agents/skills/prototype`.
- Phase 2 of the operating model (§3, §9): one named question per spike, on a throwaway branch
  `spike/<plan-name>-<slug>` that never merges; only the verdict enters main, as a block in plan
  file section 4 that flips the tested assumption to `proven: <verdict>`; a spike that answers
  nothing is deleted. The donor's "fold the winner into the real code" is replaced by a rebuild
  in the build phase, test-first.
- Form: body ≤ 60 lines, five fixed sections; LOGIC.md and UI.md moved to `references/`.
  Added `references/bypass-test.md`, `eval/` (9 trigger cases, 5 checks, split),
  `tests/test_prototype.py` (RED recorded before the import).
- Carries the `## Where this goes` block that `scripts/skill_outputs_check.py` reads.
