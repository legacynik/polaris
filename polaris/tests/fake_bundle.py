# polaris/tests/fake_bundle.py
"""Minimal stand-in for scripts/polaris_memory_repo.py — same JSON-RPC envelope
(initialize / tools/call) AND the same remember contract: requires title+body,
returns the error string "error: 'title' and 'body' are required." with
isError:False when either is missing — this mirrors a real false-success bug
found in the live bundle (Preventivi AI, scripts/polaris_memory_repo.py,
discovered 2026-07-08 during Task 2's REAL step; see task-2-report.md).
recall accepts the magic query "__force_error__" to exercise the
isError:true → shim exit 1 path end-to-end."""
import json
import sys


def _result(mid, payload):
    return {"jsonrpc": "2.0", "id": mid, "result": payload}


def _recall_reply(args: dict) -> tuple[str, bool]:
    if args.get("query") == "__force_error__":
        return "boom", True
    return f"RECALL[{args.get('query')}] top={args.get('top', 5)}", False


def _remember_reply(args: dict) -> tuple[str, bool]:
    title, body = args.get("title"), args.get("body")
    if not title or not body:
        return "error: 'title' and 'body' are required.", False
    return f"REMEMBERED[title={title}]", False


def _tool_reply(name, args: dict) -> tuple[str, bool]:
    if name == "recall":
        return _recall_reply(args)
    if name == "remember":
        return _remember_reply(args)
    return f"unknown tool: {name}", True


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
            text, err = _tool_reply(p.get("name"), p.get("arguments") or {})
            out = _result(mid, {"content": [{"type": "text", "text": text}], "isError": err})
        else:
            continue
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
