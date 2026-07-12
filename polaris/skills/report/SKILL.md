---
name: report
description: Polaris skill — produce a concise weekly repository report that compares the approved plan with actual delivery evidence. Use before a team review or at the end of a week.
user-invocable: true
---

# /report — planned versus actual

Use the same repository-root and contributor resolver as `/start`. Read the current weekly plan,
the contributor's session logs, relevant GitHub/Linear state and `git log` for the week.

## Write

Create or update `team/<login>/reports/YYYY-Www.md` from the repository template. Keep it under
one screen and answer:

1. What outcome was planned?
2. What was actually shipped or verified? Link the PR, issue, deployment or test evidence.
3. What did not happen, and why?
4. What was learned about scope, quality or collaboration?
5. What is the single best next-week starting point?

Use **planned versus actual**; do not turn commits, tokens or activity volume into success. A
blocked item is useful information when its blocker and next decision are explicit.

## Boundaries

- Do not overwrite an earlier report; append a dated update if new evidence arrives.
- Do not create tracker issues, assignments, branches, pull requests or deployments.
- Do not write to a founder workspace or infer performance judgments not supported by evidence.

