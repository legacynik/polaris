---
name: update
description: Polaris skill — record a short repository-first checkpoint during an active session. Use after meaningful progress, a blocker or a context switch.
user-invocable: true
---

# /update — leave the work legible

Use the same single-root resolver as `/start`: `polaris/` or `_polaris/`, never both. If the
repository contract or contributor profile is missing, stop and explain what is missing.

## Write only shared coordination facts

Append a short entry to `sessions/YYYY-MM-DD-@<github-login>.md`:

```md
## HH:MM — checkpoint
- Done: <verified progress>
- Next: <one concrete next step>
- Blocker: <none, or exact blocker>
```

If the current weekly-plan item changed state, update only its `Status`, `Proof` or
`Blocker / dependency` cell. Do not rewrite the plan and do not create a new plan.

## Keep `current.md` tiny

Overwrite (never append to) `<root>/state/current.md` with this compact pointer. It is gitignored;
the session log and weekly plan remain the shared history and source of truth.

```md
# Current work
Updated: YYYY-MM-DD HH:MM
Owner: @login
Outcome: <one sentence>
Status: <one verified fact>
Blocker: <none or one fact>
Next: <one concrete step>
```

Do not put a diary, transcript, raw tool output or more than one active work item in this file.

## Boundaries

- Do not write a founder vault, global memo, private workspace or automatic lesson.
- Do not create or assign issues, branches, pull requests or deployments.
- Do not claim completion without a linked proof.

Show the session checkpoint and the one-line `Next` from `current.md` when finished.
