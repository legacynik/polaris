---
name: plan-week
description: Polaris skill — prepare a capacity-bounded weekly plan for one contributor from the live tracker and current team ownership. Use at the beginning of a week or when a CEO asks for a proposal.
user-invocable: true
---

# /plan-week — propose one week of useful work

This command produces a **proposal**, not an assignment. It does not create issues, branches,
pull requests or assignments.

## Inputs

Resolve the one repository root and contributor profile as `/start` does. Read:

1. `team/<login>/profile.yml` for weekly hours, strengths and working agreement;
2. the previous weekly report and current plan, if present;
3. live GitHub or Linear issues/PRs for this repository;
4. other contributors' active week files, to exclude collisions;
5. relevant decisions and a targeted `polmem recall` when available.

State the evidence date and distinguish verified facts from assumptions.

## Output

Draft `team/<login>/weeks/YYYY-Www.md` from the repository template. It must contain:

- one outcome that matters to the product or customer;
- only capacity-fitting secondary work;
- an explicit proof of done for every item;
- what is deliberately **not** being started;
- dependencies and ownership collisions;
- a short `CEO signature` block when the plan was requested as a leadership proposal.

Write natural language for the person: explain why the sequence helps the product and what skill or
ownership muscle it develops. Do not turn the plan into a ticket dump.

## Approval boundary

When the user asked for analysis or a CEO proposal, mark:

```yaml
status: proposed
ceo_signature: pending
execution_authorized: false
```

Only a direct approval can change that boundary. After approval, the contributor may choose a
branch and update the plan; this command still does not perform tracker mutations.

