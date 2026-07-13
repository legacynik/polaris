---
name: update
description: Polaris skill — record a short repository-first checkpoint during an active session. Trigger after meaningful progress, a blocker, a context switch, or on "checkpoint / save progress / /update".
user-invocable: true
---

# /update — leave the work legible

Use the same resolver as `/start`: the Polaris root is `_polaris/`, and the contributor is their own
GitHub login (`gh api user --jq .login`) with the matching `team/<login>/profile.yml`. If your
profile is missing, run `/start` first — it provisions your own path. If the root itself is missing,
stop and point to `docs/TEAM-ONBOARDING.md`.

## What a good checkpoint contains

Three facts, no narration: **Done** (verified, not "worked on"), **Next** (one concrete step),
**Blocker** (exact, or none). No transcript, no tool dumps, no essay. If you cannot name a verified
result yet, say "in progress" — do not inflate.

## Step 1 — Append to the session log

Append to `team/<login>/sessions/YYYY-MM-DD-@<github-login>.md` (create it if today's file does not
exist):

```md
## HH:MM — checkpoint
- Done: <verified progress, with proof if any>
- Next: <one concrete next step>
- Blocker: <none, or exact blocker>
```

Keep the whole entry **≤10 lines**. This session log is shared history and is committed with the code.

## Step 2 — Tick the plan cell (only if state changed)

If the current weekly-plan item (`team/<login>/weeks/$(date +%G-W%V).md`) changed state, update only
its `Status`, `Proof` or `Blocker` cell. Do not rewrite the plan and do not create a new plan.

## Step 3 — Keep `state/current.md` tiny

**Overwrite** (never append to) `<root>/state/current.md` with this compact pointer. It is
gitignored; the session log and weekly plan remain the shared source of truth.

```md
# Current work
Updated: YYYY-MM-DD HH:MM
Owner: @login
Outcome: <one sentence>
Status: <one verified fact>
Blocker: <none or one fact>
Next: <one concrete step>
```

Do not put a diary, transcript, raw tool output or more than one active work item in this file. If
`state/current.md` already holds a different owner, you may be on another panel's checkout — confirm
before overwriting.

## Boundaries

- Do not write a founder vault, global memo, private workspace or automatic lesson.
- Do not create or assign issues, branches, pull requests or deployments.
- Do not claim completion without a linked proof.

Finish by showing the session checkpoint and the one-line `Next` from `state/current.md`.
