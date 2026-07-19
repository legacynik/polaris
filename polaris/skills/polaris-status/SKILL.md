---
name: polaris-status
description: Polaris skill — render an explicit, comprehensive status across a portfolio or one product repository, including live Git/GitHub pulse, active outcomes, team collisions, freshness, memory health, and the highest-leverage next move. Use for "polaris status", "pol status", "status completo", cross-repo priorities, portfolio briefing, or an explicit request to see everything. Do not use for "start", "resume", "continue", session recovery, or a single implementation task — `/start` is a local resume-only workflow.
user-invocable: true
---

# /polaris-status — observe the whole system

Render an evidence-first situational view. Observe; do not mutate project state, refresh generated
files, create work, or start implementation.

Keep the boundary strict:

- `/start` restores the current outcome, latest handoff/checkpoint, blocker, and next action.
- `/polaris-status` pays the cost of network, repository pulse, portfolio aggregation, team scan,
  health, and memory only when the user explicitly asks for the full view.

## Step 1 — Select scope and resolve roots

Choose one scope:

- **Portfolio** for cross-project priorities or an explicit portfolio briefing.
- **Focused repository** when the user names a repo or asks for the current repo status.
- **Portfolio + current repo** when the user asks to see everything from a product repository.

Resolve a product repo contract from `_polaris/config.yml`. Resolve the portfolio root from
`POLARIS_HOME`; when the current repo root is itself named `_polaris` and carries `config.yml`, use
that root. If portfolio scope was requested but no portfolio root is available, say so once and
continue with the focused repo pulse when possible. Never hardcode a personal filesystem path.

## Step 2 — Read portfolio state with a bounded budget

Use the semantic index before opening documents:

```bash
python3 "$POLARIS_HOME/scripts/polaris_query_index.py" "<status topic>" --top 5
```

Read no more than the top three relevant results. Then read these control surfaces directly:

1. `POLARIS.md` — current phase, capacity, alerts, and live state.
2. `POLARIS-BOARD.md` — only Active and Building plus the highest-priority blocked item.
3. Active plan frontmatter — `status`, `deadline`, `priority`, `binding_constraint`, `serves`.
4. The most recent relevant session checkpoint when it changes the status.

Run the freshness check read-only when present:

```bash
python3 "$POLARIS_HOME/scripts/polaris_freshness_check.py"
```

Interpret exit `0` as fresh, `1` as warning, and `2` as stale. On stale data, continue with live
Git/GitHub evidence and surface the refresh action as a risk. Do not run generators, HOME builders,
update rituals, or any command that rewrites the vault while producing status.

## Step 3 — Gather live repository pulse

For each explicitly requested repo, and for the current repo in combined scope, gather bounded live
evidence:

```bash
git fetch --prune origin 2>/dev/null || echo "offline — remote view may be stale"
git log origin/main -5 --oneline
git branch -vv --sort=-committerdate | head -8
gh pr list --state open --limit 10 --json number,title,author,headRefName \
  --jq '.[] | "#\(.number) @\(.author.login) [\(.headRefName)]: \(.title)"'
```

Resolve a non-`main` default branch before reading its log. Never present a failed fetch as current
remote truth.

When the repo carries `_polaris/config.yml`, also read:

1. Current authorized weekly outcomes under `_polaris/team/*/weeks/`.
2. Latest handoff title, owner, branch, blocker, and next action under
   `_polaris/team/*/sessions/`.
3. `_polaris/state/current.md` as an open-items ledger, not shipped-work evidence.
4. At most the 10 newest entries from `_polaris/decisions.md` and `_polaris/lessons.md` when they
   explain a current mismatch.

Treat tracker and git evidence as current truth. Plans and handoffs express intent; name any
disagreement instead of reconciling it silently.

## Step 4 — Check memory and health without making them gates

Run health once in explicit full-status scope:

```bash
polmem health
```

If the command is missing, the repo is not memory-wired, or process inspection is denied by the
host sandbox, report `memory health: unavailable/degraded` with the exact reason and continue.

Read only the first screen of `.wiki/hot.md` when present. Run targeted recall only when an active
outcome, blocker, or user question provides a concrete query:

```bash
polmem recall "<active outcome or blocker>" --top 3
```

Memory is assumed context, never proof of current state. Verify current-state claims against code,
git, GitHub, or the authoritative external system.

## Step 5 — Surface only decision-grade signals

Look for:

- authorized outcome versus actual active branch/PR;
- recent shipped feature without relevant test or validation evidence;
- blocked work near a deadline;
- multiple owners or branches touching the same area;
- stale Polaris state contradicted by live evidence;
- memory or code index degraded enough to affect the requested work;
- capacity concentrated on a lower-priority repo while a nearer constraint is idle.

Do not dump every task, commit, PR, or memory result. Complete means decision-grade coverage.

## Step 5b — Alignment sweep (the heavy realignment — lives here, never in start/update/end)

The fast per-session skills stay light on purpose. This is where the expensive "keep everything
coherent" work runs, on demand — so `/polaris-status` is a **total-alignment checkpoint**: run it
weekly/when-needed and it does the analysis, holds the proof, and proposes the cleanup for a
one-confirm approval — you never mark or delete by hand.

1. **Stale-state sweep.** Resolve each `state/current.md` open thread against ground truth:

   ```bash
   python3 "$CLAUDE_PLUGIN_ROOT/polaris/scripts/state_reconcile.py" _polaris/state/current.md --repo-dir .
   ```

   It flags threads whose branch is **merged into origin/main** (superseded, proven) vs active vs
   unverified. Observe-only; it writes nothing until you confirm.

2. **Branch hygiene vs the workflow rules.** How many branches are open, and how many should close:

   ```bash
   git branch --merged origin/main | grep -vE '^\*?\s*(main|master)$'   # local branches safe to delete
   gh pr list --state open --limit 20 --json number,headRefName,updatedAt   # open PRs / their branches
   git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:relative)' refs/heads
   ```

   Surface: open-branch count, merged-but-undeleted (propose delete), and any branch idle >14d
   (`stale?`, a question not a verdict — parked work on a live branch is still work).

3. **Wiki retrieval quality.** Two independent ways a wiki degrades retrieval — surface both:

   ```bash
   python3 "$CLAUDE_PLUGIN_ROOT/polaris/scripts/wiki_quality_check.py" .wiki --max-age 45 --front-door-lag 3
   ```

   - `[archive?]` — active docs stale on BOTH the `updated:` frontmatter AND git-last-commit → real
     archive candidates (verify supersession). The ONLY wiki items that enter the confirm loop.
   - `[metadata-lag]` — `updated:` old but git-recent → a LIVE doc; propose bumping the field, NEVER
     archive (a lone age flag on a load-bearing doc is a false positive — see lessons).
   - `FRONT-DOOR STALE` — hot.md / newest journal lags the newest commit → the entry point doesn't
     reflect recent work. Root cause is the distiller not auto-running; surface it, don't archive.

4. **Propose the cleanup as ONE confirm loop, with the proof.** List the superseded threads + the
   mergeable branches + the `[archive?]` wiki docs, each with its evidence (merge SHA / PR / both-stale
   ages), and ask a single yes/no. Only on yes: `state_reconcile.py --apply` to remove the confirmed
   threads, delete the named merged branches, and set `lifecycle: archived` on the confirmed candidates.
   Never auto-delete, never archive a `[metadata-lag]` or front-door item, never touch
   active/unverified/other-panel threads.

## Step 6 — Render the briefing

Match the user's language. Keep the default response under 50 lines and omit empty sections:

**POLARIS STATUS — {date}**

**PORTFOLIO**
- Phase / capacity / nearest constraint
- Active outcomes and material deadline

**CURRENT REPO**
- Branch and remote freshness
- Landed / in motion / validation pending

**TEAM / COLLISIONS**
- Owner, branch, blocker, or overlap that changes the plan

**MEMORY / HEALTH**
- Fresh, degraded, or unavailable; include only recall that affects today

**RISKS**
- Up to three evidence-backed contradictions or stale surfaces

**ALIGNMENT** (only when the Step 5b sweep found something)
- Open branches: N · mergeable/undeleted: M · idle-`stale?`: K
- Superseded state threads (branch merged → proven): list with the merge evidence
- One line: "Confirm to clean (close these threads + delete these branches)?" — apply only on yes

**MY CALL**
- One highest-leverage next move with a short reason; the user may overrule it

End after the briefing. Do not start solving the selected item until the user requests execution.
