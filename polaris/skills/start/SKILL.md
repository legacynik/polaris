---
name: start
description: Polaris skill — resume the current objective from the latest local handoff. First use also provisions your own team path.
user-invocable: true
version: 1.6.0
---

# /start — resume, do not survey

`/start` restores the smallest local context needed to continue the current objective. It does not
build a situational view of the repository or portfolio. Do not scan pull requests or other
contributors, run health checks, or recall memory here. Those belong to `/polaris-status`.

**One exception, and it is not a survey: the divergence of THIS checkout.** One bounded fetch of
one ref, because without it every local answer is unverifiable. Measured 2026-09-10 across a real
vault: **122 commits unpushed**, 94 of them session history, the oldest 14 days old — and three
answers given that day from a checkout 159 commits behind were wrong, because a checkout that is
behind reports "not on main" for things that are on main. The deferral to `/polaris-status` does
not work: 1 invocation in 1,146 over 90 days.

The recurring path is read-only and local. It never creates issues, branches, pull requests or
assignments, and never writes the cockpit.

## Step 1 — Verify the local branch

```bash
git rev-parse --abbrev-ref HEAD
```

Hold the result. If this is not a git checkout, stop. Later compare it with the current weekly
plan's branch. No fetch is needed for the branch NAME; the one fetch this skill makes belongs to
the divergence signal in Step 6, which answers a different question.

## Step 1b — One home (every path below comes from here, never from the cwd)

```bash
eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"
```

`MAIN_WT`, `ROOT`, `LOGIN`, `CURRENT` (this repo's ONE cockpit) and `RADAR` all resolve against the MAIN
worktree. Non-zero exit: read the message and stop, never guess a path. The script resolves the
contract in `_polaris/` (`_polaris/config.yml`, else where the repository root is itself named `_polaris` and
carries `./config.yml`,
else stop and point to `docs/TEAM-ONBOARDING.md`) and the identity
(`git config --local --get polaris.login`, else `gh auth status` and `gh api user --jq .login`
cached once with `git config --local polaris.login`).

## Step 2 — Provision your own team path (first use only)

If `$ROOT/team/$LOGIN/profile.yml` is absent, provision **only that contributor's** path from the
plugin template. Never create `team/<login>/` folders for other people.

```bash
mkdir -p "$ROOT/team/$LOGIN/weeks" "$ROOT/team/$LOGIN/reports" "$ROOT/team/$LOGIN/sessions"
cp "$CLAUDE_PLUGIN_ROOT/skills/start/templates/repo-contract/profile.yml" "$ROOT/team/$LOGIN/profile.yml"
perl -pi -e "s/^github: .*/github: $LOGIN/" "$ROOT/team/$LOGIN/profile.yml"
```

The identity gate runs in BOTH branches, whether the profile was just created or already existed:

```bash
grep -q "^github: $LOGIN$" "$ROOT/team/$LOGIN/profile.yml" \
  || { echo "STOP: profile github: does not match cached login ($LOGIN) — fix it first"; exit 1; }
```

## Step 2b — Voice and language

`$ROOT/team/$LOGIN/profile.yml` carries `language:` and `voice:`. Missing either, fall back to
`en` / `plain`, say nothing, and never write the file from `/start`. `language` sets the
CONVERSATION language only: code, commit messages, technical documents and skill bodies stay
English whatever it says. For what each `voice` means, and for `explain_as` / `push_back`, read
`reference/voice.md` beside this skill — once per contributor, not every session.

## Step 3 — Read only the resume set

Read these local files, in order:

1. `$ROOT/team/$LOGIN/profile.yml` — already read in Step 2b for voice and language; here take only the
   assignment fields needed for the brief.
2. `$ROOT/team/$LOGIN/weeks/$(date +%G-W%V).md` — outcome, branch, blocker, next proof. This is
   the contributor's own focus: brief it as active work, never as something
   awaiting permission. A `lead_review:` reorder is priority information; only a **red** item
   waiting on its **named** approver is blocked. Absent file, say there is no current weekly plan;
   that never blocks urgent or clearly-owned work.
3. `$CURRENT` if present — the numbered `## Active Priorities`, then only the `## Open` item for
   this branch or contributor. It is the repo's ONE cockpit and a pointer, not session history:
   never rewrite it from `/start`, and never look for a second one beside it.
4. The newest file in `$ROOT/team/<login>/sessions/` (`$ROOT/team/$LOGIN/sessions/`) — its handoff
   and concrete next action. Do not scan `team/*/sessions/`.
4b. `$ROOT/state/goals.md` if present — the goals the briefing anchors to. If empty or stale (>30 days
   untouched), ask once: "Goals aggiornati?". (Origin property; also mandated by the founder's
   global CLAUDE.md.)
4c. `$ROOT/decisions.md` — the LAST 5 entries only, for continuity (what was just decided shapes
   today's work). Never the whole file.
5. **Handoff radar** — `[ "$RADAR" = none ] || python3 "$RADAR"`. Read-only, this repo only.
   It surfaces the handoffs main cannot see: stray per-worktree `state/current.md`, session logs
   on unmerged branches, uncommitted logs in worktrees. Put any ⚠ rows under a
   `**Handoff sparsi**` line — with parallel panels that is the context that goes missing.
   `RADAR=none` → inline fallback: `git worktree list` to flag a stray `state/current.md` in an
   extra worktree, and
   `git log --all --not main --since='14 days ago' --oneline -- '*sessions/*.md' | head -5`.
6. **The signals this repo already produces (ALWAYS)** — read-only, under a second:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/brief_signals.py" \
     --root "$ROOT" --current "$CURRENT" --login "$LOGIN" --main-wt "$MAIN_WT"
   ```

   Each line is self-describing and appears only when it has something to say, so read what comes
   back: todos, follow-ups due and `RECENT` go with the work, `SPOOL_LEGACY`/`DRIFT`/`SECTIONS_MISSING`
   under `**Segnali**`. A missing line is nothing to report, never an error.

   **`AHEAD=` / `BEHIND=` / `NO_UPSTREAM` are not ordinary signals — they say whether this session
   can be trusted, so they go FIRST, above the brief, never buried under `**Segnali**`:**

   - `BEHIND=n` — **say it as a warning about answers, not about hygiene**: everything this checkout
     reports as absent may exist on the remote, so *"not on main" is unreliable until you realign*.
     **Then propose the realignment** and let the contributor decide: `git pull --ff-only`
     when nothing is ahead, otherwise name that the branch has diverged and stop — never
     realign on your own, and never `reset`, `rebase` or `stash` a tree you do not own.
   - `AHEAD=n` — those commits exist on no one else's machine and any panel sharing this repo can
     delete them, because worktrees isolate files but **share refs**. Name them as work at risk.
   - `NO_UPSTREAM` — the branch has no remote at all, so nothing here is backed up anywhere.

Do not read lessons, `.wiki/hot.md`, or unrelated files speculatively. Memory is not
current state and recall is never mandatory at session start.

Compare the local branch from Step 1 with the current plan's branch. If both are present and differ,
stop with the exact mismatch. This is a local safety gate, and it needs no fetch of its own.

## Step 4 — Render the resume brief

Answer with the brief ONLY, as plain markdown, NEVER inside a code fence. Use the profile's
`language:` (default English). Omit empty lines rather than padding them.

{Weekday} {date} — <repo> on <branch>

**RESUME**
- Outcome: <current outcome, or no current weekly outcome>
- Checkpoint: <latest verified handoff/checkpoint>
- Blocker: <one active blocker, if any>
- Next action: <the concrete continuation step from the handoff, reconciled with the plan>

If the plan and handoff disagree, name the mismatch in `Blocker`; do not invent a reconciliation.
If there is no handoff, derive `Next action` from the current plan and say that no checkpoint
exists. Implementation still requires an explicit user request.
