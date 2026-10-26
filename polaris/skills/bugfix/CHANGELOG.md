# Changelog — bugfix

## 1.3.1 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 1.3.0.

## 1.3.0 — 2026-10-24

- The 60-line form: `SKILL.md` is What it does · When · Steps · Output · Not for (56-line body);
  the previous body moved to `references/phases.md` (flow diagram, the twelve stages with their
  evidence, repo contract, anti-patterns).
- New step 3, the fix-loop breaker (from gstack `/qa` self-regulation): +15 per revert of your
  own fix, +20 per file changed outside the `raggio` perimeter, +5 for a fix touching more than
  3 files; above 20 the run stops, writes the score in the issue, sets `stato: bloccato` and asks
  the owner (`afk:blocked` when unattended). A step, not a script: it sits beside the existing
  4-red thrash breaker of stage `verde`, which is unchanged.
- New step 4: a defect found while fixing that is not this bug goes to `issue-contract` and
  becomes a bead with `discovered-from` (operating model §4), a GitHub issue only when that
  filter says so; a bug with no bead names its issue in the bead's description. A class-level hole becomes a lesson (`lesson_record.py`, model §7), not a
  ledger entry.
- Recurrence search also asks the agent memory (`ai-memory-retrieval`, skipped if absent). The
  blast-radius step, `references/phases.md` and check c4 name the code-graph verbs
  (references, call hierarchy), no harness tool.
- Evals: `evals/evals.json` removed — its four cases were already `eval/checks.json` c1, c3,
  c4, c6. New checks c7 (breaker) and c8 (side findings as beads); `eval/split/` added.
- `references/contract-template.yml`: comments in English; keys unchanged.
- `fix_gate.py` and `mutation.py` unchanged (behaviour frozen in this unit; their Italian
  messages and the Italian record fields are the gate's contract). `bugfix.toml` is not here: it
  waits for the Beads adoption tests.
- Version bump: minor, from 1.2.3. Spec: `docs/modules/polaris-harness/specs/2026-10-24-operating-model.md` (DEC-polaris-operating-model-001).


## 1.2.3 — 2026-10-24

- Baseline: the version this skill carried when the per-skill CHANGELOG became a gate (`_standard/check_skill_changelog.py`). Earlier history is in git.
