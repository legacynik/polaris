---
title: real-testing — per-phase local, production check, logged-in browser profiles
description: The two modes beside merge mode, the `real_test:` settings they read, and the rule that agents never type a password.
status: active
---

# Modes beside merge

Merge mode (`merge.md`) is the gate before a merge. The two modes below reuse its method (serve,
walk as the customer, fresh breaker, evidence) at other moments. Their cost by plan size is the
operating model's §10: per-phase local on the phases that change behaviour (medium work), on
every phase (large work), never on tiny work.

## Per-phase local

- **Serve** the phase's commit on this machine with the repo's own run command. No staging, no
  deploy, nothing shared touched.
- **Yardstick:** the phase DoD (plan file §6, the phase bead's acceptance), one line per promise.
  Not the whole feature: only what this phase claims.
- **Breaker:** fresh context, strongest model the harness has, given the local URL, the DoD lines
  and the contract, never the diff or the session.
- **Misalignment** (the product does not do what the DoD line says, or does more): one bead per
  line, and the phase depends on it:

  ```bash
  bd create "rewrite: <DoD line> — observed <what>" -t task --parent <epic-id> \
    -l src:real-test,kind:finding,area:<area> --deps discovered-from:<phase-id>,blocks:<phase-id>
  ```

  `--parent <epic-id>` keeps the bead inside the epic's molecule, where the feature gate and
  `bd ready --mol` look; never `--parent <phase-id>` (one dependency per pair in bd).

  The phase stays open until those beads close. A defect needs its test seen red first
  (`tdd-dev`), as in merge mode.
- **Receipt (required; the feature gate reads it):** the same format as merge mode, bound to the
  phase's own diff, with `ambiente: local`:

  ```bash
  python3 scripts/verdict.py new      --repo . --base <phase-start-sha> --head HEAD \
    --out .real-test/verdicts/<phase-id>-$(git rev-parse --short HEAD).json
  python3 scripts/verdict.py validate .real-test/verdicts/<file>.json --repo . --base <phase-start-sha> --head HEAD
  ```

  `--head` defaults to `STAGED`: on a committed phase pass `--head HEAD`. The validate call must
  use the same `--base`, or the perimeter is the whole branch. The merge receipt is still merge
  mode's, on staging.

## Production check

The same customer journey against production, with no diff. It replaces the per-product
"test the app" skills an operator agent used to carry: the product keeps only its `real_test:`
settings and its journey doc.

- **Reads** the product repo's `config.yml` (or `_polaris/config.yml`) `real_test:` block:

  ```yaml
  real_test:
    health: {staging: "https://api-staging.example.com/health", prod: "https://api.example.com/health"}
    journey: docs/modules/<area>/journeys/<name>.md    # the steps a customer takes, and what each must show
    browser_profile: ~/.config/browser-harness/profiles/<name>   # a dedicated user-data-dir
    account: qa@example.com                            # the dedicated test account
  ```

  No `journey:` → stop and say which file is missing; never improvise a journey.
- **Steps:** health first (the served commit is the one production claims); then each journey
  step in the browser, a screenshot per step, the timings, the console errors and the failed
  network calls; then the product's own observability for the same run, if the journey doc names
  where it is.
- **Read-only on data:** use the test account's tenant; a home page that greets anyone else is
  the wrong account: stop and report. Never touch a real customer's records.
- **Report:** healthy, or one line per defect (step, expected, observed, screenshot or trace id).
  Each defect goes through `issue-contract`, whose filter makes most of them beads and only a
  schedulable delivery an issue. No receipt: there is no diff to bind it to.

## Logged-in browser profiles — never passwords

- Each test environment has a dedicated test account (never the owner's own) and a dedicated
  browser profile (its own user-data-dir) where a human logged in once.
- The repo declares only `real_test.browser_profile` and `real_test.account`: never a cookie, a
  token or a password in git.
- browser-harness drives that profile over CDP, reusing the stored session; it starts its own
  instance on that profile and lists the tabs before any action.
- **Agents never type a password**, never fill a login form, never read a password vault.
- **An expired session stops the run**: report "session expired — log in again in profile
  `<browser_profile>`" (a human act) and end with an inconclusive result. Never a login attempt,
  never an API-only fallback presented as the walk.
- No browser-harness: the walk is API-only and ticks backend-only boxes; say so in the result.
