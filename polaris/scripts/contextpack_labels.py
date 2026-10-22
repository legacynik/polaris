#!/usr/bin/env python3
"""Issue labels -> declared domain ids, for the ContextPack (#1288, 2026-09-29).

A product repo's `domain:<x>` label is the area `<repo>.<x>` its DOMAIN.md declares; the
vault keeps its hand table in contextpack.py. Kept out of contextpack.py, which only shrinks.
"""
from __future__ import annotations

import re
from pathlib import Path

import check_context_backbone as cbb


def known_domains(root: Path) -> set[str]:
    dom = cbb._frontmatter(root / "DOMAIN.md")
    return {d["domain_id"] for d in dom.get("domains", [])}


def repo_labels(root: Path) -> set[str]:
    """The labels the repository declares in `.github/DOMAINS.yml`, one per line."""
    path = root / ".github" / "DOMAINS.yml"
    if not path.is_file():
        return set()
    return set(re.findall(r"^\s*-\s*([a-z0-9][a-z0-9_-]*)\s*$", path.read_text(), re.M))


def derived_labels(root: Path, known: set[str]) -> dict[str, list[str]]:
    """A listed label `<x>` answers to every declared id `<repo>.<x>`; nothing else is a label."""
    listed, out = repo_labels(root), {}
    for domain in sorted(known):
        label = domain.partition(".")[2]
        if label in listed:
            out.setdefault(label, []).append(domain)
    return out
