---
name: review
description: "◇ Polaris — The audit of a change on six axes: tests prove behaviour, no drift from governing decisions, constraints kept, the plan's DoD met (no less, no more), simplicity and reuse, security. Use on the whole diff before ship, or before a commit or merge; second-opinion mode asks another model family. Requires git, python3, bd; gh for PRs. Reads code; never runs or merges it."
version: 2.1.1
user-invocable: true
auto: true
lifecycle: ".review-gate/approvals/<hash>.json drained once by gate_hook.py at commit/merge time, gitignored, pruned by `finalize_review.py --prune-older-than N`; .review-gate/findings/<hash>-*.json kept as the audit trail until the same prune; structural findings live on as beads (src:review) until closed."
invokes: []
invoked-by: [human, ship, sweep, implement-plan]
io: "takes a staged diff, a phase diff or a branch/PR -> mechanical fixes applied and listed, structural findings as beads blocking the phase, taste findings as advice, and .review-gate/approvals/<hash>.json checked by a pre-commit hook"
status: active
---

# review

## What it does

The audit of a change. A fresh-context reviewer reads the diff on six axes (`references/axes.md`):
**tests** prove behaviour, not implementation · no **architecture** drift from the decisions
governing the touched code · **constraints** respected · **plan** adherence, the phase DoD and no
more · **simplicity** and reuse · **security**. Each finding is sorted: mechanical (fixed and
listed), structural (a bead that blocks the phase), taste (advisory, never blocks). An approval
bound to the tree hash lets a hook refuse a commit or merge nobody reviewed.

## When

- Once on the whole branch inside `ship`; it replaces separate simplification and security passes.
- By hand before any commit or merge, and on a PR someone asks you to review.
- Second opinion: tier 3 (a risk path or a very large diff), or when asked.

## Steps

1. **Tier and scope.** `python3 scripts/review_tier.py --staged` (or `--base <ref>`) prints the
   tier and why; `python3 scripts/finalize_review.py --print-scope --cwd .` prints the scope.
2. **Gather the yardsticks.** The phase DoD (plan file §6, phase bead) or the issue acceptance;
   the decisions governing the touched paths (`check_context_backbone.py --check` where the repo
   has it); `CONSTRAINTS.md`, `.claude/rules/`, LOCKED rules in `AGENTS.md`; the RED record of
   the new tests; for `tests`, `tdd-dev` → *How tests are written*: a test of a name, path, file
   text, wording or config value is structural. Ask the agent memory (`ai-memory-retrieval`) for
   past findings on these paths; skip if absent.
3. **Audit from fresh context.** A fresh-context agent from your harness: a light, fast model on
   tier 1, the strongest it has on tiers 2–3. It gets the diff, the scope and the yardsticks,
   never the author's session. Every finding: `lens`, file, line, quoted evidence.
4. **Sort and act.** Mechanical: apply, re-stage, list under `fixed`. Structural: one bead each,
   `bd create … -l src:review,kind:finding,area:<a> --parent <epic>
   --deps discovered-from:<phase>,blocks:<phase>`, marked `CRITICAL`. Taste: `INFORMATIONAL`. In doubt, structural.
5. **Second opinion** (tier 3 or asked): another model family's CLI, read-only, every finding
   verified against the source (`references/second-opinion.md`). No such CLI: a second fresh
   reviewer on a different model, declared as `second_reviewer`.
6. **Approve.** `plan` findings to `.review-gate/findings/<hash>-spec.json`, the other five
   axes to `<hash>-standards.json` (`references/protocol.md`), then
   `python3 scripts/finalize_review.py <standards> <spec>`. `gate_hook.py`, wired as the
   harness's pre-tool hook or a git hook, blocks a commit or merge with no matching approval
   (`references/gate.md`).

## Output

- `.review-gate/approvals/<hash>.json`: `PASS`, `PASS-WITH-WAIVER` or `FAIL`.
- A summary per axis: fixed, blocking (bead ids), advisory. The phase stays open while a
  `src:review` bead is open.
- **Next:** blocking → back to `implement-plan` or the author; PASS → the caller goes on (phase close or `ship`).

## Where this goes

This skill produces: **review** — at the path the host's `outputs:` map (`_polaris/config.yml`
or `config.yml`) gives that kind; with no map, say once where you wrote.

## Not for

- Running the code: `real-testing`. Attacking a plan, a decision record or a claim: `critic`.
- Deciding or performing the merge: `ship`.
- A docs-only diff: two empty findings files carrying the scope; `scan_blockers` still runs.
