# Changelog — start

## 1.15.4 — 2026-10-26

- The legacy-hook fixture in `install_settings.py` drops its `|| true` tail: install keys on the
  script name, so the test is unchanged and the `nonconforming.allow` excuse is gone (promotion gate).

## 1.15.3 — 2026-10-25

- `end` absorbed `update`: the session `start` opens is checkpointed and closed by `end`; description, Not-for line, references and the repo-contract templates (`README.md`, `state/current.md`, `state/todos.md`) name `/end checkpoint` instead of `/update`. `_brief_parts.py` and `_cockpit_signal.py` import the state scripts from `end/scripts/`.

## 1.15.2 — 2026-10-25

- Public-package clean (C5): CHANGELOG provenance names the public package repo, not its owner login.

## 1.15.1 — 2026-10-25

- Follows the rename `implement` → `implement-plan` (references, `invoked-by`, eval tuples). Text only.
- Version bump: patch, from 1.15.0.

## 1.15.0 — 2026-10-24

- Rewritten to the 60-line form (`## What it does` · `## When` · `## Steps` · `## Output` ·
  `## Not for`), with `lifecycle`, `io`, `status: active` and the ◇ description; the old steps live
  verbatim in `references/first-use.md`, `resume-set.md`, `compaction.md`. `reference/` renamed
  `references/` (`voice.md`, `two-stage-brief.md`). Brief headings in English (Remember, Signals).
- States that the context pack is optional and that memory is the agent memory (ai-memory), never
  read at start.
- Scripts: every one has a real `--selfcheck`; the compaction hook template is silent when the
  reinserter is absent and visible when it fails (`session_gate.py reinsert` passes its exit code
  through, RED `.rosso/b6a-compaction-hook.jsonl`); `resume_paths.sh` fixture no longer carries a
  vault directory name (public package repo issue 5).
- New: `references/bypass-test.md`, `eval/` (11 trigger cases, 3 checks, split), `tests/`. Plan unit B6a.

## 1.14.3 — 2026-10-24

- Imported into polaris-os `skills-suite/` from the public package repo at 8fdfee9 (`polaris/skills/start`).
- Version bump: patch (import), from 1.14.2. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
