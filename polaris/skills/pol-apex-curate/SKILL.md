---
name: pol-apex-curate
description: Curate a repo's CLAUDE.md (the always-loaded apex) — distill lessons/decisions into a ≤200-line PROPOSAL, route situational rules to .claude/rules/ with paths:, flag stale project.md/context.md. PROPOSE-ONLY — never writes CLAUDE.md; the apex write is the human's yes/no (G1). Use when polmem health shows apex-cap RED, when /start surfaces an apex alert, or on demand ("curate the apex", "CLAUDE.md è gonfio", "distilla le lezioni in CLAUDE.md").
user-invocable: true
---

# pol-apex-curate — apex curation (propose-only)

Spec: `_polaris/docs/superpowers/specs/2026-07-07-polaris-lifecycle-method-design.md`.
The apex is the ONLY curated always-loaded surface. You produce a PROPOSAL; the
human writes. **You are physically forbidden from editing CLAUDE.md in this skill.**

## Inputs (read in this order)
1. `<repo>/CLAUDE.md` — the current apex (note every `<!-- LOCKED -->` line).
2. `<repo>/_polaris/lessons.md` + `<repo>/_polaris/decisions.md` — the raw material.
3. `<repo>/_polaris/sessions/` (last 14 days) + `sessions/scratch/**` if present.
4. `<repo>/project.md` and `<repo>/context.md` if present — staleness check only.

## Produce ONE file: `<repo>/_polaris/state/apex-proposal.md`
Structure: the FULL proposed CLAUDE.md text, then `---`, then a change log:
`ADDED (from where) / REMOVED (why stale) / ROUTED (to which rules file) / KEPT-LOCKED`.

## Hard guardrails (all of them, every run)
- **≤200 lines** for the proposed apex body.
- **Every `<!-- LOCKED -->` line survives verbatim** (whitespace changes only).
  Never propose removing one — if you believe one is obsolete, list it under
  `## Founder questions` at the bottom instead.
- **Situational rules** (matter only for part of the codebase) are ROUTED OUT:
  write them as separate proposed files `<repo>/.claude/rules/<topic>.md` with
  `paths:` frontmatter (REQUIRED — an unscoped rule loads every session, F1).
  Propose these as fenced blocks inside the change log, one per file.
- **Recurrence counts preserved**: a lesson marked `recurrence: 3` keeps that
  number in the distilled rule — it is the graduate-to-gate signal.
- **Never compact** `_polaris/decisions.md` — it is an append-only ledger.
- **Pointer-map block required** in the proposal (exact heading
  `## Where to find things (map)` — the gate greps this literal).
- Distill = always-relevant rules/gates/gotchas only. What-it-is/direction
  content belongs in `project.md` — if you find it in the apex, move it to the
  ROUTED section as a `project.md` amendment proposal.
- **Never route a LOCKED rule to `.claude/rules/`** — LOCKED protection exists
  ONLY in CLAUDE.md; a rules file carries zero gate protection. If a LOCKED
  rule is situational, it stays in the apex anyway.

## Staleness pass (project.md / context.md)
Compare claims against the repo (README, package manifests, recent commits).
Stale claim → propose the FIX (a ready-to-apply patch block in the change log),
not just a flag.

## Self-check before presenting (deterministic, mandatory)
Extract the proposed apex body (everything above the first `---` separator) to
`/tmp/apex-body.md`, then run:
`python3 "$HOME/Desktop/All Vibe Proj/_polaris/mcp/apex_gate_cli.py" --file /tmp/apex-body.md --against <repo>/CLAUDE.md`
Exit 1 or any WARN → fix the proposal and re-run. Present only a clean proposal.

## Handoff
Present: line count before → after, the change log, founder questions.
Then STOP. The human applies (or asks you to apply AFTER an explicit yes —
that yes is the G1 gesture; without it, no write).
