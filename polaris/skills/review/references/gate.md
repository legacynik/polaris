---
title: review — the approval gate (mechanism, portability, sweep mode)
description: How the content-addressed approval and the PreToolUse hook block a commit or merge with no matching review. Moved from SKILL.md 1.2.0 unchanged in substance.
status: active
---

# The approval gate

## What it keeps from the gate it replaces

A content-addressed approval checked by a hook, now on every branch (including `main`), with no
bypass variable, and JSON parsed with `python3`'s stdlib only (a `sed -E \s` parser never matches on
BSD sed, so the old gate never blocked on macOS). The two axes stay separate, Standards and Spec,
never one ranking; Standards findings use the CRITICAL/INFORMATIONAL checklist shape.

## When NOT to use

- **Not a substitute for `real-testing`.** This reads the diff; `real-testing` executes the real
  perimeter. A PASS here says "the code looks right," not "it runs right" — both gates are
  required, neither implies the other.
- **Not for a genuinely trivial change**: docs-only or comment-only diffs touching zero
  `.py`/`.ts`/`.go`/`.sql`/config/CI files can skip straight to `finalize_review.py` with two
  empty findings files (`scan_blockers` still runs — an "docs-only" commit that happens to add
  an untracked secret file still blocks). This is a declared fast path, not a judgment call at
  review time.
- **Not for post-merge incidents.** A vulnerability found in production after merge is
  a production-monitoring finding, not this gate re-run backwards — see G9.1 below for
  why Sweep instead runs this SAME skill pre-merge, not a lighter one.
- **Not a substitute for branch protection.** This blocks the *local* `git commit`/`gh pr
  merge` invocation. A merge performed through the GitHub UI or API directly bypasses a local
  hook entirely — pair with required-status-checks on the remote (out of scope for this job;
  out of scope here).

## Mechanism

1. **Perimeter**: `git diff --staged` **and** `git status --porcelain` for untracked files.
   G9.1's command-injection case lived in a file git never tracked — a diff-only gate
   structurally cannot see it, so this gate never relies on diff alone.
2. **Key**: `git write-tree` on the staged index. This hash IS the approval file's name.
   Content-addressed, not positional — restage anything and the old approval stops matching,
   automatically, with no separate staleness check to maintain.
3. **Reviewer tier, from the diff.** Before dispatching anything, run
   `python3 scripts/review_tier.py --staged` (or `--base <ref>` for a branch or PR). It prints
   `TIER 1|2|3`, the reason (size, file count, or the first risk path: auth/permissions,
   money/pricing, data/schema/migrations, security, concurrency, or the repository's own
   `review.risk_paths` regex in `_polaris/config.yml`) and `codex: available|missing`. The tier
   picks the reviewers of step 4, never a judgement call:
   - **Tier 1** (small mechanical diff, no risk path) → the harness's light, fast model.
   - **Tier 2** (normal diff) → the strongest model the harness has.
   - **Tier 3** (risk path or very large diff) → tier 2, plus the second opinion
     (`references/second-opinion.md`): another model family's CLI on the same diff, each
     **verified** finding added to the Standards file (critical/high → `CRITICAL`, medium/low →
     `INFORMATIONAL`, the cited source line as `evidence`, `"source": "second-opinion:<cli>"`);
     with no such CLI, or `SECOND-OPINION: not-run`, a second fresh reviewer on a different
     model than the first, declared in both findings files as `second_reviewer: <model>`.
   Done when the tier line and the chosen reviewers are written at the top of the review.
4. **One audit from isolated context, two findings files** (SKILL.md step 3; a second
   reviewer, when tier 3 calls for one, never sees the first one's findings before it finishes)
   (a fresh-context subagent if your harness supports one, otherwise an equivalent isolated
   sub-session — the isolation is the requirement, the mechanism is harness-specific). **Before dispatching
   the audit**, run `scripts/finalize_review.py --print-scope --cwd .` once and hand its
   output to both — each findings file must embed it verbatim as `scope`:
   - **Standards** — repo conventions + the fixed baseline in `references/protocol.md`
     (SQL safety, LLM trust boundary, command injection, race conditions, money-path,
     mock-only tests, secrets). Every CRITICAL/INFORMATIONAL finding needs `file`, `line`,
     `severity`, one quoted `evidence` line — unquoted findings fail validation, they are not
     silently dropped or silently trusted (closes G2.7's evidence half: a reviewer that can
     assert without evidence is the broken judge this gate exists to stop).
   - **Spec** — does the diff match what the issue/plan asked (scope, traceability,
     acceptance criteria, undisclosed decisions). See `references/protocol.md`.
   Write each pass to `.review-gate/findings/<hash>-standards.json` /
   `.review-gate/findings/<hash>-spec.json` (schema in `references/protocol.md`). An
   `scope` that doesn't match what's actually staged — including an empty `findings: []`
   with no `scope` at all — is rejected the same way missing `evidence` is (closes G2.7's
   other reproduced half: two empty JSON files typed by hand, zero relation to the diff,
   used to pass as "reviewed, clean" — bypass-test case 3a). This does not prove either
   pass reasoned about the diff's meaning, only that it knew what was staged.
5. **`scripts/finalize_review.py <standards.json> <spec.json>`** — never trusts a hash you
   hand it, recomputes `git write-tree` itself, and re-validates findings structure + scope
   inside `decide_verdict` itself, not only in a CLI-only loader — a caller that imports this
   module and drives `decide_verdict`/`write_approval` directly is gated exactly like the CLI
   (bypass-test case 3b: previously only reachable through `main()`). Runs
   `scan_blockers.py`'s two mechanical scans before deciding anything: money-path changed
   with no test companion **correlated to that specific file** (G3.7 — an unrelated test
   elsewhere in the changeset no longer satisfies this), and untracked files matching a
   broadened secret/injection pattern set — AWS keys, PEM blocks, JWTs, generic
   `*_KEY=`/`*_TOKEN=`/`*_SECRET=` assignments, `os.popen`/`eval`/`exec`/`shell=True` (G9.1).
   Writes `.review-gate/approvals/<hash>.json`:
   - `PASS` — nothing found.
   - `PASS-WITH-WAIVER` — something was found and explicitly waived
     (`--waive ID:approver:reason`, `ID` = `file:line` or `MONEY-PATH`); the waiver is
     recorded in the approval file, never silent.
   - `FAIL` — anything unwaived. **Still written to disk**, with reasons — the only case
     that writes nothing at all is a hash-computation or structural-validation failure (not a
     git repo, missing evidence, bad severity, or a `scope` that doesn't match the real
     diff), because there's no key/no trustworthy content to file it under. No path in this
     script defaults to PASS when it can't tell (the same failure this
     job's own gate must not reproduce).
6. **`scripts/gate_hook.py`** — wired as `PreToolUse` in `settings.json`. Gates ANY tool
   whose input carries a `command`/`cmd`/`script` string, not only `tool_name == "Bash"` —
   closes a non-Bash shell-capable tool (e.g. an MCP `execute_shell_command`) carrying the
   identical command and reaching neither check (bypass-test case 3g). Command
   detection is word-set, not adjacency-regex: `git`+`commit` (or `gh`+`pr`+`merge`) need
   only both appear as whole words anywhere in the command — closes a config flag between the
   words, shell-variable indirection, and a `gh` flag before the subcommand (3c/3d/3f); a
   command embedded verbatim in another interpreter's argv is caught the same way, since the
   quoted `'git'`/`'commit'` tokens still read as whole words (3e). On a targeted command:
   recompute the tree hash **now**, load the approval for that exact hash, verify its
   `findings_digest` still matches the two findings files it names (a hand-written
   `{"verdict":"PASS"}` has no real digest to match — closes G2.5, "the merge wall is
   self-reported discipline"). Verdict `PASS`/`PASS-WITH-WAIVER` + digest match → exit 0.
   Anything else → exit 2, one-line reason on stderr (tutor: names exactly what's missing or
   mismatched, not just "blocked"). Still text-based: an obfuscator with no literal
   "git"/"commit" word anywhere in the command string (base64, dynamic argv construction with
   no gated word in the invocation itself) is not caught — closing that needs shell execution
   tracing, out of scope for a hook that must decide in milliseconds; declared, not hidden,
   in `references/bypass-test.md`.

## Portability (4 harnesses)

`gate_hook.py` and `finalize_review.py` are pure stdlib Python reading/writing JSON and
calling `git` — nothing Claude-Code-specific in the scripts themselves. What differs per
harness is only the **wiring**, because each has a different name/shape for "intercept this
shell command before it runs":
- **Claude Code**: `PreToolUse` hook on `Bash` in `settings.json` (shown above) — verified.
- **Codex / Hermes / Pi**: no equivalent hook config was found or verified in this pass (same
  gap CRITIC-1 flagged for this cluster) — the fallback that needs no hook support at all is a
  `pre-commit`/`pre-push` git hook calling `gate_hook.py` directly with a synthesized
  `{"tool_name":"Bash","tool_input":{"command":"git commit"},"cwd":"<repo>"}` payload; untested
  on those three harnesses, flagged here rather than asserted working.

## Dual-mode — Sweep

Same skill, cron trigger instead of a human prompt. CRITICAL/HIGH findings still **block**
the merge attempt through the same `gate_hook.py` — G9.1's second case (a Sweep-found
vulnerability landed only as a post-merge comment, never a blocking pre-merge check) is
closed by running this exact pipeline pre-merge in cron mode, not a separate lighter one.

## Rationalizations this gate is built to survive

| Excuse | Why it doesn't work here |
|---|---|
| "I already reviewed it by hand, just write PASS" | `gate_hook.py` requires the approval's `findings_digest` to match real findings files on disk — a hand-written verdict has none (bypass-test case 2/3) |
| "It's a tiny fix, skip the gate" | the fast path is a declared, path-bounded rule the reviewer applies at findings-time, not an env var or a skipped script |
| "Sweep already commented that it looks fine" | a PR comment isn't `.review-gate/approvals/<hash>.json`; only that file with a passing verdict unblocks the hook |
| "The findings file exists, that's enough" | `finalize_review.py` validates structure — missing `evidence`, wrong `axis`, or an unrecognized `severity` aborts the whole run, nothing is written |
| "Use `PARALLEL_FLOW_BYPASS_GATE=1` like before" | `gate_hook.py` reads no bypass variable — there is nothing to set (bypass-test case 6) |

## Quick reference

```bash
python3 scripts/finalize_review.py <standards.json> <spec.json> [--waive ID:approver:reason]
python3 scripts/finalize_review.py --prune-older-than 14        # lifecycle drain
python3 scripts/scan_blockers.py --cwd .                        # standalone scan, JSON out
python3 scripts/gate_hook.py --selfcheck                        # 7 branches
python3 scripts/finalize_review.py --selfcheck                  # verdict logic + real git
python3 scripts/scan_blockers.py --selfcheck                    # the 3 scans
python3 scripts/review_tier.py --staged                         # the reviewer tier and why
python3 scripts/review_tier.py --selfcheck
```
Full JSON schemas and the baseline checklist: `references/protocol.md`.
Adversarial reproduction that must fail to bypass: `references/bypass-test.md`.

