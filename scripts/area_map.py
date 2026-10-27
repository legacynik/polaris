#!/usr/bin/env python3
"""Regenerate the README map of one documentation area from file frontmatter.

Usage: area_map.py docs/modules/<area>   (rewrites <area>/README.md between the markers)
An agent reads the map, picks by title/status, opens only what it needs. Every .md in the area is
listed, whatever folder it sits in; `archive/` rows are struck through so history stays visible.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

BEGIN, END = "<!-- area-map:begin -->", "<!-- area-map:end -->"
SKIP = {"README.md", "CHANGELOG.md"}


def frontmatter(head: str) -> dict:
    m = re.match(r"---\s*\n(.*?)\n---", head, re.S)
    if not m:
        return {}
    raw = m.group(1).strip()
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except ValueError:
            return {}
    return dict(re.findall(r"^([A-Za-z_]+):\s*\"?(.+?)\"?\s*$", raw, re.M))


def meta(p: Path) -> tuple[str, str, str]:
    head = p.read_text(encoding="utf-8", errors="ignore")[:3000]
    fm = frontmatter(head)
    h1 = re.search(r"^# (.+)$", head, re.M)
    title = str(fm.get("title") or (h1.group(1) if h1 else p.stem)).strip()
    summary = str(fm.get("summary") or fm.get("description") or "")
    return title, str(fm.get("status") or "UNKNOWN"), summary


def rows(area: Path, files: list[Path], strike: bool = False) -> list[str]:
    out = []
    for p in files:
        t, s, d = meta(p)
        rel = p.relative_to(area)
        out.append(f"| ~~[{t}]({rel})~~ | `archived` | was `{s}` |" if strike else f"| [{t}]({rel}) | `{s}` | {d[:90]} |")
    return out


def buckets(area: Path) -> dict[str, list[Path]]:
    b: dict[str, list[Path]] = {}
    for p in sorted(area.rglob("*.md")):
        if p.name in SKIP or p.parent == area:
            continue
        b.setdefault(p.relative_to(area).parts[0], []).append(p)
    return b


def render(area: Path) -> str:
    lines = [BEGIN, "", "## Map (generated — do not edit by hand)", ""]
    for p in sorted(area.glob("*.md")):
        if p.name not in SKIP:
            t, s, _ = meta(p)
            lines.append(f"- canonical: [{t}]({p.name}) `{s}`")
    lines.append("")
    b = buckets(area)
    for sub, files in b.items():
        if sub == "archive":
            continue
        lines += [f"### {sub}/ ({len(files)})", "", "| document | status | summary |", "|---|---|---|", *rows(area, files), ""]
    arch = b.get("archive", [])
    if arch:
        lines += [f"### archive/ ({len(arch)}) — superseded, do not load", "", "| document | status | note |", "|---|---|---|", *rows(area, arch, strike=True), ""]
    else:
        lines += ["archive/: empty", ""]
    return "\n".join(lines + [END])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="area_map.py", description=__doc__.splitlines()[0])
    parser.add_argument("area", type=Path, help="the area folder, e.g. docs/modules/<area>")
    args = parser.parse_args(argv[1:])
    if not args.area.is_dir():
        parser.error(f"not a directory: {args.area} — nothing written")
    area = args.area.resolve()
    readme = area / "README.md"
    body = readme.read_text(encoding="utf-8") if readme.exists() else f"# {area.name}\n\n"
    block = render(area)
    if BEGIN in body and END in body:
        body = body[: body.index(BEGIN)] + block + body[body.index(END) + len(END):]
    else:
        body = body.rstrip() + "\n\n" + block + "\n"
    readme.write_text(body, encoding="utf-8")
    print(f"map written: {readme}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
