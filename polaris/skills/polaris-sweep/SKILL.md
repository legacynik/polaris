---
name: polaris-sweep
description: ◇ Polaris Sweep — review a single PR end-to-end and post a durable comment. Used by autonomous trigger (cron polling new PRs), or invoked as `claude -p "/polaris-sweep <PR_N>"` in a fresh session.
version: 1.6.0
user-invocable: true
status: active
effort: medium
job: review a PR through three lenses + the decision ledger + a runtime attestation, and decide by exit code whether it may merge on its own
when_not: not for issues (PRs only), not for PRs that are not Hand-authored (silent skip), not to deploy or put code on staging, and not to reject a PR because it is not on staging — "nobody deployed it" is not evidence of a regression
io: receives an open PR number → emits an idempotent review comment on the PR + run state in _polaris/sweep/runs/ + an auto-merge verdict via scripts/sweep_gate.py (exit code)
lifecycle: the comment lives on the PR (upserted by marker, never duplicated); the next sweep on the same PR drains the run state; .tmp/sweep/ is cleaned once collected
invokes: [real-testing, codex-review]
invoked-by: [cron, human]
---

# Polaris Sweep — review a single PR

## Bundled resources

| File | Purpose |
|---|---|
| `scripts/sweep_gate.py` | **The auto-merge decision** (Phase 4.5): exit 0 allows, 1 denies, 2 usage error. Fail-closed. `--selfcheck`: 13 checks |
| `references/BUG-HISTORY.md` | **Read first when modifying this skill.** 3 bugs from 2026-04-28 (sweep-pending jq filter, claude binary path, auto-merge trigger gap) in adjacent layers, plus the 2026-07-26 entry — 4 stacked failures in Phase 3c's own Codex invocation, a clamped tool timeout mistaken for a hang, and a truncated-diff prompt. The flags that entry produced now live in the `codex-review` skill, which owns the invocation. |
| `references/quality-review.md` | The Phase 3a checks and output shape — read before every quality review |
| `references/comment-template.md` | The exact Phase 4 comment template + Verified-clean rules (marker and Verdict line are load-bearing) |
| `references/conflict-resolution.md` | **Load lazily** — only when Phase 1.5 reports `mergeable=CONFLICTING`. Decision tree for auto-rebase vs escalate. Keeps the default tick cheap (no extra context tokens) for the common case of mergeable PRs. |
| `references/bypass-test.md` | B1–B3 (verdict on code never executed · PR touching the pipeline · verdict on a stale SHA) with before/after output |

The verdict-format eval is load-bearing: auto-merge GHA's gate regex (`Verdict.*✅[[:space:]]+approve`) depends on it. Don't change the verdict format without updating the gate regex (lives in `.github/workflows/auto-merge-trivial.yml` of each repo using Sweep).

## Pre-conditions
1. Cwd is the target repo (or `gh repo set-default` is configured).
2. `gh auth status` is clean.
3. Argument `<PR_N>` is a numeric PR number that's open and Hand-authored.

## Phase 1 — Gather

```bash
PR_DATA=$(gh pr view "$PR_N" --json url,title,body,headRefName,additions,deletions,changedFiles,labels,author,mergeable)
PR_DIFF=$(gh pr diff "$PR_N")
```

## Phase 1.5 — Conflict gate (NEW)

Inspect `.mergeable`. If `CONFLICTING`, the diff that Phase 3 would review is against a stale base — Phase 3a/3b/3c are partially meaningless until the rebase succeeds.

```bash
MERGEABLE=$(echo "$PR_DATA" | jq -r '.mergeable')
if [ "$MERGEABLE" = "CONFLICTING" ]; then
    echo "PR #$PR_N is CONFLICTING — loading conflict resolution playbook"
    # Read references/conflict-resolution.md and follow the decision tree:
    # - trivial behind → auto-rebase + push
    # - auto-resolvable → -X theirs + flag
    # - real conflict  → label needs-human-rebase + Telegram alert
    # Then EXIT this tick. On the next sweep tick, the PR will either be
    # mergeable (rebase succeeded → flow continues to Phase 2) or still
    # CONFLICTING with `needs-human-rebase` label (skip to avoid loop).
    exit 0
fi
```

Skip the conflict gate entirely (do not load the reference) when `MERGEABLE` is `MERGEABLE` or `UNKNOWN` — keeps the common-case tick fast.

## Phase 1.7 — Real-test receipt check (nag, never a block)

If the repo opted in to the real-testing gate (`.real-test/enabled` exists in the local
checkout), check whether a verdict exists for THIS PR's head:

```bash
HASH=$(python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/real-testing/scripts/perimeter.py" --repo <checkout> --head <pr-head-sha> --hash-only)
test -f "<checkout>/.real-test/verdicts/$HASH.json" || echo "no receipt"
```

No receipt (or a verdict that fails `verdict.py validate`) → add ONE line to the review
comment: *"⚠ No real-test receipt for this PR's hash (`<hash8>`) — the gate has no proof
this diff was exercised."* This is a NAG by design (lessons 2026-08-13: mandatory CI gates
on existing repos kill adoption): it makes the missing receipt visible on the PR, it never
blocks. Repos without the marker: skip silently — they never opted in.

## Phase 2 — Read repo profile

```bash
PROFILE_FILE="_polaris/sweep/repos/<repo-slug>.md"
# Read severity_threshold from frontmatter (default: high)
```

The profile is **optional**. Most repos have never been onboarded to Sweep —
`_polaris/sweep/` is often absent. A missing
profile means `severity_threshold=high` and nothing else; note it in one line and
continue. Never create a profile implicitly, and never stall waiting for one.

## Phase 3 — Run review

### Phase 3a — Quality review

Review `git diff <merge-base>..<head>` against the PR's stated intent, in a fresh-context
subagent if your harness supports one, otherwise inline, read-only on the checkout. Apply every
check in `references/quality-review.md` and return its output: strengths, findings by severity
(each with `file:line`, what is wrong, why it matters) and approve / approve-with-minor /
request-changes. Done when every check has a verdict and the verdict line is written.

### Phase 3a-bis — Over-engineering lens (threshold-gated, NEVER blocking alone)

Only when the diff is large enough for over-engineering to hide in — **additions > 100 lines**
(from Phase 1's `additions`) — read the diff once for over-engineering only: reinvented stdlib, speculative abstraction, duplicated shapes,
oversized functions. Field precedent (2026-08-17): three real findings of exactly
this class — duplicated helper, 26-line function, 4 params — that the correctness lenses had
no reason to catch.

Rules: findings land in the comment as **judgement calls** under `## Findings`, they NEVER
flip the verdict by themselves, and they never run on small diffs (a 5-line fix gets zero
friction). If simplification fixes are applied after green, the receipts re-open by
construction: real-testing receipts are content-hashed and `sweep_gate` denies on a changed
SHA — green and mutation re-run, mechanically, not by discipline.

### Phase 3b — Security review

Review the diff for security. Check each of:
1. Secrets/credentials hardcoded or logged
2. Input validation missing at API boundaries
3. SQL/command injection vectors
4. Auth/authorization gaps
5. Error messages leaking sensitive info
6. PII in logs or responses

If any finding is Critical or High severity → override final verdict to `request-changes` regardless of Phase 3a result.

### Phase 3b-bis — Decision-conformance check (highest-yield lens, do not skip)

Grep the repo's own ledger for decisions the diff touches, and read the ones that match:

```bash
grep -niE "<domain words from the diff: logging|retention|auth|region|PII|…>" \
  _polaris/decisions.md | head
```

A diff can be clean code and still be a **regression against a ratified decision** —
which no generic quality or security lens will catch, because the rule lives in the
ledger, not the code. This is the single highest-value finding class Sweep produces.

Concrete precedent (2026-07-26): the code was well-written and well-tested,
but logged merchant legal names, UBO names and screening outcomes to CloudWatch, against
`decisions.md` 2026-07-14 §3 *"no personal data in operational logs by design"* — a rule
agreed with the client and load-bearing for a GDPR-erasure claim. Both external lenses
missed it; only reading the ledger surfaced it. When you find one, quote the decision
verbatim with its date, and say what the decision's own stated rationale loses.

Treat a decision regression as **High minimum**, and name the three ways out:
comply, amend the decision deliberately, or narrow it (often the rule is stricter than
the underlying requirement — e.g. an outcome logged without a name is pseudonymous).

### Phase 3s — Spec-conformance: does the diff implement the ORIGINATING ISSUE? (do not skip)

The lens no other phase covers: 3a judges quality, 3b security, 3b-bis the decision ledger —
none of them asks whether the PR does **what the issue asked**. An unattended agent can produce
a clean, secure, well-tested PR that implements the wrong thing; without this lens it
self-merges.

1. Resolve the originating issue: `Closes #N`/`Fixes #N` in the PR body, issue refs in commit
   messages, or the branch name. Loop PRs always carry one — `issue-contract` (B9) guarantees
   every `afk:eligible` issue is born with a measurable DoD, so for the AFK class the spec
   source ALWAYS exists.
2. Read the issue's DoD checkboxes / acceptance criteria. Verify each against the diff and the
   evidence (receipts, run logs), and report per item: **met / partial / missing / creep**
   (behaviour nobody asked for), quoting the issue line.
3. Verdict rules: a REQUIRED DoD item missing → **request-changes** (the work is literally not
   done — this is not a judgement call) · partial-but-declared (the record says so, e.g.
   `MERGEABLE-CON-GAP`) → High finding, blocks auto-merge, human decides · scope creep →
   judgement call, never blocking alone. No issue found and the PR is not a chore/docs class →
   say so in the comment: an unattended PR without an originating issue is itself a finding.
4. Field precedent (2026-08-17): the spec lens is what caught an issue closed riding another
   fix's evidence without its own gate, and the honestly-open DoD item —
   findings no quality or security lens had a reason to see.

For manual pre-PR use in a session, the `polaris-review` skill covers this same axis
(plus Standards) — this phase absorbs its Spec axis into the unattended pipeline; it does not
replace the manual tool.

### Phase 3c — Codex adversarial review

Run the `codex-review` skill on this PR (`ID=$PR_N`, the PR-diff branch of its step 1). It owns
the hardened invocation, the model choice and the why-per-flag table; do not carry a copy of the
flags here. Take back its output block (`CODEX: ran|not-run`, `TRACE`, verified findings).

If it reports verified Critical/High findings → override the verdict to `request-changes`. A
`TRACE: diff-only` result is said in the comment beside its findings instead of being trusted.
`CODEX: not-run` (no CLI, timeout, zero output) goes to the fallback below.

### Phase 3c-fallback — when Codex does not run: a Standards + Spec pass takes the lens

If Codex times out, is killed, or returns nothing, **do not stall the sweep, do not
promise a later update, and do not degrade to two lenses**: run the two passes of the
`polaris-review` skill (`polaris-review/references/protocol.md`) on the changes since the merge-base with
main as the replacement adversarial lens — Standards (repo's documented coding standards)
and Spec (does the diff match the originating issue), each in its own fresh-context
subagent if your harness supports one, otherwise one after the other, inline. That keeps
the independence Codex was providing: a reviewer that did not write the code.

Map its findings into the same severity buckets, verify them against source like any
Codex finding, and mark provenance in the comment:

```
## Codex adversarial

- ⚠️ **Codex not-run** — <one line: timed out after N min / zero output / CLI unavailable>.
  Lens replaced by the Standards + Spec fallback:
- 🔴 [High] <finding from the fallback> …
```

Record `codex: not-run (<reason>) · fallback: standards-spec` in the Phase 6 run state.
Only if the fallback ALSO fails, post the two-lenses banner: *"This review is
therefore two lenses, not three. Treat the finding list as unverified-complete, not
exhaustive"* — a degraded review that says so is useful; one that silently looks
complete is worse than none.

### Phase 3e — Runtime attestation (the only lens that RUNS the code)

3a, 3b, 3b-bis and 3c **read**. None of them runs a single line. A PR can leave this point with
`approve` while nobody has seen the code work — which is why PRs declared real-tested exist that
are not: the review was excellent, and it was about a text.

This phase does not prove the code is good: it proves **something happened in the world**.

**It does not deploy and does not compare SHAs.** Whoever ran the real test says so: **look for
their comment on the PR.** Chasing the SHA staging serves is fragile and useless — staging moves
under your feet, and a matching commit does not prove anyone looked at anything.

```bash
gh pr view "$PR_N" --json comments -q '.comments[] | select(.body | test("(?i)real.?test|attestazione")) | .body' | head -c 3000
```

Two questions, in this order:

**1. Does this PR get deployed?** The repo already declares it, and the list **is not written
here**: it sits in the `paths:` of its post-deploy workflow, or in `deployabili:` of its
`.fix/contract.yml` (the key keeps its original name; `sweep_gate.py` reads it). Every repo has its
own. If the diff touches none of those paths — docs, specs, session contract, githooks — **no
attestation is needed**: say so and close the phase.

If the repo declares neither, do not guess: write that the deployable perimeter is not declared,
and treat the PR as needing attestation. A path list invented here would hold for one repo and
lie about every other.

**2. Is there a real-test comment?** That is, a comment stating **what was tried and where**, not
"tested ok".

| | What you write (run-state value of `attestazione`) |
|---|---|
| not needed | **not deployable** (`non-deployabile`) — no runtime path touched |
| present | **attested** (`attestata`) — one line on what it says: where it ran, what was observed, what failed |
| absent | **not attested** (`non-attestata`) — this code has never run anywhere |

**The sweep verdict does not change in this phase.** Being unattested is not a defect of the
code: it is missing work. Only auto-merge changes, in Phase 4.5.

### Phase 3d — Merge all verdicts

Final verdict = worst-of(3a quality, 3s spec-conformance, 3b security, 3c Codex adversarial).
Priority: security Critical/High > Codex Critical/High > quality.

3e **does not enter the verdict** — not being on staging is not a defect of the code. It enters
Phase 4.5, where it decides whether the PR may merge on its own.

All findings appear in their own sections in the comment (see Phase 4).

## Phase 4 — Render comment

Compose the markdown body from the exact template in `references/comment-template.md` —
read it now if you haven't. Two things are load-bearing:

- The hidden marker `<!-- polaris-sweep-id:<repo-slug>:<PR_N> -->` on the first line is
  what makes Phase 5's upsert idempotent, and the `**Verdict**: ✅ approve` line feeds the
  auto-merge GHA regex — don't restyle either.
- The **Verified clean** section is not padding: every finding is verified against the
  source before it is reported, and suspicions that DIE during verification are reported
  too, with the evidence that killed them. Without it a reviewer cannot tell "not
  mentioned" from "checked and fine". Verification rules (source on the PR branch, not
  diff hunks; library source cited `file:line`; `file:symbol` over drifting line numbers)
  are in the template file, with the precedents.

## Phase 4.5 — Auto-mergeable check (exit code, not prose)

**The review text does not make the decision: `scripts/sweep_gate.py` does.** Judgment stays
with the model; auto-merge is a fail-closed script — a verdict without a SHA, on a stale SHA,
unattested, or on a PR touching the pipeline NEVER self-merges
(`references/bypass-test.md`, B1–B3).

```bash
gh pr diff "$PR_N" --name-only > .tmp/sweep/files-$PR_N.txt
HEAD_SHA=$(gh pr view "$PR_N" --json headRefOid -q .headRefOid)
python3 scripts/sweep_gate.py automerge \
  --run "_polaris/sweep/runs/<repo>/pr-$PR_N.md" \
  --pr-head "$HEAD_SHA" --files ".tmp/sweep/files-$PR_N.txt" --repo <checkout>
```

Exit `0` → append the Auto-mergeable block · `1` → omit the block and report the reason (on
stderr) in the comment · `2` → usage error, the sweep fails loudly. The Phase 6 run state MUST
therefore carry `head_sha`, `attestazione` and `risk`, or the gate denies on its own.

**The policy is perimeter-based** (B4, 2026-08-17): a PR **outside the repo's declared
prod perimeter** (`deployabili:` in `.fix/contract.yml` — the same declaration Phase 3e uses)
merges **always**, with just approve + a fresh SHA: docs, tests, tooling wait for no one. The
strict path (`risk:trivial` + attestation) applies only to diffs touching `deployabili`, or when
the perimeter is **not declared** — the gate does not guess what prod is. Pipeline beats
everything: whoever touches it never self-merges.

**Inside the `deployabili` perimeter, auto-merge also requires Phase 3e's runtime
attestation.** A PR that puts code nobody has seen run into prod is exactly the defect this system
exists to close: the static review passed, and it was about a text. `risk:trivial` says the risk
is low, not that the code works. Outside the perimeter there is no runtime to prove — there the
attestation is not required, by construction.

If 3e gave **not attested** (the gate exits 1), omit the auto-merge block and write instead:

```
---

⏸️ **Not auto-mergeable** — the review is clean, but this code has never run anywhere.
Run the real test, comment here what you tried and where, and re-run the sweep.
```

If 3e gave **not deployable**, no attestation is required: auto-merge follows the normal rules.

This is not a rejection of the PR: it is the difference between "the code looks right" and "the
code worked". Only the second justifies a merge no human looks at.

If `sweep_gate.py automerge` exits `0` (approve/approve-with-minor · head_sha == PR HEAD ·
no pipeline file · and, ONLY inside the `deployabili` perimeter or with no declared perimeter,
`risk:trivial` + attestation), append the following block to the rendered body (just above the
`---` footer):

```
---

✅ **Auto-mergeable** — `risk:trivial` + Sweep approve + CI green will auto-merge via `.github/workflows/auto-merge-trivial.yml`. No human action required.
```

A `request-changes` verdict never auto-merges. Other risk levels (`risk:low/medium/high`) block
only diffs inside `deployabili` (or with no declared perimeter): there the PR stays in
`afk:done-pending-merge` awaiting human merge.

## Phase 5 — Upsert comment

```bash
/usr/local/bin/sweep-comment-upsert.sh "$PR_N" "$BODY"
```

**That script does not exist outside the unattended agent's container** (confirmed absent on
a developer machine, 2026-07-26). Check for it, and fall back to `gh api` inline — the
marker is what makes it idempotent, not the script:

```bash
R="<owner/repo>"; B=<path-to-rendered-body.md>
ID=$(gh api "repos/$R/issues/$PR_N/comments" --paginate \
       --jq ".[] | select(.body | contains(\"polaris-sweep-id:<repo-slug>:$PR_N\")) | .id" | head -1)
if [ -n "$ID" ]; then
  gh api -X PATCH "repos/$R/issues/comments/$ID" -F body=@"$B" --jq '.html_url'
else
  gh api -X POST  "repos/$R/issues/$PR_N/comments" -F body=@"$B" --jq '.html_url'
fi
```

Write the body to a file and pass it as `-F body=@file`. Do NOT inline a multi-KB
markdown body as a shell argument — quoting breaks on backticks and `$` in code spans.

## Phase 6 — Persist run state

Write `_polaris/sweep/runs/<repo>/pr-<PR_N>.md` with frontmatter:
`verdict, severity, head_sha, risk, attestazione, comment_id, ran_at` (+ `codex: not-run (<reason>)
· fallback: standards-spec` when Phase 3c degraded). `head_sha`, `risk` and `attestazione` are not
optional: they are what `sweep_gate.py` decides on — a run state without them (like the pre-v1
ones) gets denied by the gate, it does not slip past it.

## Failure modes
- API failure: retry once, then fail loud.
- Diff too large (>50k lines): summarize files-changed only, mark "diff too large for full review".
- Hand-non-authored PR: skip silently (not Sweep's territory).

## When not to use it — what this skill does NOT do
- Approve/merge PRs (apply lane is GitHub Action / human).
- Close PRs.
- Comment on issues (only PRs).
- **Deploy anything.** Phase 3e observes whether someone put the PR on staging; it does not put
  it there. Staging is shared and changes only when a human says so — automating that step here
  would change the version under whoever is testing on it.
- **Reject a PR because it is not on staging.** "Nobody deployed it" is not evidence of a
  regression: treating it as one has already opened three revert PRs against healthy code. It
  blocks only auto-merge, which is a different thing.
