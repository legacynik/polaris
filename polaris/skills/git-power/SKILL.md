---
name: git-power
description: ◇ Use before any Git commit or PR boundary and before any destructive Git action. MUST invoke for every `reset --hard` and every pre-PR comparison of a branch against origin/main; never substitute raw Git. Also censuses and safely closes worktrees, branches, stashes and PRs. Triggers on commit hygiene, PR too large, stale branches.
version: 0.5.2
user-invocable: true
auto: false
status: active
lifecycle: the phase router emits no durable artifact; census JSON is regenerated live; destructive receipts live under the shared Git common dir at polaris-cantiere/removed-log.jsonl so cleanup never dirties main
invokes: []
invoked-by: [update, issue-contract, bugfix, start, end, human esplicito, real-testing]
io: phase + live git/gh state -> one deterministic verdict or guarded action; no transcript and no full-workflow context
---

# git-power

One door, five lifecycle phases. Run only the phase matching the event; do not replay the whole
workflow. The implementation stays in `scripts/cantiere.py`, outside prompt context.

| Event | Command | Contract |
|---|---|---|
| `/update` landed a checkpoint | `phase checkpoint` | exit 0 only on a clean tree; dirty means update is incomplete |
| branch is ready for PR | `phase pre-pr` | measure `origin/<default>...HEAD`; exit 3 means split or justify |
| pre-PR boundary passed | `phase push` | push the feature branch; create its upstream when missing |
| push completed | `phase post-push` | OPEN PR = keep; MERGED PR = ready to finalize |
| PR merged or task/session ends | `phase finalize` | prove remote merge, close worktree+branch, prune, align main only when safe |

```bash
GP="<git-power>/scripts/cantiere.py"
python3 "$GP" phase checkpoint --repo <current-worktree>
python3 "$GP" phase pre-pr --repo <current-worktree>
python3 "$GP" phase push --repo <current-worktree>
python3 "$GP" phase post-push --repo <current-worktree>
python3 "$GP" phase finalize --repo <current-worktree> --confirm <same-absolute-path>
```

## Finalize invariant

`finalize` runs from the worktree it closes and requires exact path confirmation. It acts only
when `gh pr view` says `MERGED`, the PR head equals the current branch, and GitHub's merge commit
is contained in `origin/<base>` after a fresh fetch. This supports merge commits, rebase merges,
and squash merges without trusting a stale local `main`.

The primary worktree is always handled explicitly:

- clean + behind `origin/<base>` → fast-forward;
- already aligned → no-op;
- dirty, mid-operation, on another branch, ahead, or diverged → preserve exactly and report the
  state; feature-worktree cleanup still proceeds because it does not require rewriting main.

An OPEN/CLOSED-unmerged PR is never cleanup permission. `post-push` keeps the worktree while the
PR is open; `/end` records it as paused. A merged PR is not left for a future manual sweep.

## Direct guarded operations

Use these only when no lifecycle phase applies:

```bash
python3 "$GP" commit-check --repo <path> [--base origin/main]
python3 "$GP" census --repo <path> [--vault <dir>] [--out ledger.json]
python3 "$GP" census --repo <path> --tsv [--apply]
python3 "$GP" gate --repo <path> [--threshold N]
python3 "$GP" close --repo <path> --target <item> --confirm <same-item>
python3 "$GP" reset-hard --repo <path> --to <ref> --confirm <same-ref>
python3 "$GP" --selfcheck
```

`close` is one target per call. It rereads live state and refuses dirty worktrees, open
merge/rebase/cherry-pick operations, open `.method/ledger.md` tasks, clean-but-unmerged
worktrees, unmerged branches, and recent activity belonging to an unknown panel. No force flag.

### `census --tsv` and `--apply`

Worktree rows carry a dedicated verdict vocabulary — `MAIN · PRUNABLE · IN_USE · DIRTY · ACTIVE ·
CLOSABLE · COMMITS_AFTER_MERGE · ?` — replacing the old vivo/orfano/mergiato-da-chiudere/pericoloso
labels for worktrees only (branch/stash rows keep the old vocabulary, untouched). Ground truth for
"merged" is `gh pr view <branch>` compared against the local tip, never `git branch --merged`/
`for-each-ref --merged` (squash-merge-blind — a squash-merged branch is never a local ancestor of
its base, so an ancestor-only check misreports it as ACTIVE/orfano forever). `--tsv` prints one
`VERDETTO\tbranch\tpath\tnote` line per worktree; exit 0 clean, 1 if any row is `?` (a per-row
gh/git error, not removed either way), 2 if `gh` is missing from PATH entirely — checked once, up
front, before touching anything, never falling back to the squash-blind check.

`--apply` is a **declared exception** to "no mass delete" above: it removes every CLOSABLE/PRUNABLE
worktree in one run, without a `--confirm` per item. The exception is narrow and code-gated, not a
policy relaxation — `--apply` never calls anything but `close_worktree` (the same guarded primitive
`close` uses: dirty/lock/`.method`-open/PR-truth checked, no `-D`, no `--force`) and `worktree
prune` for entries already gone from disk. DIRTY and IN_USE (a live process has its cwd inside,
via `lsof`, on top of the existing `recent_activity_lock` HEAD-mtime guard) are never in the
removed set — proven by fixture and by three-consecutive-run idempotency (`removed=N` on stderr;
0 on the second and third run). `gate --threshold N` refuses a new worktree when CLOSABLE count
`>= N`; no real number is declared yet, so the default threshold is
`None`, which never blocks — it only reports the count.

`reset-hard` is the only guarded hard reset: dirty or mid-operation means exit 2. The primitive
also refuses `--force`, `branch -D`, `clean -f`, `stash clear`, and dirty-tree discard paths
(`checkout --`, `restore --worktree`, mutating `stash`) for every internal caller.

## Quando NON usarla

- Merge/deploy policy stays with the repository's merge workflow; git-power owns Git state and post-merge convergence.
- Size is a concern signal, not proof that a commit is semantically atomic.
- It does not resolve conflicts or create feature worktrees.
- Raw `git` typed outside this tool is not intercepted. Standard workflow enforcement comes from
  callers (`update`, `end`) invoking the exact phase; bypassing those callers bypasses the
  lifecycle.

## Proof

`python3 -m unittest scripts.test.test_git_power -v` proves the public CLI, including the real
failure that motivated v0.4.0: PR merged on remote + stale dirty local main + clean feature
worktree. The feature worktree closes, the branch is deleted with an exact-SHA ref update, and
the dirty main content remains present. `references/bypass-test.md` plus `--selfcheck` cover the
lower-level destructive guards.
