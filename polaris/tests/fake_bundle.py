# polaris/tests/fake_bundle.py
"""Minimal stand-in for scripts/polaris_memory_repo.py — same JSON-RPC surface
(verified against the live bundle 2026-07-08): initialize / tools/call."""
import json
import sys


def _result(mid, payload):
    return {"jsonrpc": "2.0", "id": mid, "result": payload}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method, mid = msg.get("method"), msg.get("id")
        if method == "initialize":
            out = _result(mid, {"protocolVersion": "2025-06-18",
                                "capabilities": {"tools": {}},
                                "serverInfo": {"name": "fake-bundle", "version": "0"}})
        elif method in ("notifications/initialized", "initialized"):
            continue
        elif method == "tools/call":
            p = msg.get("params") or {}
            name, args = p.get("name"), p.get("arguments") or {}
            if name == "recall":
                text, err = f"RECALL[{args.get('query')}] top={args.get('top', 5)}", False
            elif name == "remember":
                text, err = f"REMEMBERED[{args.get('text')}]", False
            else:
                text, err = f"unknown tool: {name}", True
            out = _result(mid, {"content": [{"type": "text", "text": text}], "isError": err})
        else:
            continue
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
