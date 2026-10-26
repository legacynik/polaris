---
name: crasher
description: ◇ Polaris — Drive a deployed app like a user, hunt failures, and PROPOSE one deduplicated finding per confirmed crash for a person to pick, never filing on its own; or judge whether a run's no-crash verdict stands. Use for does staging still work, smoke the deployment, hunt regressions on the live app. Requires python ≥ 3.9 and gh; bd (Beads); browser-harness for browser surfaces. Not for judging a diff, fixing what it finds, or load-testing a shared production database.
version: 0.5.1
user-invocable: true
auto: false
lifecycle: "the run record lives in the host repository's validation area and is the whole basis of a 'no crash found' claim; it also holds the proposal of an unattended run; a confirmed finding a person picked goes through issue-contract, which makes it a bead or, when its filter says so, a GitHub issue — no local bug list, no second register"
invokes: [issue-contract]
invoked-by: [human, cron]
io: "takes a deployed target, a flagged test account (a logged-in browser profile for browser surfaces) and a path budget -> produces a run record (surface, tools, writes, paths attempted, findings) and either a proposal (one entry per fingerprint: title, repro command, open twin) from which a person picks what issue-contract routes, or an explicit no-crash verdict naming every path it visited"
status: active
---

# crasher

## What it does

Drives the **running** app and asks, per screen and per flow, *does it still work?* A failure
that survives a fresh-context verify becomes one proposal entry per fingerprint, with the command
that reproduces it. It never fixes and never files on its own: it finds, proves and proposes.
Both of its claims are mechanical — `crash_report.py` refuses a "no crash" with no surface, no
attempted paths or over budget, and collapses repeats of one failure into one fingerprint.

## When

- "Does staging still work?", "smoke the deployment", "hunt regressions on the live app".
- A run record arrived and someone asks whether its no-crash verdict stands.

## Steps

1. **Declare before attacking** (QA without a webpage). Write into the run record: the `surface`
   (routes from the router directory, endpoints from route decorators, CLI commands, workers —
   whatever the target has), the `tools` per surface, the `writes` it may make and as whom, and
   the path `budget`. A CLI or API needs no browser. Default is read-only; never a shared
   production database.
2. **Use the logged-in profile, never a password.** Browser surfaces run through browser-harness
   in a dedicated instance on the profile in the repo config `real_test.browser_profile`, as
   `real_test.account`. The agent never types a credential. An expired session **stops** the run:
   "session expired, log in again in profile <X>" — a founder act, never a login attempt.
   Without browser-harness the walk is API-only and says so; it ticks no UI box.
3. **Drive each path**: it rendered, zero console errors, bound endpoints answer 2xx or 401; on an
   asynchronous money path, wait for the real result and measure the wait.
4. **Classify from fresh context** against the noise classes — flaky timing, expected validation
   error, test-account or environment quirk, stale stream, an open twin. Only survivors stay.
5. **Take the verdict from the gate**:
   ```bash
   gh issue list --state all --search "crasher" --json number,title,state --limit 500 > open.json
   python3 scripts/crash_report.py --run <run>.json --open-issues open.json [--unattended]
   # 0 no crash · 1 run refused (fix the run, never the record) · 2 unusable · 3 proposal
   ```
6. **Propose, then route only what a person picks.** Show the proposal as printed and ask which
   numbers to take. Search twins among beads too (`bd search "<fingerprint>" --status open`).
   Each picked entry without a twin goes to `issue-contract`, whose filter makes it a bead
   (`src:crasher`, fingerprint in the title) or a GitHub issue — never `gh issue create` here,
   never a twin again. `--unattended` writes the proposal into the record and stops.

## Output

The run record (`target`, `budget`, `surface`, `tools`, `writes`, `attempted`, `findings`,
`proposal` when unattended) and either a no-crash verdict naming every path visited with coverage
`attempted/surface`, or the proposal. Record shape and limits: `references/run.md`.

## Where this goes

This skill produces: **validation (the run record, with the proposal)**, where the repository's
`outputs:` map puts it; findings leave only through `issue-contract`.

## Not for

- Judging a diff or a PR before merge → `real-testing`.
- Fixing what it found → `bugfix`, in another session, so the finder never grades its own fix.
- Floods, races, exhaustion or cross-tenant reads on a shared production database.
- A repository with no live deployment, or a bug you already know how to write → `issue-contract`.
