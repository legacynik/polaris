---
title: implement-plan — rulings instead of stalls
status: active
---

# Rulings

**Goal.** A running build does not wait on a human for what judgment can settle. A wrong ruling
costs rework the founder can see and undo; a build parked on a question costs the day and buys
nothing.

**Criterion.** The spec (or the area README) binds; the plan is its argument; the code is the
fact. Where they disagree, pick what the authority implies and the code can bear. Where none of
them answers, pick the reversible option that keeps the plan's DoD reachable.

**Record.** `bd note <bead> "Ruling: <what> — <why> — <cost if wrong>"`, on the task bead for a
task's question, on the epic for a preflight or cross-task one. The note is the ledger: the next
agent, a resumed run and the PR reviewer read it there.

**Stops (only these).** Destructive or irreversible (drop, delete, force-push, data migration
without a way back); security-sensitive (credentials, permissions, auth); a side effect outside
the worktree that norms ask about (merge, push to a shared branch, publish, a shared database or
service); a plan so broken every path is a guess. Plus two evidence stops already in the skill:
`fix_budget.py` exit 1 and any `G` refusal. They are measurements, not ambiguity: a ruling cannot
overrule them.

**Traps.**
- Ruling to skip a test, the RED or a gate "because the plan is unclear": that is a stop, not a ruling.
- A ruling that rewrites the plan's outcome or DoD is a course change: `plan-area` owns it.
- A ruling without its cost line is a guess nobody can audit later.
- "Should I continue?" between tasks is a stall dressed as courtesy.
