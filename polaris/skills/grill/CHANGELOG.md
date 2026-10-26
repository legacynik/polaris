# Changelog — grill

## 2.0.5 — 2026-10-25

- A decision that surfaces in discovery (boundary, interface, contract, dependency, or a rule that binds the future) goes to `/architecture` (`design` if open, else `decide`) before the plan; Large work's path starts with `/architecture decide`. Seen in the chain probe: on a public-contract idea grill proposed `prototype` → `plan-area` and skipped `architecture`.
- Version bump: patch, from 2.0.4.

## 2.0.4 — 2026-10-25

- Public-package clean (C5): bypass-test evidence and one eval prompt use neutral product names; CHANGELOG provenance names the public package repo, not its owner login.

## 2.0.3 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 2.0.2.

## 2.0.2 — 2026-10-25

- The skeleton opens with a short `## Executive` for a person instead of the three-line exec summary.
- Version bump: patch, from 2.0.1.

## 2.0.1 — 2026-10-25

- Hands off to `plan-area` (renamed from `plan`); `invokes` and the negative eval tuple follow. No behaviour change.
- Version bump: patch, from 2.0.0.

## 2.0.0 — 2026-10-24

- Phase 1 Discover of the operating model (§3): grill now writes. For a Large or Medium idea it
  opens the plan file at `status: discovery` with sections 1–3 from `references/plan-file.md`
  (exec summary and scope diagram on top, nine §5 sections), then hands off to `plan`; the
  founder's yes on scope and assumptions is the exit. Major: it was read-only until 1.2.0.
- Proposes the size from the §2 criteria (Large · Medium · Tiny · Bug, first match wins, founder
  overrides in one word); Tiny and Bug write no file.
- Grills against prior art from primary sources, earlier ideas (`kind:idea` beads, archived plans)
  and what we already own; every assumption names how to test it.
- One open plan per area: an area already taken parks the idea as a bead `kind:idea`.
- Dropped: the chat handoff template and the critic offer (critic runs once on the plan in
  phase 3, owned by `plan`); outcome/DoD sharpening points to `plan`.
- Memory through the agent memory (`ai-memory-retrieval`), skipped if absent; no model or harness
  named.
- Form: body 58 lines, five fixed sections; the interview procedure moved to
  `references/interview.md`. Added `references/bypass-test.md`, `eval/` (10 trigger cases,
  6 checks, split), `tests/test_grill.py` (RED recorded before the rewrite).
- Chain: `invokes: [prototype, domain, architecture, database-schema]`.
- Carries the `## Where this goes` block that `scripts/skill_outputs_check.py` reads.
- One plan-file skeleton shared with `plan`: `references/plan-file.md` now also carries the
  shapes `feature_gate.py` reads (`tests:`, `### Phase N:` under section 7, `Beads epic:` under
  section 8); `invokes` gains `plan`; grill leaves `scripts/skill_outputs.allow`.

## 1.2.0 — 2026-10-24

- Imported into polaris-os `skills-suite/` from the public package repo at 8fdfee9 (`polaris/skills/polaris-grill`).
- Renamed from `polaris-grill` to `grill` (plain names, "Polaris" in the description); directory, `name:`, chain fields, body references, scripts and tests follow.
- Version bump: minor (rename), from 1.1.1. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
