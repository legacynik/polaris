---
title: implement-plan — the preflight conflict scan
status: active
---

# Preflight

**Goal.** Find the contradictions before an agent finds them mid-task, when they are cheap.

**Read** the plan's phases and §5 Contracts / §6 DoD, the spec or area README it argues from,
and the code its tasks touch. A plan with no reachable spec: note it on the epic, and every
ruling is provisional.

**Look for** what one task produces against what another consumes (a file, an interface, a
name); a task's tests against the code it specifies; the plan against the spec and against the
code as it is today (renamed, deleted, already done).

**Then** rule on each conflict (`rulings.md`) on the epic before the first dispatch. A clean scan
needs no ceremony; a "clean" you did not check is not one.

**Traps.** Trusting the plan's own description of the code; treating a task that is already done
in code as something to rebuild; re-litigating choices the plan argued for when nothing contradicts them.
