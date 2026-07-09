# Team Workflow — Standard

> Portable standard. Valid in every repo. Each repo adds only a thin technical
> appendix (commands, URLs, test user, stack, deploy) in its own
> `docs/TEAM-WORKFLOW.md`, which points here. The rules are written once.
>
> **Force is graded with RFC 2119 keywords** — **MUST** (hard gate), **SHOULD**
> (strong default, deviate only with a reason), **MAY** (optional). The core rules
> below are all **MUST**.

---

## The mantra (big changes)

For a serious change (large feature, refactor, structural bug) you **MUST** follow
the flow below; small changes **MAY** skip the heavy steps — the depth and timing of
testing scale with the type of work.

**Before touching code:**
1. **Brainstorm** — explore the problem and the options before deciding.
2. **Analyze** — understand what you are actually solving, and why.
3. **Code-graph** — read the existing code (cgc / codebase-memory) before writing new code.
4. **Pros/cons** — weigh the options; don't take the first one.
5. **Documentation** — read the official docs for any SDK/API/integration you touch.
6. **How others solved it** — frameworks + open-source repos, especially on the big problems.
7. **Spec** — only *after* all the analysis above. The spec is the output of understanding, not the starting point.
8. **Writing-plans** — break it into executable subtasks.

**Implementation:**
9. **Super-strict TDD** — RED test first, then GREEN. No code without a test that failed first.
10. **360° tests** — reason repeatedly about how to push tests beyond the standard conventions: edge cases, real inputs, failure classes, not just the happy path.

**Review:**
11. **Code review.**
12. **Fresh-eyes review** — a sub-agent with clean context, or a different model (Codex / Gemini CLI). The author and the first reviewer miss the same things.
13. **Real test.**

**Ship:**
14. **PR** — `Fixes #N`, atomic.
15. **Real test on staging** — real staging, not just unit tests.
16. **Stress the tests** — try to break them, adversarially. If they hold, go.
17. **If the gate passes → merge + deploy to production.**

---

## Conduct — how we work

- **Ship fast, test for real, log the decisions.** All three, not a choice.
- **Fixes MUST hold.** Fix the mechanism underneath, not the single case. If the same bug / file / topic comes back, it wasn't closed — it was patched.
- **Close it for good.** Close something only when you're 100% sure it should close — but then actually close it. "Task checked off" is not "done": done = verified in production.
- **Parallelize only while waiting, with a cap.** Open other fronts when one is in test/staging (there you're waiting, so it's right to do other work). Cap: 3-4 things in test/staging, max 3 in active fixing. Never parallelize while you're still writing a fix — finish it. Beyond the cap you lose pieces along the way.
- **End-to-end ownership.** Whoever takes a thing carries it to verified production. No "assigned to the team."
- **Evidence over assumption.** "It works" = a verifiable artifact (log, screenshot, comment), not "trust me."
- **Trust from track record, not seniority.** Everyone follows the same flow.
- **Being blocked is not an excuse.** If something is stuck (on someone else, or a service that's down), there's always other work to push forward.
- **Bring the solution, not the problem.** When you're blocked on a decision: propose your solution + what you need from me, in one line.

---

## Core rules (non-negotiable)

1. **No direct commits to `main`** — everything via branch + PR, docs included.
2. **1 issue = 1 branch = 1 atomic PR.** Phased execution = 1 branch per phase.
3. **Max 3 personal branches ahead of main** per contributor. Before opening the 2nd/3rd, zero file overlap with the active ones. **Parallel branches → one git worktree each** (`superpowers:using-git-worktrees`) — never share a single working tree across parallel branches: that's where branch-drag and clobbering come from.
4. **Short-lived branches: merge to main right after the real-test gate.** This keeps everyone's conflicts small and fast to resolve. PR merged + branch deleted within 24h.
5. **Docs-first** — read the official docs before touching an SDK/API.
6. **Real test before "shipped"** — staging, not just unit tests.
7. **Blocker = issue** immediately (not in a doc, not verbally).
8. **Architectural decision = logged in real time** in the decision log, when you make it.

---

## Status & Linear linking

Status lives in **Linear** (Triage → In Progress → In Review → Done, plus an
**On hold** status for blocked work). GitHub has only open/closed, so "in progress"
and "on hold" are Linear's — GitHub mirrors nothing for them.

For status to move **automatically**, the PR must be linked to the Linear issue.
GitHub has no "in progress" for the sync to mirror, so Linear must set it. To link
without dropping the GitHub-number branch convention:

- branch name stays `<type>/<gh-issue#>-<slug>`;
- the **PR body references the Linear id**: `NOE-<n>` (take it from the issue's
  Linear linkback comment) alongside `Fixes #<gh#>`;
- Linear's "link commits/PRs with magic words" is enabled.

Result: **PR opened → Linear moves the issue to In Progress** and posts a linkback
on GitHub; **PR merged → Done**. "On hold" is set by hand when work is blocked.

## Definition of Done

A thing is *done* when, in the PR's final comment:
- real test on staging done, with a verifiable artifact;
- production deploy + smoke OK;
- if it was a bug: error log marked resolved with the PR link;
- the issue is closed and **does not come back**.
