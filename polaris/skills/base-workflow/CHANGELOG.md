# Changelog — base-workflow

## 0.7.2 — 2026-10-26

- An eval case no longer names a private project (promotion leak gate).

## 0.7.1 — 2026-10-26

- Chain probe: the open-idea case expects `grill` first and `architecture` named as the next step
  (measured 2026-10-26: grill found the ADR that forbids an interface with one implementation and
  asked who the second consumer is — the decision does not exist yet). A new case, a decision
  already taken, must go straight to `architecture` (PASS 1/1).

## 0.7.0 — 2026-10-25

- SKILL.md is now the router and nothing else (founder: "the only thing it should have is which
  skill to call, how and why"): step 1 is the case → skill → why table, step 2 the hand-off table
  (after → next, or STOP with the options), step 3 asks at a STOP. The method (understand, design,
  test first, verify) moved out of the body into `references/method.md` and the skills that apply it.
- `eval/chain_probe.py` also checks the hand-off: a case's `next_any` must appear in the agent's
  last message. Eval prompts and the changelog no longer name a product.
- Every decision goes through `/architecture decide` (founder: one standard, from any skill and
  phase; `design` first when options are open, `doc` for ARCHITECTURE.md); architecture before the
  plan. A PreToolUse hook on the founder's machine refuses hand-written ADR/DEC/decisions.md/
  ARCHITECTURE.md. New probe case `architecture-before-plan`; a STOP that asks counts as a hand-off.
- Version bump: minor, from 0.6.1.

## 0.6.1 — 2026-10-25

- Follows the rename `implement` → `implement-plan` (references, `invoked-by`, eval tuples). Text only.
- Version bump: patch, from 0.6.0.

## 0.6.0 — 2026-10-25

- New `references/chains.md`: the map of hand-offs (diagram + table: situation → chain → why → when to stop and ask). Step 8: after each skill, propose its `Next:` against the map; at a STOP, ask with the options. Founder: the structured logic must not depend on the person remembering the chain.
- `eval/chain_probe.py` + `eval/chain_cases.json`: runs Claude Code headless on 5 real cases (idea, bug, scoped Medium, done, track-only) and reads which skills it actually invoked. Baseline 2026-10-25, Sonnet, before this change: 0/5 in an empty repo and 0/5 in a read-only product-repo worktree — the agent acts directly (e.g. `bd create`) instead of invoking the skill. The entry, not the chain, is the gap.
- Version bump: minor, from 0.5.2.

## 0.5.2 — 2026-10-25

- Medium and Large route through `plan-area` (renamed from `plan`). No behaviour change.
- Version bump: patch, from 0.5.1.

## 0.5.1 — 2026-10-25

- `status: active`. It carried the ◇ marker, which the standard reserves for active skills, and it
  is on the approved public list of 26 skills.

## 0.5.0 — 2026-10-24

- The 60-line form (56-line body): the method now sizes the work by operating model §2 and takes
  that size's path through the phases of §3, pointing at the model instead of restating it. The
  previous body (grading, the arc, thresholds, the simplicity ladder, architecture while coding,
  phase calibration, quality gates, rationalizations) moved to `references/method.md`.
- `## Where this goes` now says `This skill produces: **none**`: the design of Medium and Large
  work belongs to the plan file (`plan`), not to a spec this skill writes.
- Prior-art search also asks the agent memory (`ai-memory-retrieval`, skipped if absent).
- Description starts "◇ Polaris — ". First `eval/`: 11 trigger cases (7 should, 4 should-not),
  4 behavioural checks, train/test split.
- Version bump: minor, from 0.4.0. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md` (DEC-polaris-operating-model-001).


## 0.4.0 — 2026-10-24

- Baseline: the version this skill carried when the per-skill CHANGELOG became a gate (`_standard/check_skill_changelog.py`). Earlier history is in git.
