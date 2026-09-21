---
name: start
description: Polaris skill — resume the current objective from the latest local handoff. First use also provisions your own team path.
user-invocable: true
version: 1.11.0
---

# /start — resume, do not survey

`/start` restores the smallest local context needed to continue the current objective. It does not
build a situational view of the repository or portfolio. Do not fetch, scan pull requests or other
contributors, run health checks, or recall memory here. Those belong to `/polaris-status`.

The recurring path is read-only and local. It never creates issues, branches, pull requests or
assignments, and never writes the cockpit.

## Step 1 — Verify the local branch

```bash
git rev-parse --abbrev-ref HEAD
```

Hold the result. If this is not a git checkout, stop. Later compare it with the current weekly
plan's branch. Do not fetch to answer this question.

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

Then install the team settings — the permissions preset and the compaction hook of Step 3b.
It merges and never clobbers: a second run changes nothing and says so, and a
`.claude/settings.json` it cannot parse stops it (`SETTINGS_UNREADABLE`, exit 1, nothing
written) rather than being replaced.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/install_settings.py" --repo "$MAIN_WT"
```

Hooks are read at session start, so the one it writes takes effect from the NEXT session.

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
5b. **Open the session — BEFORE 6, always** (the receipt below belongs to a session, and
   `/update` and `/end` reach the one opened here):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" open \
     --root "$ROOT" --login "$LOGIN"
   ```

   One line or none. `SESSION: opened <sid>` — the session is open, so the `RECEIPT: none —
   no open session` line of Step 6 goes away and the pack receipt is written beside the
   session instead. `SESSION: resumed <sid>` — a session of today's checkout was already open, which
   is the normal second `/start`, not an error. `SESSION: blocked — <CODE>` — the engine refused
   (a stale seal, an invalid pack): report the line and go on, the brief is not the gate.
   Nothing at all: this repo has no engine, and there is nothing to open. Never pass `--sid`:
   the id is the checkout, the day and the login, and after a `/end` the same day the next
   `/start` opens a NEW seat (`…-2`) instead of resuming a closed one. `/update` and `/end`
   do not recompute it — they act on the session that is open, which is what survives
   midnight and a panel that never ran `/start`.

6. **The signals this repo already produces (ALWAYS)** — read-only, under a second:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/brief_signals.py" \
     --root "$ROOT" --current "$CURRENT" --login "$LOGIN" --main-wt "$MAIN_WT"
   ```

   Each line is self-describing: read it. `AREA:` rows index the areas, `layer:` rows are the
   chosen area's pack; on `QUESTION:` ask it and stop. Todos and `RECENT` go with the work,
   `SPOOL_LEGACY`/`DRIFT`/`SECTIONS_MISSING` under `**Segnali**`. The resolver is the host's,
   else the vault the repo declares (`git config polaris.vault`); a prose pack is a pack.
   See `reference/two-stage-brief.md`.

Do not read lessons, `.wiki/hot.md`, or unrelated files speculatively. Memory is not
current state and recall is never mandatory at session start.

Compare the local branch from Step 1 with the current plan's branch. If both are present and differ,
stop with the exact mismatch. This is a local safety gate, not a reason to fetch.

## Step 3b — After a compaction, put the pack back (never rebuild it)

A compaction empties the context window and leaves the receipt on disk. **Do not run `/start`
again and do not re-read the resume set**: the pack was already resolved, and re-resolving it
walks the tracker over the network for an answer that has not changed.

Step 2 installs a `SessionStart` hook with the `compact` matcher, so on Claude Code this runs
by itself. On a host with no compaction event, or before that hook's first session, run it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" \
  reinsert --root "$ROOT"
```

The door finds the reinserter where it finds everything else — this repository first, then
the vault it declares — and asks it for the CHECKOUT, which is where the session and the pack
receipt both live. Asking for `$ROOT` (`<repo>/_polaris`) answered `NO_OPEN_SESSION` in every
product repository, on the one path that runs by itself.

No output at all: no reinserter here and none in the declared vault, so there is nothing to
put back (contract #155). Otherwise read what it prints:

- `REINSERT: HEAD unchanged … — 0 tracker calls` followed by `PACK:` and the rows — the same
  pack, reprinted from the receipt. Nothing was recomputed and nothing was fetched.
- `REINSERT: HEAD moved <a> -> <b>` — commits landed under the session, so the pack was
  resolved again and a second receipt now sits beside the first, naming it in `CHAIN: prev=`.
- `RECEIPT_MISSING:`, `RECEIPT_UNREADABLE:`, `RECEIPT_TAMPERED:`, `SID_MISMATCH:`,
  `AREA_MISMATCH:` or `CHAIN_BROKEN:` — the receipt on disk could not be trusted, so the pack
  was resolved instead of reused. All are costs, not failures; the command still exits 0, and
  nothing on disk is overwritten. Report the line: it says something about the session.
- `NO_OPEN_SESSION:` — no session receipt is open, so there is no pack to put back. Since
  polaris-os#155 Step 5b opens one, so this now means the session was closed by `/end`, or
  this repository carries no engine at all.

`CHAIN_UNANCHORED:` may appear beside any of these. It is a report, not a refusal: every
link is there and nothing ties that area's packs to a start receipt.

The session id is not a flag anybody has to fill: the command resolves the session open today.
The same door verifies the receipt chain on demand — exit 1 on a `CHAIN_BROKEN`, 0 on anything
it merely reports:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" \
  chain --root "$ROOT"
```

`--sid` and `--area` narrow it to one session or one area; without them it asks about the
session open today, the same one everything else here is about.

## Step 4 — Render the resume brief

Answer with the brief ONLY, as plain markdown, NEVER inside a code fence. Use the profile's
`language:` (default English). Omit empty lines rather than padding them.

{Weekday} {date} — <repo> on <branch>

**RESUME**
- Outcome: <current outcome, or no current weekly outcome>
- Checkpoint: <latest verified handoff/checkpoint>
- Blocker: <one active blocker, if any>
- Next action: <the concrete continuation step from the handoff, reconciled with the plan>

**Pack** — the `SESSION:` line of Step 5b when there is one, then the Step 6 resolver lines
when there are any. Copy them **verbatim**, never summarised
and never counted: first its `UNKNOWN:`, `AREA:`, `QUESTION:`, `RECEIPT:` lines, then every
`layer:` row, one per line. Over **40** rows, print the first 40 and one last line
`… and <K> more rows`. A `layer:` row is an ADDRESS — a sentence about the rows is not the
context, it is the loss of it.

If the plan and handoff disagree, name the mismatch in `Blocker`; do not invent a reconciliation.
If there is no handoff, derive `Next action` from the current plan and say that no checkpoint
exists. Implementation still requires an explicit user request.
