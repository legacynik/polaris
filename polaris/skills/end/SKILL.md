---
name: end
description: Polaris skill — close a session — saves to repo-local _polaris/state/current.md and _polaris/sessions/, appends to cross-repo _polaris/sessions/ and memo/log.md when the vault is available, surfaces decisions to repo _polaris/decisions.md (and cross-repo decisions.md if available), and offers a commit. Use at the end of any session, before a multi-day pause, or when the user says "end", "fine", "ho finito", "wrap up".
user-invocable: true
---

# end

Close the session cleanly. Saves at two levels — repo-local `_polaris/` and cross-repo vault — surfaces decisions, and offers a commit.

## Vault resolution (cross-repo layer — optional)

The repo layer (`_polaris/` in the current repo) ALWAYS works and needs nothing.
The cross-repo portfolio layer needs the Polaris vault:
- if env `POLARIS_VAULT` is set → use it;
- else if `~/Desktop/All Vibe Proj/_polaris` exists → use it (founder machine);
- else → the portfolio layer is NOT available: print one line
  "portfolio layer: not available on this machine" in the briefing/closing and
  skip every cross-repo step silently. This is normal on teammate machines, not an error.
`polmem` (CLI or bundle): use it only if `command -v polmem` succeeds OR
`scripts/polaris_memory_repo.py` exists in the repo; otherwise say
"polmem: not available" once and continue.

## When to use

- End of any working session
- Before a multi-day pause or major context shift
- "end", "fine", "ho finito", "wrap up", "chiudi", "end session"

Use `update` for mid-session checkpoints without closing.

## Process

### 1. Get date and time
```bash
date +%Y-%m-%d   # TODAY
date +%H:%M      # NOW
```

### 2. Diff session work
```bash
git status --short
git log --since='today 00:00' --oneline | head -15
```

### 3. Summarize
From conversation + git diff, extract:
- **Topics** — 2–5 bullets of what was worked on
- **Decisions** — explicit decisions made (what + why)
- **Files modified** — from git, capped at 10
- **Open threads** — unfinished items, blockers, follow-ups
- **Next actions** — concrete steps for the next session

Surface only — do not invent.

### 4. current.md — Smart audit + ask when unsure

⚠️ **CRITICAL: Multiple panels share current.md. Use critical thinking.**

**Step-by-step:**
1. Read the entire file
2. Update the timestamp line (`<!-- last-session: ... -->`)
3. Audit each existing item with evidence:

**For each item in Open/Next, classify it:**

| Evidence | Action |
|---|---|
| **You completed it this session** (commit, PR merged, deploy done) | ✅ Remove it — you have proof |
| **Git/GH proves it's done** (PR merged, issue closed — verify with `gh issue view` or `git log`) | ✅ Remove it — evidence exists |
| **Clearly obsolete** (references a branch that was deleted, a PR that was superseded) | ✅ Remove it |
| **You're not sure** — written by another panel, can't verify, looks maybe stale | ⚠️ **ASK the user**: "Posso rimuovere X? Sembra completato/superato perché Y" |
| **You didn't touch it and can't verify** | ❌ Leave it |

4. APPEND your new Open/Next items
5. Keep Next order from other panels — add yours at the end

**The goal**: current.md stays lean and relevant. Not a graveyard of old items, not a blank slate that loses context. Use judgment. When unsure, ask.

### 5. Save repo-local _polaris/

**`_polaris/state/current.md`** — edit per step 4 rules above.

**`_polaris/sessions/{TODAY}.md`** — APPEND (create with `# Session Log: {TODAY}` if missing):
```markdown
## session-end {NOW}

### Topics
- …

### Files modified
- …

### Open threads
- …

### Next actions
- …
```

### 6. Save cross-repo vault (skip silently if the portfolio layer is not available)

**`$POLARIS_VAULT/sessions/{TODAY}.md`** — APPEND:
```markdown
## [{repo-name}] session-end {NOW}

### Topics
- …

### Decisions
- …

### Open threads
- …

### Next actions
- …
```

**`$POLARIS_VAULT/memo/log.md`** — APPEND one line:
```
## [{TODAY} {NOW}] session-end | {repo-name} | {summary ≤120 chars}
```
Idempotency: skip if last line already has identical `{TODAY} {NOW} session-end`.

### 7. Surface decisions

For each explicit decision NOT already captured, ask:
> "Capture these N decisions? (y / n / individual)"

If confirmed, APPEND to **both**:

**Repo-local** `_polaris/decisions.md` (create if missing):
```markdown
## {TODAY} — {Title}

**Context**: …
**Decision**: …
**Rationale**: …
**Status**: active
```

**Cross-repo** `$POLARIS_VAULT/decisions.md` (only if the portfolio layer is available) — only for decisions that affect multiple repos or are strategic. Ask explicitly: "Cross-repo relevant? (y/n)"

Never auto-capture. Always confirm.

### 7b. Layer-3: distill lessons (B loop)

Turn this session's corrections and decisions into behavior change so the same mistake gets *harder to repeat each time it recurs* (Karpathy system-prompt-learning). Propose-only — the human approves every routed change.

1. **Read the signal.** Read today's scratch for the current contributor at `_polaris/sessions/scratch/<contributor>/` (use the `git config user.email` slug) and pull every entry whose header is flagged `[CORRECTION]` (set by the Stop hook), plus the decisions surfaced in step 7.
2. **Distill** each into an imperative lesson — **Why** + **How-to-apply**, generalized. Write the *rule*, not the incident ("Verify branch before any git op", not "fixed branch X today").
3. **Classify.** If the portfolio layer is available (see "Vault resolution" above), classify each lesson into a tier with the §1 heuristic from `$POLARIS_VAULT/plans/2026-06-18-decision-to-enforcement-loop.md`:
   - **note** — pure rationale, no action.
   - **context** — needs judgment / is a preference.
   - **gate** — violation causes damage AND a script can mechanically detect it.
   If the portfolio layer is NOT available: print "lesson B-loop: vault not available, skipping" once, default every lesson to tier **note**, and skip step 5 below.
4. **Route** (propose, human approves) — always runs, vault or no vault:
   - **note** → append to `_polaris/lessons.md` (a `## ` block per the ledger contract) + to `decisions.md` if it's a real decision.
   - **context** → propose a `MEMORY.md` feedback entry (`**Why:** / **How to apply:**` shape) and/or one `CLAUDE.md` line.
   - **gate** → propose a preflight / pre-commit check.
5. **Recurrence check** (only if the portfolio layer is available). For each lesson run `python3 "$POLARIS_VAULT/scripts/lesson_recurrence.py" --match "<lesson>"`. If it already exists, run `--bump "<exact lesson title>"` and surface the printed promotion proposal (`note→context→gate`) for the human to confirm.

Keep this lean: a few high-signal lessons beats a long list. Don't invent lessons with no signal in the scratch or decisions.

### 8. Offer commit
If uncommitted changes exist, suggest a commit message and ask: "Commit? (y / n / edit)"
Do not push.

### 9. Confirm
3–5 lines: what was written, whether a commit was made, top 1–2 open threads for next session.

## Path standard (every repo)

```
repo/_polaris/
  sessions/{TODAY}.md     ← session log (APPEND only)
  state/current.md        ← status (smart audit: remove proven-done, ask if unsure, append new)
  decisions.md            ← repo-specific decisions (APPEND, newest on top)
```

Cross-repo vault: see "Vault resolution" above — `$POLARIS_VAULT` when available.

## Path rules

- All repo-local writes go to `_polaris/` inside the current repo root
- Create `_polaris/sessions/`, `_polaris/state/` if missing (`mkdir -p`)
- Cross-repo `_polaris/` resolves per the "Vault resolution" rule above (`$POLARIS_VAULT`); if unresolved, cross-repo writes are skipped entirely
- **current.md is a SHARED resource** — use evidence-based judgment. Remove what's proven done. Ask when unsure. Never blindly wipe.

## Memory sync — the cross-repo layer lives HERE (founder flip 2026-07-03)

Per-repo indexing is fully automatic (git hooks on main + launchd 6h backstop) —
/end does NOT need to sync product repos. What runs ONLY at /end is the
Polaris-level layer + the drain, all backgrounded, NEVER blocking the close —
and ONLY if the portfolio layer is available (writer-side, founder machine only;
else skip this whole section silently):

1. Distill drain (scratch → lessons):
   `( DISTILL_AUTORUN=1 bash "$POLARIS_VAULT/scripts/distill_runner.sh" >/dev/null 2>&1 & )`
2. Portfolio wiki (cross-repo, _polaris — the ONLY trigger for it), only if `polmem` is available:
   `( polmem sync _polaris >/dev/null 2>&1 & )`
3. Product-repo catch-up (cheap no-op when hooks already synced), only if `polmem` is available:
   `( polmem sync >/dev/null 2>&1 & )`

Skip silently if the vault or scripts are missing. Session close is a natural
freshness event — the queue never survives a closed session unprocessed.
