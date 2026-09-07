#!/usr/bin/env python3
"""License gate for `references/martin-boundary-rules.md` — issue polaris-os#87.

The Martin rules were rewritten from scratch; the chapter files of the `martin-clean-architecture`
skill are copyrighted study material and must never be quoted into a publishable perimeter.
Mechanical proof, not a promise: build 12-word shingles from both sides and fail loud on any
overlap, naming the line. Stdlib only.

    shingle_check.py [--target FILE] [--chapters-dir DIR] [--n 12]
    shingle_check.py --selfcheck
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

DEFAULT_TARGET = Path(__file__).resolve().parent.parent / "references" / "martin-boundary-rules.md"
DEFAULT_CHAPTERS = [
    Path.home() / ".claude" / "skills" / "martin-clean-architecture" / "chapters",
    Path.home() / ".agents" / "skills" / "martin-clean-architecture" / "chapters",
]
WORD = re.compile(r"[a-z0-9']+")


def words(line: str) -> list[str]:
    return WORD.findall(line.lower())


def shingles(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def chapter_shingles(chapters_dir: Path, n: int) -> set[tuple[str, ...]]:
    out: set[tuple[str, ...]] = set()
    for f in sorted(chapters_dir.glob("*.md")):
        tokens = words(f.read_text(errors="replace"))
        out |= shingles(tokens, n)
    return out


def find_matches(target_text: str, forbidden: set[tuple[str, ...]], n: int) -> list[tuple[int, str]]:
    """One match per offending line, with the line number — a run-position match without a
    line number is not actionable for someone fixing it."""
    hits = []
    for lineno, line in enumerate(target_text.splitlines(), start=1):
        toks = words(line)
        for sh in shingles(toks, n):
            if sh in forbidden:
                hits.append((lineno, " ".join(sh)))
                break  # one report per line is enough to act on
    return hits


def resolve_chapters_dir(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_dir() else None
    for candidate in DEFAULT_CHAPTERS:
        if candidate.is_dir():
            return candidate
    return None


def selfcheck() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        chapters = Path(td) / "chapters"
        chapters.mkdir()
        (chapters / "ch01.md").write_text(
            "Source code dependencies must point only in one direction, toward higher "
            "level policies, and that discipline is the whole of the dependency rule.\n"
        )
        forbidden = chapter_shingles(chapters, 12)
        assert forbidden, "fixture produced no shingles — test is void"

        # Case 1: clean text -> no matches
        clean = "This paragraph talks about boundaries in completely different words of its own."
        assert find_matches(clean, forbidden, 12) == []

        # Case 2: a 15-word run copied verbatim from the fixture -> caught, with a line number
        planted = (
            "line one is safe\n"
            "Source code dependencies must point only in one direction, toward higher "
            "level policies, and that discipline is the whole of the dependency rule extra words\n"
            "line three is safe too\n"
        )
        hits = find_matches(planted, forbidden, 12)
        assert hits and hits[0][0] == 2, hits

        # Case 3: removed -> clean again
        restored = "line one is safe\nthis line was rewritten in different words entirely\nline three is safe too\n"
        assert find_matches(restored, forbidden, 12) == []

    print("SELFCHECK OK — clean text passes, a planted 15-word run is caught with its line "
          "number, removing it clears the gate")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    p.add_argument("--chapters-dir", type=Path, default=None)
    p.add_argument("--n", type=int, default=12)
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()

    chapters_dir = resolve_chapters_dir(a.chapters_dir)
    if chapters_dir is None:
        print("chapters dir not found on this machine — NOT VERIFIED (not the same as clean). "
              "Pass --chapters-dir, or run where martin-clean-architecture is installed.")
        return 2
    if not a.target.is_file():
        print(f"target not found: {a.target}")
        return 2

    forbidden = chapter_shingles(chapters_dir, a.n)
    hits = find_matches(a.target.read_text(errors="replace"), forbidden, a.n)
    if hits:
        print(f"{len(hits)} line(s) share a {a.n}-word run with the chapter files:")
        for lineno, run in hits:
            print(f"  ✗ {a.target}:{lineno} — {run!r}")
        return 1
    print(f"0 shared {a.n}-word runs between {a.target.name} and {chapters_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
