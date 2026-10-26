# Changelog — review

## 2.1.1 — 2026-10-26

- The description no longer says "use per phase": review runs once, on the PR (operating model §10, 2026-10-26).

## 2.1.0 — 2026-10-26

- No longer run on each plan phase: it runs once on the whole branch inside `ship`, on the PR. Founder: per-phase gates on Beads were
  rigid and made small phases drift (operating model §10).

## 2.0.6 — 2026-10-25

- Public-package clean (C5): `scan_blockers.py --selfcheck` builds its AWS and `sk-` fixture keys at run time, so the file carries no key shape; the scanner sees the same input.

## 2.0.5 — 2026-10-25

- Follows the rename `implement` → `implement-plan` (references, `invoked-by`, eval tuples). Text only.
- Version bump: patch, from 2.0.4.

## 2.0.4 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 2.0.3.

## 2.0.3 — 2026-10-25

- `invoked-by` gains `implement`: its phase gate runs the audit on the phase's last commit. No behaviour change.
- Version bump: patch, from 2.0.2.

## 2.0.2 — 2026-10-25

- Axis 1 (`tests`) takes its rules from `tdd-dev` → *How tests are written*: a test that asserts a
  name, a path, a file's text, message wording or a config value is a structural finding (the test
  must be rewritten), unless that is the caller's contract. One line in Steps 2, the full rule in
  `references/axes.md` row 1.

## 2.0.1 — 2026-10-25

- Structural-finding beads carry `--parent <epic>`: the feature gate's own blocked-step check and `bd ready --mol` only see beads in the epic's molecule (measured by B2 on the merged gate); never `--parent <phase>`, since bd keeps one dependency per pair. `implement`'s adopt step becomes a no-op.

## 2.0.0 — 2026-10-24

- Major: review becomes THE audit, on six axes (tests prove behaviour, architecture drift against governing decisions, constraints, plan adherence, simplicity and reuse, security), run per phase while implementing and on the whole diff inside `ship`, where it replaces the separate simplification and security passes.
- Severity routing: mechanical fixes applied and listed under `fixed`; structural findings become beads that block the phase (`bd create … -l src:review,kind:finding --deps discovered-from:<phase>,blocks:<phase>`); taste findings advisory, never blocking. Requires `bd`.
- Absorbs `codex-review` 1.0.0 as the second-opinion mode: the hardened read-only invocation, the why-per-flag table and its two bypass cases now live in `references/second-opinion.md` and `references/bypass-test.md` (S1, S2). Another model family through whatever CLI the harness has; no model pinned. The `codex-review` folder is removed; `sweep` Phase 3c now calls this mode.
- 60-line form (What it does · When · Steps · Output · Not for); the gate mechanism moved unchanged to `references/gate.md`; axes and severities in `references/axes.md`; `protocol.md` documents `lens`, `bead` and `fixed`. No model and no harness tool named in SKILL.md.
- `invokes` drops `critic` and `codex-review`; `invoked-by` adds `sweep`. Evals: 7 new trigger cases, checks rewritten so every `cmd` runs green against this version.
- Plan: operating model §3, §10, §11 (DEC-polaris-operating-model-001), Wave B unit B4b.

## 1.2.0 — 2026-10-24

- Renamed from `polaris-review` to `review` (plain names, "Polaris" in the description); directory, `name:`, chain fields, body references, scripts and tests follow.
- Version bump: minor (rename), from 1.1.0. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
