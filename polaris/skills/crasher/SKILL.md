---
name: crasher
description: ◇ Drive a deployed app like a user, hunt failures, and PROPOSE one deduplicated issue per confirmed crash for a person to pick — never file them itself — or judge whether a run's no-crash verdict stands. Triggers on does staging still work, smoke the deployment, hunt regressions on the live app, is this run record believable. NOT for judging a diff (real-testing), fixing what it finds (bugfix), or load-testing a shared production database.
version: 0.4.0
user-invocable: true
auto: false
lifecycle: "the run record lives in the host repository's validation area and is the whole basis of a 'no crash found' claim; it also holds the proposal of an unattended run; a confirmed finding becomes a GitHub issue only when a person picks it, through issue-contract — no local bug list, no second register"
invokes: [issue-contract]
invoked-by: [human, cron]
io: "takes a deployed target URL, a flagged test account and a path budget -> produces a run record (surface, paths attempted, findings) and either a proposal (one entry per fingerprint: title, repro command, open twin) from which a person picks what issue-contract files, or an explicit no-crash verdict naming every path it visited; a filed issue is consumed by bugfix"
status: active
---

# crasher

## Where this goes (host repository decides)

A skill decides **how** to produce a document, never **where** it lives. Before writing any spec,
plan, audit, review, validation receipt or diagram, read the host repository's output map and use
it; a document that lands where the repository does not look was never written.

```bash
sed -n '/^outputs:/,/^[^ ]/p' _polaris/config.yml 2>/dev/null || sed -n '/^outputs:/,/^[^ ]/p' config.yml
```

This skill produces: **validation (the run record, with the proposal)**; tasks only through
`issue-contract`, for the findings a person picked.
Kinds: `spec` `plan` `audit` `review` `validation` `diagram` `decision` `archive` — each maps to a
documentation area `docs/modules/<area>/…` whose README is a generated map. Never invent a third
location; if the repository declares no map, say once where you wrote and why.

## What this door is for

It drives the **running** app and asks one question per screen and per flow: *does it still work?*
When it does not, and the failure survives a verify pass, it **proposes** one issue per distinct
failure, carrying the command that reproduces the symptom, and files only the ones a person
picks, through `issue-contract`. A filed issue is the entry point of `bugfix`. The crasher never
fixes and never files on its own: it finds, proves, and proposes.

The two claims it can make are the two it can fake, so both are mechanical:

| claim | how it is faked | what refuses the fake |
|---|---|---|
| "no crash found" | run two screens, declare the app healthy | `crash_report.py` refuses a verdict whose `attempted` list is empty, whose `surface` is undeclared, or which went past its budget — and prints coverage `attempted/surface` beside every no-crash line |
| "here is a crash" | propose the same hang twice, or again next week with a different timing | the finding's identity is a fingerprint over route + failure class + a symptom with its numbers collapsed; one proposal entry per fingerprint, and the open twin is named beside it from the tracker's own list |
| "and here are the issues" | file every finding of every run, and the tracker drowns | `crash_report.py` prints no filing command at all; an unattended run writes its proposal into the record and files nothing |

## When NOT to use

- **Judging a diff, a branch or a PR before merge** → `real-testing`. The crasher tests a
  deployment, not a change.
- **Fixing the bug it found** → `bugfix`. The crasher's issue is that door's input, and the two
  jobs must stay in different sessions or the finder grades its own fix.
- **Destructive or adversarial testing against a shared production database** — floods, races,
  resource exhaustion, cross-tenant reads, mutating injection. On a shared database the act of
  triggering *is* the incident. That class needs real isolation and an explicit per-run go; it is
  not this door.
- **A repository with no live deployment** — there is nothing to drive.
- **Opening an issue you already know how to write** → `issue-contract` directly. The crasher is
  the thing that *discovers*; going through it to file a known bug is ceremony.

## Flow

1. **Enumerate the surface, from the repository.** Front-end routes from the router directory,
   API endpoints from the route decorators — `ls` and `grep`, no code graph needed. Re-run after
   any change and the coverage self-updates. Decide the path budget for this run **before**
   driving and write it into the record as `budget`: an unbounded run is not the run that was
   authorised, and `crash_report.py` refuses a record without it. The budget is a field of the
   run, not a flag of the report — the report reads what the drive was allowed to do.
2. **Drive it.** Delegate to the `browser-pilot` agent, which owns the dedicated headless Chrome
   (CDP) — never the founder's everyday browser, never a Playwright script written here. Per path:
   navigate, assert the page rendered, assert zero console errors, assert bound endpoints answer
   2xx or 401. For an asynchronous money-path, wait for the real result and measure the wait; never
   hardcode a timing from a previous run.
3. **Classify before filing.** A raw finding is verified from fresh context against the noise
   classes — flaky timing, expected validation error, test-account or environment quirk, stale
   stream, duplicate of an issue already open. Only a survivor is filed. This is the step that
   keeps the tracker from filling with false positives, and it is the step an unattended run is
   most tempted to skip.
4. **Write the run record, search for twins, take the verdict.**

   ```bash
   gh issue list --state all --search "crasher" --json number,title,state --limit 500 > open.json
   python3 scripts/crash_report.py --run <run>.json --open-issues open.json
   # exit 0 no crash (accepted) · 1 run refused · 2 unusable input · 3 finding(s) proposed
   ```

   The record declares `target`, `budget`, `surface`, `attempted` and `findings`. Exit 1 means the
   run may not be reported at all — fix the run, never the record. Note what it refuses: an empty
   `attempted`, a missing `surface` (coverage without a denominator is not coverage), more paths
   than the budget or than the surface, and a finding missing its route, symptom, class or domain.
   Done when the script exited 0 or 3 on a record that names every path it visited.
5. **Propose, then file only what a person picks.** Exit 3 prints a PROPOSAL: one numbered entry
   per distinct fingerprint, with its title, reproducing command (or "transcript only"), the open
   twin if the tracker already holds one, and whether it is for a person (no repro) or claimable
   by an agent. Show it to the owner as it is and ask which numbers to file. For each picked entry
   without an open twin, hand `issue-contract` the entry's title, description, DoD, regression
   check and AFK decision; never call `gh issue create` from here. An entry with an open twin is
   never filed again: comment on the twin instead if the owner asks. Done when every entry is
   either filed by `issue-contract`, named as a twin, or left unpicked by the owner.

   **Unattended or scheduled runs file nothing.** Add `--unattended`: the script writes the same
   proposal into the run record under `proposal` and prints nothing to file. A person reads it
   later and picks, as above. Done when the record holds the proposal and no issue was created.

## The run record

```json
{
  "target": "https://staging.example.invalid",
  "repo_slug": "<owner>/<repo>",
  "budget": 12,
  "surface": ["/", "/login", "/items", "/items/new"],
  "attempted": ["/", "/login", "/items"],
  "findings": [
    {"route": "/items/new", "klass": "gen_hang", "symptom": "no result after 421s",
     "domain": "gates", "evidence": "runs/2026-09-08/transcript.log",
     "repro": "curl -f -m 180 $TARGET/api/items/new returns status 200"}
  ]
}
```

`klass` is the failure class, and it is half the fingerprint: a console flood and a hang on the
same route are two findings, not one. `domain` must be an area label the host repository already
uses (its issue labels or its declared domain list); the door will not guess one, so a finding
without it is refused here. `repro` is what turns a finding into a reproducing command — a
command that exits non-zero on the failure and zero once it is fixed. Leave it out rather than
invent one; any file path it names must exist in the repository the issue would be filed against.
An unattended run adds `proposal` to this record; nothing else writes it.

## Global door, per-repository overlay

- **This door owns** the method, the refusal gates, the fingerprint, and the proposal. It is repository-agnostic and carries no URL, account or route of any application.
- **A per-repository overlay owns** that application's target URL, its flagged test account, its
  route list, and the few judgements a generic smoke cannot infer (for example: two versions of one
  generated document must keep distinct totals). It lives with that repository, not here.

## Feeding the unattended loop

A picked finding that carries a command exiting non-zero on the failure is filed as claimable by
an agent (issue-contract applies the repository's agent label), which is the admission criterion
an unattended fixing loop reads. That is how this door is a *source* for that loop rather than a
second copy of it: it proposes and stops. Claiming, branching, fixing and shipping belong to
`bugfix`, `tdd-dev`, `real-testing` and the repository's merge workflow.

## What this door does not close — declared

- **The classify step is judgement, not a script.** `crash_report.py` refuses an unnamed or
  unbudgeted run; it cannot tell a real regression from a flaky one. A run that classifies badly
  files a bad issue, and only the fresh-context verify pass stands between the two.
- **Fingerprint collapse is lexical.** Two genuinely different failures that read the same after
  the numbers are collapsed will share one issue. That is the deliberate trade against the opposite
  failure — a new issue per run — and it is visible in the title, so a human can split them.
- **Coverage is self-reported.** The record says which paths were attempted; nothing here proves
  the browser actually visited them, only that the claim has a denominator. Closing that needs the
  driver to emit the record itself.
- **No driver ships with this door.** The abandoned branch's `drive.py` carried one application's
  selectors and login copy, so it was cut as a per-repository overlay. Until an overlay exists for
  a given application, findings arrive with no `repro` and are proposed for a person: honest, and
  not yet the unattended loop's fuel. That gap is the door's, not the loop's.

## Selfcheck

```bash
python3 scripts/crash_report.py --selfcheck    # 16 branches, offline
python3 -m pytest tests/test_crash_report.py -q
```

Bypass cases — what passed before this door and must fail now: `references/bypass-test.md`.
