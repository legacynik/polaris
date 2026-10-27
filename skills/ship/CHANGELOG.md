# Changelog — ship

## 3.1.0 — 2026-10-27

- Step 5 runs `scripts/slop_check.py` on every `.md` the branch touched: buzzwords, hedges,
  adjective triads, sentences over 40 words, empty headings, a first sentence that repeats its
  heading, "This document describes" openers. Exit 0 clean, 1 findings, 2 unreadable; a finding is
  fixed or allowed with `<!-- slop-ok: reason -->`. Rules for the judgement part in
  `references/writing.md`. Test: `tests/test_slop_check.py` (RED recorded).
- Version bump: minor, from 3.0.5. Description unchanged.

## 3.0.5 — 2026-10-26

- Tests and CHANGELOG name no product repository; the stale-main test assembles its fake key at run time, like the hook's selfcheck.

## 3.0.4 — 2026-10-26

- `pre_tool_hook.py` diffs a new PR against `origin/<default>...HEAD`, not the local default branch:
  a local `main` 61 commits behind origin dragged other people's commits into the diff and the
  redaction scan refused every `gh pr create` (reported from a product repository). Local only when the
  remote ref is missing. Test: `tests/test_pre_tool_hook_stale_main.py` (RED recorded).
- The hook fails closed when a sibling script cannot load: the imports ran outside `main()`'s
  `try`, exited 1, and Claude Code let the command run (reported from a product repository). Now exit 2.
  Test: `tests/test_pre_tool_hook_fail_closed.py` (RED recorded).

## 3.0.3 — 2026-10-25

- Public-package clean (C5): `redact_scan.py` and `pre_tool_hook.py` selfchecks build their AWS key, PEM header and URL-credential fixtures at run time, and `references/bypass-test.md` assembles the key with `printf`; the scanners see the same input.

## 3.0.2 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 3.0.1.

## 3.0.1 — 2026-10-25

- `invokes` follows the rename `plan` → `plan-area`. No behaviour change.
- Version bump: patch, from 3.0.0.

## 3.0.0 — 2026-10-24

- Rewritten to the 60-line form (What it does · When · Steps · Output · Not for); details moved to
  `references/contract.md` (contract, staging, gotchas, scripts), `references/merge-and-deploy.md`
  (proposal screen, Phase B, verification window) and `references/hook.md`.
- The steps follow the operating model §3 phase 7: local tests → `review` audit (replaces the <!-- slop-ok: changelog history, not rewritten -->
  separate simplify step and security angle) → local `real-testing` with a fresh-context breaker →
  DoD → **docs step** (new, from gstack `/document-release`: docs whose claims the diff changed are
  fixed or named under «Still open») → push and draft PR → staging once → `pr` → `babysit` →
  merge once, then phase 8 `plan close`.
- Size table: Tiny and Bug skip staging; Medium and Large hold it once.
- `invokes` gains `issue-contract` (step 4 files unmet criteria through it) and `plan` (step 10
  runs `plan_close.py`); both declare `ship` in `invoked-by`.
- Hook docs are harness-neutral: any pre-command hook that pipes `tool_input.command` can call
  `pre_tool_hook.py`; the Claude Code wiring is one example. Scripts unchanged.
- `config.yml` `ship.sop` now points to `references/merge-and-deploy.md`.
- Evals: checks retargeted to the reference files, plus c10–c13 (step order, docs step, size, close).
- Version bump: major (the step sequence changed), from 2.2.1. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md`.

## 2.2.1 — 2026-10-24

- Phase A1 names `review`'s second-opinion mode instead of the removed `codex-review` skill (B4b). No other change; the review/ship rewiring is unit B5's.

## 2.2.0 — 2026-10-24

- Renamed from `pol-ship` to `ship` (plain names, "Polaris" in the description); directory, `name:`, chain fields, body references, scripts and tests follow.
- Version bump: minor (rename), from 2.1.0. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
