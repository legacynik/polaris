#!/usr/bin/env python3
"""Launch Serena's stdio MCP server as the polmem code-graph engine (component A), with the
Polaris freshness fix installed. Project-agnostic: the agent activates a project via Serena's
own `activate_project` tool, so one launcher serves any repo the harness is working in.

stdout is the MCP protocol channel — ALL diagnostics go to stderr (Serena configures this for
stdio transport). Wire this from .mcp.json; on each machine Serena is fetched via uvx (pinned).

Why Serena (not the incumbent codebase-memory): it is the only code-graph of the four benched
(codebase-memory, cgc, Cortex, Serena) that is fresh-by-construction — LSP-live, no persistent
store to serve stale under a green 'ready'. See _polaris audit 2026-07-18-code-graph-selection.
The freshness fix wakes Serena's dormant didChangeWatchedFiles so warm queries stay correct
under edits made outside Serena's own tools (incl. autonomous agents editing concurrently).
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    # Install the freshness monkeypatch BEFORE serena starts (patches Tool.apply_ex).
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import serena_freshness_fix as fix

    fix.install_patch()
    print("[polaris] serena code-graph: freshness fix installed", file=sys.stderr, flush=True)

    from serena.cli import top_level

    # Project-agnostic: no --project. The agent calls activate_project for the repo it's in;
    # the fix's poll returns early until a project is active, so this is safe.
    sys.argv = [
        "serena", "start-mcp-server",
        "--transport", "stdio",
        "--log-level", "ERROR",
        "--enable-web-dashboard", "False",
    ]
    top_level()


if __name__ == "__main__":
    main()
