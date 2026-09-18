---
name: crasher
description: ◇ Drive a deployed app like a user, hunt failures unattended, file ONE reproducible issue per confirmed crash, and judge whether a crasher run's no-crash verdict stands or is about to file a duplicate. Triggers on does staging still work, smoke the deployment, hunt regressions on the live app, is this run record believable. NOT for judging a diff (real-testing), fixing what it finds (bugfix), or load-testing a shared production database.
version: 0.2.0
user-invocable: true
auto: false
lifecycle: "the run record lives in the host repository's validation area and is the whole basis of a 'no crash found' claim; a confirmed finding becomes a GitHub issue through issue-contract and nothing else — no local bug list, no second register"
invokes: [issue-contract]
invoked-by: [human, cron]
io: "takes a deployed target URL, a flagged test account and a path budget -> produces a run record (surface, paths attempted, findings) and either ONE issue per confirmed finding, fingerprinted so the same crash never files twice, or an explicit no-crash verdict naming every path it visited; the issue is consumed by bugfix"
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

This skill produces: **tasks (the issue, through issue-contract), validation (the run record)**.
Kinds: `spec` `plan` `audit` `review` `validation` `diagram` `decision` `archive` — each maps to a
documentation area `docs/modules/<area>/…` whose README is a generated map. Never invent a third
location; if the repository declares no map, say once where you wrote and why.

## What this door is for

It drives the **running** app and asks one question per screen and per flow: *does it still work?*
When it does not, and the failure survives a verify pass, it opens **one** issue through
`issue-contract` carrying the command that reproduces the symptom. That issue is the entry point of
`bugfix`. The crasher never fixes; it finds, proves, and files.

The two claims it can make are the two it can fake, so both are mechanical:

| claim | how it is faked | what refuses the fake |
|---|---|---|
| "no crash found" | run two screens, declare the app healthy | `crash_report.py` refuses a verdict whose `attempted` list is empty, whose `surface` is undeclared, or which went past its budget — and prints coverage `attempted/surface` beside every no-crash line |
| "here is a crash" | file the same hang again next week with a different timing in the title | the finding's identity is a fingerprint over route + failure class + a symptom with its numbers collapsed; it rides in the title, so `issue-contract`'s own apply-time dedup finds the twin |
| "and here is the issue" | print an invocation nobody ever ran, which the tracker door would have rejected | the printed argv carries the whole founder contract and is executed against `build_issue.py` in the test suite — grepping it for `build_issue.py` is what let a rejected invocation ship |

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
4. **Write the run record and take the verdict.**

   ```bash
   python3 scripts/crash_report.py --run <run>.json
   # exit 0 no crash (accepted) · 1 run refused · 2 unusable input · 3 finding(s) to file
   ```

   The record declares `target`, `budget`, `surface`, `attempted` and `findings`. Exit 1 means the
   run may not be reported at all — fix the run, never the record. Note what it refuses: an empty
   `attempted`, a missing `surface` (coverage without a denominator is not coverage), more paths
   than the budget or than the surface, and a finding missing its route, symptom, class or domain.
5. **File through `issue-contract`, never a raw `gh` call.** `crash_report.py` prints one
   invocation per finding, already carrying the founder contract: an acceptance criterion and the
   **two** adversarial tests B9 requires, each with the two measurable signals its gate counts. The
   second adversarial test is always the dedup promise — re-run and the tracker must refuse the
   twin — because that is the one proof this door can guarantee for every finding. A finding
   carrying a reproducing command is filed `--afk yes` and is claimable by an unattended agent; a
   transcript-only finding is filed `--afk no` and says so in its acceptance criteria instead of
   pretending to be reproducible. The invocation also repeats the values as `--field` pairs under
   the ids the Polaris issue forms use; if the host repository's template asks for others,
   `build_issue.py` names them and you add them — it never guesses a domain, because B12 rejects a
   label the repository's glossary does not hold.

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
     "domain": "gates", "priority": "p2", "repo_path": ".",
     "evidence": "runs/2026-09-08/transcript.log",
     "repro": "curl -f -m 180 $TARGET/api/items/new returns status 200"}
  ]
}
```

`klass` is the failure class, and it is half the fingerprint: a console flood and a hang on the
same route are two findings, not one. `domain` must be a label from the host repository's
`.github/DOMAINS.yml`; the door will not guess one, so a finding without it is refused here rather
than rejected later by B12. `repro` is what turns a finding into a reproducing command — a command
that exits non-zero on the failure and zero once it is fixed. Leave it out rather than invent one,
and remember B15: any file path it names must exist in the repository the issue is filed against.

## Global door, per-repository overlay

- **This door owns** the method, the refusal gates, the fingerprint, and the `issue-contract`
  wiring. It is repository-agnostic and carries no URL, account or route of any application.
- **A per-repository overlay owns** that application's target URL, its flagged test account, its
  route list, and the few judgements a generic smoke cannot infer (for example: two versions of one
  generated document must keep distinct totals). It lives with that repository, not here.

## Feeding the unattended loop

A finding filed with `--afk yes` carries a command that exits non-zero on the failure, which is
exactly the admission criterion the unattended loop reads. That is how this door is a *source* for
that loop rather than a second copy of it: it produces `afk:eligible` issues and stops. Claiming,
branching, fixing and shipping belong to `bugfix`, `tdd-dev`, `real-testing` and `ship`.

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
  a given application, findings arrive with no `repro` and file as `--afk no`: honest, and not yet
  the unattended loop's fuel. That gap is the door's, not the loop's.

## Selfcheck

```bash
python3 scripts/crash_report.py --selfcheck    # 13 branches, offline
python3 -m pytest tests/test_crash_report.py -q
```

Bypass cases — what passed before this door and must fail now: `references/bypass-test.md`.
