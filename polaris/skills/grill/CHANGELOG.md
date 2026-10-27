# Changelog — grill

## 2.1.0 — 2026-10-27

- The interview grounds every question in context instead of asking formulaic ones. Look before
  you ask: read what the founder pointed at and the code it touches. The first message plays the
  request back (what, for whom, why) with what was found. It ends on ONE question, the one that most
  changes what gets built. Then one Socratic question per turn, built on the last answer or a
  finding, with no menu of answers. A correctable proposal often beats a question.
- Fidelity: playback in chunks keeps the founder's words and numbers as his, unchanged; every fill
  is labelled as the agent's proposal with a reason, every handed-over technical choice as "my call".
- Before writing: appetite (never invented as his), no-gos and rabbit holes, recorded in Discovery;
  a press release + FAQ option for Large work.
- Approaches in a message of their own: 2–3 coarse ways, trade-offs, one recommended, the founder
  picks. Approaches that differ on a boundary, data contract, dependency or pipeline shape go to
  `/architecture design` then `decide`; all weak, repeated failure or "flip the plan" go to
  `problem-solver` (added to `invokes`; problem-solver 0.4.1 declares grill in `invoked-by`), then
  the grill resumes.
- Three thinking tools, one line each: what would have to be true (the assumptions), a pre-mortem
  (anti-goals, no-gos, rabbit holes), a quick divergence with at least one inverted approach before
  the 2–3 are laid out; deeper → `problem-solver`.
- Lighter body: procedure (evidence pack, prior art, premise teardown, size table) moved to
  `references/interview.md` or compressed; the body gives goal, moves and critical-thinking prompts.
  Body 60 → 60 lines. `references/interview.md` rewritten with an example per move;
  `references/plan-file.md` Discovery gains appetite, no-gos, rabbit holes, approaches, theirs/ours
  and the optional press release + FAQ.
- Eval: checks c7–c13 with a `task` for `eval_run.py --lift` (first message, vague request,
  fidelity, approaches, appetite/no-gos, architecture handoff, problem-solver handoff); c1–c6 unchanged.
- Description unchanged. Version bump: minor, from 2.0.6.
## 2.0.6 — 2026-10-27

- Plan template (sections plan-area fills): `## Review Focus` between §6 and §7; §5 asks for
  signatures and the owner's words verbatim, agent additions as `proposal (agent):`; §7 tasks are
  one action with a checkable result. Owned by plan-area 0.5.0; grill's own sections untouched.
- Version bump: patch, from 2.0.5.

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
