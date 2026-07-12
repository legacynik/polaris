# Polaris Team OS

**Polaris Team OS** is the shared, repository-first working method for a product team. It provides
the session lifecycle (`/start` · `/update` · `/end`), repository memory through `polmem`, and a
small committed record of ownership, weekly goals, reports and decisions.

It is **not** a personal vault and it does not require a founder-specific workspace. Product
repositories own their own working context; the plugin is installed once per machine.

## Team onboarding — give this repository to a collaborator

1. Clone the product repository they will work on.
2. Ensure it has the committed team contract described in
   [`docs/TEAM-ONBOARDING.md`](docs/TEAM-ONBOARDING.md). The repository owner does this once;
   contributors never bootstrap a private Polaris environment.
3. In Claude Code, install this marketplace and plugin:

   ```text
   /plugin marketplace add legacynik/polaris
   /plugin install polaris-team-os@polaris-team-os
   ```

4. Open Claude Code from the product repository and run `/start`.
5. Use `/update` for a real handoff and `/end` when closing a session. Use `polmem recall` before
   a consequential decision and `polmem remember` to record a candidate lesson.

The complete contributor and repo-owner checklist is in
[`docs/TEAM-ONBOARDING.md`](docs/TEAM-ONBOARDING.md). It is self-contained: share this repository
and the product repo; no internal vault path is required.

## Current commands

| Command | What it does today |
|---|---|
| `/start` | Reads repository-local session state and available repo memory. |
| `/update` | Saves a concise mid-session handoff. |
| `/end` | Closes the local session, surfaces repo decisions and offers a commit. |
| `/pol-report` | Produces a weekly repository report from sessions, decisions and git history. |
| `polmem recall` / `remember` / `health` | Queries or records against the product repo's committed memory bundle. |

`/pol-bootstrap` is retained only for existing legacy repositories. **Do not use it for team
onboarding.** New product repos adopt the tracked contract explicitly, via the templates and
checklist below.

## Repository-first model

The plugin is global; the information colleagues need is committed in the product repository:

```text
_polaris/
  config.yml
  team/<github-login>/{profile.yml,weeks/,reports/}
  sessions/YYYY-MM-DD-@<github-login>.md
  decisions.md
  lessons.md
  state/current.md                 # local-only, ignored
```

GitHub/Linear remain the live tracker. Markdown coordinates people: the current plan, ownership,
proof and blockers. A founder portfolio view is an optional reader of committed product reports;
it never becomes a second session writer.

## `polmem`

`polaris/bin/polmem` is a thin, stdlib-only CLI for the current product repository's memory bundle
at `scripts/polaris_memory_repo.py`; it does not carry or duplicate memory itself.

```bash
python3 path/to/polaris/bin/polmem recall "pricing calibration" --top 5
python3 path/to/polaris/bin/polmem remember "decided to cap retries at 3"
python3 path/to/polaris/bin/polmem health
```

If the repo is not memory-wired, the command reports that plainly and exits non-zero. It never
creates a home-directory vault.

## Migration and roadmap

The full team contract, migration map and acceptance tests live in the public Polaris OS repository:

- [`Polaris Team OS design`](https://github.com/legacynik/polaris-os/blob/main/docs/superpowers/specs/2026-07-12-polaris-team-os-design.md)
- [`Implementation package`](https://github.com/legacynik/polaris-os/blob/main/docs/superpowers/plans/2026-07-12-polaris-team-os-package.md)

The next implementation release consolidates duplicate lifecycle/report skills into `/end`,
`/plan-week` and `/report`; it does not add a second workspace or dashboard.
