---
title: bypass-test — git-power
description: The tests that must fail if someone bypasses the commit boundary or the guided-close gate.
---

# Bypass-test

Six scenarios: three taken **verbatim** from a registry entry (G7#2, G8#2) or from the near-miss
measured on the repo, three added after the adversarial attack of 2026-08-09
(verdict WEAK on the side paths L1/L3, DOES-NOT-COVER on `reset --hard`/`.method`). Each has the runnable command and what MUST
happen. If a command below behaves differently from what is written, the skill is not
hardened — do not promote it.

**Runnable in one shot**: `python3 ../scripts/cantiere.py --selfcheck` — it builds each of
these six scenarios (plus three more: a merge-safe that closes correctly, a lock from recent activity
true/false, an orphan branch never force-deleted) on **real** git repos in a temporary folder,
not mocks. Exit 0 only if all 9 behave as declared here.

## 1 — Worktree with uncommitted changes (registry G7#2)

> "asking to close a worktree with uncommitted changes — the skill must refuse and
> show `git status`, not propose `--force`."

```bash
tmp=$(mktemp -d) && cd "$tmp"
git init -q -b main repo && cd repo
git config user.email t@t.t && git config user.name t
echo 1 > f.txt && git add . && git commit -q -m init
git worktree add -q -b feat/dirty ../wt-dirty
echo uncommitted > ../wt-dirty/f.txt

python3 /path/to/cantiere/scripts/cantiere.py close --repo "$tmp/repo" \
  --target "$tmp/wt-dirty" --confirm "$tmp/wt-dirty"
echo "EXIT=$?"                      # DEVE essere 2, mai 0
git worktree list | grep wt-dirty   # DEVE ancora esistere
```

**Must happen**: `EXIT=2`, the printed text includes the real output of `git status` (not a
generic message), the worktree stays on disk. **Must not happen**: no printed or executed
line contains `--force`; also verified statically — `scripts/cantiere.py` contains
NOT ONE real `git()` call with `--force` or `-D` as a literal argument (AST walk, not a surface
grep: see `_assert_no_force_call_sites` in the selfcheck, so as not to be fooled by a
comment that TALKS about it).

## 2 — Stash during a merge with an unresolved conflict (registry G8#2)

> "working tree with 1 modified uncommitted file + fake merge in progress → `git stash` must
> exit with a blocking error, not silent success; verify that `.git/MERGE_HEAD`
> survives the attempt."

```bash
# a repo with a pre-existing stash AND THEN a merge that conflicts (never create the stash
# DURING the conflict to build the test: that is exactly the dangerous command)
tmp=$(mktemp -d) && cd "$tmp" && git init -q -b main repo && cd repo
git config user.email t@t.t && git config user.name t
echo x > g.txt && git add g.txt && git commit -q -m g
echo y > g.txt && git stash push -q -m unrelated

git checkout -q -b a && echo A > f.txt 2>/dev/null; : # abbreviated setup, see the selfcheck for the real one
# ... (the selfcheck builds the real conflict: two branches editing the same line)

python3 /path/to/cantiere/scripts/cantiere.py close --repo "$tmp/repo" \
  --target "stash@{0}" --confirm "stash@{0}"
echo "EXIT=$?"                       # MUST be 2
test -f .git/MERGE_HEAD && echo "MERGE_HEAD survives"   # MUST print
git stash list | grep 'stash@{0}'    # MUST still exist
```

**Must happen**: `EXIT=2`, `.git/MERGE_HEAD` intact, the stash NOT touched — even if the
stash itself has nothing to do with the merge (it is "unrelated"): the rule is unconditional while the
repo is mid-merge, because it is the only way not to trust which stash is "harmless".

## 3 — Concurrent activity detected (real near-miss)

> *"The agent that was measuring acme-api caught, during the measurement, a `git pull --rebase`
> launched by another panel... for a few seconds `git ls-files` returned a
> pre-migration tree."*

```bash
tmp=$(mktemp -d) && git -C "$tmp" init -q -b main
git -C "$tmp" config user.email t@t.t && git -C "$tmp" config user.name t
echo 1 > "$tmp/f.txt" && git -C "$tmp" add . && git -C "$tmp" commit -q -m init
# .git/HEAD was just written by the commit — simulates a panel operating RIGHT NOW
python3 -c "
import sys; sys.path.insert(0, '/path/to/cantiere/scripts')
import cantiere, pathlib
print(cantiere.recent_activity_lock(pathlib.Path('$tmp')))"
# MUST print True right after a commit; False if rerun after 180s
```

**Must happen**: `census`/`close` classify the worktree `pericoloso` with the note
"attività concorrente rilevata" until `HEAD` has been still for >180s — no action proposed in
that window, regardless of how "clean" the git state looks.

## 4 — Direct call to the function, not the CLI (bypass-eval L1)

> "the direct call to the function must be gated as much as the CLI — it is the real hole found
> in the corpus (a gate that fires only via `main()`)."

Before this fix, `import cantiere; cantiere.git(repo, "worktree", "remove", "--force", str(wt))`
removed a dirty worktree **without going through `close_worktree`**, because the guard lived only
in the wrappers, not in the `git()` primitive. Reproducible outside the selfcheck:

```bash
tmp=$(mktemp -d) && git -C "$tmp" init -q -b main
git -C "$tmp" config user.email t@t.t && git -C "$tmp" config user.name t
echo 1 > "$tmp/f.txt" && git -C "$tmp" add . && git -C "$tmp" -c user.email=t@t.t -c user.name=t commit -q -m init
git -C "$tmp" worktree add -q -b feat/dirty-direct "$tmp/../wt-direct"
echo uncommitted > "$tmp/../wt-direct/f.txt"

python3 -c "
import sys; sys.path.insert(0, '/path/to/cantiere/scripts')
import cantiere, pathlib
repo = pathlib.Path('$tmp')
wt = repo.parent / 'wt-direct'
try:
    cantiere.git(repo, 'worktree', 'remove', '--force', str(wt))
    print('BYPASS RIUSCITO')
except cantiere.Refused as e:
    print('RIFIUTATO:', e)
"
```

**Must happen**: `cantiere.Refused` raised by `git()` itself, the worktree stays on disk.
**Must not happen**: no exception, the worktree disappears. The same test covers `-D` on an
unmerged branch, `reset --hard` on a dirty tree, and `stash clear` — all refused by the
same primitive, not by a wrapper the caller can skip. Selfcheck:
`_selfcheck_direct_git_call_still_refuses`.

## 5 — `.method/ledger.md` open

> "`cantiere` drains/removes [ledger.md + .polaris-owner] when the worktree or branch closes" —
> declared by `method/SKILL.md`, never implemented before this fix.

```bash
tmp=$(mktemp -d) && cd "$tmp" && git init -q -b main repo && cd repo
git config user.email t@t.t && git config user.name t
echo ".method/" >> .git/info/exclude
echo 1 > f.txt && git add . && git commit -q -m init
git worktree add -q -b feat/x ../wt
mkdir -p ../wt/.method && printf 'PLAN: p\nTASK 1: started\n' > ../wt/.method/ledger.md

git -C ../wt status --porcelain   # DEVE essere vuoto: .method è ignorato, non è "sporco"
python3 /path/to/cantiere/scripts/cantiere.py close --repo "$tmp/repo" \
  --target "$tmp/wt" --confirm "$tmp/wt"
echo "EXIT=$?"                    # DEVE essere 2, non 0 — anche se git status non vede nulla
```

**Must happen**: `EXIT=2` even though `git status` is clean — the guard reads the ledger, not
only `git status`. **Note on manual reproduction**: the command above ALSO refuses because of
`recent_activity_lock` (the worktree was just created, <180s ago) — to isolate the `.method`
gate alone with `TASK 1: complete` and see `EXIT=0`, you need to backdate the worktree's `.git/HEAD`
past 180s (`_age_head()` does it in the selfcheck, not reproducible by hand in a few lines). The half
that matters for safety — the refusal when the plan is open — is the one above, reproducible
right away. **Declared limit**: it does not distinguish the plan's owner from whoever calls `close` —
it blocks for any open plan, not only another panel's. Full selfcheck
(both directions, controlled mtime): `_selfcheck_method_ledger_blocks_close`.

## 6 — guarded `reset --hard` (the description declared it, 0 lines implemented it)

```bash
tmp=$(mktemp -d) && git -C "$tmp" init -q -b main
git -C "$tmp" config user.email t@t.t && git -C "$tmp" config user.name t
echo 1 > "$tmp/f.txt" && git -C "$tmp" add . && git -C "$tmp" commit -q -m init
echo dirty > "$tmp/f.txt"   # non committato — il tree che l'incidente 2026-08-03 perdeva

python3 /path/to/cantiere/scripts/cantiere.py reset-hard --repo "$tmp" --to HEAD --confirm HEAD
echo "EXIT=$?"              # DEVE essere 2
cat "$tmp/f.txt"             # DEVE mostrare ancora 'dirty' — nessuna perdita
```

**Must happen**: `EXIT=2`, the uncommitted content survives, `git status` is shown.
On a clean tree the same command performs the reset and logs `ORIG_HEAD` in the Git common dir,
`polaris-cantiere/removed-log.jsonl`, before anything is lost, without dirtying main. Selfcheck:
`_selfcheck_reset_hard_guarded`.

## 7 — Staged commit beyond the boundary

`scripts/test/test_git_power.py` builds a real repo: 5 staged files must give `OK`/exit 0;
the sixth must give `CONCERN`/exit 3 with exact counts. The test goes through the public CLI, it does not
call the function directly. A binary file is always `CONCERN`, because `--numstat` cannot
prove its line count.

## 8 — Lifecycle: remote merge, dirty main, cleanup

`scripts/test/test_git_power.py` creates a bare origin, a stale and dirty local main, a clean
feature worktree and a `MERGED` PR simulated at the public `gh` boundary. `phase finalize` must prove
that the merge commit is in `origin/main`, preserve the untracked file on main, remove the
worktree and delete the branch with compare-and-delete on the exact SHA. The same module proves
that `post-push` keeps an OPEN PR and that `close` refuses a clean but unmerged worktree.

The same `--selfcheck`, calling the `git()` primitive directly, also proves the incident-class
commands: `clean -fd`, `checkout --`, `restore --worktree` and `stash push` on a dirty
tree must raise `Refused` and leave tracked/untracked files intact.

## Honesty about the limit

Case 3 is a **mechanical proxy** (recency), not true ownership-by-provenance: if another
panel wrote >180s ago and then stopped without committing (e.g. it is still editing a file
without saving), this tool does not see it — it sees only `git status` (dirty → `pericoloso` for
another reason) or nothing (if the file is untracked and not yet modified). It is not a silent
hole: it is declared here and in `SKILL.md` §Meccanismo, not hidden behind "provenance"
as if it were solved.

**Limit not closed, declared on purpose (bypass-eval L2)**: nothing above intercepts a
`git reset --hard`/`git stash`/`git worktree remove --force` typed **outside** this tool —
no harness has a `PreToolUse` hook that redirects it here today. The guard is real for whoever
invokes it (CLI or direct function, §4 above); it is not an automatic interception of an
arbitrary shell command. Building that hook touches `~/.claude/settings.json`, shared by all the
repo owner's parallel panels — out of scope for a fix to this bundle, by explicit choice, not by
omission.
