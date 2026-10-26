---
title: start — the resume set and the signals
description: Step 3 of the pre-form start body, kept verbatim: what is read, in which order, and how each signal line is placed in the brief.
status: active
---

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
   never rewrite it from `start`, and never look for a second one beside it.
4. The newest file in `$ROOT/team/<login>/sessions/` (`$ROOT/team/$LOGIN/sessions/`) — its handoff
   and concrete next action. Do not scan `team/*/sessions/`.
4b. `$ROOT/state/goals.md` if present — the goals the briefing anchors to. If empty or stale (>30 days
   untouched), ask once: "Are the goals still current?". (Origin property; also mandated by the
   founder's global agent rules.)
4c. `$ROOT/decisions.md` — the LAST 5 entries only, for continuity (what was just decided shapes
   today's work). Never the whole file.
5. **Handoff radar** — `[ "$RADAR" = none ] || python3 "$RADAR"`. Read-only, this repo only.
   It surfaces the handoffs main cannot see: stray per-worktree `state/current.md`, session logs
   on unmerged branches, uncommitted logs in worktrees. Put any ⚠ rows under a
   `**Scattered handoffs**` line — with parallel panels that is the context that goes missing.
   `RADAR=none` → inline fallback: `git worktree list` to flag a stray `state/current.md` in an
   extra worktree, and
   `git log --all --not main --since='14 days ago' --oneline -- '*sessions/*.md' | head -5`.
5b. **Open the session — BEFORE 6, always** (the receipt below belongs to a session, and
   `end` checkpoints and closes reach the one opened here):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" open \
     --root "$ROOT" --login "$LOGIN"
   ```

   One line or none. `SESSION: opened <sid>` — the session is open, so the `RECEIPT: none —
   no open session` line of Step 6 goes away and the pack receipt is written beside the
   session instead. `SESSION: resumed <sid>` — a session of today's checkout was already open, which
   is the normal second `start`, not an error. `SESSION: blocked — <CODE>` — the engine refused
   (a stale seal, an invalid pack): report the line and go on, the brief is not the gate.
   Nothing at all: this repo has no engine, and there is nothing to open. Never pass `--sid`:
   the id is the checkout, the day and the login, and after a `end` the same day the next
   `start` opens a NEW seat (`…-2`) instead of resuming a closed one. `end` checkpoints and closes
   do not recompute it — they act on the session that is open, which is what survives
   midnight and a panel that never ran `start`.

6. **The signals this repo already produces (ALWAYS)** — read-only, under a second:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/brief_signals.py" \
     --root "$ROOT" --current "$CURRENT" --login "$LOGIN" --main-wt "$MAIN_WT"
   ```

   Each line is self-describing: read it. `AREA:` rows index the areas; the pack itself is
   NOT printed here — one `PACK: <n> rows held for lane entry` line counts it, because the
   pack loads when a lane is entered, never at `start` (measured 2026-09-23: 0 of 131 rows
   changed a brief). Never ask which area. Todos and `RECENT` go with the work,
   `SPOOL_LEGACY`/`DRIFT`/`SECTIONS_MISSING`/`PRIORITIES_STALE`/`COCKPIT_REWRITE` under
   `**Signals**` — a stale order is named, never briefed as today's priorities.
   `QUEUE:`/`QUEUE_MORE:`/`QUEUE_ASK:` (from `## Coda founder`) go under `**Remember**`.
   `COCKPIT_REWRITE` = the cockpit is due for a rewrite: name it, never rewrite here.
   The resolver is the host's, else the vault the repo declares (`git config polaris.vault`); a prose pack is a pack.
   See `references/two-stage-brief.md`.

Do not read lessons, `.wiki/hot.md`, or unrelated files speculatively. Memory is not
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

**Remember** — the Step 6 `QUEUE*` lines, verbatim, first.

**Pack** — the `SESSION:` line of Step 5b when there is one, then the Step 6 resolver lines
when there are any, verbatim: `UNKNOWN:`, `RECEIPT:`, `PACK: blocked …` and the one
`PACK: <n> rows held for lane entry` count. No `layer:` row is printed at `start`.

**Signals** — the Step 6 signal lines, verbatim.

If the plan and handoff disagree, name the mismatch in `Blocker`; do not invent a reconciliation.
If there is no handoff, derive `Next action` from the current plan and say that no checkpoint
exists. Implementation still requires an explicit user request.
