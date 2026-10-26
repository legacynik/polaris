---
name: issue-contract
description: ◇ Polaris — Create or update GitHub issues with a clear definition of done and regression checks, and route operational work to a Beads bead instead. Use when asked to open an issue, track a bug or finding, promote a bead, or hand work to another lane. Requires bd (Beads), gh and python 3.
version: 2.6.3
user-invocable: true
auto: true
job: record the requested work in the tracker without starting implementation
when_not: implementation, code review, or speculative roadmap decomposition
lifecycle: GitHub issue or update, or a bead; no duplicate local brief, never a GitHub-Beads mirror
invokes: [bugfix, git-power, plan-area]
invoked-by: [cron-sweep, crasher, ship, human]
io: request and existing evidence -> issue URL carrying its AFK label, with branch link when supplied; or a bead id and the one-line reason
status: active
---

# Issue Contract

## What it does

The only door to the tracker. A GitHub issue only when a human must schedule or approve the work,
it falls outside the current PR or phase, it has «Come si prova» and an area, and no open issue
twins it; everything else becomes a Beads bead, with the reason in one line. The ticket is short:
what and why, a DoD, «Come si prova», and who may pick it up, in the language of the
repository's issues. Never a mirror between GitHub and Beads.

## When

- Someone asks to open an issue, track a bug or a finding, or hand work to another lane.
- A bead grew into a delivery and must be promoted (`--bead`).

## Steps

1. **Search once for duplicates:** `gh issue list --state all --search "<key words>"`. Reuse a
   clear twin. *Done when you hold its number or the search that found none.*
2. **Route.** `command -v bd`, else stop: install Beads (`brew install beads`). Then
   `python3 scripts/route.py --human yes|no --in-current-work yes|no --test-section yes|no
   --area <area> --dup <twin|none> --src <who found it> --kind <what it is>` (flags in
   `references/flow.md`). `beads` → run its `next` with a real title, give the reason, return
   the bead id, stop. `github` → continue. Exit 2 names a missing fact.
3. **Refine a feature only when its outcome or DoD is unclear:** it is medium or large work,
   hand it to `plan-area`; the issue links its plan file. Bugs and mechanical tickets skip this.
4. **Who picks it up.** A person when the request says so, or it needs access, a decision or an
   authority an agent lacks. Then `gh label list --json name --limit 500 > /tmp/labels.json` and
   `python3 scripts/afk_label.py pick --human yes|no --labels /tmp/labels.json`; exit 2 = no label to
   carry work for a person: say which to create, file nothing.
5. **Write and file** the ticket below with `gh issue create --body-file … --label <step-4
   label>` plus routine labels from the repository's own; preserve assignees and state. With
   `--bead`, run route's `next` with the issue number. No second confirmation.
6. **Read back:** `gh issue view <N> --json labels > /tmp/issue.json` and
   `python3 scripts/afk_label.py verify --human yes|no --issue /tmp/issue.json --labels /tmp/labels.json`
   must exit 0; fix the labels and verify again.

```markdown
<What is wrong or needed, why it matters, branch or evidence link.>

## DoD
- <Observable result that makes the work complete.>

## Come si prova
- <How to see it done, the behaviour to preserve, the failure or edge case to exercise.>
```
«Come si prova» says what a user or caller observes, never "file X contains", "function is named Y",
"config says Z" or a real wait (lower the limit), even if asked (`tdd-dev` → *How tests are written*).

## Output

The issue URL carrying its AFK label (and the branch link when supplied), or a bead id plus the
one-line reason. Selfcheck: `python3 scripts/route.py --selfcheck && python3 scripts/afk_label.py --selfcheck`.
**Next:** STOP — filing authorizes nothing; offer the options: start now (`bugfix` · `plan-area` · `tdd-dev`) or later.

## Not for

- Implementation, self-assignment or launching an agent: opening an issue authorizes none.
- Plans, ADRs, dossiers or review processes created just to open an issue.
- Invented numbers, commands or paths to fill the template. Limits in full: `references/flow.md`.
