# issue-contract — the flow in full

Read by `issue-contract` while it runs. `SKILL.md` carries the short form of each step; this
file keeps every rule, command and the ticket template.

Make the ticket useful and easy to read. The required content is a short description, a
definition of done, what to test to avoid regressions, and who may pick the work up. Write in
the language the repository's existing issues use unless the user asks for another. Technical
names and commands belong only where they help someone execute or verify the work.

## Flow in full

`invokes` lists available routes, not mandatory steps; use the conditions below.

1. **Search once for duplicates.** `gh issue list --state all --search "<key words>"`. Reuse a
   clearly matching issue; otherwise route it (step 2). Inspect code only to resolve a concrete
   uncertainty, through the code graph or LSP if available. Done when you hold either the twin's
   number or the search that found none.
2. **Route: GitHub issue or bead.** `command -v bd` first; when absent, stop and tell the user
   to install Beads (`brew install beads`, github.com/gastownhall/beads). Then give the facts:

   ```bash
   python3 scripts/route.py --human yes|no --in-current-work yes|no --test-section yes|no \
     --area <area or ''> --dup <open twin or none> --src <who found it> --kind <what it is> \
     [--type bug] [--from <bead it came from>] [--bead <bead to promote>]
   ```

   `--human yes`: a human must schedule or approve it (not who picks it up: step 4).
   `--test-section yes`: you can write its «Come si prova» now. Exit 2 names a missing fact.
   `beads`: run its `next` command with a real title, tell the user the `reason` in one line,
   return the bead id; stop here. `github`: continue; with `--bead`, after step 6 run its `next`
   with the issue number. Never mirror: a filed issue gets no new bead, a bead no new issue.
3. **Refine a feature only when needed.** For a feature or feature epic whose outcome, scope or
   DoD is unclear, hand it to `plan-area`, whose plan file holds the
   outcome and DoD; the issue links that file. Bugs and mechanical tickets skip this step; no mandatory interview.
4. **Decide who may pick it up, before writing.** The work is for a **person** when any holds:
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
5. **Write the short ticket below**, then pick routine labels (type, area, priority) from the
   repository's existing labels and its issue templates. Preserve existing assignees and state
   unless asked to change them.
6. **Create or update directly** with the connected GitHub tools or `gh` with a body file and
   `--label <the step-4 label>`. A request to open an issue already authorizes creation: no
   second confirmation or dry-run handoff.

```markdown
<What is wrong or needed, why it matters, and any relevant branch or evidence link.>

## DoD
- <Observable result that makes the work complete.>

## Come si prova
- <How to see it done, the normal behavior to preserve and the failure or edge case to exercise.>
```

«Come si prova» describes behaviour a user or caller can observe — the output, the side effect,
the exit code, what the screen shows — never "the file contains X", "the function is named Y",
"the config says Z" or anything that depends on real timing; when the request dictates such a
check, write the behaviour it stands for (a timeout: the run stops with an error once the
configured limit passes, the limit lowered for the test). A name the user does type — a CLI flag,
a URL — is proved by using it, not by finding it in the source. Same rule as `tdd-dev` →
*How tests are written*.

Use as many bullets as the actual work needs. Do not invent numeric targets, commands, file
paths, or a test implementation merely to fill a template. Distinguish tests still to run from
evidence already collected. Add reproduction steps only when they help.

## Before returning

Read the issue back and check its labels carry the step-4 decision:

```bash
gh issue view <N> --json labels > /tmp/issue.json
python3 scripts/afk_label.py verify --human yes --issue /tmp/issue.json --labels /tmp/labels.json
```

Exit 0 is required: exit 1 names the missing label, or an agent label on work for a person;
fix it with `gh issue edit <N> --add-label/--remove-label` and verify again. Then check the DoD
and «Come si prova» match the request and any supplied branch link is present. Return the
link without replaying the workflow.

## Limits in full

- Opening an issue does not authorize implementation, assigning it to yourself, or launching
  an agent. A handoff stays with the receiving lane; do not fix it while preparing the ticket.
- Link existing branches, PRs and evidence. Do not create a plan, ADR, local dossier, patch
  archive or review process just to open an issue. Create a branch only when requested.
- No mandatory multi-field contract, score, cost estimate, executive section, dedup essay,
  minimum test count or measurable-signal regex. Honor any genuinely enforced repository
  requirement without turning optional issue-form fields into another interview.
- Do not promote or dispatch work merely because an issue was created.


## Selfcheck

```bash
python3 scripts/afk_label.py --selfcheck && python3 scripts/route.py --selfcheck
python3 -m pytest -q tests/test_afk_label.py tests/test_route.py
```

Bypass cases: `references/bypass-test.md`.
