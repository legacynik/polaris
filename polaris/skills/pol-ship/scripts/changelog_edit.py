#!/usr/bin/env python3
"""CHANGELOG discipline: never blind-overwrite, only insert at a known anchor.

Never `Write`s the whole file. Finds the anchor line by exact string match and
inserts one bullet after it; if the anchor is missing, refuses (exit 2) rather
than guessing where the entry belongs — a wrong guess corrupts a file every
future reader trusts. Idempotent: inserting the same bullet twice is a no-op.

    changelog_edit.py --file CHANGELOG.md --bullet "- Fixed X (#42)"
    changelog_edit.py --file CHANGELOG.md --bullet "..." --anchor "## [Unreleased]"
    changelog_edit.py --selfcheck
"""
from __future__ import annotations
import sys, argparse, tempfile
from pathlib import Path

DEFAULT_ANCHOR = "## [Unreleased]"


def insert_entry(text: str, bullet: str, anchor: str = DEFAULT_ANCHOR) -> tuple[str, str]:
    """Returns (new_text, status). status in INSERTED / IDEMPOTENT_SKIP / NO_ANCHOR."""
    bullet = bullet.rstrip("\n")
    if any(line.strip() == bullet.strip() for line in text.splitlines()):
        return text, "IDEMPOTENT_SKIP"
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.rstrip("\n") == anchor:
            insert_at = i + 1
            if insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1  # keep the blank line right after the heading
            new_lines = lines[:insert_at] + [bullet + "\n"] + lines[insert_at:]
            return "".join(new_lines), "INSERTED"
    return text, "NO_ANCHOR"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--bullet")
    ap.add_argument("--anchor", default=DEFAULT_ANCHOR)
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)
    if args.selfcheck:
        return selfcheck()

    path = Path(args.file)
    if not path.exists():
        print(f'{{"status": "NO_FILE", "file": "{path}"}}')
        return 2
    text = path.read_text()
    new_text, status = insert_entry(text, args.bullet, args.anchor)
    if status == "NO_ANCHOR":
        print(f'{{"status": "NO_ANCHOR", "anchor": {args.anchor!r}, "why": "refusing to guess insertion point"}}')
        return 2
    if status == "INSERTED":
        path.write_text(new_text)
    print(f'{{"status": "{status}"}}')
    return 0


def selfcheck() -> int:
    base = "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-01-01\n- initial\n"

    new, status = insert_entry(base, "- Fixed the redaction false positive (#42)")
    assert status == "INSERTED", status
    assert new.splitlines()[4] == "- Fixed the redaction false positive (#42)", new

    new2, status2 = insert_entry(new, "- Fixed the redaction false positive (#42)")
    assert status2 == "IDEMPOTENT_SKIP", status2
    assert new2 == new, "idempotent re-insert must not duplicate or otherwise change the file"

    no_anchor_text = "# Changelog\nnothing here\n"
    new3, status3 = insert_entry(no_anchor_text, "- x")
    assert status3 == "NO_ANCHOR", status3
    assert new3 == no_anchor_text, "must not touch the file when the anchor is missing"

    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "CHANGELOG.md"
        assert main(["--file", str(missing), "--bullet", "- x"]) == 2, "missing file must exit 2, not crash"

        real = Path(td) / "CHANGELOG.md"
        real.write_text(base)
        assert main(["--file", str(real), "--bullet", "- y"]) == 0
        assert "- y" in real.read_text()
        before = real.read_text()
        assert main(["--file", str(real), "--bullet", "- y"]) == 0  # idempotent via CLI too
        assert real.read_text() == before

    print("SELFCHECK OK — INSERTED/IDEMPOTENT_SKIP/NO_ANCHOR/NO_FILE, all as expected, file never blind-overwritten")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
