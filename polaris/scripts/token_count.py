#!/usr/bin/env python3
"""L2-T6 (#405) — the one declared ruler the brief and the pack are both measured with.

THE FORMULA: `(len(text.encode("utf-8")) + 3) // 4` — four UTF-8 BYTES to a token, rounded
up. Nothing about it is learned or sampled: it is arithmetic, so two people measuring the
same brief get the same number, which is the only thing that makes «under 1.500 tokens» an
acceptance criterion rather than an impression.

**Bytes, not characters.** An Italian decision title is full of two-byte characters, and a
counter that reads characters under-reports every non-ASCII brief it will ever measure —
the direction that matters, since a budget that under-reports never fires.

**The same arithmetic the pack is already billed with.** `contextpack_receipt._estimate`
and `contextpack._area` both charge `(len(...) + 3) // 4`. Adding a second, better ruler
here would mean the 1.500 of the brief and the 4.000 of the pack are measured on different
scales, and nobody could add them up. One ruler, even where a tokenizer would be closer.

It ships with the resolver (`_standard/sync_scripts.py`)."""
from __future__ import annotations

import sys
from pathlib import Path

BYTES_PER_TOKEN = 4


def tokens(text: str) -> int:
    """The declared count. See the module docstring for the formula and why it is this one."""
    return (len(text.encode("utf-8")) + BYTES_PER_TOKEN - 1) // BYTES_PER_TOKEN


def main() -> int:
    """`token_count.py [path]` — a file, or stdin. A path that cannot be read is exit 2."""
    args = sys.argv[1:]
    if not args:
        print(tokens(sys.stdin.read()))
        return 0
    try:
        text = Path(args[0]).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"UNREADABLE: {args[0]}: {exc.strerror or exc}", file=sys.stderr)
        return 2
    print(tokens(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
