# Changelog — crasher

## 0.5.1 — 2026-10-25

- Public-package clean (C5): the description names its `bd (Beads)` dependency (step 6 searches twins among beads), as the promotion gate requires.

## 0.5.0 — 2026-10-24

- The 60-line form (60-line body); the previous body moved to `references/run.md`.
- New step 1, "QA without a webpage" (gstack): before the first probe the run record declares the
  `surface`, the `tools` per surface and the `writes` it may make; an API or CLI surface
  needs no browser. `crash_report.py` does not refuse a record without them yet (eval check c7).
- New step 2: browser surfaces use browser-harness in a dedicated instance on the logged-in
  profile `real_test.browser_profile` as `real_test.account`; the agent never types a
  credential, and an expired session stops the run ("log in again in profile <X>"). Replaces the
  harness-specific `browser-pilot` agent. Without browser-harness the walk is API-only.
- Picked findings go to `issue-contract`, whose filter makes them beads or, when it says so,
  GitHub issues (operating model §4); twins are searched among open beads too (`bd search`).
- `## Where this goes` stays in `SKILL.md` (`skill_outputs_check.py`): produces **validation**.
- Description starts "◇ Polaris — " and names its dependencies.
- Version bump: minor, from 0.4.0. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md` (DEC-polaris-operating-model-001).


## 0.4.0 — 2026-10-24

- Baseline: the version this skill carried when the per-skill CHANGELOG became a gate (`_standard/check_skill_changelog.py`). Earlier history is in git.
