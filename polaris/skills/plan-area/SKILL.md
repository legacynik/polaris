---
name: plan-area
description: "◇ Polaris — Write ONE plan file per piece of medium or large work (area first, outcome, DoD, contracts, every claim assumed or proven), pour its phases into a Beads epic gated by feature_gate.py, record course changes, and close it after merge. Use when an idea is scoped and needs a plan, the plan must become phases, evidence contradicts it, or ship merged it. Requires bd (Beads), git, gh."
version: 0.4.0
user-invocable: true
status: active
lifecycle: "docs/<areas|modules>/<area>/plans/open/<date>-<name>.md + a poured Beads epic → plan close: canonical doc absorbs, file to done/, epic burned"
invokes: []
invoked-by: [issue-contract, grill, ship, implement-plan, human]
io: "scoped idea + code + open issues → one plan file (exec summary, diagram, status) and a Beads epic whose steps close only through feature_gate.py"
---

# plan

## What it does

Turns scoped work into one stable plan file — spec and plan in one document (operating model §5)
— then pours its phases into a Beads epic whose steps close only through `feature_gate.py`, and
at the end closes it. Outcome/DoD sharpening (ex ambitious-goal) and code-reading with issue
dedupe (gstack /spec) are part of writing it.

## When

- Medium or large work (model §2) is scoped and has no plan file yet; tiny work is a bead.
- The founder set `status: accepted`: pour the phases (break down).
- Evidence contradicts the plan: a Trajectory change, before any code changes.
- `ship` merged the PR, or the work is abandoned: `plan close`.

## Steps

1. **Dependencies.** `command -v bd gh git`; bd missing → stop: `brew install beads`
   (github.com/gastownhall/beads). No markdown-checklist fallback.
2. **Area first.** Resolve it from `config.yml` `outputs.plan` and the area map (`README.md` of
   `docs/<areas|modules>/`); unknown → ask once. The file goes in `<area>/plans/open/`. One open
   plan per area: if one exists, the new idea is a bead (`bd create … -l kind:idea,area:<area>`).
3. **Read before writing.** Read the code the work touches (code graph or symbol search first) and search
   duplicates: `gh issue list --state all --search "<words>"`. Ask the agent memory
   (`ai-memory-retrieval`) for prior attempts, if installed. Cite what you read.
4. **Write the file** from `references/plan-file.md`: an executive summary on top (`## Executive`,
   a few lines for a person: outcome, decision, risk, which sections to read), sections 1–9, a
   diagram of the phases, `status: discovery|proposed`. Every claim in 3–7 is `assumed` or `proven: <pointer>`.
   The outcome is falsifiable; each DoD line pairs a result with the evidence that could refute it.
   `python3 scripts/check_plan_files.py --root . --gate` (where the repo has it) must pass.
5. **Critic, then the founder.** `critic` attacks the plan once; fix blocking findings; the founder
   sets `accepted`. Decisions to enact get a DEC file (architecture), named in Links.
6. **Pour.** `python3 scripts/feature_gate.py pour --record <plan> --repo .` — epic + one bead per
   `### Phase N` (tasks as children), status → `in-progress`, epic id in Links. Then close the
   `plan` and `critic` steps: `feature_gate.py close --step <id> --record <plan> --repo . [--report]`.
7. **Course change.** Append to section 9: date · what proved wrong · evidence · what changes —
   before the code changes. A changed decision is superseded, never edited.
8. **Close** (called by `ship` after merge): absorb the proven content into the area's canonical
   doc (`<area>/<area>.md`, naming the plan), then
   `python3 scripts/plan_close.py --record <plan> --repo . --merged --pr <N>`; abandoned work:
   `--abandoned "<reason>"`. Rules for bd: `references/beads.md`.

## Output

The plan file path and its status; after pour, the epic id and its `bd ready --mol <epic>`; after
close, the `done/` (or `archive/`) path and the DECs promoted to `executed`.
**Next:** written → `critic` on the plan, then ask the founder with options (accept · change · pause);
poured → `implement-plan`; closed → STOP.

## Where this goes

This skill produces: **plan, idea, tasks** — the plan file at `outputs.plan`, ideas and phases in Beads.

## Not for

- Tiny work or a bug with a reproduction: a bead → `tdd-dev`, or `bugfix`.
- Executing phases: `implement-plan`. Judging a diff: `review`.
- Deciding one architecture commitment: `architecture`. Clarifying a vague idea: `grill`.
