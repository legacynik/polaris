#!/usr/bin/env python3
"""critic_gate — the CLI over critic_rules. Exit 0 pass, 1 fail, 2 unusable input.

The rules themselves live in critic_rules.py, a single importable source of truth.

Pure stdlib. Exit 0 pass, 1 fail (reasons on stdout), 2 unusable input.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from critic_rules import validate  # noqa: F401  (re-exported for callers)


class Unusable(SystemExit):
    """Exit 2: the gate could not read the report. Never confused with a clean pass."""

    def __init__(self, message: str) -> None:
        print(f"UNUSABLE: {message}", file=sys.stderr)
        super().__init__(2)


def load(path: Path) -> object:
    if not path.is_file():
        raise Unusable(f"no such report: {path}")
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        raise Unusable(f"cannot read report ({exc.strerror}): {path}") from exc
    if not text:
        raise Unusable(f"empty report: {path}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise Unusable(f"not JSON ({exc.msg}): {path}") from exc


def run(path: Path) -> int:
    reasons = validate(load(path), path.resolve().parent)
    if reasons:
        print(f"FAIL — {len(reasons)} reason(s)")
        for reason in reasons:
            print(f"  - {reason}")
        return 1
    print("PASS")
    return 0


def selfcheck() -> int:
    """Delegated to the sibling module so this file stays under the size gate."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from critic_gate_selfcheck import run_branches

    return run_branches()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--validate", type=Path)
    group.add_argument("--selfcheck", action="store_true")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if not args.validate:
        parser.error("--validate <report.json> or --selfcheck")
    return run(args.validate)


if __name__ == "__main__":
    sys.exit(main())
