# Changelog — issue-contract

## 2.6.3 — 2026-10-25

- Public-package clean (C5): `references/bypass-test-legacy.md` translated to English; fenced commands and the quoted strings the gate matches («Come si prova», «italiano semplice») unchanged.

## 2.6.2 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 2.6.1.

## 2.6.1 — 2026-10-25

- An unclear feature goes to `plan-area` (renamed from `plan`); `invokes` follows. No behaviour change.
- Version bump: patch, from 2.6.0.

## 2.6.0 — 2026-10-25

- «Come si prova» follows tdd-dev's first rule (founder, 2026-10-25): it states behaviour a user
  or caller can observe, never "file X contains", "function is named Y", "config says Z" or a
  timing, even when the request dictates such a check. Two lines under the SKILL.md template, the
  full rule with the timeout example in `references/flow.md`, both pointing at `tdd-dev` →
  *How tests are written*. `route.py` and `afk_label.py` unchanged.
- Eval: check c6. A request that dictates "deploy.sh contains --dry-run, the function is named
  run_dry, config.yml has DEPLOY_TIMEOUT: 300" as its proof: 2.5.0 copied all three into «Come si
  prova» (RED); a first 2.6.0 draft that said only "or a timing" still proved the timeout by
  waiting the real 300 s (RED again), so the SKILL.md line now says "a real wait (lower the
  limit)"; 2.6.0 writes the observable behaviour (`eval/red-2026-10-25/`, blind judge).
- Version bump: minor, from 2.5.0.

## 2.5.0 — 2026-10-24

- Rewritten to the 60-line form; every rule, the flags of `route.py` and the limits moved to
  `references/flow.md`. `scripts/route.py`, `scripts/afk_label.py` and their tests unchanged.
- Description names its deps (bd, gh, python 3). `invoked-by` gains `ship` (its DoD step).
- Version bump: minor, from 2.4.2. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md`.

## 2.4.2 — 2026-10-24

- Dropped `wayfinder` from `invoked-by`: that skill moved to `skills-suite/_archived/` (unused since 2026-08-09, cut approved 2026-10-24).

## 2.4.1 — 2026-10-24

- Step 3 hands a feature with an unclear outcome or DoD to `plan` (which absorbed
  `ambitious-goal`); `invokes` follows. No behaviour of the scripts changes.

## 2.4.0 — 2026-10-24

- New step 2: the GitHub-vs-Beads filter of the operating model §4 (`scripts/route.py`). A GitHub
  issue only when a human must schedule or approve it, it does not close inside the current PR or
  phase, it has «Come si prova» and an `area:`, and it duplicates no open issue; otherwise a bead
  (`bd create` with type + `src:` `kind:` `area:`, `--deps discovered-from:` when found while
  working) and the reason in one line. A bead is promoted through the same door and gets
  `external_ref gh#N`. Never a mirror. `bd` is a hard dependency: the skill stops with install
  instructions when it is missing. Fail-closed: a blank duplicate search or a bead without
  `--src`/`--kind` exits 2 instead of routing.
- Template: `## Regression checks` becomes `## Come si prova`, the section the filter requires.
- `afk_label.py` unchanged. Tests: `tests/test_route.py` (RED recorded with `red_check.py`).
- Version bump: minor, from 2.3.0. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md`.
