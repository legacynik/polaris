#!/usr/bin/env python3
"""#320 — a skill that writes declares kinds the host output map has, and invokes only skills that exist.

    skill_outputs_check.py --skills <root> [--skills <root2>] --config config.yml [--known <root>]

Exit 1 with one line per defect. `--known` adds roots whose skill names count as existing
(e.g. the Polaris suite when checking the Osmani fork) without being checked themselves.
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

BLOCK = "## Where this goes"
PRODUCES = re.compile(r"This skill produces: \*\*(.+?)\*\*")


def outputs_kinds(config: Path) -> set[str]:
    text = config.read_text(errors="replace")
    m = re.search(r"^outputs:\n((?:[ \t]+.*\n?)+)", text, re.M)
    return {ln.strip().split(":")[0] for ln in m.group(1).splitlines() if ln.strip() and not ln.strip().startswith("#")} if m else set()


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    return dict(re.findall(r"^([a-z][a-z0-9_-]*):\s*(.*)$", text[4:end], re.M)) if end > 0 else {}


def invokes_of(fm: dict[str, str]) -> list[str]:
    raw = fm.get("invokes", "").strip().strip("[]")
    return [x.strip().strip("`'\"") for x in raw.split(",") if x.strip()]


def kinds_of(text: str) -> list[str] | None:
    m = PRODUCES.search(text)
    if not m:
        return None
    if m.group(1).lower().startswith("none"):
        return []
    flat = re.sub(r"\([^)]*\)", "", m.group(1))  # drop parenthesised notes before splitting
    return [part.strip().split(" ")[0] for part in flat.split(",") if part.strip()]


def check_skill(path: Path, kinds_ok: set[str], known: set[str]) -> list[str]:
    name, text = path.parent.name, path.read_text(errors="replace")
    if BLOCK not in text:
        return [f"{name}: no 'Where this goes' block"]
    kinds = kinds_of(text)
    err = [f"{name}: block present but no 'This skill produces' line"] if kinds is None else []
    err += [f"{name}: kind '{k}' not in outputs map" for k in (kinds or []) if k not in kinds_ok]
    err += [f"{name}: invokes unknown skill '{s}'" for s in invokes_of(frontmatter(text)) if s not in known]
    return err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills", action="append", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--known", action="append", default=[], type=Path)
    ap.add_argument("--allow-missing", type=Path, help="skills allowed to lack the block for now; the list only shrinks")
    a = ap.parse_args()
    files = [p for root in a.skills for p in sorted(root.glob("*/SKILL.md"))]
    known = {p.parent.name for p in files} | {p.parent.name for r in a.known for p in r.glob("*/SKILL.md")}
    kinds_ok = outputs_kinds(a.config)
    allowed = set(a.allow_missing.read_text().split()) if a.allow_missing and a.allow_missing.is_file() else set()
    errors = [e for p in files for e in check_skill(p, kinds_ok, known)
              if not (p.parent.name in allowed and e.endswith("no 'Where this goes' block"))]
    errors += [f"{s}: allowed as missing but now has the block — remove it from the allowlist"
               for s in allowed if any(p.parent.name == s and BLOCK in p.read_text(errors="replace") for p in files)]
    for e in errors:
        print(e)
    print(f"skill_outputs_check: {len(files)} skills, {len(errors)} defects, kinds={sorted(kinds_ok)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
