# Component A — code-graph = Serena (freshness-fixed)

Replaces the incumbent `codebase-memory` MCP with **Serena** (LSP-live) as the polmem code-graph.

## Why
Serena is the only code-graph of four benched (codebase-memory, cgc/Kuzu, Cortex/Maggy, Serena)
that is **fresh by construction** — no persistent store to serve stale answers under a green
`ready`. The others all silently served stale caller sets after external edits (the health-honesty
failure). Full verdict + evidence: `_polaris/audit/2026-07-18-code-graph-selection/VERDICT.md`.

Serena's one gap — its `workspace/didChangeWatchedFiles` notification is defined but never fired,
so a warm-resident server goes stale under edits made outside its own tools — is closed by
`serena_freshness_fix.py` (a pre-query mtime poll on `Tool.apply_ex`, covering both stdio-MCP and
HTTP paths, config-driven, concurrency-safe). Validated 23/23 fresh on the real MCP delivery path
at ~48k symbols.

## What's wired
- `.mcp.json` → `serena-code-graph`: `uvx` fetches the pinned Serena + pyright and runs
  `serena_code_graph_launcher.py`, which installs the freshness patch then starts Serena's stdio
  MCP server, **project-agnostic** (the agent calls `activate_project` for the repo it's in).
- Per-machine: first run downloads Serena+pyright via uvx (cached after). The index is live
  (per-machine, nothing shipped). Cross-harness: Claude Code and Codex consume the same MCP entry.

## Smoke-tested
Launcher starts under the pinned Serena and installs the patch cleanly (`freshness fix installed`,
no traceback). NOT yet validated: end-to-end load as a live plugin MCP in the harness (needs a
plugin reload) — do that before go-live.

## OPEN — deployment decision (needs box topology)
Two models; the fix covers both:
- **stdio-per-client** (this wiring's default): each harness spawns its own Serena LS. Simple,
  serialized, safe — but N warm language servers on the box (~540MB each).
- **one shared resident server per box**: run Serena's HTTP project-server once; all harnesses +
  autonomous agents point at it (one warm graph, concurrency handled by the fix's lock). Better for
  a multi-harness / autonomous-agent box (Leecloud/S9). Requires an HTTP-MCP bridge or client config.

Pick per the actual box topology before go-live.

## Go-live (founder)
1. Reload the plugin locally; confirm `serena-code-graph` connects and `find_referencing_symbols`
   works after `activate_project`.
2. Merge `feat/serena-code-graph` → `main`; publish. Team gets it on next plugin update.
3. Remove the `codebase-memory` MCP install once Serena is confirmed in the field.

Caveats carried from validation: poll adds ~150–200ms per symbolic tool call (O(source files);
cache-list+TTL for >10k-file monorepos); cold-start retry-on-empty is a safety net; a middle-process
LS kill can transiently mislead `is_running` (leaf/backend kill self-heals in ~2.3s).
