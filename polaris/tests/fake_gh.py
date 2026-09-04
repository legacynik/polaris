"""Minimal stand-in for the `gh` CLI, so the merge-truth gate is tested without a network.

Same shape as `fake_bundle.py` does for the memory bundle: the real binary is not this package's
to ship, and a test that reaches GitHub proves the network, not the gate. The scenario arrives in
`POLARIS_FAKE_GH` as JSON — `{"pr": {"<n>": {...}}, "issue": {"<n>": {...}}}` — and a number whose
value is the string `"__error__"` fails the way a rate limit does: exit 1, nothing on stdout.
"""
import json
import os
import sys


def _fields(argv: list[str]) -> list[str]:
    """`--json a,b,c` → the field names gh would emit, in the order asked."""
    at = argv.index("--json") + 1 if "--json" in argv else 0
    return argv[at].split(",") if at else []


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) < 3 or argv[1] != "view":
        print(f"unknown command: {' '.join(argv)}", file=sys.stderr)
        return 1
    known = json.loads(os.environ.get("POLARIS_FAKE_GH", "{}")).get(argv[0], {})
    facts = known.get(argv[2])
    if facts is None:
        print(f"no {argv[0]} found for {argv[2]}", file=sys.stderr)
        return 1
    if facts == "__error__":
        print("API rate limit exceeded", file=sys.stderr)
        return 1
    print(json.dumps({k: facts.get(k) for k in _fields(argv)} if _fields(argv) else facts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
