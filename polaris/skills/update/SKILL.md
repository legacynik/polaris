---
name: update
description: Polaris skill — record a short repository-first checkpoint during an active session. Trigger after meaningful progress, a blocker, a context switch, or on "checkpoint / save progress / /update".
user-invocable: true
---

# /update — leave the work legible

Use the same resolver as `/start` (including the root-is-`_polaris` vault case): the Polaris root is `_polaris/`, and the contributor is their own
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

## Step 3 — Reconcile `state/current.md` (the open-items ledger)

`current.md` is the repo's live ledger of what is genuinely open — checkpoint line on top, open
items below. **Reconcile it, never blind-overwrite and never append**: read the existing file
first, then apply state changes. Two invariants, in priority order:

1. **Nothing open is ever lost.** An item leaves the file ONLY when (a) you closed it and can name
   the evidence (PR/commit/test — cite it in the session log), or (b) it is promoted to an
   issue/plan — promotion replaces the item's detail with one pointer line (`→ #123`), it never
   deletes silently. Items owned by other sessions/panels stay untouched.
2. **Only open truth lives here.** No narrative of shipped work (→ session log), no decisions
   taken (→ decisions.md), no history. Size is an OUTPUT of that discipline, never a constraint:
   10 genuinely open items = 10 items in the file; each may carry 1–3 lines of context (an item
   stripped of its why/where is half-lost). Never trim an open item to make the file smaller.

```md
# Current — open items
Updated: YYYY-MM-DD HH:MM by @login — <checkpoint: one line on what this session moved>

## Open
- [@login] <item> — <1–3 lines of context: where it stands, what unblocks it> · since YYYY-MM-DD
- [@other] <untouched item from another session — not yours to remove>

## Next
- <one concrete first step>
```

An item idle >14 days gets flagged `stale?` — it stays until a human closes or promotes it, never
auto-dropped. It is gitignored; the session log and weekly plan remain the shared source of truth.
If the file holds another owner's fresher checkpoint line, you may be on another panel's checkout —
confirm before touching it.

## Boundaries

- Do not write a founder vault, global memo, private workspace or automatic lesson.
- Do not create or assign issues, branches, pull requests or deployments.
- Do not claim completion without a linked proof.

Finish by showing the session checkpoint and the `Next` line from `state/current.md`.
