---
title: codex-review — why each flag of the Codex invocation exists
description: The why-per-flag table of step 4. All of these failures were observed live in one real run; read it before changing any flag.
status: active
---

# Each flag earns its place

| Flag / choice | Why — each observed live |
|---|---|
| `< /dev/null` | Without it `codex exec` blocks forever on stdin (`"Reading additional input from stdin..."`), producing a zero-byte output file after an hour |
| `--skip-git-repo-check` | Without it, a working directory Codex does not consider trusted aborts at once: `"Not inside a trusted directory"` |
| no `--full-auto` | Deprecated, and it contradicts `--sandbox read-only` (it warns and asks for a write sandbox) |
| `timeout 900` + `nohup … &` | A foreground tool call is capped by the harness (ten minutes on Claude Code): a longer run is killed by the *caller*, which looks identical to a hang. Detach and poll |
| `--output-schema` | `--output-last-message` alone is not guaranteed: Codex can end on a tool block and never write the file. The schema forces a final structured message |
| `--json` | The log becomes a JSONL event trace, which is the only way to check that the reviewer opened the touched files instead of skimming the diff |
| HARD CONSTRAINTS block | Left unconstrained, Codex routes itself into running the project's test suite: the run log showed a connection error to an external tracing host after ~50 minutes with no review output |
| no `-codex` model id | Every `-codex`-suffixed id returns 400 on a ChatGPT-account login; use `gpt-5.6-sol` |
