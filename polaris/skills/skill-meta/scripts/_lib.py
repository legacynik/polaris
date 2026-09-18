#!/usr/bin/env python3
"""Shared primitives for the skill-meta script bundle — ONE implementation each.

Born from the 2026-08-18 /simplify pass: four review angles found three divergent
frontmatter parsers (one of which matched `description:` anywhere in the file, not just
the frontmatter block), two eval-corpus unwrappers (one with a silent dict-flows-into-len
bug), and a sys.path hack that needed its own selfcheck to be trusted. Everything here is
the single source; sibling scripts import from this module.

Import contract: entry scripts insert their own directory once —
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _lib import ...
That single insert is the whole loading story; no by-path-load compensation tests.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path


# A field satisfied by "TODO", "." or nothing is not satisfied — the cheapest bypass there
# is, and the rule SKILL-STANDARD.md says cost 16 skills out of 16. Lives here because two
# gates now need the same answer: the eval corpus and the prose declaration.
PLACEHOLDER = re.compile(r"^\s*(todo|tbd|\.{1,3}|xxx|fixme)?\s*$", re.I)


def frontmatter(text: str) -> dict[str, str]:
    """Frontmatter fields, bounded to the leading ---...--- block ONLY.

    Never search the whole file: a body table containing a `description:` cell must not
    shadow the real trigger text (the exact defect the old collision_check parser had).
    """
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out: dict[str, str] = {}
    for line in (m.group(1).splitlines() if m else []):
        kv = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if kv:
            out[kv.group(1)] = kv.group(2).strip().strip("'\"")
    return out


def body(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)


def desc_sha(text: str) -> str:
    """Hash the trigger, not the status badge. The `◇`/`✦` mark is prefixed to the
    description at promotion, so hashing it would void every routing measurement at
    exactly the moment nobody wants to spend 18 dispatches again — and the mark is not
    trigger text. Everything after it is."""
    desc = frontmatter(text).get("description", "").lstrip("◇✦ ")
    return hashlib.sha256(desc.encode()).hexdigest()[:16]


def load_eval_cases(path: Path) -> tuple[list, dict, str]:
    """One unwrapper for the eval-corpus shape: `{skill?, dimensions?, cases: [...]}` or a
    bare list. Returns (cases, meta, err). LOUD on malformation — the old inline variant
    fell back to the whole dict, whose len() silently counted keys instead of cases."""
    try:
        raw = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001 — a gate reports, it does not crash
        return [], {}, f"{path.name}: unreadable ({e})"
    if isinstance(raw, list):
        return raw, {}, ""
    if isinstance(raw, dict):
        cases = raw.get("cases")
        if isinstance(cases, list):
            return cases, {k: v for k, v in raw.items() if k != "cases"}, ""
        return [], {}, f"{path.name}: dict without a 'cases' list — malformed corpus"
    return [], {}, f"{path.name}: neither list nor object"


def selfcheck() -> int:
    fm = frontmatter("---\nname: x\ndescription: 'a b'\n---\nbody\ndescription: DECOY\n")
    assert fm["description"] == "a b", "frontmatter must be block-bounded, not whole-file"
    assert body("---\nk: v\n---\nrest") == "rest"
    assert desc_sha("---\ndescription: ◇ t\n---\n") == desc_sha("---\ndescription: t\n---\n"), \
        "mark must not move the pin"
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d, "c.json")
        p.write_text('{"skill": "s", "cases": [1, 2]}')
        cases, meta, err = load_eval_cases(p)
        assert cases == [1, 2] and meta.get("skill") == "s" and not err
        p.write_text('{"skill": "s"}')
        cases, _, err = load_eval_cases(p)
        assert cases == [] and "malformed" in err, "dict without cases must FAIL loud"
        p.write_text("[1]")
        assert load_eval_cases(p)[0] == [1]
    assert all(PLACEHOLDER.match(s) for s in ("", "   ", "TODO", ".", "...", "fixme"))
    assert not PLACEHOLDER.match("client name replaced by a placeholder")
    print("_lib selfcheck: OK (5 groups)")
    return 0


if __name__ == "__main__":
    import sys as _sys
    if "--selfcheck" not in _sys.argv[1:]:
        print("usage: _lib.py --selfcheck (shared library — the selfcheck is its only CLI)")
        raise SystemExit(2)
    raise SystemExit(selfcheck())
