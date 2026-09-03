---
name: start
description: Polaris skill — resume the current objective from the latest local handoff. First use also provisions your own team path.
user-invocable: true
version: 1.1.0
---

# /start — resume, do not survey

`/start` restores the smallest local context needed to continue the current objective. It does not
build a situational view of the repository or portfolio. Do not fetch, scan pull requests or other
contributors, run health checks, or recall memory here. Those belong to `/polaris-status`.

The recurring path is read-only and local. First use may cache the contributor login in local git
config and provision that contributor's own `_polaris/team/<login>/` path. It never creates issues,
branches, pull requests or assignments, and never writes `state/current.md`.

## Step 1 — Verify the local branch

```bash
git rev-parse --abbrev-ref HEAD
```

Hold the result. If this is not a git checkout, stop. Later compare it with the current weekly
plan's branch. Do not fetch to answer this question.

## Step 2 — Resolve the repository contract and local identity

The Polaris root is **`_polaris/`** — one root, committed with the code:

1. `_polaris/` if `_polaris/config.yml` exists;
2. otherwise, if the repository root is itself named `_polaris` and carries `./config.yml`, use the
   repository root;
3. otherwise stop and point to `docs/TEAM-ONBOARDING.md`. Do not create a contract implicitly.

Use the cached repo-local login on recurring sessions:

```bash
LOGIN="$(git config --local --get polaris.login || true)"
```

If it is absent, this is machine setup: require authenticated `gh`, resolve the exact login once,
and cache it locally:

```bash
gh auth status
LOGIN="$(gh api user --jq .login)"
git config --local polaris.login "$LOGIN"
```

If `_polaris/team/$LOGIN/profile.yml` is absent, provision **only that contributor's** path from the
plugin template:

```bash
mkdir -p "_polaris/team/$LOGIN/weeks" "_polaris/team/$LOGIN/reports" "_polaris/team/$LOGIN/sessions"
cp "$CLAUDE_PLUGIN_ROOT/templates/repo-contract/profile.yml" "_polaris/team/$LOGIN/profile.yml"
perl -pi -e "s/^github: .*/github: $LOGIN/" "_polaris/team/$LOGIN/profile.yml"
```

Never create `team/<login>/` folders for other people. The identity gate runs in BOTH branches,
whether the profile was just created or already existed:

```bash
grep -q "^github: $LOGIN$" "_polaris/team/$LOGIN/profile.yml" \
  || { echo "STOP: profile github: does not match cached login ($LOGIN) — fix it first"; exit 1; }
```

## Step 2b — Read the contributor profile (voice and language)

`_polaris/team/$LOGIN/profile.yml` already carries `language:` and `voice:`. Older copies predate
those fields: when either is missing, fall back to `en` / `plain` and say nothing — never invent the
value, never write the file from `/start`.

`language` sets the CONVERSATION language only. Code, commit messages, technical documents and skill
bodies stay English whatever it says.

**What `voice` means** — the field named a tone but nothing defined it, so it was inert. It is not a
personality costume: it changes how a conclusion is delivered, never whether it is true.

| `voice` | behaviour |
|---|---|
| `cynical` | Direct, no preamble. Assumes broken until seen running. Says a thing is wrong BEFORE acting on it, not in the post-mortem. Cites a path or a number, or does not make the claim. Marks *verified* apart from *assumed*. No moralising bolted onto technical work. |
| `plain` | Same substance, softer edges. The fallback when the field is absent. |
| free text | Any line the contributor wrote describing the tone they want — honour it as written. |

Two rules hold under EVERY voice, because they are about honesty and not about tone: never
manufacture disagreement to look rigorous, and say "I do not know" when that is the true answer
instead of filling the gap with prose.

`explain_as: vibe-coder` (optional) means plain language and analogies in conversation, with paths,
numbers and citations kept for the written documents. `push_back: false` (optional, default true)
means execute without pressure-testing; a contributor can also suspend it for one session by saying so.

## Step 3 — Read only the resume set

Read these local files, in order:

1. `team/<login>/profile.yml` — already read in Step 2b for voice and language; here take only the
   assignment fields needed for the brief.
2. `team/<login>/weeks/$(date +%G-W%V).md` — current outcome, branch, blocker and next proof. This is
   the contributor's own focus: brief it as active work, never as something
   awaiting permission. If `lead_review:` records a reorder, surface it as priority information.
   Only a **red** item waiting on its **named** approver is blocked. If the file is absent, say there
   is no current weekly plan; its absence never blocks urgent or clearly-owned work.
3. `state/current.md` if present — only the current checkpoint and `## Open` item for this branch or
   contributor. It is a pointer, not session history; never rewrite it from `/start`.
4. The newest file in `team/<login>/sessions/` — read its handoff/checkpoint and concrete next
   action. Do not scan `team/*/sessions/`.
4b. `state/goals.md` if present — the goals the briefing anchors to. If empty or stale (>30 days
   untouched), ask once: "Goals aggiornati?". (Origin property; also mandated by the founder's
   global CLAUDE.md.)
4c. `<root>/decisions.md` — the LAST 5 entries only, for continuity (what was just decided shapes
   today's work). Never the whole file.
5. **Handoff radar (multi-panel machines)** — if `<polaris-root>/scripts/handoff_radar.py` exists,
   run it (`python3 <polaris-root>/scripts/handoff_radar.py`, read-only, <2s). It surfaces
   end-of-session handoffs that main cannot see: stray per-worktree `state/current.md`, session
   logs committed on unmerged branches, uncommitted logs in worktrees. Include any ⚠ rows in the
   brief under a `**Handoff sparsi**` line so the operator can decide where to resume — this is
   exactly the context that silently goes missing with parallel panels. If the script is absent (team machines — npx ships
   skills only), run the inline fallback, same purpose, two read-only commands scoped to THIS repo:
   `git worktree list` → for each extra worktree, flag any `<polaris-root>/state/current-state.md`
   or `current.md` living there (stray cockpit), and
   `git log --all --not main --since='14 days ago' --oneline -- '*sessions/*.md' | head -5` →
   handoffs committed on unmerged branches.
6. **Cockpit tail (ALWAYS, radar or not)** — read the last 2 blocks of `state/current-state.md`
   (main worktree) if present: it is the dense record with next-steps and resume instructions;
   the brief's `Checkpoint`/`Next action` should prefer it when fresher than the session log.

Do not read lessons, `.wiki/hot.md`, or unrelated files speculatively (decisions: last 5 only, per 4c). Memory is not
current state and recall is never mandatory at session start.

Compare the local branch from Step 1 with the current plan's branch. If both are present and differ,
stop with the exact mismatch. This is a local safety gate, not a reason to fetch.

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
