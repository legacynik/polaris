# Bug History — polaris-sweep

Empirical bugs from real Sweep runs. Each links to a regression test in `evals/evals.json`. Read before non-trivial SKILL.md edits.

## 2026-04-28 — sweep-pending jq filter bug (cost ~$1.30/h waste)

**Symptom**: Sweep cron fires every 15 min. After review of two PRs, Sweep kept re-reviewing the same PRs every subsequent tick. Each re-review costs ~$0.17 (token-equivalent). With 2 PRs open, ~$1.30/h waste until fixed.

**Root cause**: `sweep-pending.sh` (cron entry-point script that lists pending PRs and dispatches `polaris-sweep.sh` per PR) had a buggy jq filter:
```bash
gh pr list --label afk:done-pending-merge --state open --json number,comments \
  -q '.[] | select((.comments[]? | .body | startswith("<!-- polaris-sweep-id")) | not).number'
```
The `select((.comments[]? | ... | startswith) | not)` produced one boolean per comment per PR. A PR with N non-marker comments emitted the PR N times — Sweep ran N times on it.

**Fix shipped** (commit `074eddc` in _polaris): collapse to per-PR boolean:
```bash
-q '.[] | select([.comments[]?.body] | map(startswith("<!-- polaris-sweep-id")) | any | not).number'
```

This is in `sweep-pending.sh`, not in polaris-sweep skill itself. polaris-sweep is correctly idempotent (comment upsert via marker) — the bug was at the trigger layer above. Documented here for cross-skill awareness; the eval test for idempotency (`evals/evals.json` test #2) covers Sweep's part.

## 2026-04-28 — `/usr/local/bin/claude` path missing

**Symptom**: `polaris-sweep.sh` wrapper hardcoded `/usr/local/bin/claude` — a path that doesn't exist on the HolyClaude container. Cron Sweep would have failed at the first tick if it ever fired (caught before deployment by code review at 21:35 CEST).

**Root cause**: phase567 agent that wrote the wrapper assumed the binary path from a different convention. The container actually has claude at `~claude/.local/bin/claude`.

**Fix shipped** (commit `72843e6` in _polaris): use PATH lookup `exec claude -p ...` instead of absolute path. Cron file already sets PATH correctly.

This bug is in the wrapper script, not in the skill. But it's a reminder: when adding scripts that invoke claude headless, prefer PATH lookup over hardcoded absolute paths — the binary location varies by install method.

## 2026-04-28 — auto-merge gate triggered too late (manual label-toggle workaround)

**Symptom**: a PR had ✅ approve verdict from Sweep at 18:48 UTC. Auto-merge GHA didn't fire until 18:54 UTC, only after I manually toggled a label on the PR.

**Root cause**: auto-merge GHA's trigger list was [pull_request_target.labeled, pull_request_review.submitted, check_suite.completed]. Sweep posts a *comment* (not a review), so none of those events fired. The gate sat waiting indefinitely.

**Fix shipped** (commit `4204b39` in acme-quotes): added `issue_comment.created` to the trigger list. Now Sweep's verdict comment auto-triggers gate evaluation.

This bug is in the GHA workflow, not in the polaris-sweep skill. But it informs the skill's design: Sweep's contract is "post a comment that's machine-readable and triggers downstream gates". The verdict-format eval (`evals/evals.json` test #1) covers the contract — the emoji is part of the trigger criteria.

## How to use this file

Same pattern as other Hand skills:

1. Read before SKILL.md edits.
2. New bug → add an entry here + add eval test → fix → confirm.
3. Old bugs are regression tests — never let them silently regrow.

The Sweep skill itself was robust during the dogfood; the bugs were in adjacent layers (wrapper script, cron filter, GHA triggers). Documenting them here keeps the cross-cutting picture in one place.

---

## 2026-07-26 — Phase 3c Codex invocation was broken in four independent ways (cost ~2h wall-clock, 2 runs, zero output)

**Context**: first real Sweep run on `acme-api`, PR A (2378+/325−, 65 files) and PR B (955+/411−, 26 files). Both reviews completed and posted; only the Codex lens failed, twice, for four different reasons stacked on each other.

**Symptoms, in the order they were hit**:
1. `codex exec` from a non-repo cwd (a scratchpad dir) aborted immediately: `"Not inside a trusted directory and --skip-git-repo-check was not specified"`. Zero-byte output, exit 0 — indistinguishable from "found nothing".
2. Re-run from the repo root: the log showed `"Reading additional input from stdin..."` and the process sat there. Backgrounded processes inherit no stdin, so `codex exec` blocks forever. One run burned ~1h before being killed.
3. `--full-auto` emitted `"warning: --full-auto is deprecated; use --sandbox workspace-write"` — it also contradicts `--sandbox read-only`, which is what a review wants.
4. Third run, correctly flagged, still produced nothing for 50 min. The run log (ANSI-encoded — plain `grep` matches nothing, `grep -a` works) ended in `requests.exceptions.ConnectionError: … cloud.langfuse.com`: **Codex had routed itself into running the project's test suite** instead of reading the diff. It was never reviewing.

**A fifth, self-inflicted**: the 4th run was launched via the `Bash` tool with `timeout: 960000`, which exceeds the tool's 600000 ms cap and is silently clamped — the harness SIGTERMed it at exactly 10:00, which reads exactly like a hang. Long Codex runs must be `nohup … &` detached and polled, never foreground.

**Also wrong, independent of the hangs**: the prompt pasted `$(cat diff | head -500)` inline. On the PR A diff that is 500 of 3992 lines — 87% discarded — while still producing a confident-looking review. Write the diff to a file inside the repo and point Codex at the path; it can read it, and it can read the surrounding source too, which is what makes the findings verifiable.

**Fix shipped** (this commit, SKILL.md Phase 3c rewritten): `nohup timeout 900 codex exec --sandbox read-only --skip-git-repo-check --output-schema … --output-last-message … "$(cat prompt.md)" < /dev/null > run.log 2>&1 &`, no `--full-auto`, diff passed by path, plus a HARD CONSTRAINTS block in the prompt forbidding test execution and network access and requiring the JSON as the final message. `--output-schema` added because `--output-last-message` is not guaranteed (Codex can end on a tool block and never write the file); `grep -a` documented as the log fallback. New Phase 3c-fallback: when a lens does not run, mark the section ⚠️ **Not run**, state the review is two lenses not three, and record `codex: not-run (<reason>)` in run state — never leave "will be filled in later" on a client-visible PR comment.

**Cross-checks that also failed in the same run** (fixed in the same edit):
- Phase 2's `_polaris/sweep/repos/<slug>.md`: the whole `_polaris/sweep/` tree did not exist. Profile is optional → default `severity_threshold=high`, note it, continue.
- Phase 5's `/usr/local/bin/sweep-comment-upsert.sh`: absent outside the HolyClaude container. Inline `gh api` upsert on the marker added as the fallback, with `-F body=@file` (a multi-KB markdown body inlined as a shell arg breaks on backticks and `$`).

**Lesson beyond the flags**: the Codex lens was the *least* valuable of the three on these two PRs. It confirmed one finding the Claude pass already had and added three minor ones. The highest-value finding of the whole run — PII logged to CloudWatch against a decision ratified with the client — came from grepping `_polaris/decisions.md`, which no external tool can do. Hence the new Phase 3b-bis (decision-conformance check). Do not let a broken external lens block the sweep; the ledger lens is the one that pays.

## 2026-07-26 — "verified clean" retracted: checked the file that RENDERS the parent, not the file that OWNS the behaviour

**Symptom**: Sweep revision 1 on PR PR B reported, under *Verified clean*, that two deleted frontend test files were "already dead — the seam was refactored away earlier on main". Wrong. The tests were live and passing on `main`, and the PR under review is what removed the behaviour they covered.

**Root cause**: the deleted assertions targeted `data-testid="inline-chat-panel-wrapper"` from inside `OnboardingTab.test.tsx`. I verified by diffing **`OnboardingTab.tsx`** (`git diff --stat origin/main FETCH_HEAD` → empty, 88 lines, no chat panel) and concluded the seam was gone before this PR. But `OnboardingTab` only renders `NewCaseForm`, and the panel lives at `NewCaseForm.tsx:772` on `main` — a file this PR changes by -93 lines. The right check was one `git grep` across the whole frontend tree on both refs:
```bash
git grep -n "inline-chat-panel-wrapper" origin/main   -- <fe-src>   # present at NewCaseForm.tsx:772
git grep -n "inline-chat-panel-wrapper" refs/sweep/pr -- <fe-src>   # absent → removed BY THIS PR
```

**Second, compounding**: reused a bare `FETCH_HEAD` across two PRs in one session. A later `git fetch origin <other-branch>` silently repointed it, so a "PR branch" verification actually ran against the *other* PR's head and produced a confident false negative. Caught only because the old pre-fix code showed up in the output.

**Fix shipped** (SKILL.md, Phase 4 verification rules): verify against the file that **owns** the behaviour, found by `git grep`ing the symbol/testid across the tree on **both** refs — never by diffing the component you assume renders it. And fetch each PR to a **named ref** (`git fetch origin <branch>:refs/sweep/pr<N> -f`), never bare `FETCH_HEAD`, whenever more than one PR is in play.

**Why it matters beyond the miss**: a wrong entry under *Verified clean* is worse than a missing one — it actively tells the reviewer not to look. The retraction has to be as visible as the original claim (revision 1 → revision 2 note at the top of the comment, plus a *Corrections* section), not a silent edit.
