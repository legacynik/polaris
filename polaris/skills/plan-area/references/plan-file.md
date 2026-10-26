# The plan file

One file per piece of work at `docs/<areas|modules>/<area>/plans/open/<YYYY-MM-DD>-<name>.md`
(operating model §5). Spec and plan in one document: the stable contract lives here, the moving
state (phases, tasks, findings) lives in Beads. `feature_gate.py` parses the frontmatter, the
`## 6. DoD` bullets, the `### Phase N: title` headings under `## 7. Approach` and the
`Beads epic:` line under `## 8. Links` — keep those shapes.

The skeleton is one file for the whole life of the plan: `../../grill/references/plan-file.md`.
`grill` writes sections 1–3 from it at `status: discovery`; this skill fills the rest — the
`tests:` frontmatter key, the `## 6.` DoD bullets, the `### Phase N:` headings with their `- task`
bullets under `## 7. Approach`, and the Links lines (`pour` writes `- Beads epic: <id>`). A plan
that starts here without a grill run copies the same skeleton.

## Rules

- **Tags.** Every claim in sections 3–7 is `assumed` or `proven: <test | receipt | verdict | PR | path>`.
  `check_plan_files.py` refuses a `proven:` path that does not exist.
- **Outcome and DoD** (ex ambitious-goal). Name who benefits and what becomes possible; go one level
  above the request when that clarifies it. Ask one question at a time, only when the answer changes
  outcome, scope or acceptance. Separate required acceptance from stretch; never invent baselines,
  dates or thresholds — without a credible number, an observable condition plus what to measure.
  A DoD of "code written" or "document produced" is not a DoD. Name the environment that counts as
  done (candidate, integrated, released).
- **Read before writing** (gstack /spec). The Discovery section cites the code read and the issue
  search; a plan that cites neither is written from memory.
- **Phases.** Each phase has an observable result and can close on its own checks (model §10). A
  phase that only exists to "set up" is folded into the next.
- **Status moves.** `paused` → the file moves to `archive/paused/` and a bead `kind:idea` keeps the way
  back; `abandoned` → `plan_close.py --abandoned` (archive/ + digest); `done` → only `plan_close.py`.
