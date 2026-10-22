---
name: issue-contract
description: ◇ Create or update GitHub issues with a clear definition of done and regression checks. Use when asked to open an issue, track a bug, or hand work to another lane.
version: 2.3.0
user-invocable: true
auto: true
job: record the requested work in the tracker without starting implementation
when_not: implementation, code review, or speculative roadmap decomposition
lifecycle: GitHub issue or update; no duplicate local brief
invokes: [bugfix, git-power, ambitious-goal]
invoked-by: [start, cron-sweep, crasher, human]
io: request and existing evidence -> issue URL carrying its AFK label, with branch link when supplied
status: active
---

# Issue Contract

Make the ticket useful and easy to read. The required content is a short description, a
definition of done, what to test to avoid regressions, and who may pick the work up. Write in
the language the repository's existing issues use unless the user asks for another. Technical
names and commands belong only where they help someone execute or verify the work.

## Default flow

`invokes` lists available routes, not mandatory steps; use the conditions below.

1. **Search once for duplicates.** `gh issue list --state all --search "<key words>"`. Reuse a
   clearly matching issue; otherwise create one. Inspect code only to resolve a concrete
   uncertainty, through the code graph or LSP if available. Done when you hold either the twin's
   number or the search that found none.
2. **Refine a feature only when needed.** For a feature or feature epic whose outcome, scope or
   DoD is unclear, use `ambitious-goal`: pass the evidence and constraints, take back the
   contract, publish it here. Bugs and mechanical tickets skip this step; no mandatory interview.
3. **Decide who may pick it up, before writing.** The work is for a **person** when any holds:
   the request says to leave it to a person, keep it, not hand it to an agent, or not auto-claim
   it; it needs an access, credential or authority an agent does not hold; it waits on a
   product, business, legal or owner decision; the repository's own policy reserves that kind of
   work. Otherwise follow the repository's AFK policy. Then let the script name the label:

   ```bash
   gh label list --json name --limit 500 > /tmp/labels.json
   python3 scripts/afk_label.py pick --human yes --labels /tmp/labels.json   # or --human no
   ```

   It reads `tracker.afk_human` / `tracker.afk_agent` from the product repository's
   `_polaris/config.yml` when present, else the repository's own labels (`afk:human`,
   `ready-for-human`, `needs-human` for a person; `afk:eligible`, `ready-for-agent`,
   `agent-ready` for an agent). Exit 2 means work for a person has no label to carry it: tell the
   user which label to create or configure, and do not file the issue without it. Done when you
   hold the label name (empty only for agent work in a repository with no AFK labels).
4. **Write the short ticket below**, then pick routine labels (type, area, priority) from the
   repository's existing labels and its issue templates. Preserve existing assignees and state
   unless asked to change them.
5. **Create or update directly** with the connected GitHub tools or `gh` with a body file and
   `--label <the step-3 label>`. A request to open an issue already authorizes creation: no
   second confirmation or dry-run handoff.

```markdown
<What is wrong or needed, why it matters, and any relevant branch or evidence link.>

## DoD
- <Observable result that makes the work complete.>

## Regression checks
- <The normal behavior to preserve and the failure or edge case to exercise.>
```

Use as many bullets as the actual work needs. Do not invent numeric targets, commands, file
paths, or a test implementation merely to fill a template. Distinguish tests still to run from
evidence already collected. Add reproduction steps only when they help.

## When NOT to use

- Opening an issue does not authorize implementation, assigning it to yourself, or launching
  an agent. A handoff stays with the receiving lane; do not fix it while preparing the ticket.
- Link existing branches, PRs and evidence. Do not create a plan, ADR, local dossier, patch
  archive or review process just to open an issue. Create a branch only when requested.
- No mandatory multi-field contract, score, cost estimate, executive section, dedup essay,
  minimum test count or measurable-signal regex. Honor any genuinely enforced repository
  requirement without turning optional issue-form fields into another interview.
- Do not promote or dispatch work merely because an issue was created.

## Before returning

Read the issue back and check its labels carry the step-3 decision:

```bash
gh issue view <N> --json labels > /tmp/issue.json
python3 scripts/afk_label.py verify --human yes --issue /tmp/issue.json --labels /tmp/labels.json
```

Exit 0 is required: exit 1 names the missing label, or an agent label on work for a person;
fix it with `gh issue edit <N> --add-label/--remove-label` and verify again. Then check the DoD
and regression checks match the request and any supplied branch link is present. Return the
link without replaying the workflow.

## Selfcheck

```bash
python3 scripts/afk_label.py --selfcheck
python3 -m pytest -q tests/test_afk_label.py
```

Bypass cases: `references/bypass-test.md`.
