---
name: git-power
description: ◇ Polaris — Use before any Git commit or PR boundary and before any destructive Git action. MUST invoke for every `reset --hard` and every pre-PR comparison of a branch against origin/main; never substitute raw Git. Also censuses and safely closes worktrees, branches, stashes and PRs. Triggers on commit hygiene, PR too large, stale branches. Requires git, gh and python 3.
version: 0.7.4
user-invocable: true
auto: false
status: active
lifecycle: the phase router emits no durable artifact; census JSON is regenerated live; destructive receipts live under the shared Git common dir at polaris-cantiere/removed-log.jsonl so cleanup never dirties main
invokes: []
invoked-by: [issue-contract, bugfix, ship, end, human, real-testing]
io: phase + live git/gh state -> one deterministic verdict or guarded action; no transcript and no full-workflow context
---

# git-power

## What it does

One door for Git state: five lifecycle phases plus a few guarded operations, all in
`scripts/cantiere.py`. Run only the phase matching the event; never replay the whole workflow.
"Merged" is what `gh pr view` says, never `git branch --merged` (blind to squash merges).

## When

| Event | Command (`GP=<skill-dir>/scripts/cantiere.py`) | Contract |
|---|---|---|
| a checkpoint landed | `python3 "$GP" phase checkpoint --repo <wt>` | exit 0 only on a clean tree |
| branch ready for a PR | `python3 "$GP" phase pre-pr --repo <wt>` | measures `origin/<default>...HEAD`; exit 3 = split or justify |
| pre-PR passed | `python3 "$GP" phase push --repo <wt>` | pushes; creates the upstream when missing |
| push completed | `python3 "$GP" phase post-push --repo <wt>` | OPEN PR = keep; MERGED = ready to finalize |
| PR merged, or the task ends | `python3 "$GP" phase finalize --repo <wt> --confirm <same-path>` | proves the merge, closes worktree and branch, aligns main only when safe |

## Steps

1. Pick the row above for the event and run its command from the worktree it concerns.
2. No phase fits → one guarded operation, one target per call:
   `commit-check --repo <p> [--base origin/main]` · `census --repo <p> [--tsv] [--apply]` ·
   `gate --repo <p> [--threshold N]` · `close --repo <p> --target <item> --confirm <same-item>` ·
   `reset-hard --repo <p> --to <ref> --confirm <same-ref>`.
3. Read the exit code as the verdict. A refusal (dirty tree, open merge or rebase, unmerged
   branch, recent activity of an unknown panel) is reported as it is; there is no force flag.
4. `finalize` acts only when GitHub says MERGED, the PR head equals the branch and the merge
   commit is in `origin/<base>` after a fresh fetch. A dirty, diverged or mid-operation main is
   preserved exactly and reported. Full invariant, census verdicts and `--apply`:
   `references/phases.md`.

## Output

One deterministic verdict or one guarded action per call, with its exit code; destructive
receipts in `polaris-cantiere/removed-log.jsonl` under the Git common dir. Proof:
`python3 "$GP" --selfcheck` and `references/bypass-test.md`.

## Not for

- Merge or deploy policy: that is the repository's merge workflow (`ship`); git-power owns Git
  state and post-merge convergence.
- Judging whether a commit is semantically atomic: size is a signal, not proof.
- Resolving conflicts or creating feature worktrees.
- Raw `git` typed outside this tool: it is not intercepted; callers invoke the exact phase.
