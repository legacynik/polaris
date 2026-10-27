---
title: review — the six axes and the three severity classes
description: What each axis checks, where its evidence comes from, and how a finding is sorted into mechanical, structural or taste.
status: active
---

# The six axes

Every finding names one axis (`"lens"` in the findings file) and quotes the line it is about.
Axis 4 goes to the Spec findings file; the other five go to the Standards file
(`protocol.md`). The two files never merge into one ranking.

| # | Axis (`lens`) | Ask | Evidence to read |
|---|---|---|---|
| 1 | `tests` | Do the tests prove behaviour, not implementation? A test that asserts on a mock of the code it claims to test, on call counts of internals, or on a private shape proves nothing a user sees. Each new behaviour has a test seen red first. The test-value bar (gstack `/test-audit`): no assertion-free probe, no grep of the source standing in for a behaviour check, no test-only export, no near-duplicate of an existing test; a contract test on machine-read tokens is kept. The rules are `tdd-dev` → *How tests are written*: a test that asserts a name, a path, a file's text, message wording, a config value, private structure or timing is a **structural** finding (the test must be rewritten), unless that is the contract a caller sees. | `tdd-dev`'s RED record (`red_check.py verify`), the test diff, `scan_blockers.py`'s mock-only flag |
| 2 | `architecture` | Does the diff drift from the decisions governing the touched paths: a boundary crossed, a contract changed, a dependency direction reversed, an `accepted`/`executed` DEC contradicted? | `check_context_backbone.py --check` where the repo has it (architecture skill); else the DEC files and ledger entries naming the touched paths |
| 3 | `constraints` | Does it break a written rule? | `CONSTRAINTS.md`, `.claude/rules/`, every LOCKED / "blindato" rule in the `AGENTS.md`/`CLAUDE.md` covering the touched paths |
| 4 | `plan` | Does it do the phase DoD, no less and no more? A missing DoD line, an unasked feature, or a decision the plan left open taken silently. | the plan file §6 (DoD) and the phase bead's acceptance; for a tiny change, the bead or issue acceptance |
| 5 | `simplicity` | Reinvented stdlib or platform feature, a needless new dependency, an abstraction with one caller, dead code or dead flags, an existing helper not reused. | the diff plus a search of the repo for the helper it re-implements |
| 6 | `security` | Trust boundaries (LLM or tool output used unchecked), unvalidated input reaching SQL, shell, paths or templates, secrets in code or untracked files, a race on shared state. | `protocol.md` baseline checklist; `scan_blockers.py` runs the secret and injection scans |

## Severity — what happens to a finding

| Class | Test | What happens | Findings file |
|---|---|---|---|
| **mechanical** | one correct fix, visible in the diff, no judgement (a typo, an unused import, a missing `ORDER BY` with an obvious key) | applied now, re-staged, listed under `fixed[]` | not a finding |
| **structural** | the fix needs a design choice, touches more than the line, or a test must be rewritten | a bead that blocks the phase (below); the phase cannot close | `CRITICAL` |
| **taste** | reasonable people differ; nothing breaks if left | advisory, listed, never blocks | `INFORMATIONAL` |

A structural finding becomes one bead, and the phase depends on it:

```bash
bd create "<summary>" -t task -l src:review,kind:finding,area:<area> --parent <epic-id> \
  --deps discovered-from:<phase-id>,blocks:<phase-id> -d "<file>:<line> — <evidence>"
```

`blocks:<phase-id>` makes the phase depend on the new bead, so `bd ready` will not offer the
phase's close until it is done. `--parent <epic-id>` puts it in the epic's molecule, so
`bd mol show <epic>`, `bd ready --mol` and the feature gate see it; never `--parent <phase-id>`
(bd keeps one dependency per pair, and the phase already has `discovered-from`). Run by hand
with no phase, drop the parent and both deps; the `CRITICAL` in the
findings file still blocks the commit through the gate. No `bd` on PATH: stop and say
"review needs bd for structural findings", never downgrade them to taste.

Doubt between structural and taste: structural. Doubt between mechanical and structural:
structural. A class is never lowered to make a phase close.
