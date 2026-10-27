# Legacy machine interface (vault only, not shipped)

`scripts/build_issue.py`, `scripts/parse_template.py` and `scripts/transition_gate.py` preserve
older automation callers (the `wayfinder` handoff, the suite selfchecks). They are not the
default route of this skill and their stricter contracts do not govern ordinary tickets. Use them
only when an existing integration explicitly requires that machine interface. Their bypass cases
are in [bypass-test-legacy.md](bypass-test-legacy.md).

# The transition gate — shape and why

`scripts/transition_gate.py` has one decision surface, `decide()`. The CLI (`run()`/`main()`) is a
thin wrapper around it, and `import transition_gate; transition_gate.decide(...)` gets the exact
same checks — there is no lower-privilege path to a label (corpus audit found a gate that only
fired through `main()`; this one fires the same way for a direct function call). It never calls
`gh` unless `--apply` is passed, and only after `decide()` itself returned ALLOW — see
[bypass-test-update.md](bypass-test-update.md) for why this split, and what `--apply` does and does not close.

## `--issue-json` (required for `--to ready-for-agent`, and for `--to wontfix` with a
`rejected-*` reason)

```json
{"assignee": null, "linked_active_workstream": false, "category": "bug"}
```
Build it from `gh issue view <n> --json assignees,labels` plus a check of open teammate
branches/PRs/epics against the item. Missing the file at all, or missing the `assignee` /
`linked_active_workstream` key inside it, **BLOCKs** — a key that was never checked is not the
same as a key checked and found empty, and the gate fails closed on the difference, never open.
`linked_active_workstream: true` blocks the promotion.

**Why this guardrail exists** (inherited from `daily-triage`, the donor with 0 registry coverage
of its own but a real incident behind this one rule): on 2026-06-18 an autonomous loop free-picked
an unassigned issue that was actually a teammate's in-progress residual — collision. The fix,
carried over verbatim as mechanism: `assignee == null` AND not linked to an active
workstream/epic/branch, **verified**, checked before every `ready-for-agent` promotion, never
assumed.

**`category`** (`bug`/`enhancement`) is only read by the `wontfix` path, to cross-check a
`rejected-bug`/`rejected-enhancement` `--reason` against a verified field instead of the caller's
own say-so — see below.

## PR-specific cross-check

For a PR, also read `git-power`'s parked-work ledger (census of worktree/branch/stash/PR age
and state) for the branch the PR sits on. An orphaned or stale branch (no commits in N days, no
alive worktree) downgrades the recommendation to `needs-info` regardless of how good the diff
looks — a PR on a dead branch is not "ready for a human", it's a PR someone needs to ask about
first. This is a read-only consult, not a sequential call: issue-contract reads `git-power`'s output,
it does not wait for `git-power` to run first.

## `--to wontfix`: `--reason` is required and cross-checked, not trusted

`--reason` (`already-implemented` / `rejected-bug` / `rejected-enhancement`) is now required —
omitting it entirely used to ALLOW silently and skip every check below it; that's closed.
`already-implemented` must NOT carry an `--out-of-scope-file` (poisons dedup, see below).
`rejected-bug` and `rejected-enhancement` both now require the `.out-of-scope/<concept>.md` file
**and** a `--issue-json` whose `category` field matches what the reason claims — a bare
`--reason rejected-bug` used to close an enhancement without writing the file at all, because
nothing checked it against anything. The category comes from the tracker (a real label), not from
the flag the triager typed.

## `--to new-issue`: the F10 dedup gate

Before handing a raw item to `issue-contract`, run:
```
python3 scripts/transition_gate.py --to new-issue --concept "<domain concept, a few words>" \
  --open-issues-json /tmp/issues.json [--override "why this is different"]
```
`/tmp/issues.json` is the same file `scan_backlog.py` already reads (`gh issue list ... > issues.json`
from the "What needs attention" step) — no second fetch. The check tokenizes `--concept` and every
open issue's title (case-insensitive, words ≥4 chars) and BLOCKs on any overlap unless `--override`
states why the match is a false positive; the override is printed to stdout as part of the ALLOW,
so it lands in the redundancy trail. This is real matching against real data pulled live from the
tracker — not the free-text "check the unlabeled bucket" instruction it replaces, which nothing
ever enforced. It is still a heuristic (word-overlap, not semantic similarity) — a paraphrase with
zero shared words slips through; that ceiling is inherent to a dependency-free text match and is
disclosed, not hidden.

## What "not eligible" looks like even when assignee is verified null

Small + has a clear RED-first-testable contract, AND not a judgment call requiring
product/legal/design authority. Both are judgment, not automatable — the gate does not check
them (no script can decide "is this a judgment call"); the triager states the call explicitly
before running the gate, same as `daily-triage`'s "when unsure → NOT agent-ready" default.

## Known limits — disclosed, not silently accepted as "closed"

1. **The redundancy-check and dedup-concept fields prove form, not truth.** `check_redundancy`
   now rejects a `Searched:` under 10 chars (a one-word non-answer), which raises the floor, but
   no text field can verify a search actually happened — `"Searched: nowhere real, made this up"`
   is 30-odd characters and still passes. Same limit applies to `--concept` in the F10 check: it
   trusts the triager's own phrasing of the concept, it does not independently derive it from the
   item. This is the same class of limit the codebase-search side of G9#7 already accepts
   elsewhere in this suite — a mechanized form-check is real progress over prose, it is not proof.
2. **`--apply` closes the gap only for callers that use this tool.** Nothing outside this script —
   no hook, no CI check — stops an agent from running `gh issue edit --add-label ready-for-agent`
   directly, skipping `transition_gate.py` entirely. `--apply` removes the *documented* manual
   step (SKILL.md no longer instructs "then apply it by hand"), so the correct path is now
   atomic — decision and mutation in one process, one exit code — but a caller that ignores the
   tool and calls `gh` itself is not something a script living in `skills-suite/issue-contract/` can
   intercept; that would need a `PreToolUse`-style hook watching `gh issue edit` system-wide,
   which is out of this skill's boundary (and would break the "self-contained, 4-harness" rule in
   `SKILL-STANDARD.md` if built Claude-Code-only). Not fixed here — see the skill's own
   `non_fatto` note for the honest reason.
