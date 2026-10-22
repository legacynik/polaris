---
title: polaris-sweep — perché ogni flag dell'invocazione Codex esiste
description: La tabella why-per-flag della Phase 3c. Tutti e quattro i fallimenti osservati dal vivo il 2026-07-26 — vedi BUG-HISTORY.md per il racconto completo. Da leggere PRIMA di cambiare qualunque flag.
status: active
---

# Phase 3c — each flag earns its place

| Flag / choice | Why — all four observed live |
|---|---|
| `< /dev/null` | Without it `codex exec` blocks forever on stdin (`"Reading additional input from stdin..."`), producing a zero-byte output file after an hour |
| `--skip-git-repo-check` | Without it, a cwd Codex doesn't consider trusted aborts instantly: `"Not inside a trusted directory"` |
| no `--full-auto` | Deprecated, and it contradicts `--sandbox read-only` (emits a warning and asks for write sandbox) |
| `timeout 900` + `nohup … &` | A foreground `Bash` call is capped at 10 min by the harness — a longer run gets SIGTERMed by the *caller*, which looks identical to a hang. Detach and poll |
| `--output-schema` | `--output-last-message` alone is not guaranteed: Codex can end on a tool block and never write the file. The schema forces a final structured message |
| HARD CONSTRAINTS block | Left unconstrained, Codex routes itself into running the project's test suite. Confirmed by a `requests.exceptions.ConnectionError` to `cloud.langfuse.com` in the run log after ~50 min of no review output |
