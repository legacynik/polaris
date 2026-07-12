---
name: start
description: Polaris skill — begin a repository-first team session. Read the contributor's plan, active ownership, decisions and relevant memory before proposing work. Use at the beginning of a session or after a pause.
user-invocable: true
---

# /start — orient before acting

This command is read-only. Its job is to make the next choice visible, not to create a workspace,
issue, branch, pull request or assignment.

## Resolve the repository contract

From the repository root, use **one** Polaris root:

1. `polaris/` if `polaris/config.yml` exists;
2. otherwise `_polaris/` if `_polaris/config.yml` exists;
3. otherwise stop and say that the repository has no committed Team OS contract. Do not run a
   bootstrap command and do not create personal state.

Then identify the contributor from the matching `team/<github-login>/profile.yml`. Prefer the
GitHub login configured for the current checkout; if it is not unambiguous, show the available
profiles and ask the contributor which one is theirs.

## Read in this order

1. `team/<login>/profile.yml` — capacity and working agreement.
2. The current ISO-week file in `team/<login>/weeks/` — outcomes, branch, proof and blockers.
3. Other current week files — only titles, owners and active branches, to avoid collisions.
4. `decisions.md`, then `<root>/state/current.md` if it exists. `current.md` is only a compact,
   gitignored pointer: if it conflicts with the approved plan or evidence, treat it as stale.
5. The most recent relevant session log.
6. If `polmem` is available, run a small recall for the issue/domain named in the active plan.
   If it is unavailable, say so once and continue; do not invent a fallback memory store.

## Briefing

Return at most seven lines:

```text
<repo> — <date>
Your outcome this week: <one sentence>
Active item: <issue / branch / status>
Proof needed: <one sentence>
Collision or blocker: <one sentence, or none>
Relevant decision: <one sentence, or none>
What do you want to move forward first?
```

If there is no signed plan, say that plainly. Planning happens in `/plan-week`; implementation
still needs an explicit user request.

Do not overwrite `state/current.md` from `/start`; `/update` and `/end` keep it short.
