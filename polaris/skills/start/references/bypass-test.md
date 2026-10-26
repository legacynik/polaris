---
title: bypass-test — start
description: The ways start was turned into something it is not, or skipped a stop, and the check that now holds each.
status: active
---

# Bypass cases — start

## B1 — a guessed path

Before `resume_paths.sh`, three copies of the path rule lived in three skills and a worktree panel
wrote a cockpit no merge brought back. Now every path comes from one resolver that exits 2 rather
than guess (no checkout, no contract, no login).

```bash
bash skills-suite/start/scripts/resume_paths.sh --selfcheck
# expected: resume_paths selfcheck: ok (quoted paths · cockpit fallback · no contract · no checkout)
```

## B2 — another contributor's identity

A cached login that differs from the profile's `github:` wrote into someone else's path. Step 3's
identity gate runs on every start, profile new or old, and stops with exit 1.

## B3 — start becomes status

Fetching, scanning PRs and recalling memory at session start cost seconds and changed no brief
(measured 2026-09-23: 0 of 131 pack rows changed a brief). The body names no fetch, no `gh pr`, no
memory call; the network is touched only by `gh api user` on first use.

## B4 — the session not opened

Without step 5, `end` had no session to tick (checkpoint) or close, and `end` closed nothing.
`session_gate.py open` is a numbered step; `blocked` is reported in the brief, never swallowed.

```bash
python3 skills-suite/start/scripts/session_gate.py --selfcheck
```

## B5 — a compaction re-runs start

Re-running the resume set after a compaction re-resolves the pack over the network for an
unchanged answer. The SessionStart hook (installed on first use) reinserts it from the receipt; a
failing reinserter is now visible instead of swallowed:

```bash
python3 skills-suite/start/scripts/install_settings.py --selfcheck
# includes: a failing reinserter is visible (non-zero)
```
