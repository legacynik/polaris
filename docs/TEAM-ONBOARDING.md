# Polaris Team OS — onboarding

This document is the only operating manual a new collaborator needs alongside the product
repository.

## Contributor: first ten minutes

1. Clone the one product repository you own for this period and open it in Claude Code.
2. Install **Polaris Team OS**:

   ```text
   /plugin marketplace add legacynik/polaris
   /plugin install polaris-team-os@polaris-team-os
   ```

3. Confirm the repository contains `_polaris/config.yml` and your
   `_polaris/team/<github-login>/profile.yml`. If either is missing, stop and ask the repo owner;
   do **not** run `/pol-bootstrap` and do not create a personal workspace.
4. Run `/start`. Read the decisions, your active week, other active ownership and the recall
   receipt before proposing work.
5. Work on one planned item. Record meaningful progress with `/update`, and close with `/end`.
6. Before a branch, PR, migration, dependency or architecture decision: use `polmem recall` for
   the issue/domain and check the active team plan. The coming branch gate automates this check.

### Daily rules

- GitHub/Linear is live issue state; do not reproduce it manually as a dashboard.
- Your weekly plan is coordination state. Keep status, branch, proof and blockers current.
- `state/current.md` is local panel state and stays ignored. Sessions, plans, reports and decisions
  are shared Git records.
- Never record tokens, credentials or secrets in Polaris files.
- Do not claim an item already active for another contributor. Escalate the conflict instead.

## Repository owner: one-time setup

Commit the templates in [`templates/repo-contract`](../polaris/templates/repo-contract/) into the
product repo, replacing the example contributors with real GitHub logins.

```text
_polaris/
  config.yml
  team/<login>/profile.yml
  team/<login>/weeks/
  team/<login>/reports/
  sessions/
  decisions.md
  lessons.md
  state/.gitignore
```

The owner also commits the repository's existing memory bundle (`.wiki/`, `.mcp.json` and
`scripts/polaris_memory_repo.py`) if memory recall is part of the repository standard. Do not put
that bundle in the plugin and do not configure `POLARIS_VAULT` for teammates.

## Weekly operating loop

The target workflow is deliberately small:

1. At the start of the week, each contributor receives/claims a capacity-bounded set of issues.
2. One Markdown plan per contributor links each issue to owner, branch, status, proof, blocker and
   dependency. It is committed in the product repo.
3. Work closes by updating the matching plan item and session log.
4. A weekly report compares the plan to git/tracker reality. It does not rewrite decisions.

The current release has `/pol-report`; the planned `/plan-week` and unified `/report` are tracked
in the public implementation package. Until that release, use the included Markdown shapes
directly rather than inventing another workspace or workflow.

## Naming and migration

The marketplace/plugin identifier is now **`polaris-team-os`**. Existing installations named
`polaris` can stay installed while a maintainer validates the new release, then move to the command
above. Do not run both lifecycle command sets in the same session.

Legacy `/pol-bootstrap` exists only for old repositories and is not the onboarding path. Duplicate
global skills are retired after the replacement commands pass the published acceptance tests.
