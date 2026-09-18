#!/usr/bin/env python3
"""The declaration channel for a prose-only body edit, and the gate on the list itself.

`change_gate.py` has always answered a prose-only change with exit 3 and the sentence
"declare whether behaviour moved", while accepting no declaration of any kind: `--help` had
no flag, and CI runs the gate nude under `bash -e`. Redacting three words from a body was
unmergeable by any route. This is the channel that makes the demand payable — one line in
`_standard/prose.allow`, in the grammar of `_standard/nonconforming.allow` with a pin added:

    <slug> <sha256-16 of the body> : why behaviour did not move

The pin is the whole difference between a declaration and a switch: an unpinned "yes"
excuses every future edit of that door, a pinned one dies the next time the body moves.

Two readers, on purpose, failing in opposite directions:
  * `declared()` runs at gate time and is fail-closed — a line it cannot parse declares
    nothing, so a broken waiver never widens into a wildcard for the whole skill;
  * `--check <suite>` is the gate on the list, and there a line that excuses nothing is red:
    unparsable, placeholder reason, slug not in the suite, or a pin no body still hashes to.
    Without it the list would only grow, and the shrink rule would live where
    SKILL-STANDARD.md forbids it — in prose, as a reminder.

    prose_declaration.py --check <skills-suite>
    prose_declaration.py --selfcheck

Exit: 0 PASS · 1 FAIL · 2 usage. Stdlib only, no network, no pip.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import PLACEHOLDER, body, frontmatter  # noqa: E402 — one implementation each

PROSE_ALLOW = "prose.allow"
DECLARATION = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s+([0-9a-f]{16})\s*:(.*)$")


def body_sha(text: str) -> str:
    """The pin: the body only, so the frontmatter — version bumps included — cannot move it."""
    return hashlib.sha256(body(text).encode()).hexdigest()[:16]


def allow_path(suite: Path) -> Path:
    return suite / "_standard" / PROSE_ALLOW


def parse(line: str) -> tuple[str, str] | None:
    """(slug, pin) for a line that really declares something, else None.

    A reason of "." or "TODO" is not a reason — that is the rule SKILL-STANDARD.md says cost
    16 skills out of 16, and the cheapest way this list could have become a switch."""
    m = DECLARATION.match(line)
    return None if not m or PLACEHOLDER.match(m.group(3)) else (m.group(1), m.group(2))


def declarations(path: Path) -> dict[str, set[str]]:
    """slug -> the body hashes declared for it. Fail-closed: what does not parse is absent."""
    out: dict[str, set[str]] = {}
    for line in (path.read_text().splitlines() if path.exists() else []):
        entry = parse(line)
        if entry:
            out.setdefault(entry[0], set()).add(entry[1])
    return out


def declared(skill: Path, new: str) -> tuple[bool, str]:
    """A prose-only edit clears only when a line names THIS skill and THIS body.

    The message carries the exact line to paste, hash included, and the list it actually
    read: the path is derived from `--skill`, so a gate run by hand against a copy elsewhere
    honours that copy's list, and a green whose provenance is not printed is not evidence.
    CI pins the path; this line is what lets a reader tell the two apart."""
    slug = frontmatter(new).get("name", skill.name)
    sha, allow = body_sha(new), allow_path(skill.parent)
    if sha in declarations(allow).get(slug, set()):
        return True, f"prose declared for body {sha} in {allow}"
    return False, (f"prose-only change is not declared — add the line "
                   f"`{slug} {sha}: <why behaviour did not move>` to {allow}")


def line_error(suite: Path, num: int, line: str) -> str | None:
    """The three ways a line stops excusing anything. Same shape as the sibling allowlist:
    the list may only shrink, so a row that no longer covers a real case is red, not inert."""
    entry = parse(line)
    if not entry:
        return (f"{PROSE_ALLOW}:{num}: expected `<slug> <16 hex> : reason` with a reason "
                "written out — a declaration without one is a switch")
    slug, pin = entry
    target = suite / slug / "SKILL.md"
    if not target.is_file():
        return f"{PROSE_ALLOW}:{num}: {slug!r} is not a skill in this suite — stale row, remove it"
    if body_sha(target.read_text()) != pin:
        return (f"{PROSE_ALLOW}:{num}: {slug!r} now hashes to {body_sha(target.read_text())}, "
                f"not {pin} — the row excuses nothing, remove it")
    return None


def check(suite: Path) -> list[str]:
    """Every declaration still names a live skill and a body that is really on disk."""
    path = allow_path(suite)
    if not path.is_file():
        return [f"{path} is missing — an absent list is not an empty one (SKILL-STANDARD rule 1)"]
    errs = []
    for num, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        line = raw.strip()
        if line and not line.startswith("#"):
            errs.append(line_error(suite, num, line))
    return [e for e in errs if e]


SKILL_TEXT = "---\nname: d\ndescription: t\nversion: 0.1.0\n---\n\n# d\n\nProse only.\n"


def selfcheck_reads(suite: Path, sha: str) -> None:
    """B10 in miniature: what parses, what does not, and what a pin cannot outlive."""
    assert parse(f"d {sha}: client names replaced by placeholders") == ("d", sha)
    for reason in ("", " ", " .", " ...", " TODO", " fixme"):
        assert parse(f"d {sha}:{reason}") is None, reason
    assert parse(f"d {sha[:8]}: real reason") is None, "a pin must be a full 16-hex body hash"
    assert parse(f"# d {sha}: real reason") is None, "a comment declares nothing"
    allow = allow_path(suite)
    assert declarations(allow) == {}, "an absent list declares nothing"
    allow.write_text(f"# head\nd {sha}: real reason\n")
    assert declarations(allow) == {"d": {sha}}, declarations(allow)
    assert declared(suite / "d", SKILL_TEXT)[0]
    moved = SKILL_TEXT + "\nAnother sentence.\n"
    ok, note = declared(suite / "d", moved)
    assert not ok and body_sha(moved) in note, "a declaration must not outlive its body"


def selfcheck() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        suite = Path(td) / "skills-suite"
        (suite / "_standard").mkdir(parents=True)
        (suite / "d").mkdir()
        (suite / "d" / "SKILL.md").write_text(SKILL_TEXT)
        sha, allow = body_sha(SKILL_TEXT), allow_path(suite)
        assert check(suite) and "missing" in check(suite)[0], "absent is not empty"
        selfcheck_reads(suite, sha)
        assert not check(suite), check(suite)
        allow.write_text(f"d {sha}: .\n")
        assert "switch" in check(suite)[0], "a placeholder reason is red"
        allow.write_text(f"ghost {sha}: real reason\n")
        assert "stale row" in check(suite)[0]
        (suite / "d" / "SKILL.md").write_text(SKILL_TEXT + "\nAnother sentence.\n")
        allow.write_text(f"d {sha}: real reason\n")
        assert "excuses nothing" in check(suite)[0], "a dead pin must be pruned, not kept"
    print("SELFCHECK OK — 10 branches: parsed, placeholder reason (B10), short pin, comment, "
          "absent list, present list, matching body, stale pin (B10), ghost slug, dead row")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--selfcheck"]:
        return selfcheck()
    if argv[:1] != ["--check"] or len(argv) != 2:
        print(__doc__.split("    prose_declaration.py")[1], file=sys.stderr)
        return 2
    errs = check(Path(argv[1]))
    print("\n".join(errs) if errs else
          f"{PROSE_ALLOW}: every declaration still names a live skill and the body on disk")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
