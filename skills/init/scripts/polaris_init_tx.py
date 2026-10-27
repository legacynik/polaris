#!/usr/bin/env python3
"""polaris_init_tx.py — `apply` is all-or-nothing, and this is how.

Validation runs last and raises for reasons no precheck sees: a Decision from another
workspace, a path that will not open. Round 1 on #438 found three such endings, each
leaving a half-written backbone on disk, and the scope variant never recovered on a
re-run. Every path `apply` may touch is therefore read BEFORE any of them is written,
and any failure puts all of them back, byte for byte.

Covered by `polaris_init.py --selfcheck`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as backbone  # noqa: E402
from polaris_init_probe import TRIAD, identity  # noqa: E402


def touchable(root: Path) -> list[Path]:
    """Every path `apply` may write, known BEFORE it writes any of them."""
    shadows = [
        root / item["source_id"].removeprefix("source:path:")
        for item in backbone.audit_authorities(root)["findings"]
        if item["code"] == "AUTHORITY_SHADOW"
    ]
    return [root / name for name in TRIAD] + shadows + [
        root / "decisions" / f"DEC-{identity(root)['repo']}-polaris-backbone-001.md",
    ]


def restore(before: dict[Path, bytes | None]) -> None:
    """Put the tree back exactly as it was, down to the directories apply created."""
    for path, original in before.items():
        if original is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(original)
    for path in sorted({p.parent for p in before}, key=lambda p: -len(p.parts)):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
