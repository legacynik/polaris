---
name: review
description: ◇ Legge il diff come un reviewer senior, cioè cosa ti farebbe rifiutare l'approvazione. Two axes kept separate, Standards (this repo's documented conventions) and Specification (what the originating issue actually asked for). Use before any git commit or gh pr merge, or to get the code-quality blockers on a branch before it goes further. It reads the code; it never runs it and never merges it.
version: 1.0.2
user-invocable: true
auto: true
lifecycle: ".review-gate/approvals/<hash>.json drained once by gate_hook.py at commit/merge time, gitignored, pruned by `finalize_review.py --prune-older-than N`; .review-gate/findings/<hash>-*.json kept as the audit trail for doc-truth/human review until the same prune."
invokes: [critic]
invoked-by: [human]
io: "riceve: diff staged (git tree hash) o branch/PR indicati a mano. produce: .review-gate/approvals/<hash>.json consumato da un hook PreToolUse reale; due file di findings Standards/Spec separati, mai fusi in un ranking unico."
status: draft
---

# review

## Where this goes (host repository decides)

A skill decides **how** to produce a document, never **where** it lives. Before writing any spec,
plan, audit, review, validation receipt or diagram, read the host repository's output map and use
it; a document that lands where the repository does not look was never written.

```bash
sed -n '/^outputs:/,/^[^ ]/p' _polaris/config.yml 2>/dev/null || sed -n '/^outputs:/,/^[^ ]/p' config.yml
```

This skill produces: **review (the two-axis verdict)**. Kinds: `spec` `plan` `audit` `review` `validation` `diagram` `decision` `archive` — each maps to a
documentation area `docs/modules/<area>/…` whose README is a generated map. Never invent a third
location; if the repository declares no map, say once where you wrote and why.

Pre-merge review gate. Two isolated-context passes — Standards, Spec — that never merge into
one ranking, ending in a content-addressed approval file that a real `PreToolUse` hook checks
before `git commit` / `gh pr merge` is allowed to run. No matching approval for the tree
you're about to commit = blocked, not "please remember to review this."

**What this closes, precisely:** the *local* half of the merge wall
(a hand-written or stale approval can no longer pass; remote branch protection is the other
half, not built here); an empty or unscoped findings file passing as "reviewed, clean" (it does
not prove genuine reasoning happened, which no script can decide); and it tightens the
money-path check (the companion test must correlate to the changed money-path file) and the
secret/injection patterns, without a production-side scheduled scan, which is out of scope.
A test that hits the real system is `real-testing`'s job, not this gate's.

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
3. **Two passes, dispatched with isolated context, findings never shared before both finish**
   (a fresh-context subagent if your harness supports one, otherwise an equivalent isolated
   sub-session — the isolation is the requirement, the mechanism is harness-specific). **Before dispatching
   either pass**, run `scripts/finalize_review.py --print-scope --cwd .` once and hand its
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
4. **`scripts/finalize_review.py <standards.json> <spec.json>`** — never trusts a hash you
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
5. **`scripts/gate_hook.py`** — wired as `PreToolUse` in `settings.json`. Gates ANY tool
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
```
Full JSON schemas and the baseline checklist: `references/protocol.md`.
Adversarial reproduction that must fail to bypass: `references/bypass-test.md`.

## What this job does NOT do

Doesn't run the code (`real-testing`'s job), doesn't decide *when* to merge (the repository's merge workflow),
doesn't scan production or the live server, doesn't touch remote branch protection settings. It produces one artifact — the approval — that those
jobs read or that blocks a local commit/merge attempt directly.
